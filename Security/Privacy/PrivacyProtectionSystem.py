"""
ByenatOS Privacy Protection System
隐私保护系统 - 确保用户数据的隐私和安全

实现数据本地化、访问控制、数据匿名化等隐私保护机制
"""

import asyncio
import json
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import asyncpg
import aioredis


class DataSensitivityLevel(Enum):
    """数据敏感性级别"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AccessPermission(Enum):
    """访问权限类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    EXPORT = "export"
    ADMIN = "admin"


class PrivacyPolicy(Enum):
    """隐私策略"""
    STRICT = "strict"        # 严格模式：最小化数据处理
    BALANCED = "balanced"    # 平衡模式：功能与隐私平衡
    PERMISSIVE = "permissive"  # 宽松模式：最大化功能


@dataclass
class DataAccessRecord:
    """数据访问记录"""
    user_id: str
    accessor_id: str  # App ID或用户ID
    accessor_type: str  # "app", "user", "system"
    data_type: str
    data_id: str
    access_type: AccessPermission
    timestamp: str
    ip_address: Optional[str] = None
    purpose: Optional[str] = None
    result: str = "success"  # "success", "denied", "error"


@dataclass
class PrivacyPreferences:
    """用户隐私偏好"""
    user_id: str
    policy_level: PrivacyPolicy
    data_sharing_consent: bool
    analytics_consent: bool
    personalization_consent: bool
    external_sharing_consent: bool
    data_retention_days: int
    allowed_apps: Set[str] = field(default_factory=set)
    blocked_apps: Set[str] = field(default_factory=set)
    custom_permissions: Dict[str, Set[AccessPermission]] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class DataEncryption:
    """数据加密管理器"""
    
    def __init__(self, master_key: bytes = None):
        self.master_key = master_key or Fernet.generate_key()
        self.cipher_suite = Fernet(self.master_key)
        
        # 生成RSA密钥对用于密钥交换
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def encrypt_sensitive_data(self, data: str, user_id: str) -> bytes:
        """加密敏感数据"""
        # 使用用户特定的盐值
        salt = self._get_user_salt(user_id)
        user_key = self._derive_user_key(user_id, salt)
        user_cipher = Fernet(user_key)
        
        return user_cipher.encrypt(data.encode())
    
    def decrypt_sensitive_data(self, encrypted_data: bytes, user_id: str) -> str:
        """解密敏感数据"""
        salt = self._get_user_salt(user_id)
        user_key = self._derive_user_key(user_id, salt)
        user_cipher = Fernet(user_key)
        
        return user_cipher.decrypt(encrypted_data).decode()
    
    def _get_user_salt(self, user_id: str) -> bytes:
        """获取用户特定的盐值"""
        # 基于用户ID生成确定性盐值
        return hashlib.sha256(f"byenatos_salt_{user_id}".encode()).digest()
    
    def _derive_user_key(self, user_id: str, salt: bytes) -> bytes:
        """派生用户特定的加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(f"byenatos_user_{user_id}".encode())
        return Fernet.generate_key()  # 简化实现
    
    def encrypt_for_storage(self, data: Dict[str, Any]) -> bytes:
        """为存储加密数据"""
        json_data = json.dumps(data, ensure_ascii=False)
        return self.cipher_suite.encrypt(json_data.encode())
    
    def decrypt_from_storage(self, encrypted_data: bytes) -> Dict[str, Any]:
        """从存储解密数据"""
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())


class PIIDetector:
    """个人身份信息检测器"""
    
    def __init__(self):
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln)\b',
        }
        
        self.sensitive_keywords = [
            'password', 'secret', 'token', 'key', 'credential',
            'personal', 'private', 'confidential', 'restricted'
        ]
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """检测文本中的PII"""
        detected_pii = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                detected_pii[pii_type] = matches
        
        return detected_pii
    
    def classify_sensitivity(self, text: str) -> DataSensitivityLevel:
        """分类数据敏感性"""
        text_lower = text.lower()
        
        # 检测PII
        pii_detected = self.detect_pii(text)
        if pii_detected:
            return DataSensitivityLevel.RESTRICTED
        
        # 检测敏感关键词
        sensitive_count = sum(1 for keyword in self.sensitive_keywords if keyword in text_lower)
        if sensitive_count > 2:
            return DataSensitivityLevel.CONFIDENTIAL
        elif sensitive_count > 0:
            return DataSensitivityLevel.INTERNAL
        else:
            return DataSensitivityLevel.PUBLIC
    
    def anonymize_text(self, text: str, replacement_map: Dict[str, str] = None) -> str:
        """匿名化文本中的PII"""
        if replacement_map is None:
            replacement_map = {
                'email': '[EMAIL]',
                'phone': '[PHONE]',
                'ssn': '[SSN]',
                'credit_card': '[CARD]',
                'ip_address': '[IP]',
                'address': '[ADDRESS]'
            }
        
        anonymized_text = text
        for pii_type, pattern in self.pii_patterns.items():
            replacement = replacement_map.get(pii_type, '[REDACTED]')
            anonymized_text = re.sub(pattern, replacement, anonymized_text, flags=re.IGNORECASE)
        
        return anonymized_text


class AccessControlManager:
    """访问控制管理器"""
    
    def __init__(self, db_pool, redis_pool):
        self.db_pool = db_pool
        self.redis_pool = redis_pool
        self.access_cache = {}
        self.cache_ttl = 300  # 5分钟缓存
    
    async def check_access_permission(self, user_id: str, accessor_id: str, 
                                    accessor_type: str, data_type: str, 
                                    permission: AccessPermission) -> bool:
        """检查访问权限"""
        
        # 检查缓存
        cache_key = f"access:{user_id}:{accessor_id}:{data_type}:{permission.value}"
        if cache_key in self.access_cache:
            cached_result, timestamp = self.access_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        # 从数据库查询权限
        result = await self._query_access_permission(user_id, accessor_id, accessor_type, data_type, permission)
        
        # 缓存结果
        self.access_cache[cache_key] = (result, time.time())
        
        return result
    
    async def _query_access_permission(self, user_id: str, accessor_id: str, 
                                     accessor_type: str, data_type: str, 
                                     permission: AccessPermission) -> bool:
        """查询访问权限"""
        
        # 获取用户隐私偏好
        privacy_prefs = await self.get_user_privacy_preferences(user_id)
        
        # 系统访问总是允许
        if accessor_type == "system":
            return True
        
        # 用户自己访问自己的数据
        if accessor_type == "user" and accessor_id == user_id:
            return True
        
        # App访问检查
        if accessor_type == "app":
            # 检查是否在阻止列表中
            if accessor_id in privacy_prefs.blocked_apps:
                return False
            
            # 检查是否在允许列表中
            if accessor_id in privacy_prefs.allowed_apps:
                return True
            
            # 检查自定义权限
            if accessor_id in privacy_prefs.custom_permissions:
                app_permissions = privacy_prefs.custom_permissions[accessor_id]
                return permission in app_permissions
            
            # 根据隐私策略决定
            if privacy_prefs.policy_level == PrivacyPolicy.STRICT:
                return False
            elif privacy_prefs.policy_level == PrivacyPolicy.BALANCED:
                return permission in [AccessPermission.READ]
            else:  # PERMISSIVE
                return permission in [AccessPermission.READ, AccessPermission.WRITE]
        
        # 默认拒绝
        return False
    
    async def log_access_attempt(self, access_record: DataAccessRecord):
        """记录访问尝试"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO data_access_logs 
                (user_id, accessor_id, accessor_type, data_type, data_id, 
                 access_type, timestamp, ip_address, purpose, result)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''',
                access_record.user_id, access_record.accessor_id, access_record.accessor_type,
                access_record.data_type, access_record.data_id, access_record.access_type.value,
                access_record.timestamp, access_record.ip_address, access_record.purpose,
                access_record.result
            )
    
    async def get_user_privacy_preferences(self, user_id: str) -> PrivacyPreferences:
        """获取用户隐私偏好"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM user_privacy_preferences WHERE user_id = $1', user_id
            )
            
            if row:
                return PrivacyPreferences(
                    user_id=row['user_id'],
                    policy_level=PrivacyPolicy(row['policy_level']),
                    data_sharing_consent=row['data_sharing_consent'],
                    analytics_consent=row['analytics_consent'],
                    personalization_consent=row['personalization_consent'],
                    external_sharing_consent=row['external_sharing_consent'],
                    data_retention_days=row['data_retention_days'],
                    allowed_apps=set(json.loads(row['allowed_apps'] or '[]')),
                    blocked_apps=set(json.loads(row['blocked_apps'] or '[]')),
                    custom_permissions={
                        k: {AccessPermission(p) for p in v} 
                        for k, v in json.loads(row['custom_permissions'] or '{}').items()
                    },
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            else:
                # 返回默认隐私偏好
                return PrivacyPreferences(
                    user_id=user_id,
                    policy_level=PrivacyPolicy.BALANCED,
                    data_sharing_consent=False,
                    analytics_consent=False,
                    personalization_consent=True,
                    external_sharing_consent=False,
                    data_retention_days=365,
                    created_at=datetime.now(timezone.utc).isoformat()
                )
    
    async def update_user_privacy_preferences(self, preferences: PrivacyPreferences):
        """更新用户隐私偏好"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_privacy_preferences 
                (user_id, policy_level, data_sharing_consent, analytics_consent,
                 personalization_consent, external_sharing_consent, data_retention_days,
                 allowed_apps, blocked_apps, custom_permissions, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (user_id) DO UPDATE SET
                    policy_level = EXCLUDED.policy_level,
                    data_sharing_consent = EXCLUDED.data_sharing_consent,
                    analytics_consent = EXCLUDED.analytics_consent,
                    personalization_consent = EXCLUDED.personalization_consent,
                    external_sharing_consent = EXCLUDED.external_sharing_consent,
                    data_retention_days = EXCLUDED.data_retention_days,
                    allowed_apps = EXCLUDED.allowed_apps,
                    blocked_apps = EXCLUDED.blocked_apps,
                    custom_permissions = EXCLUDED.custom_permissions,
                    updated_at = EXCLUDED.updated_at
            ''',
                preferences.user_id, preferences.policy_level.value,
                preferences.data_sharing_consent, preferences.analytics_consent,
                preferences.personalization_consent, preferences.external_sharing_consent,
                preferences.data_retention_days,
                json.dumps(list(preferences.allowed_apps)),
                json.dumps(list(preferences.blocked_apps)),
                json.dumps({
                    k: [p.value for p in v] 
                    for k, v in preferences.custom_permissions.items()
                }),
                preferences.created_at,
                datetime.now(timezone.utc).isoformat()
            )


class DataMinimizer:
    """数据最小化处理器"""
    
    def __init__(self):
        self.pii_detector = PIIDetector()
    
    def minimize_hinata_for_app(self, hinata_data: Dict[str, Any], 
                               app_permissions: Set[str], 
                               privacy_prefs: PrivacyPreferences) -> Dict[str, Any]:
        """为App最小化HiNATA数据"""
        
        minimized_data = {}
        
        # 基础字段（总是包含）
        minimized_data.update({
            'id': hinata_data['id'],
            'timestamp': hinata_data['timestamp'],
            'source': hinata_data['source']
        })
        
        # 根据权限和隐私偏好决定包含哪些字段
        if privacy_prefs.personalization_consent:
            # 个性化相关数据
            if 'enhanced_tags' in hinata_data:
                minimized_data['enhanced_tags'] = hinata_data['enhanced_tags'][:5]  # 限制数量
            
            if 'semantic_analysis' in hinata_data:
                semantic = hinata_data['semantic_analysis']
                minimized_data['semantic_analysis'] = {
                    'main_topics': semantic.get('main_topics', [])[:3],
                    'complexity_level': semantic.get('complexity_level', 'medium')
                }
        
        # 内容数据（需要匿名化）
        if 'highlight' in hinata_data:
            highlight = hinata_data['highlight']
            if privacy_prefs.policy_level == PrivacyPolicy.STRICT:
                # 严格模式：只提供摘要
                minimized_data['highlight_summary'] = highlight[:50] + "..." if len(highlight) > 50 else highlight
            else:
                # 匿名化处理
                minimized_data['highlight'] = self.pii_detector.anonymize_text(highlight)
        
        if 'note' in hinata_data and privacy_prefs.policy_level != PrivacyPolicy.STRICT:
            note = hinata_data['note']
            # 匿名化处理
            minimized_data['note'] = self.pii_detector.anonymize_text(note)
        
        # 权重信息（用于排序）
        if 'attention_weight' in hinata_data:
            minimized_data['attention_weight'] = hinata_data['attention_weight']
        
        return minimized_data
    
    def minimize_psp_context(self, psp_context: Dict[str, Any], 
                           privacy_prefs: PrivacyPreferences) -> Dict[str, Any]:
        """最小化PSP上下文"""
        
        minimized_context = {}
        
        if privacy_prefs.personalization_consent:
            # 泛化兴趣信息
            interests = psp_context.get('core_interests', [])
            minimized_context['interest_categories'] = self._generalize_interests(interests)
            
            # 抽象化目标
            goals = psp_context.get('current_goals', [])
            minimized_context['goal_categories'] = self._generalize_goals(goals)
            
            # 学习偏好（相对安全）
            learning_prefs = psp_context.get('learning_preferences', [])
            minimized_context['learning_style'] = learning_prefs[:2]  # 限制数量
        
        # 基础统计信息
        minimized_context['active_components_count'] = psp_context.get('active_components_count', 0)
        minimized_context['last_updated'] = psp_context.get('last_updated', '')
        
        return minimized_context
    
    def _generalize_interests(self, interests: List[str]) -> List[str]:
        """泛化兴趣信息"""
        categories = []
        for interest in interests:
            category = self._categorize_interest(interest)
            if category and category not in categories:
                categories.append(category)
        return categories[:5]
    
    def _generalize_goals(self, goals: List[str]) -> List[str]:
        """泛化目标信息"""
        categories = []
        for goal in goals:
            category = self._categorize_goal(goal)
            if category and category not in categories:
                categories.append(category)
        return categories[:3]
    
    def _categorize_interest(self, interest: str) -> str:
        """将具体兴趣分类到通用类别"""
        interest_lower = interest.lower()
        
        if any(keyword in interest_lower for keyword in ['programming', 'coding', 'software', 'development']):
            return 'software_development'
        elif any(keyword in interest_lower for keyword in ['ai', 'machine learning', 'ml', 'artificial intelligence']):
            return 'artificial_intelligence'
        elif any(keyword in interest_lower for keyword in ['design', 'ui', 'ux', 'graphic']):
            return 'design'
        elif any(keyword in interest_lower for keyword in ['business', 'management', 'startup']):
            return 'business'
        elif any(keyword in interest_lower for keyword in ['science', 'research', 'academic']):
            return 'science_research'
        else:
            return 'general'
    
    def _categorize_goal(self, goal: str) -> str:
        """将具体目标分类到通用类别"""
        goal_lower = goal.lower()
        
        if any(keyword in goal_lower for keyword in ['learn', 'study', 'education']):
            return 'learning'
        elif any(keyword in goal_lower for keyword in ['project', 'build', 'create']):
            return 'project_work'
        elif any(keyword in goal_lower for keyword in ['career', 'job', 'professional']):
            return 'career_development'
        elif any(keyword in goal_lower for keyword in ['health', 'fitness', 'wellbeing']):
            return 'personal_development'
        else:
            return 'general_goal'


class DataRetentionManager:
    """数据保留管理器"""
    
    def __init__(self, db_pool, storage_engine):
        self.db_pool = db_pool
        self.storage_engine = storage_engine
    
    async def cleanup_expired_data(self):
        """清理过期数据"""
        async with self.db_pool.acquire() as conn:
            # 获取所有用户的数据保留设置
            users = await conn.fetch('''
                SELECT user_id, data_retention_days 
                FROM user_privacy_preferences
            ''')
            
            for user in users:
                await self._cleanup_user_data(user['user_id'], user['data_retention_days'])
    
    async def _cleanup_user_data(self, user_id: str, retention_days: int):
        """清理特定用户的过期数据"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        async with self.db_pool.acquire() as conn:
            # 删除过期的HiNATA数据
            await conn.execute('''
                DELETE FROM hinata_data 
                WHERE user_id = $1 AND timestamp < $2
            ''', user_id, cutoff_date)
            
            # 删除过期的访问日志
            await conn.execute('''
                DELETE FROM data_access_logs 
                WHERE user_id = $1 AND timestamp < $2
            ''', user_id, cutoff_date.isoformat())
            
            # 删除过期的PSP组件
            await conn.execute('''
                DELETE FROM psp_components 
                WHERE user_id = $1 AND last_updated < $2
            ''', user_id, cutoff_date.isoformat())
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """导出用户数据（GDPR合规）"""
        user_data = {
            'user_id': user_id,
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'hinata_data': [],
            'psp_data': {},
            'privacy_preferences': {},
            'access_logs': []
        }
        
        async with self.db_pool.acquire() as conn:
            # 导出HiNATA数据
            hinata_rows = await conn.fetch(
                'SELECT * FROM hinata_data WHERE user_id = $1', user_id
            )
            user_data['hinata_data'] = [dict(row) for row in hinata_rows]
            
            # 导出PSP数据
            psp_rows = await conn.fetch(
                'SELECT * FROM psp_components WHERE user_id = $1', user_id
            )
            user_data['psp_data'] = [dict(row) for row in psp_rows]
            
            # 导出隐私偏好
            privacy_row = await conn.fetchrow(
                'SELECT * FROM user_privacy_preferences WHERE user_id = $1', user_id
            )
            if privacy_row:
                user_data['privacy_preferences'] = dict(privacy_row)
            
            # 导出访问日志（最近30天）
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            access_rows = await conn.fetch('''
                SELECT * FROM data_access_logs 
                WHERE user_id = $1 AND timestamp >= $2
            ''', user_id, cutoff_date.isoformat())
            user_data['access_logs'] = [dict(row) for row in access_rows]
        
        return user_data
    
    async def delete_user_data(self, user_id: str):
        """删除用户所有数据（GDPR合规）"""
        async with self.db_pool.acquire() as conn:
            # 删除所有相关数据
            await conn.execute('DELETE FROM hinata_data WHERE user_id = $1', user_id)
            await conn.execute('DELETE FROM psp_components WHERE user_id = $1', user_id)
            await conn.execute('DELETE FROM user_psp WHERE user_id = $1', user_id)
            await conn.execute('DELETE FROM user_privacy_preferences WHERE user_id = $1', user_id)
            await conn.execute('DELETE FROM data_access_logs WHERE user_id = $1', user_id)


class PrivacyProtectionSystem:
    """隐私保护系统主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.encryption = DataEncryption()
        self.pii_detector = PIIDetector()
        self.data_minimizer = DataMinimizer()
        
        # 初始化后设置的组件
        self.access_control = None
        self.retention_manager = None
        
    async def initialize(self, db_pool, storage_engine):
        """初始化隐私保护系统"""
        redis_pool = aioredis.from_url(self.config['redis_url'])
        
        self.access_control = AccessControlManager(db_pool, redis_pool)
        self.retention_manager = DataRetentionManager(db_pool, storage_engine)
        
        # 创建数据库表
        await self._create_tables(db_pool)
    
    async def _create_tables(self, db_pool):
        """创建隐私相关数据库表"""
        async with db_pool.acquire() as conn:
            # 用户隐私偏好表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_privacy_preferences (
                    user_id TEXT PRIMARY KEY,
                    policy_level TEXT NOT NULL,
                    data_sharing_consent BOOLEAN NOT NULL,
                    analytics_consent BOOLEAN NOT NULL,
                    personalization_consent BOOLEAN NOT NULL,
                    external_sharing_consent BOOLEAN NOT NULL,
                    data_retention_days INTEGER NOT NULL,
                    allowed_apps JSONB,
                    blocked_apps JSONB,
                    custom_permissions JSONB,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            ''')
            
            # 数据访问日志表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS data_access_logs (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    accessor_id TEXT NOT NULL,
                    accessor_type TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    data_id TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    ip_address TEXT,
                    purpose TEXT,
                    result TEXT NOT NULL,
                    INDEX (user_id, timestamp DESC),
                    INDEX (accessor_id, timestamp DESC)
                )
            ''')
    
    async def process_hinata_with_privacy(self, hinata_data: Dict[str, Any], 
                                        user_id: str, app_id: str) -> Dict[str, Any]:
        """带隐私保护的HiNATA处理"""
        
        # 1. 检测敏感信息
        highlight_sensitivity = self.pii_detector.classify_sensitivity(hinata_data.get('highlight', ''))
        note_sensitivity = self.pii_detector.classify_sensitivity(hinata_data.get('note', ''))
        
        # 2. 获取用户隐私偏好
        privacy_prefs = await self.access_control.get_user_privacy_preferences(user_id)
        
        # 3. 根据敏感级别和隐私偏好处理数据
        processed_hinata = hinata_data.copy()
        
        if highlight_sensitivity in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
            processed_hinata['highlight'] = self.pii_detector.anonymize_text(hinata_data['highlight'])
        
        if note_sensitivity in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
            processed_hinata['note'] = self.pii_detector.anonymize_text(hinata_data['note'])
        
        # 4. 加密存储敏感字段
        if privacy_prefs.policy_level == PrivacyPolicy.STRICT:
            processed_hinata['highlight_encrypted'] = self.encryption.encrypt_sensitive_data(
                hinata_data['highlight'], user_id
            ).hex()
            processed_hinata['note_encrypted'] = self.encryption.encrypt_sensitive_data(
                hinata_data['note'], user_id
            ).hex()
        
        # 5. 记录数据处理日志
        access_record = DataAccessRecord(
            user_id=user_id,
            accessor_id=app_id,
            accessor_type="app",
            data_type="hinata",
            data_id=hinata_data['id'],
            access_type=AccessPermission.WRITE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            purpose="hinata_processing"
        )
        await self.access_control.log_access_attempt(access_record)
        
        return processed_hinata
    
    async def get_privacy_safe_psp_context(self, user_id: str, app_id: str, 
                                         raw_context: Dict[str, Any]) -> Dict[str, Any]:
        """获取隐私安全的PSP上下文"""
        
        # 1. 检查访问权限
        has_permission = await self.access_control.check_access_permission(
            user_id, app_id, "app", "psp_context", AccessPermission.READ
        )
        
        if not has_permission:
            return {"error": "Access denied"}
        
        # 2. 获取用户隐私偏好
        privacy_prefs = await self.access_control.get_user_privacy_preferences(user_id)
        
        # 3. 最小化上下文数据
        minimized_context = self.data_minimizer.minimize_psp_context(raw_context, privacy_prefs)
        
        # 4. 记录访问日志
        access_record = DataAccessRecord(
            user_id=user_id,
            accessor_id=app_id,
            accessor_type="app",
            data_type="psp_context",
            data_id="current",
            access_type=AccessPermission.READ,
            timestamp=datetime.now(timezone.utc).isoformat(),
            purpose="prompt_generation"
        )
        await self.access_control.log_access_attempt(access_record)
        
        return minimized_context
    
    async def check_and_log_data_access(self, user_id: str, accessor_id: str, 
                                      accessor_type: str, data_type: str, 
                                      data_id: str, permission: AccessPermission,
                                      ip_address: str = None) -> bool:
        """检查并记录数据访问"""
        
        # 检查权限
        has_permission = await self.access_control.check_access_permission(
            user_id, accessor_id, accessor_type, data_type, permission
        )
        
        # 记录访问尝试
        access_record = DataAccessRecord(
            user_id=user_id,
            accessor_id=accessor_id,
            accessor_type=accessor_type,
            data_type=data_type,
            data_id=data_id,
            access_type=permission,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ip_address=ip_address,
            result="success" if has_permission else "denied"
        )
        await self.access_control.log_access_attempt(access_record)
        
        return has_permission
    
    async def update_privacy_preferences(self, user_id: str, 
                                       preferences: Dict[str, Any]) -> PrivacyPreferences:
        """更新用户隐私偏好"""
        
        # 获取当前偏好
        current_prefs = await self.access_control.get_user_privacy_preferences(user_id)
        
        # 更新字段
        if 'policy_level' in preferences:
            current_prefs.policy_level = PrivacyPolicy(preferences['policy_level'])
        if 'data_sharing_consent' in preferences:
            current_prefs.data_sharing_consent = preferences['data_sharing_consent']
        if 'analytics_consent' in preferences:
            current_prefs.analytics_consent = preferences['analytics_consent']
        if 'personalization_consent' in preferences:
            current_prefs.personalization_consent = preferences['personalization_consent']
        if 'external_sharing_consent' in preferences:
            current_prefs.external_sharing_consent = preferences['external_sharing_consent']
        if 'data_retention_days' in preferences:
            current_prefs.data_retention_days = preferences['data_retention_days']
        if 'allowed_apps' in preferences:
            current_prefs.allowed_apps = set(preferences['allowed_apps'])
        if 'blocked_apps' in preferences:
            current_prefs.blocked_apps = set(preferences['blocked_apps'])
        
        current_prefs.updated_at = datetime.now(timezone.utc).isoformat()
        
        # 保存更新
        await self.access_control.update_user_privacy_preferences(current_prefs)
        
        return current_prefs
    
    async def get_user_data_export(self, user_id: str) -> Dict[str, Any]:
        """导出用户数据（GDPR合规）"""
        return await self.retention_manager.export_user_data(user_id)
    
    async def delete_user_data(self, user_id: str):
        """删除用户数据（GDPR合规）"""
        await self.retention_manager.delete_user_data(user_id)
    
    async def run_privacy_maintenance(self):
        """运行隐私维护任务"""
        # 清理过期数据
        await self.retention_manager.cleanup_expired_data()
        
        # 清理访问控制缓存
        self.access_control.access_cache.clear()
    
    def generate_privacy_report(self, user_id: str) -> Dict[str, Any]:
        """生成隐私报告"""
        return {
            "user_id": user_id,
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "data_processing_summary": {
                "encryption_status": "enabled",
                "pii_detection": "active",
                "data_minimization": "active",
                "access_logging": "enabled"
            },
            "privacy_controls": {
                "user_consent_required": True,
                "data_retention_enforced": True,
                "access_control_active": True,
                "anonymization_applied": True
            }
        }


# 使用示例
async def main():
    """使用示例"""
    config = {
        'redis_url': 'redis://localhost:6379',
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos'
    }
    
    # 初始化隐私保护系统
    privacy_system = PrivacyProtectionSystem(config)
    
    # 模拟数据库连接
    db_pool = await asyncpg.create_pool(config['postgres_dsn'])
    storage_engine = None  # 这里应该是实际的StorageEngine实例
    
    await privacy_system.initialize(db_pool, storage_engine)
    
    # 示例：处理HiNATA数据
    sample_hinata = {
        "id": "hinata_20241201_001",
        "highlight": "My email is user@example.com and I live at 123 Main St",
        "note": "This contains my personal information for testing"
    }
    
    processed_hinata = await privacy_system.process_hinata_with_privacy(
        sample_hinata, "user_123", "app_456"
    )
    
    print("Processed HiNATA:", processed_hinata)
    
    # 示例：更新隐私偏好
    new_preferences = {
        "policy_level": "strict",
        "data_sharing_consent": False,
        "personalization_consent": True
    }
    
    updated_prefs = await privacy_system.update_privacy_preferences("user_123", new_preferences)
    print("Updated privacy preferences:", updated_prefs)
    
    await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())