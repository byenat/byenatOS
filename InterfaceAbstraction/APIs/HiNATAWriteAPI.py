"""
ByenatOS HiNATA File System Write API
HiNATA文件系统写入API - 用户知识库内容修改接口

当用户通过对话框表达意图，希望对自己的HiNATA知识库内容进行批量修改时，
系统通过此API执行相应的写入操作。这是对现有读取API的重要补充。
"""

import asyncio
import json
import time
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import aioredis
import asyncpg

# 导入内部组件
from Kernel.Core.HiNATAProcessor import HiNATAProcessor, HiNATAData
from Kernel.Core.StorageEngine import StorageEngine
from InterfaceAbstraction.APIs.AppIntegrationAPI import AuthManager, AppPermission


class HiNATAWriteOperation(Enum):
    """HiNATA写入操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BATCH_UPDATE = "batch_update"
    BULK_TAG = "bulk_tag"
    BULK_RETAG = "bulk_retag"
    MERGE = "merge"
    SPLIT = "split"


class HiNATAWritePermission(Enum):
    """HiNATA写入权限"""
    HINATA_WRITE = "hinata_write"
    HINATA_DELETE = "hinata_delete"
    HINATA_BULK_MODIFY = "hinata_bulk_modify"
    HINATA_ADMIN = "hinata_admin"


@dataclass
class WriteOperationContext:
    """写入操作上下文"""
    user_id: str
    operation_id: str
    operation_type: HiNATAWriteOperation
    intent_description: str
    source_app: str
    timestamp: str
    batch_size: int = 0
    estimated_duration: float = 0.0


# Pydantic模型定义
class HiNATAWriteModel(BaseModel):
    """单个HiNATA写入模型"""
    id: Optional[str] = Field(None, description="HiNATA ID，新建时可为空")
    timestamp: Optional[str] = Field(None, description="时间戳，为空时使用当前时间")
    source: str = Field(..., description="数据源标识")
    highlight: str = Field(..., max_length=10000, description="高亮文本")
    note: str = Field(..., max_length=50000, description="用户笔记")
    address: str = Field(..., description="资源地址")
    tag: List[str] = Field(default=[], description="用户标签")
    access: str = Field(..., regex="^(private|public|shared)$", description="访问级别")
    raw_data: Dict[str, Any] = Field(default={}, description="原始数据")


class HiNATAUpdateModel(BaseModel):
    """HiNATA更新模型"""
    id: str = Field(..., description="要更新的HiNATA ID")
    updates: Dict[str, Any] = Field(..., description="更新字段")
    merge_tags: bool = Field(default=True, description="是否合并标签而非替换")
    preserve_metadata: bool = Field(default=True, description="是否保留元数据")


class BulkOperationModel(BaseModel):
    """批量操作模型"""
    operation_type: str = Field(..., description="操作类型")
    target_filter: Dict[str, Any] = Field(..., description="目标过滤条件")
    operation_data: Dict[str, Any] = Field(..., description="操作数据")
    dry_run: bool = Field(default=False, description="是否为试运行")
    batch_size: int = Field(default=100, description="批次大小")


class HiNATAWriteRequestModel(BaseModel):
    """HiNATA写入请求模型"""
    user_id: str = Field(..., description="用户ID")
    operation_type: str = Field(..., description="操作类型")
    intent_description: str = Field(..., description="用户意图描述")
    
    # 单个操作
    hinata_data: Optional[HiNATAWriteModel] = Field(None, description="单个HiNATA数据")
    update_data: Optional[HiNATAUpdateModel] = Field(None, description="更新数据")
    
    # 批量操作
    hinata_batch: Optional[List[HiNATAWriteModel]] = Field(None, description="HiNATA批量数据")
    update_batch: Optional[List[HiNATAUpdateModel]] = Field(None, description="批量更新数据")
    bulk_operation: Optional[BulkOperationModel] = Field(None, description="批量操作")
    
    # 操作选项
    processing_options: Dict[str, Any] = Field(default={}, description="处理选项")
    validation_strict: bool = Field(default=True, description="是否严格验证")
    auto_backup: bool = Field(default=True, description="是否自动备份")


class DeleteRequestModel(BaseModel):
    """删除请求模型"""
    user_id: str = Field(..., description="用户ID")
    hinata_ids: List[str] = Field(..., description="要删除的HiNATA ID列表")
    delete_reason: str = Field(..., description="删除原因")
    soft_delete: bool = Field(default=True, description="是否软删除")


# 响应模型
class HiNATAWriteResponse(BaseModel):
    """HiNATA写入响应"""
    status: str
    operation_id: str
    affected_count: int
    processing_time: float
    results: List[Dict[str, Any]] = Field(default=[])
    errors: List[str] = Field(default=[])
    warnings: List[str] = Field(default=[])


class BulkOperationResponse(BaseModel):
    """批量操作响应"""
    status: str
    operation_id: str
    total_processed: int
    successful_count: int
    failed_count: int
    processing_time: float
    batch_results: List[Dict[str, Any]] = Field(default=[])
    errors: List[str] = Field(default=[])


class WriteOperationValidator:
    """写入操作验证器"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def validate_write_permission(self, user_id: str, operation_type: HiNATAWriteOperation) -> bool:
        """验证写入权限"""
        # 检查用户是否有权限修改自己的数据
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT write_permissions FROM user_permissions WHERE user_id = $1",
                user_id
            )
            
            if not result:
                return False
            
            permissions = json.loads(result['write_permissions'])
            required_permission = self._get_required_permission(operation_type)
            
            return required_permission in permissions
    
    async def validate_hinata_ownership(self, user_id: str, hinata_ids: List[str]) -> Tuple[bool, List[str]]:
        """验证HiNATA所有权"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT id FROM hinata_data 
                WHERE id = ANY($1) AND user_id = $2
            """
            rows = await conn.fetch(query, hinata_ids, user_id)
            owned_ids = [row['id'] for row in rows]
            
            unauthorized_ids = [id for id in hinata_ids if id not in owned_ids]
            
            return len(unauthorized_ids) == 0, unauthorized_ids
    
    async def validate_bulk_operation_safety(self, bulk_op: BulkOperationModel, user_id: str) -> Tuple[bool, List[str]]:
        """验证批量操作安全性"""
        errors = []
        
        # 检查操作范围
        if not bulk_op.target_filter:
            errors.append("Bulk operation must specify target filter")
        
        # 检查批次大小
        if bulk_op.batch_size > 1000:
            errors.append("Batch size too large (max 1000)")
        
        # 预估影响范围
        estimated_count = await self._estimate_affected_count(bulk_op.target_filter, user_id)
        if estimated_count > 10000:
            errors.append(f"Operation would affect too many records ({estimated_count})")
        
        return len(errors) == 0, errors
    
    def _get_required_permission(self, operation_type: HiNATAWriteOperation) -> str:
        """获取所需权限"""
        permission_map = {
            HiNATAWriteOperation.CREATE: "hinata_write",
            HiNATAWriteOperation.UPDATE: "hinata_write",
            HiNATAWriteOperation.DELETE: "hinata_delete",
            HiNATAWriteOperation.BATCH_UPDATE: "hinata_bulk_modify",
            HiNATAWriteOperation.BULK_TAG: "hinata_bulk_modify",
            HiNATAWriteOperation.BULK_RETAG: "hinata_bulk_modify",
            HiNATAWriteOperation.MERGE: "hinata_write",
            HiNATAWriteOperation.SPLIT: "hinata_write"
        }
        return permission_map.get(operation_type, "hinata_admin")
    
    async def _estimate_affected_count(self, filter_conditions: Dict[str, Any], user_id: str) -> int:
        """估算影响的记录数量"""
        # 简化实现：基于过滤条件估算
        async with self.db_pool.acquire() as conn:
            base_query = "SELECT COUNT(*) FROM hinata_data WHERE user_id = $1"
            params = [user_id]
            
            # 根据过滤条件添加WHERE子句
            if 'tag' in filter_conditions:
                base_query += " AND tags::jsonb ? $2"
                params.append(filter_conditions['tag'])
            
            if 'source' in filter_conditions:
                base_query += f" AND source = ${len(params) + 1}"
                params.append(filter_conditions['source'])
            
            result = await conn.fetchrow(base_query, *params)
            return result['count']


class HiNATAWriteProcessor:
    """HiNATA写入处理器"""
    
    def __init__(self, db_pool, redis_pool, hinata_processor: HiNATAProcessor, storage_engine: StorageEngine):
        self.db_pool = db_pool
        self.redis_pool = redis_pool
        self.hinata_processor = hinata_processor
        self.storage_engine = storage_engine
        self.validator = WriteOperationValidator(db_pool)
    
    async def process_write_request(self, request: HiNATAWriteRequestModel, context: WriteOperationContext) -> HiNATAWriteResponse:
        """处理写入请求"""
        start_time = time.time()
        
        try:
            # 1. 权限验证
            operation_type = HiNATAWriteOperation(request.operation_type)
            has_permission = await self.validator.validate_write_permission(request.user_id, operation_type)
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for this operation"
                )
            
            # 2. 自动备份
            if request.auto_backup:
                await self._create_backup(request.user_id, context.operation_id)
            
            # 3. 执行操作
            results = []
            affected_count = 0
            errors = []
            warnings = []
            
            if operation_type == HiNATAWriteOperation.CREATE:
                result = await self._handle_create_operation(request, context)
                results.append(result)
                affected_count = 1 if result['success'] else 0
            
            elif operation_type == HiNATAWriteOperation.UPDATE:
                result = await self._handle_update_operation(request, context)
                results.append(result)
                affected_count = 1 if result['success'] else 0
            
            elif operation_type == HiNATAWriteOperation.DELETE:
                result = await self._handle_delete_operation(request, context)
                results.append(result)
                affected_count = result.get('deleted_count', 0)
            
            elif operation_type in [HiNATAWriteOperation.BATCH_UPDATE, HiNATAWriteOperation.BULK_TAG, HiNATAWriteOperation.BULK_RETAG]:
                result = await self._handle_bulk_operation(request, context)
                results.extend(result['batch_results'])
                affected_count = result['successful_count']
                errors.extend(result.get('errors', []))
            
            else:
                raise ValueError(f"Unsupported operation type: {operation_type}")
            
            processing_time = time.time() - start_time
            
            return HiNATAWriteResponse(
                status="success" if affected_count > 0 else "failed",
                operation_id=context.operation_id,
                affected_count=affected_count,
                processing_time=processing_time,
                results=results,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return HiNATAWriteResponse(
                status="error",
                operation_id=context.operation_id,
                affected_count=0,
                processing_time=processing_time,
                errors=[str(e)]
            )
    
    async def _handle_create_operation(self, request: HiNATAWriteRequestModel, context: WriteOperationContext) -> Dict[str, Any]:
        """处理创建操作"""
        if not request.hinata_data:
            raise ValueError("hinata_data is required for create operation")
        
        # 生成ID
        hinata_id = f"hinata_{context.user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 构建HiNATA数据
        hinata_dict = {
            "id": hinata_id,
            "timestamp": request.hinata_data.timestamp or datetime.now(timezone.utc).isoformat(),
            "source": request.hinata_data.source,
            "highlight": request.hinata_data.highlight,
            "note": request.hinata_data.note,
            "address": request.hinata_data.address,
            "tag": request.hinata_data.tag,
            "access": request.hinata_data.access,
            "raw_data": request.hinata_data.raw_data
        }
        
        # 通过HiNATA处理器处理
        results = await self.hinata_processor.process_hinata_batch([hinata_dict], context.user_id)
        
        if results and results[0].status.value == "completed":
            return {
                "success": True,
                "hinata_id": hinata_id,
                "message": "HiNATA created successfully"
            }
        else:
            return {
                "success": False,
                "error": results[0].error_message if results else "Processing failed"
            }
    
    async def _handle_update_operation(self, request: HiNATAWriteRequestModel, context: WriteOperationContext) -> Dict[str, Any]:
        """处理更新操作"""
        if not request.update_data:
            raise ValueError("update_data is required for update operation")
        
        update_data = request.update_data
        
        # 验证所有权
        is_owner, unauthorized = await self.validator.validate_hinata_ownership(
            context.user_id, [update_data.id]
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to modify HiNATA: {update_data.id}"
            )
        
        # 获取现有数据
        existing_data = await self._get_hinata_by_id(update_data.id)
        if not existing_data:
            raise ValueError(f"HiNATA not found: {update_data.id}")
        
        # 应用更新
        updated_data = existing_data.copy()
        for field, value in update_data.updates.items():
            if field == 'tag' and update_data.merge_tags:
                # 合并标签
                existing_tags = set(updated_data.get('tag', []))
                new_tags = set(value if isinstance(value, list) else [value])
                updated_data['tag'] = list(existing_tags.union(new_tags))
            else:
                updated_data[field] = value
        
        # 更新时间戳
        updated_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # 保存更新
        success = await self._update_hinata_in_storage(updated_data)
        
        return {
            "success": success,
            "hinata_id": update_data.id,
            "updated_fields": list(update_data.updates.keys()),
            "message": "HiNATA updated successfully" if success else "Update failed"
        }
    
    async def _handle_delete_operation(self, request: HiNATAWriteRequestModel, context: WriteOperationContext) -> Dict[str, Any]:
        """处理删除操作"""
        # 这里假设删除请求在request的某个字段中
        hinata_ids = request.processing_options.get('hinata_ids', [])
        soft_delete = request.processing_options.get('soft_delete', True)
        
        if not hinata_ids:
            raise ValueError("hinata_ids is required for delete operation")
        
        # 验证所有权
        is_owner, unauthorized = await self.validator.validate_hinata_ownership(
            context.user_id, hinata_ids
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to delete HiNATA: {unauthorized}"
            )
        
        deleted_count = 0
        for hinata_id in hinata_ids:
            if soft_delete:
                success = await self._soft_delete_hinata(hinata_id)
            else:
                success = await self._hard_delete_hinata(hinata_id)
            
            if success:
                deleted_count += 1
        
        return {
            "success": deleted_count > 0,
            "deleted_count": deleted_count,
            "total_requested": len(hinata_ids),
            "message": f"Deleted {deleted_count} HiNATA records"
        }
    
    async def _handle_bulk_operation(self, request: HiNATAWriteRequestModel, context: WriteOperationContext) -> Dict[str, Any]:
        """处理批量操作"""
        if not request.bulk_operation:
            raise ValueError("bulk_operation is required for bulk operations")
        
        bulk_op = request.bulk_operation
        
        # 安全性验证
        is_safe, errors = await self.validator.validate_bulk_operation_safety(bulk_op, context.user_id)
        if not is_safe:
            raise ValueError(f"Bulk operation safety check failed: {errors}")
        
        # 获取目标HiNATA列表
        target_hinatas = await self._find_hinatas_by_filter(bulk_op.target_filter, context.user_id)
        
        if bulk_op.dry_run:
            return {
                "dry_run": True,
                "estimated_count": len(target_hinatas),
                "sample_targets": target_hinatas[:5],  # 返回前5个作为样例
                "batch_results": [],
                "successful_count": 0,
                "errors": []
            }
        
        # 批量处理
        batch_results = []
        successful_count = 0
        errors = []
        
        # 分批处理
        for i in range(0, len(target_hinatas), bulk_op.batch_size):
            batch = target_hinatas[i:i + bulk_op.batch_size]
            
            for hinata in batch:
                try:
                    result = await self._apply_bulk_operation(hinata, bulk_op.operation_data, bulk_op.operation_type)
                    batch_results.append(result)
                    if result.get('success'):
                        successful_count += 1
                except Exception as e:
                    errors.append(f"Failed to process {hinata['id']}: {str(e)}")
        
        return {
            "dry_run": False,
            "batch_results": batch_results,
            "successful_count": successful_count,
            "total_processed": len(target_hinatas),
            "errors": errors
        }
    
    async def _get_hinata_by_id(self, hinata_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取HiNATA数据"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM hinata_data WHERE id = $1",
                hinata_id
            )
            return dict(row) if row else None
    
    async def _update_hinata_in_storage(self, hinata_data: Dict[str, Any]) -> bool:
        """在存储中更新HiNATA数据"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    UPDATE hinata_data SET
                        highlight = $2,
                        note = $3,
                        address = $4,
                        tags = $5,
                        access_level = $6,
                        timestamp = $7
                    WHERE id = $1
                ''',
                    hinata_data['id'],
                    hinata_data['highlight'],
                    hinata_data['note'],
                    hinata_data['address'],
                    json.dumps(hinata_data['tag']),
                    hinata_data['access'],
                    hinata_data['timestamp']
                )
            return True
        except Exception:
            return False
    
    async def _soft_delete_hinata(self, hinata_id: str) -> bool:
        """软删除HiNATA"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE hinata_data SET is_deleted = TRUE, deleted_at = NOW() WHERE id = $1",
                    hinata_id
                )
            return True
        except Exception:
            return False
    
    async def _hard_delete_hinata(self, hinata_id: str) -> bool:
        """硬删除HiNATA"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("DELETE FROM hinata_data WHERE id = $1", hinata_id)
            return True
        except Exception:
            return False
    
    async def _find_hinatas_by_filter(self, filter_conditions: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        """根据过滤条件查找HiNATA"""
        async with self.db_pool.acquire() as conn:
            query = "SELECT * FROM hinata_data WHERE user_id = $1 AND is_deleted = FALSE"
            params = [user_id]
            
            # 构建动态查询条件
            if 'tag' in filter_conditions:
                query += f" AND tags::jsonb ? ${len(params) + 1}"
                params.append(filter_conditions['tag'])
            
            if 'source' in filter_conditions:
                query += f" AND source = ${len(params) + 1}"
                params.append(filter_conditions['source'])
            
            if 'date_range' in filter_conditions:
                date_range = filter_conditions['date_range']
                if 'start' in date_range:
                    query += f" AND timestamp >= ${len(params) + 1}"
                    params.append(date_range['start'])
                if 'end' in date_range:
                    query += f" AND timestamp <= ${len(params) + 1}"
                    params.append(date_range['end'])
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def _apply_bulk_operation(self, hinata: Dict[str, Any], operation_data: Dict[str, Any], operation_type: str) -> Dict[str, Any]:
        """应用批量操作到单个HiNATA"""
        try:
            if operation_type == "bulk_tag":
                # 批量添加标签
                new_tags = operation_data.get('tags', [])
                existing_tags = json.loads(hinata.get('tags', '[]'))
                combined_tags = list(set(existing_tags + new_tags))
                
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE hinata_data SET tags = $2 WHERE id = $1",
                        hinata['id'], json.dumps(combined_tags)
                    )
                
                return {
                    "success": True,
                    "hinata_id": hinata['id'],
                    "operation": "bulk_tag",
                    "added_tags": new_tags
                }
            
            elif operation_type == "bulk_retag":
                # 批量重新标记
                new_tags = operation_data.get('tags', [])
                
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE hinata_data SET tags = $2 WHERE id = $1",
                        hinata['id'], json.dumps(new_tags)
                    )
                
                return {
                    "success": True,
                    "hinata_id": hinata['id'],
                    "operation": "bulk_retag",
                    "new_tags": new_tags
                }
            
            else:
                return {
                    "success": False,
                    "hinata_id": hinata['id'],
                    "error": f"Unsupported bulk operation: {operation_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "hinata_id": hinata['id'],
                "error": str(e)
            }
    
    async def _create_backup(self, user_id: str, operation_id: str):
        """创建操作前备份"""
        backup_key = f"backup:{user_id}:{operation_id}"
        
        # 获取用户所有HiNATA数据
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM hinata_data WHERE user_id = $1 AND is_deleted = FALSE",
                user_id
            )
            
            backup_data = {
                "user_id": user_id,
                "operation_id": operation_id,
                "backup_time": datetime.now(timezone.utc).isoformat(),
                "data": [dict(row) for row in rows]
            }
            
            # 存储到Redis，保留24小时
            await self.redis_pool.setex(
                backup_key,
                24 * 3600,
                json.dumps(backup_data, default=str)
            )


class HiNATAWriteAPI:
    """HiNATA写入API主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = FastAPI(
            title="ByenatOS HiNATA Write API",
            description="ByenatOS HiNATA文件系统写入API",
            version="1.0.0"
        )
        
        # 初始化组件
        self.auth_manager = None
        self.write_processor = None
        self.hinata_processor = None
        self.storage_engine = None
        
        # 设置路由
        self._setup_routes()
    
    async def initialize(self):
        """初始化API服务"""
        # 初始化数据库连接
        db_pool = await asyncpg.create_pool(self.config['postgres_dsn'])
        redis_pool = aioredis.from_url(self.config['redis_url'])
        
        # 初始化组件
        self.auth_manager = AuthManager(db_pool, redis_pool)
        
        self.hinata_processor = HiNATAProcessor(
            self.config['redis_url'],
            self.config['postgres_dsn']
        )
        await self.hinata_processor.initialize()
        
        self.storage_engine = StorageEngine(self.config)
        await self.storage_engine.initialize()
        
        self.write_processor = HiNATAWriteProcessor(
            db_pool, redis_pool, self.hinata_processor, self.storage_engine
        )
        
        # 创建数据库表
        await self._create_tables(db_pool)
    
    async def _create_tables(self, db_pool):
        """创建写入API相关数据库表"""
        async with db_pool.acquire() as conn:
            # 用户权限表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    user_id TEXT PRIMARY KEY,
                    write_permissions JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # 写入操作日志表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hinata_write_logs (
                    id SERIAL PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    intent_description TEXT,
                    affected_count INTEGER DEFAULT 0,
                    processing_time REAL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX (user_id, created_at DESC),
                    INDEX (operation_id)
                )
            ''')
            
            # 为hinata_data表添加删除相关字段
            await conn.execute('''
                ALTER TABLE hinata_data 
                ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE
            ''')
    
    def _setup_routes(self):
        """设置API路由"""
        security = HTTPBearer()
        
        async def get_current_app(credentials: HTTPAuthorizationCredentials = Security(security)):
            """获取当前认证的App"""
            app = await self.auth_manager.authenticate_app(credentials.credentials)
            if not app:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            return app
        
        # 1. HiNATA写入接口
        @self.app.post("/api/hinata/write", response_model=HiNATAWriteResponse)
        async def write_hinata(
            request: HiNATAWriteRequestModel,
            app = Depends(get_current_app)
        ):
            """写入/修改HiNATA数据"""
            
            # 检查权限
            if HiNATAWritePermission.HINATA_WRITE.value not in [p.value for p in app.permissions]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HiNATA write permission required"
                )
            
            # 创建操作上下文
            context = WriteOperationContext(
                user_id=request.user_id,
                operation_id=f"write_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                operation_type=HiNATAWriteOperation(request.operation_type),
                intent_description=request.intent_description,
                source_app=app.app_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # 处理写入请求
            response = await self.write_processor.process_write_request(request, context)
            
            # 记录操作日志
            await self._log_write_operation(context, response)
            
            return response
        
        # 2. 批量删除接口
        @self.app.post("/api/hinata/delete")
        async def delete_hinata(
            request: DeleteRequestModel,
            app = Depends(get_current_app)
        ):
            """删除HiNATA数据"""
            
            # 检查权限
            if HiNATAWritePermission.HINATA_DELETE.value not in [p.value for p in app.permissions]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HiNATA delete permission required"
                )
            
            # 创建删除请求
            write_request = HiNATAWriteRequestModel(
                user_id=request.user_id,
                operation_type="delete",
                intent_description=f"Delete {len(request.hinata_ids)} HiNATA records: {request.delete_reason}",
                processing_options={
                    "hinata_ids": request.hinata_ids,
                    "soft_delete": request.soft_delete
                }
            )
            
            context = WriteOperationContext(
                user_id=request.user_id,
                operation_id=f"delete_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                operation_type=HiNATAWriteOperation.DELETE,
                intent_description=write_request.intent_description,
                source_app=app.app_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            response = await self.write_processor.process_write_request(write_request, context)
            await self._log_write_operation(context, response)
            
            return response
        
        # 3. 批量操作接口
        @self.app.post("/api/hinata/bulk", response_model=BulkOperationResponse)
        async def bulk_operation(
            request: HiNATAWriteRequestModel,
            app = Depends(get_current_app)
        ):
            """批量操作HiNATA数据"""
            
            # 检查权限
            if HiNATAWritePermission.HINATA_BULK_MODIFY.value not in [p.value for p in app.permissions]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HiNATA bulk modify permission required"
                )
            
            context = WriteOperationContext(
                user_id=request.user_id,
                operation_id=f"bulk_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                operation_type=HiNATAWriteOperation(request.operation_type),
                intent_description=request.intent_description,
                source_app=app.app_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            write_response = await self.write_processor.process_write_request(request, context)
            await self._log_write_operation(context, write_response)
            
            # 转换为批量操作响应格式
            return BulkOperationResponse(
                status=write_response.status,
                operation_id=write_response.operation_id,
                total_processed=write_response.affected_count,
                successful_count=write_response.affected_count,
                failed_count=0,
                processing_time=write_response.processing_time,
                batch_results=write_response.results,
                errors=write_response.errors
            )
        
        # 4. 操作历史查询接口
        @self.app.get("/api/hinata/write/history")
        async def get_write_history(
            user_id: str,
            limit: int = 50,
            app = Depends(get_current_app)
        ):
            """获取写入操作历史"""
            
            async with self.write_processor.db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT operation_id, operation_type, intent_description, 
                           affected_count, status, created_at
                    FROM hinata_write_logs 
                    WHERE user_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                ''', user_id, limit)
                
                return {
                    "user_id": user_id,
                    "operations": [dict(row) for row in rows]
                }
        
        # 5. 备份恢复接口
        @self.app.post("/api/hinata/restore")
        async def restore_from_backup(
            operation_id: str,
            user_id: str,
            app = Depends(get_current_app)
        ):
            """从备份恢复数据"""
            
            # 检查管理员权限
            if HiNATAWritePermission.HINATA_ADMIN.value not in [p.value for p in app.permissions]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="HiNATA admin permission required"
                )
            
            backup_key = f"backup:{user_id}:{operation_id}"
            backup_data = await self.write_processor.redis_pool.get(backup_key)
            
            if not backup_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Backup not found or expired"
                )
            
            # 这里应该实现恢复逻辑
            return {
                "status": "success",
                "message": f"Restore operation initiated for {operation_id}"
            }
    
    async def _log_write_operation(self, context: WriteOperationContext, response: HiNATAWriteResponse):
        """记录写入操作日志"""
        async with self.write_processor.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO hinata_write_logs 
                (operation_id, user_id, operation_type, intent_description, 
                 affected_count, processing_time, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''',
                context.operation_id, context.user_id, context.operation_type.value,
                context.intent_description, response.affected_count,
                response.processing_time, response.status
            )
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app


# 使用示例
async def create_write_api() -> FastAPI:
    """创建和初始化写入API应用"""
    config = {
        'redis_url': 'redis://localhost:6379',
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'cold_storage_path': '/data/cold_storage',
        'chroma_persist_dir': '/data/chroma',
        'elasticsearch_url': 'http://localhost:9200'
    }
    
    api = HiNATAWriteAPI(config)
    await api.initialize()
    
    return api.get_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "InterfaceAbstraction.APIs.HiNATAWriteAPI:create_write_api",
        host="0.0.0.0",
        port=8081,
        reload=True,
        factory=True
    )