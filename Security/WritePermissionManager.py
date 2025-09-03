"""
ByenatOS Write Permission Manager
写入权限管理器 - HiNATA文件系统写入操作的权限控制和安全验证

确保只有经过授权的用户和应用程序才能修改用户的HiNATA知识库内容，
并提供细粒度的权限控制和操作审计功能。
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import asyncpg
import aioredis
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets
import base64


class PermissionLevel(Enum):
    """权限级别"""
    NONE = "none"
    READ_ONLY = "read_only"
    WRITE_LIMITED = "write_limited"  # 只能创建和修改自己的内容
    WRITE_FULL = "write_full"       # 可以批量操作
    ADMIN = "admin"                 # 管理员权限


class OperationRisk(Enum):
    """操作风险级别"""
    LOW = "low"        # 单条记录操作
    MEDIUM = "medium"  # 小批量操作 (<100)
    HIGH = "high"      # 大批量操作 (>=100)
    CRITICAL = "critical"  # 删除或不可逆操作


@dataclass
class UserPermissionProfile:
    """用户权限配置"""
    user_id: str
    permission_level: PermissionLevel
    allowed_operations: Set[str]
    daily_operation_limit: int
    batch_size_limit: int
    require_2fa: bool
    
    # 时间限制
    valid_from: str
    valid_until: Optional[str] = None
    
    # 操作限制
    allowed_sources: Set[str] = None  # 允许操作的数据源
    forbidden_operations: Set[str] = None  # 禁止的操作
    
    # 审计设置
    audit_level: str = "standard"  # minimal, standard, detailed
    
    # 元数据
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""


@dataclass
class OperationAuditLog:
    """操作审计日志"""
    log_id: str
    user_id: str
    operation_type: str
    operation_details: Dict[str, Any]
    risk_level: OperationRisk
    permission_check_result: bool
    execution_result: str
    affected_records: int
    
    # 上下文信息
    source_app: str
    user_agent: str
    ip_address: str
    session_id: str
    
    # 时间信息
    requested_at: str
    executed_at: Optional[str] = None
    duration: float = 0.0
    
    # 安全信息
    auth_method: str = ""
    risk_score: float = 0.0
    security_flags: List[str] = None


class RiskAssessment:
    """风险评估器"""
    
    def __init__(self):
        self.risk_factors = self._load_risk_factors()
    
    def assess_operation_risk(self, operation_type: str, operation_data: Dict[str, Any], 
                            user_profile: UserPermissionProfile) -> Tuple[OperationRisk, float, List[str]]:
        """评估操作风险"""
        
        risk_score = 0.0
        risk_flags = []
        
        # 1. 操作类型风险
        operation_risks = {
            "create": 0.1,
            "update": 0.3,
            "delete": 0.8,
            "bulk_tag": 0.4,
            "bulk_retag": 0.5,
            "batch_update": 0.6,
            "merge": 0.7,
            "split": 0.6
        }
        
        base_risk = operation_risks.get(operation_type, 0.5)
        risk_score += base_risk
        
        # 2. 批量操作风险
        affected_count = operation_data.get("estimated_affected_count", 1)
        if affected_count > 1000:
            risk_score += 0.8
            risk_flags.append("large_batch_operation")
        elif affected_count > 100:
            risk_score += 0.5
            risk_flags.append("medium_batch_operation")
        elif affected_count > 10:
            risk_score += 0.2
            risk_flags.append("small_batch_operation")
        
        # 3. 删除操作特殊风险
        if operation_type == "delete":
            if not operation_data.get("soft_delete", True):
                risk_score += 0.3
                risk_flags.append("hard_delete")
            
            if affected_count > 50:
                risk_score += 0.4
                risk_flags.append("bulk_delete")
        
        # 4. 时间因素风险
        current_time = datetime.now(timezone.utc)
        
        # 非工作时间操作风险更高
        if current_time.hour < 6 or current_time.hour > 22:
            risk_score += 0.1
            risk_flags.append("off_hours_operation")
        
        # 5. 用户行为风险
        if user_profile.permission_level == PermissionLevel.WRITE_LIMITED:
            if operation_type in ["batch_update", "bulk_tag", "bulk_retag"]:
                risk_score += 0.3
                risk_flags.append("limited_user_bulk_operation")
        
        # 6. 数据源风险
        target_sources = operation_data.get("target_sources", [])
        if target_sources and user_profile.allowed_sources:
            unauthorized_sources = set(target_sources) - user_profile.allowed_sources
            if unauthorized_sources:
                risk_score += 0.5
                risk_flags.append("unauthorized_source_access")
        
        # 确定风险级别
        if risk_score >= 1.0:
            risk_level = OperationRisk.CRITICAL
        elif risk_score >= 0.7:
            risk_level = OperationRisk.HIGH
        elif risk_score >= 0.4:
            risk_level = OperationRisk.MEDIUM
        else:
            risk_level = OperationRisk.LOW
        
        return risk_level, min(risk_score, 1.0), risk_flags
    
    def _load_risk_factors(self) -> Dict[str, Any]:
        """加载风险因子配置"""
        return {
            "high_risk_operations": ["delete", "merge", "batch_update"],
            "bulk_operation_threshold": 100,
            "critical_batch_threshold": 1000,
            "off_hours_start": 22,
            "off_hours_end": 6
        }


class PermissionValidator:
    """权限验证器"""
    
    def __init__(self, db_pool, redis_pool):
        self.db_pool = db_pool
        self.redis_pool = redis_pool
        self.risk_assessor = RiskAssessment()
    
    async def validate_write_permission(self, user_id: str, operation_type: str, 
                                      operation_data: Dict[str, Any], 
                                      context: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """验证写入权限"""
        
        # 1. 获取用户权限配置
        user_profile = await self.get_user_permission_profile(user_id)
        if not user_profile:
            return False, "User permission profile not found", []
        
        # 2. 检查基础权限
        if user_profile.permission_level == PermissionLevel.NONE:
            return False, "No write permissions", []
        
        if user_profile.permission_level == PermissionLevel.READ_ONLY:
            return False, "Read-only access", []
        
        # 3. 检查操作是否被允许
        if operation_type not in user_profile.allowed_operations:
            return False, f"Operation '{operation_type}' not permitted", []
        
        # 4. 检查禁止操作
        if user_profile.forbidden_operations and operation_type in user_profile.forbidden_operations:
            return False, f"Operation '{operation_type}' is forbidden", []
        
        # 5. 检查时间有效性
        current_time = datetime.now(timezone.utc)
        valid_from = datetime.fromisoformat(user_profile.valid_from.replace('Z', '+00:00'))
        
        if current_time < valid_from:
            return False, "Permissions not yet active", []
        
        if user_profile.valid_until:
            valid_until = datetime.fromisoformat(user_profile.valid_until.replace('Z', '+00:00'))
            if current_time > valid_until:
                return False, "Permissions expired", []
        
        # 6. 检查操作限制
        daily_count = await self.get_daily_operation_count(user_id)
        if daily_count >= user_profile.daily_operation_limit:
            return False, "Daily operation limit exceeded", []
        
        # 7. 检查批量操作限制
        affected_count = operation_data.get("estimated_affected_count", 1)
        if affected_count > user_profile.batch_size_limit:
            return False, f"Batch size limit exceeded ({affected_count} > {user_profile.batch_size_limit})", []
        
        # 8. 风险评估
        risk_level, risk_score, risk_flags = self.risk_assessor.assess_operation_risk(
            operation_type, operation_data, user_profile
        )
        
        # 9. 基于风险级别的权限检查
        if risk_level == OperationRisk.CRITICAL:
            if user_profile.permission_level != PermissionLevel.ADMIN:
                return False, "Admin permissions required for critical operations", risk_flags
        
        elif risk_level == OperationRisk.HIGH:
            if user_profile.permission_level not in [PermissionLevel.WRITE_FULL, PermissionLevel.ADMIN]:
                return False, "Full write permissions required for high-risk operations", risk_flags
        
        # 10. 2FA检查
        if user_profile.require_2fa and risk_level in [OperationRisk.HIGH, OperationRisk.CRITICAL]:
            if not await self.verify_2fa_for_operation(user_id, context.get("session_id")):
                return False, "Two-factor authentication required", risk_flags
        
        return True, "Permission granted", risk_flags
    
    async def get_user_permission_profile(self, user_id: str) -> Optional[UserPermissionProfile]:
        """获取用户权限配置"""
        
        # 先从缓存获取
        cache_key = f"user_permissions:{user_id}"
        cached_profile = await self.redis_pool.get(cache_key)
        
        if cached_profile:
            profile_data = json.loads(cached_profile)
            profile_data['allowed_operations'] = set(profile_data['allowed_operations'])
            profile_data['allowed_sources'] = set(profile_data.get('allowed_sources', []))
            profile_data['forbidden_operations'] = set(profile_data.get('forbidden_operations', []))
            profile_data['permission_level'] = PermissionLevel(profile_data['permission_level'])
            return UserPermissionProfile(**profile_data)
        
        # 从数据库获取
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_write_permissions WHERE user_id = $1 AND is_active = TRUE",
                user_id
            )
            
            if not row:
                # 创建默认权限配置
                return await self.create_default_permission_profile(user_id)
            
            profile = UserPermissionProfile(
                user_id=row['user_id'],
                permission_level=PermissionLevel(row['permission_level']),
                allowed_operations=set(json.loads(row['allowed_operations'])),
                daily_operation_limit=row['daily_operation_limit'],
                batch_size_limit=row['batch_size_limit'],
                require_2fa=row['require_2fa'],
                valid_from=row['valid_from'],
                valid_until=row['valid_until'],
                allowed_sources=set(json.loads(row.get('allowed_sources', '[]'))),
                forbidden_operations=set(json.loads(row.get('forbidden_operations', '[]'))),
                audit_level=row.get('audit_level', 'standard'),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                created_by=row['created_by']
            )
            
            # 缓存配置
            cache_data = asdict(profile)
            cache_data['allowed_operations'] = list(profile.allowed_operations)
            cache_data['allowed_sources'] = list(profile.allowed_sources or [])
            cache_data['forbidden_operations'] = list(profile.forbidden_operations or [])
            cache_data['permission_level'] = profile.permission_level.value
            
            await self.redis_pool.setex(
                cache_key,
                3600,  # 1小时缓存
                json.dumps(cache_data, default=str)
            )
            
            return profile
    
    async def create_default_permission_profile(self, user_id: str) -> UserPermissionProfile:
        """创建默认权限配置"""
        
        default_profile = UserPermissionProfile(
            user_id=user_id,
            permission_level=PermissionLevel.WRITE_LIMITED,
            allowed_operations={"create", "update", "bulk_tag"},
            daily_operation_limit=100,
            batch_size_limit=50,
            require_2fa=False,
            valid_from=datetime.now(timezone.utc).isoformat(),
            audit_level="standard",
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by="system"
        )
        
        # 保存到数据库
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_write_permissions 
                (user_id, permission_level, allowed_operations, daily_operation_limit,
                 batch_size_limit, require_2fa, valid_from, audit_level, created_at, created_by, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, TRUE)
            ''',
                user_id, default_profile.permission_level.value,
                json.dumps(list(default_profile.allowed_operations)),
                default_profile.daily_operation_limit, default_profile.batch_size_limit,
                default_profile.require_2fa, default_profile.valid_from,
                default_profile.audit_level, default_profile.created_at,
                default_profile.created_by
            )
        
        return default_profile
    
    async def get_daily_operation_count(self, user_id: str) -> int:
        """获取用户今日操作次数"""
        today = datetime.now(timezone.utc).date()
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow('''
                SELECT COUNT(*) as count 
                FROM operation_audit_logs 
                WHERE user_id = $1 AND DATE(requested_at) = $2
            ''', user_id, today)
            
            return result['count'] if result else 0
    
    async def verify_2fa_for_operation(self, user_id: str, session_id: str) -> bool:
        """验证两因子认证"""
        
        # 检查会话中的2FA状态
        if session_id:
            cache_key = f"2fa_verified:{session_id}"
            verified = await self.redis_pool.get(cache_key)
            if verified:
                return True
        
        # 这里应该实现具体的2FA验证逻辑
        # 例如检查TOTP、SMS验证码等
        return False
    
    async def log_operation_audit(self, user_id: str, operation_type: str, 
                                operation_data: Dict[str, Any], context: Dict[str, Any],
                                permission_result: Tuple[bool, str, List[str]],
                                execution_result: Optional[Dict[str, Any]] = None) -> str:
        """记录操作审计日志"""
        
        log_id = f"audit_{int(time.time())}_{user_id}_{secrets.token_hex(4)}"
        
        # 评估风险
        user_profile = await self.get_user_permission_profile(user_id)
        risk_level, risk_score, risk_flags = self.risk_assessor.assess_operation_risk(
            operation_type, operation_data, user_profile
        )
        
        audit_log = OperationAuditLog(
            log_id=log_id,
            user_id=user_id,
            operation_type=operation_type,
            operation_details=operation_data,
            risk_level=risk_level,
            permission_check_result=permission_result[0],
            execution_result=execution_result.get('status', 'not_executed') if execution_result else 'not_executed',
            affected_records=execution_result.get('affected_count', 0) if execution_result else 0,
            source_app=context.get('source_app', 'unknown'),
            user_agent=context.get('user_agent', ''),
            ip_address=context.get('ip_address', ''),
            session_id=context.get('session_id', ''),
            requested_at=datetime.now(timezone.utc).isoformat(),
            executed_at=datetime.now(timezone.utc).isoformat() if execution_result else None,
            duration=execution_result.get('processing_time', 0.0) if execution_result else 0.0,
            auth_method=context.get('auth_method', 'api_key'),
            risk_score=risk_score,
            security_flags=risk_flags + permission_result[2]
        )
        
        # 保存审计日志
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO operation_audit_logs 
                (log_id, user_id, operation_type, operation_details, risk_level,
                 permission_check_result, execution_result, affected_records,
                 source_app, user_agent, ip_address, session_id,
                 requested_at, executed_at, duration, auth_method, risk_score, security_flags)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            ''',
                audit_log.log_id, audit_log.user_id, audit_log.operation_type,
                json.dumps(audit_log.operation_details), audit_log.risk_level.value,
                audit_log.permission_check_result, audit_log.execution_result,
                audit_log.affected_records, audit_log.source_app, audit_log.user_agent,
                audit_log.ip_address, audit_log.session_id, audit_log.requested_at,
                audit_log.executed_at, audit_log.duration, audit_log.auth_method,
                audit_log.risk_score, json.dumps(audit_log.security_flags or [])
            )
        
        return log_id


class WritePermissionManager:
    """写入权限管理器主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_pool = None
        self.redis_pool = None
        self.validator = None
    
    async def initialize(self):
        """初始化权限管理器"""
        self.db_pool = await asyncpg.create_pool(self.config['postgres_dsn'])
        self.redis_pool = aioredis.from_url(self.config['redis_url'])
        self.validator = PermissionValidator(self.db_pool, self.redis_pool)
        
        # 创建数据库表
        await self._create_tables()
    
    async def _create_tables(self):
        """创建权限相关数据库表"""
        async with self.db_pool.acquire() as conn:
            # 用户写入权限表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_write_permissions (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    permission_level TEXT NOT NULL,
                    allowed_operations JSONB NOT NULL,
                    daily_operation_limit INTEGER DEFAULT 100,
                    batch_size_limit INTEGER DEFAULT 50,
                    require_2fa BOOLEAN DEFAULT FALSE,
                    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
                    valid_until TIMESTAMP WITH TIME ZONE,
                    allowed_sources JSONB DEFAULT '[]',
                    forbidden_operations JSONB DEFAULT '[]',
                    audit_level TEXT DEFAULT 'standard',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_by TEXT DEFAULT 'system',
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(user_id, is_active) DEFERRABLE INITIALLY DEFERRED
                )
            ''')
            
            # 操作审计日志表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS operation_audit_logs (
                    id SERIAL PRIMARY KEY,
                    log_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    operation_details JSONB NOT NULL,
                    risk_level TEXT NOT NULL,
                    permission_check_result BOOLEAN NOT NULL,
                    execution_result TEXT NOT NULL,
                    affected_records INTEGER DEFAULT 0,
                    source_app TEXT,
                    user_agent TEXT,
                    ip_address TEXT,
                    session_id TEXT,
                    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    executed_at TIMESTAMP WITH TIME ZONE,
                    duration REAL DEFAULT 0,
                    auth_method TEXT,
                    risk_score REAL DEFAULT 0,
                    security_flags JSONB DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # 创建索引
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_write_permissions(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON operation_audit_logs(user_id, requested_at DESC)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_risk_level ON operation_audit_logs(risk_level, requested_at DESC)')
    
    async def validate_and_audit_operation(self, user_id: str, operation_type: str,
                                         operation_data: Dict[str, Any],
                                         context: Dict[str, Any]) -> Tuple[bool, str, str]:
        """验证权限并记录审计"""
        
        # 权限验证
        permission_result = await self.validator.validate_write_permission(
            user_id, operation_type, operation_data, context
        )
        
        # 记录审计日志
        audit_log_id = await self.validator.log_operation_audit(
            user_id, operation_type, operation_data, context, permission_result
        )
        
        return permission_result[0], permission_result[1], audit_log_id
    
    async def update_user_permissions(self, user_id: str, updates: Dict[str, Any], 
                                    admin_user_id: str) -> bool:
        """更新用户权限（需要管理员权限）"""
        
        try:
            async with self.db_pool.acquire() as conn:
                # 禁用当前权限配置
                await conn.execute(
                    "UPDATE user_write_permissions SET is_active = FALSE WHERE user_id = $1",
                    user_id
                )
                
                # 创建新的权限配置
                await conn.execute('''
                    INSERT INTO user_write_permissions 
                    (user_id, permission_level, allowed_operations, daily_operation_limit,
                     batch_size_limit, require_2fa, valid_from, valid_until,
                     allowed_sources, forbidden_operations, audit_level,
                     created_by, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, TRUE)
                ''',
                    user_id,
                    updates.get('permission_level', 'write_limited'),
                    json.dumps(updates.get('allowed_operations', ['create', 'update'])),
                    updates.get('daily_operation_limit', 100),
                    updates.get('batch_size_limit', 50),
                    updates.get('require_2fa', False),
                    updates.get('valid_from', datetime.now(timezone.utc).isoformat()),
                    updates.get('valid_until'),
                    json.dumps(updates.get('allowed_sources', [])),
                    json.dumps(updates.get('forbidden_operations', [])),
                    updates.get('audit_level', 'standard'),
                    admin_user_id
                )
                
                # 清除缓存
                await self.redis_pool.delete(f"user_permissions:{user_id}")
                
                return True
                
        except Exception as e:
            print(f"Failed to update permissions for {user_id}: {e}")
            return False
    
    async def get_audit_logs(self, user_id: str = None, risk_level: str = None,
                           limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取审计日志"""
        
        query = "SELECT * FROM operation_audit_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += f" AND user_id = ${len(params) + 1}"
            params.append(user_id)
        
        if risk_level:
            query += f" AND risk_level = ${len(params) + 1}"
            params.append(risk_level)
        
        query += f" ORDER BY requested_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def close(self):
        """关闭连接"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_pool:
            await self.redis_pool.close()


# 使用示例
async def main():
    """使用示例"""
    config = {
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'redis_url': 'redis://localhost:6379'
    }
    
    manager = WritePermissionManager(config)
    await manager.initialize()
    
    # 测试权限验证
    user_id = "test_user_123"
    operation_type = "bulk_tag"
    operation_data = {
        "estimated_affected_count": 50,
        "target_sources": ["browser_extension"]
    }
    context = {
        "source_app": "conversational_interface",
        "session_id": "session_123",
        "ip_address": "192.168.1.100"
    }
    
    allowed, reason, audit_id = await manager.validate_and_audit_operation(
        user_id, operation_type, operation_data, context
    )
    
    print(f"Permission check: {allowed}")
    print(f"Reason: {reason}")
    print(f"Audit ID: {audit_id}")
    
    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())