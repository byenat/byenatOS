"""
ByenatOS App Integration API
App集成API - 提供标准化的App与系统集成接口

支持第三方App与ByenatOS的深度集成，包括HiNATA提交、PSP查询、用户认证等
"""

import asyncio
import json
import time
import uuid
import hashlib
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
import aioredis
import asyncpg

# 导入内部组件
from Kernel.Core.HiNATAProcessor import HiNATAProcessor
from Kernel.Core.PSPEngine import PSPEngine  
from Kernel.Core.StorageEngine import StorageEngine


class AppPermission(Enum):
    """App权限类型"""
    HINATA_SUBMIT = "hinata_submit"
    HINATA_QUERY = "hinata_query"  # 新增：问题相关HiNATA检索权限
    PSP_READ = "psp_read"
    PSP_CONTEXT = "psp_context"
    ENHANCEMENT_ACCESS = "enhancement_access"  # 新增：综合增强功能权限
    USER_DATA_READ = "user_data_read"
    STORAGE_ACCESS = "storage_access"
    ADMIN = "admin"


@dataclass
class AppRegistration:
    """App注册信息"""
    app_id: str
    app_name: str
    app_version: str
    developer: str
    description: str
    permissions: Set[AppPermission]
    api_key: str
    webhook_url: Optional[str] = None
    rate_limit: int = 1000  # 每小时请求限制
    created_at: str = ""
    last_active: str = ""
    is_active: bool = True


# Pydantic模型定义
class HiNATASubmissionModel(BaseModel):
    """HiNATA提交模型"""
    id: str = Field(..., description="HiNATA唯一标识符")
    timestamp: str = Field(..., description="创建时间戳 (ISO 8601)")
    source: str = Field(..., description="数据源标识")
    highlight: str = Field(..., max_length=10000, description="高亮文本")
    note: str = Field(..., max_length=50000, description="用户笔记")
    address: str = Field(..., description="资源地址")
    tag: List[str] = Field(default=[], description="用户标签")
    access: str = Field(..., regex="^(private|public|shared)$", description="访问级别")
    raw_data: Dict[str, Any] = Field(default={}, description="原始数据")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid timestamp format')


class HiNATABatchSubmissionModel(BaseModel):
    """HiNATA批量提交模型"""
    app_id: str = Field(..., description="App标识符")
    user_id: str = Field(..., description="用户标识符")
    hinata_batch: List[HiNATASubmissionModel] = Field(..., description="HiNATA数据批次")
    processing_options: Dict[str, Any] = Field(default={}, description="处理选项")
    
    @validator('hinata_batch')
    def validate_batch_size(cls, v):
        if len(v) > 100:
            raise ValueError('Batch size cannot exceed 100')
        return v


class PSPContextRequestModel(BaseModel):
    """PSP上下文请求模型"""
    user_id: str = Field(..., description="用户标识符")
    current_request: str = Field(default="", description="当前用户请求")
    include_details: bool = Field(default=False, description="是否包含详细信息")
    context_type: str = Field(default="prompt", description="上下文类型")


class AppRegistrationModel(BaseModel):
    """App注册模型"""
    app_name: str = Field(..., description="应用名称")
    app_version: str = Field(..., description="应用版本")
    developer: str = Field(..., description="开发者")
    description: str = Field(..., description="应用描述")
    requested_permissions: List[str] = Field(..., description="请求的权限")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")


class RetrievalQueryModel(BaseModel):
    """检索查询模型"""
    user_id: str = Field(..., description="用户标识符")
    query_text: Optional[str] = Field(None, description="查询文本")
    semantic_vector: Optional[List[float]] = Field(None, description="语义向量")
    filters: Dict[str, Any] = Field(default={}, description="过滤条件")
    limit: int = Field(default=10, max=50, description="返回结果数量限制")
    min_relevance_score: float = Field(default=0.5, description="最小相关性分数")


class HiNATAQueryModel(BaseModel):
    """HiNATA问题查询模型"""
    user_id: str = Field(..., description="用户标识符")
    question: str = Field(..., max_length=2000, description="用户问题")
    limit: int = Field(default=10, max=20, description="返回结果数量限制")
    min_relevance_score: float = Field(default=0.5, description="最小相关性分数")
    include_metadata: bool = Field(default=True, description="是否包含元数据")


class PersonalizedEnhancementModel(BaseModel):
    """个性化增强请求模型"""
    user_id: str = Field(..., description="用户标识符")
    question: str = Field(..., max_length=2000, description="用户问题")
    context_limit: int = Field(default=5, max=10, description="HiNATA上下文数量限制")
    include_psp_details: bool = Field(default=False, description="是否包含PSP详细信息")


# 响应模型
class HiNATASubmissionResponse(BaseModel):
    """HiNATA提交响应"""
    status: str
    processed_count: int
    job_id: Optional[str] = None
    processing_time: float
    errors: List[str] = Field(default=[])


class PSPContextResponse(BaseModel):
    """PSP上下文响应"""
    user_id: str
    context: Dict[str, Any]
    last_updated: str
    active_components_count: int


class AppRegistrationResponse(BaseModel):
    """App注册响应"""
    status: str
    app_id: str
    api_key: str
    granted_permissions: List[str]
    rate_limit: int


class RetrievalResponse(BaseModel):
    """检索响应"""
    total_results: int
    results: List[Dict[str, Any]]
    query_time: float


class HiNATAQueryResponse(BaseModel):
    """HiNATA问题查询响应"""
    user_id: str
    question: str
    relevant_hinata: List[Dict[str, Any]]
    total_results: int
    query_time: float


class PersonalizedEnhancementResponse(BaseModel):
    """个性化增强响应 - 提供构建完整上下文所需的组件"""
    user_id: str
    question: str
    personalized_prompt: str  # PSP个性化组件（融入系统提示词）
    knowledge_components: List[Dict[str, Any]]  # HiNATA知识组件
    psp_summary: Dict[str, Any]  # PSP摘要信息
    processing_time: float


class RateLimiter:
    """API速率限制器"""
    
    def __init__(self, redis_pool):
        self.redis_pool = redis_pool
    
    async def check_rate_limit(self, app_id: str, user_id: str, limit: int = 1000) -> bool:
        """检查速率限制"""
        key = f"rate_limit:{app_id}:{user_id}"
        current_hour = int(time.time() // 3600)
        hour_key = f"{key}:{current_hour}"
        
        current_count = await self.redis_pool.get(hour_key)
        if current_count is None:
            await self.redis_pool.setex(hour_key, 3600, 1)
            return True
        
        current_count = int(current_count)
        if current_count >= limit:
            return False
        
        await self.redis_pool.incr(hour_key)
        return True
    
    async def get_remaining_quota(self, app_id: str, user_id: str, limit: int = 1000) -> int:
        """获取剩余配额"""
        key = f"rate_limit:{app_id}:{user_id}"
        current_hour = int(time.time() // 3600)
        hour_key = f"{key}:{current_hour}"
        
        current_count = await self.redis_pool.get(hour_key)
        if current_count is None:
            return limit
        
        return max(0, limit - int(current_count))


class AuthManager:
    """认证管理器"""
    
    def __init__(self, db_pool, redis_pool):
        self.db_pool = db_pool
        self.redis_pool = redis_pool
        self.jwt_secret = "byenatos_jwt_secret_key"  # 应该从配置文件读取
        self.jwt_algorithm = "HS256"
    
    async def register_app(self, registration_data: AppRegistrationModel) -> AppRegistration:
        """注册新App"""
        app_id = self._generate_app_id(registration_data.app_name)
        api_key = self._generate_api_key()
        
        # 验证和授予权限
        granted_permissions = self._validate_permissions(registration_data.requested_permissions)
        
        app_registration = AppRegistration(
            app_id=app_id,
            app_name=registration_data.app_name,
            app_version=registration_data.app_version,
            developer=registration_data.developer,
            description=registration_data.description,
            permissions=granted_permissions,
            api_key=api_key,
            webhook_url=registration_data.webhook_url,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # 保存到数据库
        await self._save_app_registration(app_registration)
        
        return app_registration
    
    def _generate_app_id(self, app_name: str) -> str:
        """生成App ID"""
        timestamp = int(time.time())
        hash_input = f"{app_name}_{timestamp}_{uuid.uuid4()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _generate_api_key(self) -> str:
        """生成API密钥"""
        return f"byo_{uuid.uuid4().hex}"
    
    def _validate_permissions(self, requested: List[str]) -> Set[AppPermission]:
        """验证和授予权限"""
        granted = set()
        
        for perm_str in requested:
            try:
                permission = AppPermission(perm_str)
                # 基础权限自动授予
                if permission in [
                    AppPermission.HINATA_SUBMIT, 
                    AppPermission.HINATA_QUERY,  # 新增基础权限
                    AppPermission.PSP_READ, 
                    AppPermission.PSP_CONTEXT,
                    AppPermission.ENHANCEMENT_ACCESS  # 新增基础权限
                ]:
                    granted.add(permission)
                # 其他权限需要审核
            except ValueError:
                continue
        
        return granted
    
    async def _save_app_registration(self, registration: AppRegistration):
        """保存App注册信息"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO app_registrations 
                (app_id, app_name, app_version, developer, description, permissions,
                 api_key, webhook_url, rate_limit, created_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''',
                registration.app_id, registration.app_name, registration.app_version,
                registration.developer, registration.description,
                json.dumps([p.value for p in registration.permissions]),
                registration.api_key, registration.webhook_url, registration.rate_limit,
                registration.created_at, registration.is_active
            )
    
    async def authenticate_app(self, api_key: str) -> Optional[AppRegistration]:
        """验证App API密钥"""
        # 检查缓存
        cached_app = await self.redis_pool.get(f"app_auth:{api_key}")
        if cached_app:
            app_data = json.loads(cached_app)
            permissions = {AppPermission(p) for p in app_data['permissions']}
            app_data['permissions'] = permissions
            return AppRegistration(**app_data)
        
        # 从数据库查询
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM app_registrations WHERE api_key = $1 AND is_active = TRUE',
                api_key
            )
            
            if row:
                permissions = {AppPermission(p) for p in json.loads(row['permissions'])}
                app_registration = AppRegistration(
                    app_id=row['app_id'],
                    app_name=row['app_name'],
                    app_version=row['app_version'],
                    developer=row['developer'],
                    description=row['description'],
                    permissions=permissions,
                    api_key=row['api_key'],
                    webhook_url=row['webhook_url'],
                    rate_limit=row['rate_limit'],
                    created_at=row['created_at'],
                    last_active=row['last_active'] or '',
                    is_active=row['is_active']
                )
                
                # 缓存认证结果
                cache_data = asdict(app_registration)
                cache_data['permissions'] = [p.value for p in permissions]
                await self.redis_pool.setex(
                    f"app_auth:{api_key}",
                    3600,  # 1小时缓存
                    json.dumps(cache_data, default=str)
                )
                
                return app_registration
        
        return None
    
    def generate_user_token(self, user_id: str, app_id: str) -> str:
        """生成用户会话token"""
        payload = {
            'user_id': user_id,
            'app_id': app_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_user_token(self, token: str) -> Optional[Dict[str, str]]:
        """验证用户token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return {
                'user_id': payload['user_id'],
                'app_id': payload['app_id']
            }
        except jwt.InvalidTokenError:
            return None


class PrivacyFilter:
    """隐私过滤器"""
    
    def __init__(self):
        self.sensitive_patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 信用卡号
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 电话号码
        ]
    
    def filter_psp_context(self, psp_context: Dict[str, Any], app_permissions: Set[AppPermission]) -> Dict[str, Any]:
        """为App过滤PSP上下文"""
        filtered_context = {}
        
        # 基础信息（所有App可见）
        if AppPermission.PSP_READ in app_permissions:
            filtered_context.update({
                'core_interests': self._generalize_interests(psp_context.get('core_interests', [])),
                'learning_preferences': self._abstract_preferences(psp_context.get('learning_preferences', [])),
                'active_components_count': psp_context.get('active_components_count', 0)
            })
        
        # 详细上下文（需要特殊权限）
        if AppPermission.PSP_CONTEXT in app_permissions:
            filtered_context.update({
                'current_goals': self._anonymize_goals(psp_context.get('current_goals', [])),
                'communication_style': psp_context.get('communication_style', []),
                'high_priority_focus': self._generalize_focus(psp_context.get('high_priority_focus', []))
            })
        
        # 移除个人标识信息
        return self._remove_pii(filtered_context)
    
    def _generalize_interests(self, interests: List[str]) -> List[str]:
        """泛化兴趣信息"""
        generalized = []
        for interest in interests:
            # 移除具体的个人信息，保留主题类别
            if len(interest) > 3:
                generalized.append(self._abstract_topic(interest))
        return generalized[:5]  # 限制数量
    
    def _abstract_preferences(self, preferences: List[str]) -> List[str]:
        """抽象化偏好信息"""
        abstract = []
        for pref in preferences:
            # 只保留学习风格，移除具体内容
            if any(keyword in pref.lower() for keyword in ['visual', 'auditory', 'interactive', 'structured']):
                abstract.append(pref)
        return abstract
    
    def _anonymize_goals(self, goals: List[str]) -> List[str]:
        """匿名化目标信息"""
        anonymized = []
        for goal in goals:
            # 移除具体的项目名称和时间
            anonymized_goal = self._remove_specifics(goal)
            if anonymized_goal:
                anonymized.append(anonymized_goal)
        return anonymized
    
    def _generalize_focus(self, focus_areas: List[str]) -> List[str]:
        """泛化关注焦点"""
        return [self._abstract_topic(focus) for focus in focus_areas[:3]]
    
    def _abstract_topic(self, topic: str) -> str:
        """抽象化主题"""
        # 简化实现：移除具体名称，保留类别
        topic_lower = topic.lower()
        if 'programming' in topic_lower or 'coding' in topic_lower:
            return 'software development'
        elif 'machine learning' in topic_lower or 'ai' in topic_lower:
            return 'artificial intelligence'
        elif 'design' in topic_lower:
            return 'design'
        else:
            return 'general topic'
    
    def _remove_specifics(self, text: str) -> str:
        """移除具体信息"""
        # 移除日期、时间、具体数字等
        import re
        text = re.sub(r'\d{4}-\d{2}-\d{2}', '[DATE]', text)
        text = re.sub(r'\d+', '[NUMBER]', text)
        return text if text != '[DATE]' and text != '[NUMBER]' else ''
    
    def _remove_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """移除个人识别信息"""
        import re
        
        def clean_string(s: str) -> str:
            for pattern in self.sensitive_patterns:
                s = re.sub(pattern, '[REDACTED]', s)
            return s
        
        def clean_recursive(obj):
            if isinstance(obj, dict):
                return {k: clean_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_recursive(item) for item in obj]
            elif isinstance(obj, str):
                return clean_string(obj)
            else:
                return obj
        
        return clean_recursive(data)


class AppIntegrationAPI:
    """App集成API主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = FastAPI(
            title="ByenatOS App Integration API",
            description="ByenatOS应用集成API",
            version="1.0.0"
        )
        
        # 中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # 初始化组件
        self.auth_manager = None
        self.rate_limiter = None
        self.privacy_filter = PrivacyFilter()
        self.hinata_processor = None
        self.psp_engine = None
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
        self.rate_limiter = RateLimiter(redis_pool)
        
        self.hinata_processor = HiNATAProcessor(
            self.config['redis_url'],
            self.config['postgres_dsn']
        )
        await self.hinata_processor.initialize()
        
        self.psp_engine = PSPEngine(db_pool)
        
        self.storage_engine = StorageEngine(self.config)
        await self.storage_engine.initialize()
        
        # 创建数据库表
        await self._create_tables(db_pool)
    
    async def _create_tables(self, db_pool):
        """创建API相关数据库表"""
        async with db_pool.acquire() as conn:
            # App注册表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS app_registrations (
                    app_id TEXT PRIMARY KEY,
                    app_name TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    developer TEXT NOT NULL,
                    description TEXT,
                    permissions JSONB NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    webhook_url TEXT,
                    rate_limit INTEGER DEFAULT 1000,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_active TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX (api_key),
                    INDEX (app_name),
                    INDEX (created_at DESC)
                )
            ''')
            
            # API调用日志表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS api_call_logs (
                    id SERIAL PRIMARY KEY,
                    app_id TEXT NOT NULL,
                    user_id TEXT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time REAL NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX (app_id, created_at DESC),
                    INDEX (endpoint, created_at DESC)
                )
            ''')
    
    def _setup_routes(self):
        """设置API路由"""
        
        # 依赖注入
        security = HTTPBearer()
        
        async def get_current_app(credentials: HTTPAuthorizationCredentials = Security(security)) -> AppRegistration:
            """获取当前认证的App"""
            app = await self.auth_manager.authenticate_app(credentials.credentials)
            if not app:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            return app
        
        async def check_permission(required_permission: AppPermission):
            """检查权限装饰器"""
            def permission_checker(app: AppRegistration = Depends(get_current_app)):
                if required_permission not in app.permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission {required_permission.value} required"
                    )
                return app
            return permission_checker
        
        async def check_rate_limit(app: AppRegistration, user_id: str = None):
            """检查速率限制"""
            if not await self.rate_limiter.check_rate_limit(app.app_id, user_id or "system", app.rate_limit):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
        
        # 1. App注册接口
        @self.app.post("/api/apps/register", response_model=AppRegistrationResponse)
        async def register_app(registration: AppRegistrationModel):
            """注册新的App"""
            try:
                app_registration = await self.auth_manager.register_app(registration)
                
                return AppRegistrationResponse(
                    status="success",
                    app_id=app_registration.app_id,
                    api_key=app_registration.api_key,
                    granted_permissions=[p.value for p in app_registration.permissions],
                    rate_limit=app_registration.rate_limit
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # 2. HiNATA提交接口
        @self.app.post("/api/hinata/submit", response_model=HiNATASubmissionResponse)
        async def submit_hinata_batch(
            submission: HiNATABatchSubmissionModel,
            app: AppRegistration = Depends(check_permission(AppPermission.HINATA_SUBMIT))
        ):
            """提交HiNATA数据批次"""
            start_time = time.time()
            
            # 检查速率限制
            await check_rate_limit(app, submission.user_id)
            
            try:
                # 转换为内部格式
                hinata_batch = [asdict(hinata) for hinata in submission.hinata_batch]
                
                # 处理HiNATA
                results = await self.hinata_processor.process_hinata_batch(
                    hinata_batch, submission.user_id
                )
                
                # 统计结果
                successful_count = sum(1 for r in results if r.status.value == "completed")
                errors = [r.error_message for r in results if r.error_message]
                
                processing_time = time.time() - start_time
                
                return HiNATASubmissionResponse(
                    status="success" if successful_count > 0 else "failed",
                    processed_count=successful_count,
                    processing_time=processing_time,
                    errors=errors
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Processing failed: {str(e)}"
                )
        
        # 3. PSP上下文查询接口
        @self.app.post("/api/psp/context", response_model=PSPContextResponse)
        async def get_psp_context(
            request: PSPContextRequestModel,
            app: AppRegistration = Depends(check_permission(AppPermission.PSP_READ))
        ):
            """获取用户PSP上下文"""
            
            # 检查速率限制
            await check_rate_limit(app, request.user_id)
            
            try:
                # 获取PSP上下文
                raw_context = await self.psp_engine.get_psp_context_for_prompt(
                    request.user_id, request.current_request
                )
                
                # 隐私过滤
                filtered_context = self.privacy_filter.filter_psp_context(
                    raw_context, app.permissions
                )
                
                return PSPContextResponse(
                    user_id=request.user_id,
                    context=filtered_context,
                    last_updated=raw_context.get('last_updated', ''),
                    active_components_count=raw_context.get('active_components_count', 0)
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get PSP context: {str(e)}"
                )
        
        # 4. HiNATA检索接口
        @self.app.post("/api/hinata/search", response_model=RetrievalResponse)
        async def search_hinata(
            query: RetrievalQueryModel,
            app: AppRegistration = Depends(check_permission(AppPermission.STORAGE_ACCESS))
        ):
            """检索HiNATA数据"""
            start_time = time.time()
            
            # 检查速率限制
            await check_rate_limit(app, query.user_id)
            
            try:
                # 构建检索查询
                from Kernel.Core.StorageEngine import RetrievalQuery
                
                retrieval_query = RetrievalQuery(
                    user_id=query.user_id,
                    query_type="multi_strategy",
                    query_text=query.query_text,
                    semantic_vector=query.semantic_vector,
                    filters=query.filters,
                    limit=query.limit,
                    min_relevance_score=query.min_relevance_score
                )
                
                # 执行检索
                results = await self.storage_engine.multi_strategy_search(retrieval_query)
                
                # 格式化结果（移除敏感信息）
                formatted_results = []
                for result in results:
                    formatted_result = {
                        'hinata_id': result.hinata_id,
                        'relevance_score': result.relevance_score,
                        'content_summary': result.content_summary,
                        'metadata': {
                            'source': result.metadata.get('source', ''),
                            'timestamp': result.metadata.get('timestamp', ''),
                            'quality_score': result.metadata.get('quality_score', 0)
                        }
                    }
                    formatted_results.append(formatted_result)
                
                query_time = time.time() - start_time
                
                return RetrievalResponse(
                    total_results=len(results),
                    results=formatted_results,
                    query_time=query_time
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Search failed: {str(e)}"
                )
        
        # 5. 问题相关HiNATA检索接口（核心新增功能）
        @self.app.post("/api/hinata/query-relevant", response_model=HiNATAQueryResponse)
        async def query_relevant_hinata(
            query: HiNATAQueryModel,
            app: AppRegistration = Depends(check_permission(AppPermission.HINATA_QUERY))
        ):
            """根据问题检索相关HiNATA内容"""
            start_time = time.time()
            
            # 检查速率限制
            await check_rate_limit(app, query.user_id)
            
            try:
                # 生成查询向量（使用本地模型）
                query_vector = await self._generate_query_vector(query.question)
                
                # 构建检索查询
                from Kernel.Core.StorageEngine import RetrievalQuery
                
                retrieval_query = RetrievalQuery(
                    user_id=query.user_id,
                    query_type="question_focused",  # 专门针对问题的检索类型
                    query_text=query.question,
                    semantic_vector=query_vector,
                    limit=query.limit,
                    min_relevance_score=query.min_relevance_score
                )
                
                # 执行检索（与PSP无关的纯问题匹配）
                results = await self.storage_engine.multi_strategy_search(retrieval_query)
                
                # 格式化结果
                formatted_hinata = []
                for result in results:
                    hinata_item = {
                        'hinata_id': result.hinata_id,
                        'content_summary': result.content_summary,
                        'relevance_score': result.relevance_score,
                    }
                    
                    if query.include_metadata:
                        hinata_item['metadata'] = {
                            'source': result.metadata.get('source', ''),
                            'timestamp': result.metadata.get('timestamp', ''),
                            'attention_weight': result.metadata.get('attention_weight', 0),
                            'quality_score': result.metadata.get('quality_score', 0)
                        }
                    
                    formatted_hinata.append(hinata_item)
                
                query_time = time.time() - start_time
                
                return HiNATAQueryResponse(
                    user_id=query.user_id,
                    question=query.question,
                    relevant_hinata=formatted_hinata,
                    total_results=len(results),
                    query_time=query_time
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"HiNATA query failed: {str(e)}"
                )
        
        # 6. 个性化增强接口（PSP + HiNATA结合）
        @self.app.post("/api/enhancement/personalized", response_model=PersonalizedEnhancementResponse)
        async def get_personalized_enhancement(
            request: PersonalizedEnhancementModel,
            app: AppRegistration = Depends(check_permission(AppPermission.ENHANCEMENT_ACCESS))
        ):
            """获取个性化增强内容（PSP + 相关HiNATA）"""
            start_time = time.time()
            
            # 检查速率限制
            await check_rate_limit(app, request.user_id)
            
            try:
                # 并行获取PSP和相关HiNATA
                psp_task = self.psp_engine.get_psp_context_for_prompt(
                    request.user_id, request.question
                )
                
                # 获取相关HiNATA（复用上面的逻辑）
                query_vector = await self._generate_query_vector(request.question)
                retrieval_query = RetrievalQuery(
                    user_id=request.user_id,
                    query_type="question_focused",
                    query_text=request.question,
                    semantic_vector=query_vector,
                    limit=request.context_limit,
                    min_relevance_score=0.5
                )
                hinata_task = self.storage_engine.multi_strategy_search(retrieval_query)
                
                # 等待两个任务完成
                psp_context, hinata_results = await asyncio.gather(psp_task, hinata_task)
                
                # 生成个性化提示词
                personalized_prompt = await self._generate_personalized_prompt(
                    psp_context, request.question
                )
                
                # 格式化HiNATA知识组件
                knowledge_components = []
                for result in hinata_results:
                    knowledge_item = {
                        'content_summary': result.content_summary,
                        'relevance_score': result.relevance_score,
                        'source': result.metadata.get('source', ''),
                        'timestamp': result.metadata.get('timestamp', ''),
                        'component_type': 'knowledge'  # 明确标识为知识组件
                    }
                    knowledge_components.append(knowledge_item)
                
                # 生成PSP摘要（隐私过滤后）
                psp_summary = self.privacy_filter.filter_psp_context(
                    psp_context, app.permissions
                )
                
                processing_time = time.time() - start_time
                
                return PersonalizedEnhancementResponse(
                    user_id=request.user_id,
                    question=request.question,
                    personalized_prompt=personalized_prompt,  # PSP个性化组件
                    knowledge_components=knowledge_components,  # HiNATA知识组件
                    psp_summary=psp_summary if request.include_psp_details else {},
                    processing_time=processing_time
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Personalized enhancement failed: {str(e)}"
                )
        
        # 7. 用户认证接口
        @self.app.post("/api/auth/user-token")
        async def generate_user_token(
            user_id: str,
            app: AppRegistration = Depends(get_current_app)
        ):
            """生成用户会话token"""
            token = self.auth_manager.generate_user_token(user_id, app.app_id)
            
            return {
                "status": "success",
                "token": token,
                "expires_in": 86400  # 24小时
            }
        
        # 6. API状态和指标接口
        @self.app.get("/api/status")
        async def get_api_status():
            """获取API状态"""
            return {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/api/apps/{app_id}/metrics")
        async def get_app_metrics(
            app_id: str,
            app: AppRegistration = Depends(get_current_app)
        ):
            """获取App使用指标"""
            if app.app_id != app_id and AppPermission.ADMIN not in app.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            
            # 获取指标数据
            remaining_quota = await self.rate_limiter.get_remaining_quota(
                app_id, "system", app.rate_limit
            )
            
            return {
                "app_id": app_id,
                "rate_limit": app.rate_limit,
                "remaining_quota": remaining_quota,
                "last_active": app.last_active
            }
        
        # 7. 健康检查接口
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "ok"}
    
    async def _generate_query_vector(self, question: str) -> List[float]:
        """生成查询向量"""
        try:
            # 这里应该使用本地的嵌入模型
            # 暂时返回模拟向量，实际应该调用本地模型
            import numpy as np
            # 模拟向量生成 - 实际应该替换为真实的嵌入模型调用
            vector = np.random.rand(768).tolist()  # 假设使用768维向量
            return vector
        except Exception as e:
            # 如果向量生成失败，返回空列表，系统会使用其他检索策略
            return []
    
    async def _generate_personalized_prompt(self, psp_context: Dict[str, Any], question: str) -> str:
        """
        基于PSP上下文和问题生成个性化系统提示词
        
        注意：这里生成的是融合了PSP个性化信息的系统提示词，
        它是完整上下文的个性化组件部分，而不是完整上下文本身。
        完整上下文 = 这个个性化提示词 + HiNATA知识组件 + 用户问题
        """
        try:
            # 提取PSP核心信息（个性化组件）
            core_interests = psp_context.get('core_interests', [])
            learning_preferences = psp_context.get('learning_preferences', [])
            communication_style = psp_context.get('communication_style', [])
            
            # 构建个性化系统提示词（上下文的个性化组件）
            prompt_parts = []
            
            # 基础系统提示
            prompt_parts.append("You are an AI assistant that provides personalized responses.")
            
            # 融入用户个性化信息（PSP组件）
            if core_interests:
                interests_str = ", ".join(core_interests[:5])
                prompt_parts.append(f"User interests: {interests_str}.")
            
            if learning_preferences:
                preferences_str = ", ".join(learning_preferences[:3])
                prompt_parts.append(f"Learning style: {preferences_str}.")
            
            if communication_style:
                style_str = ", ".join(communication_style[:2])
                prompt_parts.append(f"Communication style: {style_str}.")
            
            # 指导AI如何使用知识组件
            prompt_parts.append("Use the provided knowledge context to give accurate answers.")
            prompt_parts.append("Combine your knowledge with the user's personalization preferences.")
            
            return " ".join(prompt_parts)
            
        except Exception as e:
            # 如果PSP处理失败，返回通用系统提示词
            return "You are a helpful AI assistant. Use the provided context to answer questions accurately."
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app


# 使用示例和启动脚本
async def create_app() -> FastAPI:
    """创建和初始化API应用"""
    config = {
        'redis_url': 'redis://localhost:6379',
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'cold_storage_path': '/data/cold_storage',
        'chroma_persist_dir': '/data/chroma',
        'elasticsearch_url': 'http://localhost:9200'
    }
    
    api = AppIntegrationAPI(config)
    await api.initialize()
    
    return api.get_app()


if __name__ == "__main__":
    import uvicorn
    
    # 开发环境启动
    uvicorn.run(
        "ApplicationFramework.APIs.AppIntegrationAPI:create_app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        factory=True
    )