"""
ByenatOS 模型热插拔管理器
========================

这是byenatOS的模型热插拔系统，类似于USB设备的即插即用功能。
支持在系统运行时动态加载、卸载和切换大语言模型，无需重启系统。

类比：就像在电脑运行时可以插拔USB设备一样，可以在操作系统运行时插拔不同的"AI处理器"。
"""

import asyncio
import logging
import threading
import weakref
from typing import Dict, List, Optional, Set, Callable, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .LLMInterface import (
    ILLMDriver, ModelSpecification, InferenceRequest, InferenceResponse,
    ModelHealthStatus, LLMDriverException, ResourceExhaustedError
)
from .LLMDriverManager import LLMDriverManager, DriverStatus, LoadBalanceStrategy
from .ModelRegistry import ModelRegistry, ModelRegistryEntry

class SwapOperation(Enum):
    """热插拔操作类型"""
    LOAD = "load"           # 加载模型
    UNLOAD = "unload"       # 卸载模型
    SWITCH = "switch"       # 切换模型
    RELOAD = "reload"       # 重新加载模型
    MIGRATE = "migrate"     # 迁移会话到新模型

class SwapStrategy(Enum):
    """热插拔策略"""
    IMMEDIATE = "immediate"         # 立即切换（可能中断当前请求）
    GRACEFUL = "graceful"          # 优雅切换（等待当前请求完成）
    BACKGROUND = "background"       # 后台预加载
    SESSION_AWARE = "session_aware" # 会话感知切换

class SwapTrigger(Enum):
    """切换触发条件"""
    MANUAL = "manual"               # 手动触发
    PERFORMANCE = "performance"     # 性能触发
    RESOURCE = "resource"           # 资源触发
    ERROR = "error"                 # 错误触发
    SCHEDULE = "schedule"           # 定时触发
    WORKLOAD = "workload"          # 工作负载触发

@dataclass
class SwapRequest:
    """热插拔请求"""
    RequestId: str
    Operation: SwapOperation
    SourceModelId: Optional[str] = None     # 源模型ID
    TargetModelId: Optional[str] = None     # 目标模型ID
    Strategy: SwapStrategy = SwapStrategy.GRACEFUL
    Trigger: SwapTrigger = SwapTrigger.MANUAL
    Priority: int = 0                       # 优先级（0-100）
    MaxWaitTime: float = 30.0              # 最大等待时间（秒）
    PreserveSession: bool = True           # 是否保持会话状态
    Config: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SwapStatus:
    """热插拔状态"""
    RequestId: str
    Operation: SwapOperation
    Status: str                            # pending, in_progress, completed, failed, cancelled
    Progress: float = 0.0                  # 进度百分比
    StartTime: Optional[datetime] = None
    EndTime: Optional[datetime] = None
    ErrorMessage: Optional[str] = None
    Metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SessionState:
    """会话状态数据"""
    SessionId: str
    ModelId: str
    ConversationHistory: List[Dict[str, Any]]
    ContextCache: Optional[Any] = None
    UserPreferences: Dict[str, Any] = field(default_factory=dict)
    LastActivity: datetime = field(default_factory=datetime.now)
    Metadata: Dict[str, Any] = field(default_factory=dict)

class HotSwapManager:
    """
    模型热插拔管理器
    ==============
    
    核心功能：
    1. 动态加载和卸载 - 运行时安装/移除"AI处理器"
    2. 无缝切换 - 在不同模型间无感知切换
    3. 会话保持 - 切换过程中保持用户会话状态
    4. 性能监控 - 监控模型性能并自动优化
    5. 资源管理 - 智能管理内存和计算资源
    6. 故障恢复 - 模型故障时自动切换备用模型
    """
    
    def __init__(self, driver_manager: LLMDriverManager, model_registry: ModelRegistry):
        """
        初始化热插拔管理器
        
        Args:
            driver_manager: 驱动管理器实例
            model_registry: 模型注册表实例
        """
        self._driver_manager = driver_manager
        self._model_registry = model_registry
        
        # 状态管理
        self._current_requests: Dict[str, SwapRequest] = {}
        self._request_status: Dict[str, SwapStatus] = {}
        self._active_sessions: Dict[str, SessionState] = {}
        self._preloaded_models: Set[str] = set()
        
        # 切换历史和统计
        self._swap_history: List[SwapStatus] = []
        self._performance_metrics: Dict[str, Dict[str, float]] = {}
        self._error_counts: Dict[str, int] = {}
        
        # 配置
        self._max_concurrent_swaps = 3
        self._max_preloaded_models = 2
        self._session_timeout = 1800  # 30分钟
        self._auto_optimization_enabled = True
        self._fallback_model_id: Optional[str] = None
        
        # 线程同步
        self._swap_lock = threading.RLock()
        self._session_lock = threading.RLock()
        
        # 异步任务管理
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._request_queue = asyncio.Queue()
        
        # 事件处理
        self._event_handlers: Dict[str, List[Callable]] = {
            'swap_started': [],
            'swap_completed': [],
            'swap_failed': [],
            'model_loaded': [],
            'model_unloaded': [],
            'session_migrated': []
        }
        
        # 监控和优化
        self._monitoring_enabled = True
        self._optimization_rules: List[Dict[str, Any]] = []
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 启动后台任务
        self._start_background_tasks()
    
    async def RequestSwap(self, request: SwapRequest) -> str:
        """
        请求模型热插拔操作
        
        Args:
            request: 热插拔请求
            
        Returns:
            str: 请求ID
        """
        request_id = request.RequestId
        
        try:
            # 验证请求
            if not await self._validate_swap_request(request):
                raise ValueError("Invalid swap request")
            
            # 检查并发限制
            active_count = len([r for r in self._current_requests.values() 
                               if r.Operation in [SwapOperation.LOAD, SwapOperation.SWITCH]])
            if active_count >= self._max_concurrent_swaps:
                raise ResourceExhaustedError("Too many concurrent swap operations")
            
            # 创建状态记录
            status = SwapStatus(
                RequestId=request_id,
                Operation=request.Operation,
                Status="pending",
                StartTime=datetime.now()
            )
            
            with self._swap_lock:
                self._current_requests[request_id] = request
                self._request_status[request_id] = status
            
            # 将请求加入队列
            await self._request_queue.put(request)
            
            self._logger.info(f"Queued swap request {request_id}: {request.Operation.value}")
            
            # 触发事件
            await self._trigger_event('swap_started', {
                'request_id': request_id,
                'operation': request.Operation.value,
                'strategy': request.Strategy.value
            })
            
            return request_id
            
        except Exception as e:
            self._logger.error(f"Failed to queue swap request: {e}")
            raise
    
    async def GetSwapStatus(self, request_id: str) -> Optional[SwapStatus]:
        """获取热插拔请求状态"""
        return self._request_status.get(request_id)
    
    async def CancelSwap(self, request_id: str) -> bool:
        """
        取消热插拔请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            status = self._request_status.get(request_id)
            if not status or status.Status in ['completed', 'failed', 'cancelled']:
                return False
            
            status.Status = "cancelled"
            status.EndTime = datetime.now()
            
            # 从当前请求中移除
            with self._swap_lock:
                self._current_requests.pop(request_id, None)
            
            self._logger.info(f"Cancelled swap request {request_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to cancel swap request {request_id}: {e}")
            return False
    
    async def QuickSwitch(self, target_model_id: str, 
                         strategy: SwapStrategy = SwapStrategy.GRACEFUL) -> str:
        """
        快速切换到指定模型
        
        Args:
            target_model_id: 目标模型ID
            strategy: 切换策略
            
        Returns:
            str: 请求ID
        """
        request = SwapRequest(
            RequestId=f"quick_switch_{int(time.time())}",
            Operation=SwapOperation.SWITCH,
            TargetModelId=target_model_id,
            Strategy=strategy,
            Trigger=SwapTrigger.MANUAL,
            Priority=80
        )
        
        return await self.RequestSwap(request)
    
    async def PreloadModel(self, model_id: str) -> str:
        """
        预加载模型到内存
        
        Args:
            model_id: 模型ID
            
        Returns:
            str: 请求ID
        """
        if len(self._preloaded_models) >= self._max_preloaded_models:
            # 卸载最少使用的预加载模型
            await self._unload_least_used_preloaded_model()
        
        request = SwapRequest(
            RequestId=f"preload_{model_id}_{int(time.time())}",
            Operation=SwapOperation.LOAD,
            TargetModelId=model_id,
            Strategy=SwapStrategy.BACKGROUND,
            Trigger=SwapTrigger.MANUAL,
            Priority=30
        )
        
        return await self.RequestSwap(request)
    
    async def CreateSession(self, session_id: str, model_id: str, 
                           user_preferences: Optional[Dict[str, Any]] = None) -> bool:
        """
        创建新的用户会话
        
        Args:
            session_id: 会话ID
            model_id: 使用的模型ID
            user_preferences: 用户偏好设置
            
        Returns:
            bool: 是否成功创建
        """
        try:
            session = SessionState(
                SessionId=session_id,
                ModelId=model_id,
                ConversationHistory=[],
                UserPreferences=user_preferences or {},
                LastActivity=datetime.now()
            )
            
            with self._session_lock:
                self._active_sessions[session_id] = session
            
            self._logger.info(f"Created session {session_id} with model {model_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def MigrateSession(self, session_id: str, target_model_id: str) -> bool:
        """
        迁移会话到新模型
        
        Args:
            session_id: 会话ID
            target_model_id: 目标模型ID
            
        Returns:
            bool: 是否成功迁移
        """
        try:
            session = self._active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            old_model_id = session.ModelId
            
            # 验证目标模型可用性
            if not await self._driver_manager.GetDriverStatus(target_model_id):
                # 模型未加载，先加载
                load_request = SwapRequest(
                    RequestId=f"migrate_load_{session_id}_{int(time.time())}",
                    Operation=SwapOperation.LOAD,
                    TargetModelId=target_model_id,
                    Strategy=SwapStrategy.GRACEFUL,
                    Trigger=SwapTrigger.MANUAL
                )
                await self.RequestSwap(load_request)
                
                # 等待加载完成
                timeout = 30
                while timeout > 0:
                    if await self._driver_manager.GetDriverStatus(target_model_id):
                        break
                    await asyncio.sleep(1)
                    timeout -= 1
                
                if timeout <= 0:
                    raise TimeoutError("Failed to load target model")
            
            # 迁移会话状态
            session.ModelId = target_model_id
            session.LastActivity = datetime.now()
            
            # 可能需要转换对话历史格式以适应新模型
            if await self._needs_history_conversion(old_model_id, target_model_id):
                session.ConversationHistory = await self._convert_conversation_history(
                    session.ConversationHistory, old_model_id, target_model_id
                )
            
            self._logger.info(f"Migrated session {session_id} from {old_model_id} to {target_model_id}")
            
            # 触发事件
            await self._trigger_event('session_migrated', {
                'session_id': session_id,
                'old_model_id': old_model_id,
                'new_model_id': target_model_id
            })
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to migrate session {session_id}: {e}")
            return False
    
    async def GetActiveModels(self) -> List[str]:
        """获取当前活动的模型列表"""
        available_models = await self._driver_manager.GetAvailableModels()
        return [spec.ModelId for spec in available_models]
    
    async def GetPreloadedModels(self) -> List[str]:
        """获取预加载的模型列表"""
        return list(self._preloaded_models)
    
    async def GetSessionInfo(self, session_id: str) -> Optional[SessionState]:
        """获取会话信息"""
        return self._active_sessions.get(session_id)
    
    async def GetSwapHistory(self, limit: int = 100) -> List[SwapStatus]:
        """获取热插拔历史记录"""
        return self._swap_history[-limit:]
    
    async def GetPerformanceMetrics(self) -> Dict[str, Dict[str, float]]:
        """获取性能指标"""
        return self._performance_metrics.copy()
    
    def SetFallbackModel(self, model_id: str):
        """设置故障恢复模型"""
        self._fallback_model_id = model_id
    
    def EnableAutoOptimization(self, enabled: bool):
        """启用/禁用自动优化"""
        self._auto_optimization_enabled = enabled
    
    def AddOptimizationRule(self, rule: Dict[str, Any]):
        """添加自动优化规则"""
        self._optimization_rules.append(rule)
    
    def RegisterEventHandler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
    
    async def Shutdown(self):
        """关闭热插拔管理器"""
        self._logger.info("Shutting down Hot Swap Manager...")
        
        # 设置关闭事件
        self._shutdown_event.set()
        
        # 取消所有待处理的请求
        for request_id in list(self._current_requests.keys()):
            await self.CancelSwap(request_id)
        
        # 等待后台任务完成
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._logger.info("Hot Swap Manager shutdown complete")
    
    # 私有方法实现
    async def _validate_swap_request(self, request: SwapRequest) -> bool:
        """验证热插拔请求"""
        # 检查操作类型
        if request.Operation == SwapOperation.SWITCH:
            if not request.TargetModelId:
                return False
        elif request.Operation == SwapOperation.LOAD:
            if not request.TargetModelId:
                return False
        elif request.Operation == SwapOperation.UNLOAD:
            if not request.SourceModelId:
                return False
        
        # 检查目标模型是否存在于注册表
        if request.TargetModelId:
            model_entry = await self._model_registry.GetModel(request.TargetModelId)
            if not model_entry:
                return False
        
        return True
    
    async def _process_swap_request(self, request: SwapRequest) -> bool:
        """处理热插拔请求"""
        request_id = request.RequestId
        status = self._request_status[request_id]
        
        try:
            status.Status = "in_progress"
            status.Progress = 0.0
            
            if request.Operation == SwapOperation.LOAD:
                success = await self._handle_load_operation(request, status)
            elif request.Operation == SwapOperation.UNLOAD:
                success = await self._handle_unload_operation(request, status)
            elif request.Operation == SwapOperation.SWITCH:
                success = await self._handle_switch_operation(request, status)
            elif request.Operation == SwapOperation.RELOAD:
                success = await self._handle_reload_operation(request, status)
            else:
                raise ValueError(f"Unsupported operation: {request.Operation}")
            
            status.Status = "completed" if success else "failed"
            status.Progress = 100.0
            status.EndTime = datetime.now()
            
            # 记录历史
            self._swap_history.append(status)
            if len(self._swap_history) > 1000:  # 限制历史记录数量
                self._swap_history = self._swap_history[-500:]
            
            # 触发事件
            event_type = 'swap_completed' if success else 'swap_failed'
            await self._trigger_event(event_type, {
                'request_id': request_id,
                'operation': request.Operation.value,
                'success': success,
                'duration': (status.EndTime - status.StartTime).total_seconds()
            })
            
            return success
            
        except Exception as e:
            status.Status = "failed"
            status.ErrorMessage = str(e)
            status.EndTime = datetime.now()
            
            self._logger.error(f"Swap request {request_id} failed: {e}")
            
            await self._trigger_event('swap_failed', {
                'request_id': request_id,
                'operation': request.Operation.value,
                'error': str(e)
            })
            
            return False
        
        finally:
            # 清理当前请求
            with self._swap_lock:
                self._current_requests.pop(request_id, None)
    
    async def _handle_load_operation(self, request: SwapRequest, status: SwapStatus) -> bool:
        """处理加载操作"""
        model_id = request.TargetModelId
        
        # 检查是否已经加载
        current_models = await self.GetActiveModels()
        if model_id in current_models:
            self._logger.info(f"Model {model_id} already loaded")
            return True
        
        status.Progress = 10.0
        
        # 获取模型配置
        model_entry = await self._model_registry.GetModel(model_id)
        if not model_entry:
            raise ValueError(f"Model {model_id} not found in registry")
        
        status.Progress = 20.0
        
        # 检查系统兼容性
        system_info = await self._get_system_info()
        compatibility = await self._model_registry.CheckCompatibility(model_id, system_info)
        if not compatibility['compatible']:
            raise ValueError(f"Model {model_id} is not compatible: {compatibility['warnings']}")
        
        status.Progress = 30.0
        
        # 加载模型
        load_config = request.Config.copy()
        load_config.update(model_entry.Metadata.get('load_config', {}))
        
        success = await self._driver_manager.LoadDriver(model_id, load_config)
        if not success:
            raise Exception(f"Failed to load model {model_id}")
        
        status.Progress = 90.0
        
        # 添加到预加载列表（如果是后台加载）
        if request.Strategy == SwapStrategy.BACKGROUND:
            self._preloaded_models.add(model_id)
        
        status.Progress = 100.0
        
        await self._trigger_event('model_loaded', {
            'model_id': model_id,
            'strategy': request.Strategy.value
        })
        
        return True
    
    async def _handle_unload_operation(self, request: SwapRequest, status: SwapStatus) -> bool:
        """处理卸载操作"""
        model_id = request.SourceModelId
        
        status.Progress = 10.0
        
        # 检查是否有活动会话使用该模型
        active_sessions = [
            session for session in self._active_sessions.values()
            if session.ModelId == model_id
        ]
        
        if active_sessions and not request.Config.get('force', False):
            # 尝试迁移会话到其他模型
            fallback_model = self._fallback_model_id or await self._find_best_fallback_model(model_id)
            if fallback_model:
                for session in active_sessions:
                    await self.MigrateSession(session.SessionId, fallback_model)
            else:
                raise Exception(f"Cannot unload {model_id}: active sessions and no fallback available")
        
        status.Progress = 50.0
        
        # 卸载模型
        success = await self._driver_manager.UnloadDriver(model_id)
        if not success:
            raise Exception(f"Failed to unload model {model_id}")
        
        status.Progress = 90.0
        
        # 从预加载列表移除
        self._preloaded_models.discard(model_id)
        
        status.Progress = 100.0
        
        await self._trigger_event('model_unloaded', {
            'model_id': model_id
        })
        
        return True
    
    async def _handle_switch_operation(self, request: SwapRequest, status: SwapStatus) -> bool:
        """处理切换操作"""
        target_model_id = request.TargetModelId
        
        status.Progress = 10.0
        
        # 获取当前活动模型
        current_models = await self.GetActiveModels()
        
        # 如果目标模型未加载，先加载
        if target_model_id not in current_models:
            load_request = SwapRequest(
                RequestId=f"switch_load_{request.RequestId}",
                Operation=SwapOperation.LOAD,
                TargetModelId=target_model_id,
                Strategy=request.Strategy,
                Config=request.Config
            )
            load_status = SwapStatus(
                RequestId=load_request.RequestId,
                Operation=SwapOperation.LOAD,
                Status="pending"
            )
            
            if not await self._handle_load_operation(load_request, load_status):
                raise Exception(f"Failed to load target model {target_model_id}")
        
        status.Progress = 60.0
        
        # 切换活动模型
        success = await self._driver_manager.SwitchActiveDriver(target_model_id)
        if not success:
            raise Exception(f"Failed to switch to model {target_model_id}")
        
        status.Progress = 80.0
        
        # 如果需要保持会话状态，迁移相关会话
        if request.PreserveSession:
            affected_sessions = [
                session for session in self._active_sessions.values()
                if session.ModelId != target_model_id
            ]
            
            for session in affected_sessions:
                await self.MigrateSession(session.SessionId, target_model_id)
        
        status.Progress = 100.0
        
        return True
    
    async def _handle_reload_operation(self, request: SwapRequest, status: SwapStatus) -> bool:
        """处理重新加载操作"""
        model_id = request.TargetModelId or request.SourceModelId
        
        # 先卸载
        unload_request = SwapRequest(
            RequestId=f"reload_unload_{request.RequestId}",
            Operation=SwapOperation.UNLOAD,
            SourceModelId=model_id,
            Config={'force': True}
        )
        unload_status = SwapStatus(
            RequestId=unload_request.RequestId,
            Operation=SwapOperation.UNLOAD,
            Status="pending"
        )
        
        if not await self._handle_unload_operation(unload_request, unload_status):
            raise Exception(f"Failed to unload model {model_id} for reload")
        
        status.Progress = 50.0
        
        # 再加载
        load_request = SwapRequest(
            RequestId=f"reload_load_{request.RequestId}",
            Operation=SwapOperation.LOAD,
            TargetModelId=model_id,
            Strategy=request.Strategy,
            Config=request.Config
        )
        load_status = SwapStatus(
            RequestId=load_request.RequestId,
            Operation=SwapOperation.LOAD,
            Status="pending"
        )
        
        if not await self._handle_load_operation(load_request, load_status):
            raise Exception(f"Failed to reload model {model_id}")
        
        status.Progress = 100.0
        
        return True
    
    async def _find_best_fallback_model(self, current_model_id: str) -> Optional[str]:
        """寻找最佳的故障恢复模型"""
        current_model = await self._model_registry.GetModel(current_model_id)
        if not current_model:
            return None
        
        # 查找相似的模型
        criteria = {
            'model_type': current_model.Specification.ModelType,
            'status': 'available'
        }
        
        similar_models = await self._model_registry.FindModels(criteria)
        available_models = await self.GetActiveModels()
        
        # 优先选择已加载的相似模型
        for model_entry in similar_models:
            if (model_entry.Specification.ModelId != current_model_id and 
                model_entry.Specification.ModelId in available_models):
                return model_entry.Specification.ModelId
        
        # 如果没有已加载的，选择第一个可用的
        for model_entry in similar_models:
            if model_entry.Specification.ModelId != current_model_id:
                return model_entry.Specification.ModelId
        
        return None
    
    async def _unload_least_used_preloaded_model(self):
        """卸载最少使用的预加载模型"""
        if not self._preloaded_models:
            return
        
        # 简单实现：卸载第一个预加载模型
        model_to_unload = next(iter(self._preloaded_models))
        
        unload_request = SwapRequest(
            RequestId=f"auto_unload_{int(time.time())}",
            Operation=SwapOperation.UNLOAD,
            SourceModelId=model_to_unload,
            Strategy=SwapStrategy.BACKGROUND,
            Trigger=SwapTrigger.RESOURCE
        )
        
        await self.RequestSwap(unload_request)
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        # 这里应该实现获取实际系统信息的逻辑
        return {
            'available_memory_gb': 16,
            'gpu_count': 1,
            'cpu_cores': 8,
            'system_version': '1.0.0',
            'compute_capability': 'high'
        }
    
    async def _needs_history_conversion(self, old_model_id: str, new_model_id: str) -> bool:
        """检查是否需要转换对话历史格式"""
        # 简单实现：不同厂商的模型可能需要格式转换
        old_model = await self._model_registry.GetModel(old_model_id)
        new_model = await self._model_registry.GetModel(new_model_id)
        
        if not old_model or not new_model:
            return False
        
        return old_model.Specification.Vendor != new_model.Specification.Vendor
    
    async def _convert_conversation_history(self, history: List[Dict[str, Any]], 
                                          old_model_id: str, new_model_id: str) -> List[Dict[str, Any]]:
        """转换对话历史格式"""
        # 这里应该实现具体的格式转换逻辑
        # 目前简单返回原历史
        return history
    
    async def _trigger_event(self, event_type: str, event_data: Dict[str, Any]):
        """触发事件"""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, event_data)
                else:
                    handler(event_type, event_data)
            except Exception as e:
                self._logger.error(f"Event handler error for '{event_type}': {e}")
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 请求处理任务
        request_processor_task = asyncio.create_task(self._request_processor_loop())
        self._background_tasks.add(request_processor_task)
        request_processor_task.add_done_callback(self._background_tasks.discard)
        
        # 会话清理任务
        session_cleanup_task = asyncio.create_task(self._session_cleanup_loop())
        self._background_tasks.add(session_cleanup_task)
        session_cleanup_task.add_done_callback(self._background_tasks.discard)
        
        # 性能监控任务
        if self._monitoring_enabled:
            monitoring_task = asyncio.create_task(self._performance_monitoring_loop())
            self._background_tasks.add(monitoring_task)
            monitoring_task.add_done_callback(self._background_tasks.discard)
        
        # 自动优化任务
        if self._auto_optimization_enabled:
            optimization_task = asyncio.create_task(self._auto_optimization_loop())
            self._background_tasks.add(optimization_task)
            optimization_task.add_done_callback(self._background_tasks.discard)
    
    async def _request_processor_loop(self):
        """请求处理循环"""
        while not self._shutdown_event.is_set():
            try:
                # 等待新请求
                request = await asyncio.wait_for(
                    self._request_queue.get(), timeout=1.0
                )
                
                # 处理请求
                await self._process_swap_request(request)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Request processor error: {e}")
                await asyncio.sleep(1)
    
    async def _session_cleanup_loop(self):
        """会话清理循环"""
        while not self._shutdown_event.is_set():
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                with self._session_lock:
                    for session_id, session in self._active_sessions.items():
                        if (current_time - session.LastActivity).total_seconds() > self._session_timeout:
                            expired_sessions.append(session_id)
                
                # 清理过期会话
                for session_id in expired_sessions:
                    with self._session_lock:
                        self._active_sessions.pop(session_id, None)
                    self._logger.info(f"Cleaned up expired session {session_id}")
                
                await asyncio.sleep(300)  # 每5分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _performance_monitoring_loop(self):
        """性能监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # 收集性能指标
                driver_metrics = await self._driver_manager.GetPerformanceMetrics()
                
                # 更新本地性能指标
                for model_id, metrics in driver_metrics.items():
                    self._performance_metrics[model_id] = metrics
                
                # 检查是否需要触发自动优化
                if self._auto_optimization_enabled:
                    await self._check_optimization_triggers()
                
                await asyncio.sleep(60)  # 每分钟监控一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _auto_optimization_loop(self):
        """自动优化循环"""
        while not self._shutdown_event.is_set():
            try:
                # 应用优化规则
                for rule in self._optimization_rules:
                    await self._apply_optimization_rule(rule)
                
                await asyncio.sleep(300)  # 每5分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Auto optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _check_optimization_triggers(self):
        """检查优化触发条件"""
        # 这里可以实现各种优化触发逻辑
        # 例如：性能下降时自动切换到更快的模型
        pass
    
    async def _apply_optimization_rule(self, rule: Dict[str, Any]):
        """应用优化规则"""
        # 这里可以实现具体的优化规则逻辑
        pass

# 全局热插拔管理器实例
_global_hotswap_manager: Optional[HotSwapManager] = None

def GetGlobalHotSwapManager() -> Optional[HotSwapManager]:
    """获取全局热插拔管理器实例"""
    return _global_hotswap_manager

def SetGlobalHotSwapManager(manager: HotSwapManager):
    """设置全局热插拔管理器实例"""
    global _global_hotswap_manager
    _global_hotswap_manager = manager