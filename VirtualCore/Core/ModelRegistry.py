"""
ByenatOS 虚拟系统模型注册表和发现系统
===============================

这是byenatOS虚拟系统的本地AI模型管理中心，类似于传统操作系统的设备管理器。
它负责管理所有可用的本地AI模型、版本信息、兼容性数据和自动发现机制。

类比：就像Windows设备管理器记录所有硬件设备驱动一样，
     这里记录了所有可以作为"虚拟CPU"的本地AI模型及其规格。
"""

import asyncio
import json
import sqlite3
import aiofiles
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from .LLMInterface import (
    ModelSpecification, ModelType, ModelSize, ComputeRequirement,
    ILLMDriverFactory, LLMDriverException
)

class RegistrySource(Enum):
    """注册表数据源类型"""
    LOCAL = "local"                 # 本地安装的模型
    OFFICIAL = "official"           # 官方模型仓库
    COMMUNITY = "community"         # 社区贡献模型
    PRIVATE = "private"             # 私有模型仓库
    CLOUD = "cloud"                 # 云端API模型

class ModelStatus(Enum):
    """模型状态"""
    AVAILABLE = "available"         # 可用
    DEPRECATED = "deprecated"       # 已弃用
    EXPERIMENTAL = "experimental"   # 实验性
    BETA = "beta"                  # 测试版
    STABLE = "stable"              # 稳定版
    INCOMPATIBLE = "incompatible"   # 不兼容

@dataclass
class ModelRegistryEntry:
    """模型注册表条目"""
    Specification: ModelSpecification
    Source: RegistrySource
    Status: ModelStatus
    RegistrationTime: datetime
    LastUpdated: datetime
    DownloadUrl: Optional[str] = None
    InstallPath: Optional[str] = None
    Checksum: Optional[str] = None
    Dependencies: List[str] = None
    Conflicts: List[str] = None
    MinSystemVersion: Optional[str] = None
    MaxSystemVersion: Optional[str] = None
    Tags: List[str] = None
    Metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.Dependencies is None:
            self.Dependencies = []
        if self.Conflicts is None:
            self.Conflicts = []
        if self.Tags is None:
            self.Tags = []
        if self.Metadata is None:
            self.Metadata = {}

@dataclass
class RepositoryConfig:
    """模型仓库配置"""
    Name: str
    Url: str
    Type: RegistrySource
    Enabled: bool = True
    Priority: int = 0
    AuthToken: Optional[str] = None
    LastSync: Optional[datetime] = None
    SyncInterval: int = 3600  # 秒
    Metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.Metadata is None:
            self.Metadata = {}

class ModelRegistry:
    """
    模型注册表和发现系统
    ==================
    
    核心功能：
    1. 模型注册和索引 - 维护所有可用模型的目录
    2. 自动发现机制 - 自动扫描和发现新模型
    3. 版本管理 - 跟踪模型版本和更新
    4. 兼容性检查 - 验证模型与系统的兼容性
    5. 依赖解析 - 处理模型之间的依赖关系
    6. 仓库同步 - 与远程模型仓库同步
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        初始化模型注册表
        
        Args:
            registry_path: 注册表数据库路径
        """
        self._registry_path = registry_path or "data/model_registry.db"
        self._registry_dir = Path(self._registry_path).parent
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据存储
        self._models: Dict[str, ModelRegistryEntry] = {}
        self._repositories: Dict[str, RepositoryConfig] = {}
        self._discovery_paths: Set[str] = set()
        
        # 缓存和索引
        self._models_by_type: Dict[ModelType, List[str]] = {}
        self._models_by_vendor: Dict[str, List[str]] = {}
        self._models_by_size: Dict[ModelSize, List[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        
        # 异步任务管理
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._sync_lock = asyncio.Lock()
        
        # 线程池
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 配置
        self._auto_discovery_enabled = True
        self._auto_sync_enabled = True
        self._discovery_interval = 300  # 5分钟
        self._max_cache_age = 3600     # 1小时
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 初始化
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """初始化注册表"""
        try:
            # 创建数据库表
            await self._create_database_schema()
            
            # 加载现有数据
            await self._load_registry_data()
            
            # 加载默认仓库配置
            await self._load_default_repositories()
            
            # 重建索引
            await self._rebuild_indexes()
            
            # 启动后台任务
            if self._auto_discovery_enabled:
                self._start_discovery_task()
            
            if self._auto_sync_enabled:
                self._start_sync_task()
            
            self._logger.info("Model registry initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize model registry: {e}")
            raise
    
    async def RegisterModel(self, entry: ModelRegistryEntry) -> bool:
        """
        注册模型
        
        Args:
            entry: 模型注册表条目
            
        Returns:
            bool: 注册是否成功
        """
        try:
            model_id = entry.Specification.ModelId
            
            # 验证模型规格
            if not self._validate_model_specification(entry.Specification):
                raise ValueError(f"Invalid model specification for '{model_id}'")
            
            # 检查冲突
            conflicts = await self._check_conflicts(entry)
            if conflicts:
                self._logger.warning(f"Model '{model_id}' has conflicts: {conflicts}")
            
            # 更新注册表
            entry.LastUpdated = datetime.now()
            if model_id not in self._models:
                entry.RegistrationTime = datetime.now()
            
            self._models[model_id] = entry
            
            # 更新索引
            await self._update_indexes(model_id, entry)
            
            # 持久化到数据库
            await self._save_model_to_db(entry)
            
            self._logger.info(f"Registered model '{model_id}' from {entry.Source.value}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register model: {e}")
            return False
    
    async def UnregisterModel(self, model_id: str) -> bool:
        """
        注销模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if model_id not in self._models:
                self._logger.warning(f"Model '{model_id}' not found in registry")
                return True
            
            # 从内存中移除
            entry = self._models.pop(model_id)
            
            # 更新索引
            await self._remove_from_indexes(model_id, entry)
            
            # 从数据库中删除
            await self._delete_model_from_db(model_id)
            
            self._logger.info(f"Unregistered model '{model_id}'")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to unregister model '{model_id}': {e}")
            return False
    
    async def FindModels(self, criteria: Dict[str, Any]) -> List[ModelRegistryEntry]:
        """
        根据条件查找模型
        
        Args:
            criteria: 查找条件字典
                - model_type: ModelType
                - vendor: str
                - model_size: ModelSize
                - min_parameters: int
                - max_parameters: int
                - tags: List[str]
                - status: ModelStatus
                - local_only: bool
                
        Returns:
            List[ModelRegistryEntry]: 匹配的模型列表
        """
        matching_models = []
        
        for model_id, entry in self._models.items():
            if await self._matches_criteria(entry, criteria):
                matching_models.append(entry)
        
        # 按优先级排序
        matching_models.sort(key=lambda x: self._calculate_model_priority(x), reverse=True)
        
        return matching_models
    
    async def GetModel(self, model_id: str) -> Optional[ModelRegistryEntry]:
        """获取指定模型的注册信息"""
        return self._models.get(model_id)
    
    async def GetAllModels(self) -> List[ModelRegistryEntry]:
        """获取所有注册的模型"""
        return list(self._models.values())
    
    async def GetModelsByType(self, model_type: ModelType) -> List[ModelRegistryEntry]:
        """按类型获取模型"""
        model_ids = self._models_by_type.get(model_type, [])
        return [self._models[model_id] for model_id in model_ids if model_id in self._models]
    
    async def GetModelsByVendor(self, vendor: str) -> List[ModelRegistryEntry]:
        """按厂商获取模型"""
        model_ids = self._models_by_vendor.get(vendor, [])
        return [self._models[model_id] for model_id in model_ids if model_id in self._models]
    
    async def GetModelsByTag(self, tag: str) -> List[ModelRegistryEntry]:
        """按标签获取模型"""
        model_ids = self._tag_index.get(tag, set())
        return [self._models[model_id] for model_id in model_ids if model_id in self._models]
    
    async def DiscoverLocalModels(self, search_paths: Optional[List[str]] = None) -> int:
        """
        发现本地模型
        
        Args:
            search_paths: 搜索路径列表
            
        Returns:
            int: 发现的模型数量
        """
        if search_paths:
            self._discovery_paths.update(search_paths)
        
        discovered_count = 0
        search_paths = search_paths or list(self._discovery_paths)
        
        for search_path in search_paths:
            try:
                count = await self._scan_directory_for_models(search_path)
                discovered_count += count
            except Exception as e:
                self._logger.error(f"Failed to scan directory '{search_path}': {e}")
        
        self._logger.info(f"Discovered {discovered_count} local models")
        return discovered_count
    
    async def SyncWithRepositories(self, force: bool = False) -> Dict[str, int]:
        """
        与远程仓库同步
        
        Args:
            force: 是否强制同步
            
        Returns:
            Dict[str, int]: 每个仓库同步的模型数量
        """
        sync_results = {}
        
        async with self._sync_lock:
            for repo_name, repo_config in self._repositories.items():
                if not repo_config.Enabled:
                    continue
                
                try:
                    # 检查是否需要同步
                    if not force and not self._needs_sync(repo_config):
                        continue
                    
                    count = await self._sync_with_repository(repo_config)
                    sync_results[repo_name] = count
                    
                    # 更新同步时间
                    repo_config.LastSync = datetime.now()
                    
                except Exception as e:
                    self._logger.error(f"Failed to sync with repository '{repo_name}': {e}")
                    sync_results[repo_name] = 0
        
        return sync_results
    
    async def AddRepository(self, config: RepositoryConfig) -> bool:
        """添加模型仓库"""
        try:
            # 验证仓库配置
            if not await self._validate_repository_config(config):
                return False
            
            self._repositories[config.Name] = config
            
            # 保存到数据库
            await self._save_repository_to_db(config)
            
            # 初始同步
            if config.Enabled:
                await self._sync_with_repository(config)
            
            self._logger.info(f"Added repository '{config.Name}'")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to add repository: {e}")
            return False
    
    async def RemoveRepository(self, repo_name: str) -> bool:
        """移除模型仓库"""
        try:
            if repo_name not in self._repositories:
                return True
            
            # 移除该仓库的所有模型
            models_to_remove = [
                model_id for model_id, entry in self._models.items()
                if entry.Metadata.get('repository') == repo_name
            ]
            
            for model_id in models_to_remove:
                await self.UnregisterModel(model_id)
            
            # 移除仓库配置
            del self._repositories[repo_name]
            await self._delete_repository_from_db(repo_name)
            
            self._logger.info(f"Removed repository '{repo_name}' and {len(models_to_remove)} models")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to remove repository '{repo_name}': {e}")
            return False
    
    async def CheckCompatibility(self, model_id: str, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查模型兼容性
        
        Args:
            model_id: 模型ID
            system_info: 系统信息
            
        Returns:
            Dict[str, Any]: 兼容性检查结果
        """
        entry = self._models.get(model_id)
        if not entry:
            return {'compatible': False, 'reason': 'Model not found'}
        
        result = {
            'compatible': True,
            'warnings': [],
            'requirements': {},
            'recommendations': []
        }
        
        spec = entry.Specification
        
        # 检查计算需求
        system_compute = system_info.get('compute_capability', ComputeRequirement.LOW)
        if spec.ComputeRequirement.value > system_compute.value:
            result['compatible'] = False
            result['warnings'].append(f"Insufficient compute capability. Required: {spec.ComputeRequirement.value}, Available: {system_compute.value}")
        
        # 检查内存需求
        estimated_memory = self._estimate_memory_requirement(spec)
        available_memory = system_info.get('available_memory_gb', 0)
        if estimated_memory > available_memory:
            result['compatible'] = False
            result['warnings'].append(f"Insufficient memory. Required: {estimated_memory}GB, Available: {available_memory}GB")
        
        # 检查系统版本
        if entry.MinSystemVersion:
            current_version = system_info.get('system_version', '0.0.0')
            if self._compare_versions(current_version, entry.MinSystemVersion) < 0:
                result['compatible'] = False
                result['warnings'].append(f"System version too old. Required: >={entry.MinSystemVersion}, Current: {current_version}")
        
        if entry.MaxSystemVersion:
            current_version = system_info.get('system_version', '999.999.999')
            if self._compare_versions(current_version, entry.MaxSystemVersion) > 0:
                result['compatible'] = False
                result['warnings'].append(f"System version too new. Required: <={entry.MaxSystemVersion}, Current: {current_version}")
        
        # 检查依赖
        for dependency in entry.Dependencies:
            if dependency not in self._models:
                result['compatible'] = False
                result['warnings'].append(f"Missing dependency: {dependency}")
        
        # 检查冲突
        for conflict in entry.Conflicts:
            if conflict in self._models:
                result['warnings'].append(f"Potential conflict with: {conflict}")
        
        return result
    
    async def GetRegistryStatistics(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        stats = {
            'total_models': len(self._models),
            'by_type': {},
            'by_vendor': {},
            'by_size': {},
            'by_source': {},
            'by_status': {},
            'total_repositories': len(self._repositories),
            'enabled_repositories': sum(1 for repo in self._repositories.values() if repo.Enabled),
            'last_discovery': None,
            'last_sync': None
        }
        
        # 按类型统计
        for model_type in ModelType:
            stats['by_type'][model_type.value] = len(self._models_by_type.get(model_type, []))
        
        # 按厂商统计
        for vendor, model_ids in self._models_by_vendor.items():
            stats['by_vendor'][vendor] = len(model_ids)
        
        # 按规模统计
        for size in ModelSize:
            stats['by_size'][size.value] = len(self._models_by_size.get(size, []))
        
        # 按来源和状态统计
        for entry in self._models.values():
            source = entry.Source.value
            status = entry.Status.value
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        return stats
    
    async def Shutdown(self):
        """关闭注册表"""
        self._logger.info("Shutting down model registry...")
        
        # 设置关闭事件
        self._shutdown_event.set()
        
        # 等待后台任务完成
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # 关闭线程池
        self._thread_pool.shutdown(wait=True)
        
        self._logger.info("Model registry shutdown complete")
    
    # 私有方法实现
    async def _create_database_schema(self):
        """创建数据库表结构"""
        def create_tables(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 模型表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
                    specification TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    registration_time TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    download_url TEXT,
                    install_path TEXT,
                    checksum TEXT,
                    dependencies TEXT,
                    conflicts TEXT,
                    min_system_version TEXT,
                    max_system_version TEXT,
                    tags TEXT,
                    metadata TEXT
                )
            ''')
            
            # 仓库表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    name TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    type TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    auth_token TEXT,
                    last_sync TEXT,
                    sync_interval INTEGER NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_type ON models (source, status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_vendor ON models (model_id)')
            
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, create_tables, self._registry_path
        )
    
    async def _load_registry_data(self):
        """从数据库加载注册表数据"""
        def load_data(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            models = {}
            repositories = {}
            
            try:
                # 加载模型
                cursor.execute('SELECT * FROM models')
                for row in cursor.fetchall():
                    try:
                        model_id = row[0]
                        spec_data = json.loads(row[1])
                        spec = ModelSpecification(**spec_data)
                        
                        entry = ModelRegistryEntry(
                            Specification=spec,
                            Source=RegistrySource(row[2]),
                            Status=ModelStatus(row[3]),
                            RegistrationTime=datetime.fromisoformat(row[4]),
                            LastUpdated=datetime.fromisoformat(row[5]),
                            DownloadUrl=row[6],
                            InstallPath=row[7],
                            Checksum=row[8],
                            Dependencies=json.loads(row[9]) if row[9] else [],
                            Conflicts=json.loads(row[10]) if row[10] else [],
                            MinSystemVersion=row[11],
                            MaxSystemVersion=row[12],
                            Tags=json.loads(row[13]) if row[13] else [],
                            Metadata=json.loads(row[14]) if row[14] else {}
                        )
                        
                        models[model_id] = entry
                    except Exception as e:
                        logging.error(f"Failed to load model {row[0]}: {e}")
                
                # 加载仓库
                cursor.execute('SELECT * FROM repositories')
                for row in cursor.fetchall():
                    try:
                        repo_config = RepositoryConfig(
                            Name=row[0],
                            Url=row[1],
                            Type=RegistrySource(row[2]),
                            Enabled=bool(row[3]),
                            Priority=row[4],
                            AuthToken=row[5],
                            LastSync=datetime.fromisoformat(row[6]) if row[6] else None,
                            SyncInterval=row[7],
                            Metadata=json.loads(row[8]) if row[8] else {}
                        )
                        
                        repositories[repo_config.Name] = repo_config
                    except Exception as e:
                        logging.error(f"Failed to load repository {row[0]}: {e}")
                        
            except sqlite3.OperationalError:
                # 表不存在，这是正常的初始状态
                pass
            
            conn.close()
            return models, repositories
        
        self._models, self._repositories = await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, load_data, self._registry_path
        )
    
    async def _load_default_repositories(self):
        """加载默认仓库配置"""
        default_repos = [
            RepositoryConfig(
                Name="byenatos_official",
                Url="https://models.byenatos.org/v1/",
                Type=RegistrySource.OFFICIAL,
                Priority=100
            ),
            RepositoryConfig(
                Name="huggingface",
                Url="https://huggingface.co/api/",
                Type=RegistrySource.COMMUNITY,
                Priority=50
            )
        ]
        
        for repo in default_repos:
            if repo.Name not in self._repositories:
                await self.AddRepository(repo)
    
    async def _rebuild_indexes(self):
        """重建所有索引"""
        self._models_by_type.clear()
        self._models_by_vendor.clear()
        self._models_by_size.clear()
        self._tag_index.clear()
        
        for model_id, entry in self._models.items():
            await self._update_indexes(model_id, entry)
    
    async def _update_indexes(self, model_id: str, entry: ModelRegistryEntry):
        """更新索引"""
        spec = entry.Specification
        
        # 按类型索引
        if spec.ModelType not in self._models_by_type:
            self._models_by_type[spec.ModelType] = []
        if model_id not in self._models_by_type[spec.ModelType]:
            self._models_by_type[spec.ModelType].append(model_id)
        
        # 按厂商索引
        if spec.Vendor not in self._models_by_vendor:
            self._models_by_vendor[spec.Vendor] = []
        if model_id not in self._models_by_vendor[spec.Vendor]:
            self._models_by_vendor[spec.Vendor].append(model_id)
        
        # 按规模索引
        if spec.ModelSize not in self._models_by_size:
            self._models_by_size[spec.ModelSize] = []
        if model_id not in self._models_by_size[spec.ModelSize]:
            self._models_by_size[spec.ModelSize].append(model_id)
        
        # 按标签索引
        for tag in entry.Tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(model_id)
    
    async def _remove_from_indexes(self, model_id: str, entry: ModelRegistryEntry):
        """从索引中移除"""
        spec = entry.Specification
        
        # 从类型索引移除
        if spec.ModelType in self._models_by_type:
            if model_id in self._models_by_type[spec.ModelType]:
                self._models_by_type[spec.ModelType].remove(model_id)
        
        # 从厂商索引移除
        if spec.Vendor in self._models_by_vendor:
            if model_id in self._models_by_vendor[spec.Vendor]:
                self._models_by_vendor[spec.Vendor].remove(model_id)
        
        # 从规模索引移除
        if spec.ModelSize in self._models_by_size:
            if model_id in self._models_by_size[spec.ModelSize]:
                self._models_by_size[spec.ModelSize].remove(model_id)
        
        # 从标签索引移除
        for tag in entry.Tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(model_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
    
    async def _save_model_to_db(self, entry: ModelRegistryEntry):
        """保存模型到数据库"""
        def save_model(db_path, entry):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.Specification.ModelId,
                json.dumps(asdict(entry.Specification)),
                entry.Source.value,
                entry.Status.value,
                entry.RegistrationTime.isoformat(),
                entry.LastUpdated.isoformat(),
                entry.DownloadUrl,
                entry.InstallPath,
                entry.Checksum,
                json.dumps(entry.Dependencies),
                json.dumps(entry.Conflicts),
                entry.MinSystemVersion,
                entry.MaxSystemVersion,
                json.dumps(entry.Tags),
                json.dumps(entry.Metadata)
            ))
            
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, save_model, self._registry_path, entry
        )
    
    def _validate_model_specification(self, spec: ModelSpecification) -> bool:
        """验证模型规格"""
        required_fields = ['ModelId', 'ModelName', 'Vendor', 'Version']
        return all(getattr(spec, field, None) for field in required_fields)
    
    async def _matches_criteria(self, entry: ModelRegistryEntry, criteria: Dict[str, Any]) -> bool:
        """检查模型是否匹配查找条件"""
        spec = entry.Specification
        
        # 检查模型类型
        if 'model_type' in criteria and spec.ModelType != criteria['model_type']:
            return False
        
        # 检查厂商
        if 'vendor' in criteria and spec.Vendor.lower() != criteria['vendor'].lower():
            return False
        
        # 检查模型规模
        if 'model_size' in criteria and spec.ModelSize != criteria['model_size']:
            return False
        
        # 检查参数数量范围
        if 'min_parameters' in criteria and spec.ParameterCount < criteria['min_parameters']:
            return False
        if 'max_parameters' in criteria and spec.ParameterCount > criteria['max_parameters']:
            return False
        
        # 检查标签
        if 'tags' in criteria:
            required_tags = set(criteria['tags'])
            model_tags = set(entry.Tags)
            if not required_tags.issubset(model_tags):
                return False
        
        # 检查状态
        if 'status' in criteria and entry.Status != criteria['status']:
            return False
        
        # 检查是否仅本地模型
        if criteria.get('local_only', False) and not spec.LocalSupport:
            return False
        
        return True
    
    def _calculate_model_priority(self, entry: ModelRegistryEntry) -> float:
        """计算模型优先级"""
        priority = 0.0
        
        # 状态优先级
        status_priority = {
            ModelStatus.STABLE: 100,
            ModelStatus.BETA: 80,
            ModelStatus.EXPERIMENTAL: 60,
            ModelStatus.DEPRECATED: 20,
            ModelStatus.INCOMPATIBLE: 0
        }
        priority += status_priority.get(entry.Status, 0)
        
        # 来源优先级
        source_priority = {
            RegistrySource.OFFICIAL: 50,
            RegistrySource.LOCAL: 40,
            RegistrySource.COMMUNITY: 30,
            RegistrySource.PRIVATE: 20,
            RegistrySource.CLOUD: 10
        }
        priority += source_priority.get(entry.Source, 0)
        
        # 版本新旧程度（假设版本格式为x.y.z）
        try:
            version_parts = [int(x) for x in entry.Specification.Version.split('.')]
            version_score = sum(part * (100 ** (len(version_parts) - i - 1)) 
                              for i, part in enumerate(version_parts))
            priority += min(version_score / 10000, 10)  # 最多加10分
        except:
            pass
        
        return priority
    
    def _estimate_memory_requirement(self, spec: ModelSpecification) -> float:
        """估算模型内存需求（GB）"""
        # 简单估算：每个参数约4字节（float32）
        base_memory = spec.ParameterCount * 4 / (1024 ** 3)
        
        # 添加缓冲区和运行时开销
        overhead_multiplier = 1.5
        
        return base_memory * overhead_multiplier
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """比较版本号，返回-1, 0, 1"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
            
            return 0
        except:
            return 0  # 无法比较时认为相等
    
    async def _check_conflicts(self, entry: ModelRegistryEntry) -> List[str]:
        """检查模型冲突"""
        conflicts = []
        
        for conflict_id in entry.Conflicts:
            if conflict_id in self._models:
                conflicts.append(conflict_id)
        
        return conflicts
    
    async def _scan_directory_for_models(self, directory: str) -> int:
        """扫描目录查找模型文件"""
        # 这里应该实现具体的模型文件扫描逻辑
        # 例如查找 .safetensors, .bin, .onnx 等模型文件
        # 并解析模型元数据
        
        # 临时实现，返回0
        return 0
    
    def _needs_sync(self, repo_config: RepositoryConfig) -> bool:
        """检查仓库是否需要同步"""
        if repo_config.LastSync is None:
            return True
        
        time_since_sync = datetime.now() - repo_config.LastSync
        return time_since_sync.total_seconds() > repo_config.SyncInterval
    
    async def _sync_with_repository(self, repo_config: RepositoryConfig) -> int:
        """与仓库同步"""
        # 这里应该实现具体的仓库同步逻辑
        # 根据仓库类型调用不同的API
        
        # 临时实现，返回0
        return 0
    
    async def _validate_repository_config(self, config: RepositoryConfig) -> bool:
        """验证仓库配置"""
        # 检查URL格式
        try:
            parsed = urllib.parse.urlparse(config.Url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except:
            return False
        
        return True
    
    async def _save_repository_to_db(self, config: RepositoryConfig):
        """保存仓库配置到数据库"""
        def save_repo(db_path, config):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO repositories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.Name,
                config.Url,
                config.Type.value,
                int(config.Enabled),
                config.Priority,
                config.AuthToken,
                config.LastSync.isoformat() if config.LastSync else None,
                config.SyncInterval,
                json.dumps(config.Metadata)
            ))
            
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, save_repo, self._registry_path, config
        )
    
    async def _delete_model_from_db(self, model_id: str):
        """从数据库删除模型"""
        def delete_model(db_path, model_id):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM models WHERE model_id = ?', (model_id,))
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, delete_model, self._registry_path, model_id
        )
    
    async def _delete_repository_from_db(self, repo_name: str):
        """从数据库删除仓库"""
        def delete_repo(db_path, repo_name):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM repositories WHERE name = ?', (repo_name,))
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self._thread_pool, delete_repo, self._registry_path, repo_name
        )
    
    def _start_discovery_task(self):
        """启动自动发现任务"""
        async def discovery_loop():
            while not self._shutdown_event.is_set():
                try:
                    await self.DiscoverLocalModels()
                    await asyncio.sleep(self._discovery_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Discovery loop error: {e}")
                    await asyncio.sleep(60)  # 出错时等待1分钟
        
        task = asyncio.create_task(discovery_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    def _start_sync_task(self):
        """启动自动同步任务"""
        async def sync_loop():
            while not self._shutdown_event.is_set():
                try:
                    await self.SyncWithRepositories()
                    await asyncio.sleep(3600)  # 每小时同步一次
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Sync loop error: {e}")
                    await asyncio.sleep(300)  # 出错时等待5分钟
        
        task = asyncio.create_task(sync_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

# 全局模型注册表实例
_global_model_registry: Optional[ModelRegistry] = None

def GetGlobalModelRegistry() -> ModelRegistry:
    """获取全局模型注册表实例"""
    global _global_model_registry
    if _global_model_registry is None:
        _global_model_registry = ModelRegistry()
    return _global_model_registry

def SetGlobalModelRegistry(registry: ModelRegistry):
    """设置全局模型注册表实例"""
    global _global_model_registry
    _global_model_registry = registry