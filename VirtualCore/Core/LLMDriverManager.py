"""
ByenatOS 大语言模型驱动管理器
==========================

这是byenatOS的核心LLM管理组件，类似于操作系统中的设备管理器。
它负责管理所有已安装的大语言模型驱动，支持动态切换、负载均衡、健康监控等功能。

类比：就像主板上的CPU插槽管理器，可以检测、管理和切换不同的CPU。
"""

import asyncio
import logging
import threading
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import weakref
from collections import defaultdict, deque

from .LLMInterface import (
    ILLMDriver, ILLMDriverFactory, ModelSpecification, 
    InferenceRequest, InferenceResponse, ModelHealthStatus,
    ModelType, ModelSize, ComputeRequirement,
    LLMDriverException, ModelNotFoundError, ResourceExhaustedError
)

class DriverStatus(Enum):
    """驱动状态枚举"""
    UNKNOWN = "unknown"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    UNLOADING = "unloading"
    OFFLINE = "offline"

class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"      # 轮询
    LEAST_LOADED = "least_loaded"    # 最少负载
    FASTEST_RESPONSE = "fastest_response"  # 最快响应
    HIGHEST_QUALITY = "highest_quality"    # 最高质量
    RESOURCE_AWARE = "resource_aware"      # 资源感知

@dataclass
class DriverInstance:
    """驱动实例信息"""
    DriverId: str
    Driver: ILLMDriver
    Specification: ModelSpecification
    Status: DriverStatus
    LoadTime: datetime
    LastUsed: datetime
    RequestCount: int = 0
    ErrorCount: int = 0
    TotalProcessingTime: float = 0.0
    AverageResponseTime: float = 0.0
    Config: Dict[str, Any] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LoadBalanceMetrics:
    """负载均衡指标"""
    CurrentLoad: int = 0           # 当前负载
    QueueLength: int = 0           # 队列长度
    AverageResponseTime: float = 0.0  # 平均响应时间
    ErrorRate: float = 0.0         # 错误率
    ResourceUsage: float = 0.0     # 资源使用率
    QualityScore: float = 0.0      # 质量评分

class LLMDriverManager:
    """
    大语言模型驱动管理器
    ==================
    
    核心职责：
    1. 驱动注册和发现 - 自动发现和注册可用的LLM驱动
    2. 动态加载和卸载 - 支持热插拔，按需加载模型
    3. 负载均衡调度 - 智能分配请求到最合适的模型
    4. 健康监控 - 实时监控模型健康状态和性能
    5. 资源管理 - 优化内存和计算资源使用
    6. 配置管理 - 统一的配置存储和管理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化驱动管理器"""
        self._config = config or {}
        self._drivers: Dict[str, DriverInstance] = {}
        self._factories: Dict[str, ILLMDriverFactory] = {}
        self._active_driver_id: Optional[str] = None
        self._default_driver_id: Optional[str] = None
        
        # 负载均衡相关
        self._load_balance_strategy = LoadBalanceStrategy.LEAST_LOADED
        self._driver_metrics: Dict[str, LoadBalanceMetrics] = {}
        self._request_queue: deque = deque()
        self._processing_queues: Dict[str, deque] = defaultdict(deque)
        
        # 监控和统计
        self._health_check_interval = self._config.get('health_check_interval', 30)
        self._performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._error_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # 线程安全
        self._lock = threading.RLock()
        self._driver_locks: Dict[str, threading.Lock] = {}
        
        # 事件回调
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # 异步任务管理
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 初始化监控任务
        self._start_background_tasks()
    
    async def RegisterDriverFactory(self, factory_name: str, factory: ILLMDriverFactory) -> bool:
        """
        注册驱动工厂
        
        Args:
            factory_name: 工厂名称
            factory: 驱动工厂实例
            
        Returns:
            bool: 注册是否成功
        """
        try:
            with self._lock:
                self._factories[factory_name] = factory
            
            # 发现并注册该工厂支持的模型
            supported_models = await factory.GetSupportedModels()
            self._logger.info(f"Registered factory '{factory_name}' with {len(supported_models)} models")
            
            # 触发工厂注册事件
            await self._trigger_event('factory_registered', {
                'factory_name': factory_name,
                'supported_models': [spec.ModelId for spec in supported_models]
            })
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register factory '{factory_name}': {e}")
            return False
    
    async def LoadDriver(self, model_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        加载模型驱动
        类似于安装新的CPU到主板
        
        Args:
            model_id: 模型ID
            config: 驱动配置
            
        Returns:
            bool: 加载是否成功
        """
        if model_id in self._drivers:
            self._logger.warning(f"Driver '{model_id}' already loaded")
            return True
        
        try:
            # 查找支持该模型的工厂
            factory, spec = await self._find_model_factory(model_id)
            if not factory:
                raise ModelNotFoundError(f"No factory found for model '{model_id}'")
            
            # 创建驱动实例
            driver_config = config or {}
            driver = await factory.CreateDriver(model_id, driver_config)
            
            # 初始化驱动
            load_start = datetime.now()
            success = await driver.Initialize(driver_config)
            if not success:
                raise Exception("Driver initialization failed")
            
            # 创建驱动实例记录
            driver_instance = DriverInstance(
                DriverId=model_id,
                Driver=driver,
                Specification=spec,
                Status=DriverStatus.READY,
                LoadTime=load_start,
                LastUsed=datetime.now(),
                Config=driver_config
            )
            
            # 注册驱动
            with self._lock:
                self._drivers[model_id] = driver_instance
                self._driver_locks[model_id] = threading.Lock()
                self._driver_metrics[model_id] = LoadBalanceMetrics()
            
            # 预热模型
            await driver.WarmUp()
            
            # 如果这是第一个驱动，设为默认驱动
            if not self._default_driver_id:
                self._default_driver_id = model_id
                self._active_driver_id = model_id
            
            load_time = (datetime.now() - load_start).total_seconds()
            self._logger.info(f"Loaded driver '{model_id}' in {load_time:.2f} seconds")
            
            # 触发驱动加载事件
            await self._trigger_event('driver_loaded', {
                'model_id': model_id,
                'load_time': load_time,
                'specification': spec
            })
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load driver '{model_id}': {e}")
            return False
    
    async def UnloadDriver(self, model_id: str, force: bool = False) -> bool:
        """
        卸载模型驱动
        类似于从主板上移除CPU
        
        Args:
            model_id: 模型ID
            force: 是否强制卸载
            
        Returns:
            bool: 卸载是否成功
        """
        if model_id not in self._drivers:
            self._logger.warning(f"Driver '{model_id}' not found")
            return True
        
        try:
            driver_instance = self._drivers[model_id]
            
            # 检查是否可以安全卸载
            if not force and driver_instance.Status == DriverStatus.BUSY:
                self._logger.warning(f"Driver '{model_id}' is busy, cannot unload")
                return False
            
            # 如果是当前活动驱动，需要切换到其他驱动
            if self._active_driver_id == model_id:
                await self._switch_to_backup_driver(model_id)
            
            # 标记为卸载中
            driver_instance.Status = DriverStatus.UNLOADING
            
            # 关闭驱动
            await driver_instance.Driver.Shutdown()
            
            # 移除驱动记录
            with self._lock:
                del self._drivers[model_id]
                del self._driver_locks[model_id]
                del self._driver_metrics[model_id]
                if model_id in self._performance_history:
                    del self._performance_history[model_id]
                if model_id in self._error_history:
                    del self._error_history[model_id]
            
            self._logger.info(f"Unloaded driver '{model_id}'")
            
            # 触发驱动卸载事件
            await self._trigger_event('driver_unloaded', {
                'model_id': model_id,
                'was_active': model_id == self._active_driver_id
            })
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to unload driver '{model_id}': {e}")
            return False
    
    async def SwitchActiveDriver(self, model_id: str) -> bool:
        """
        切换当前活动驱动
        类似于主板选择当前使用的CPU核心
        
        Args:
            model_id: 目标模型ID
            
        Returns:
            bool: 切换是否成功
        """
        if model_id not in self._drivers:
            self._logger.error(f"Driver '{model_id}' not found")
            return False
        
        driver_instance = self._drivers[model_id]
        if driver_instance.Status != DriverStatus.READY:
            self._logger.error(f"Driver '{model_id}' not ready (status: {driver_instance.Status})")
            return False
        
        try:
            old_driver_id = self._active_driver_id
            self._active_driver_id = model_id
            
            self._logger.info(f"Switched active driver from '{old_driver_id}' to '{model_id}'")
            
            # 触发驱动切换事件
            await self._trigger_event('driver_switched', {
                'old_driver_id': old_driver_id,
                'new_driver_id': model_id,
                'switch_time': datetime.now()
            })
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to switch to driver '{model_id}': {e}")
            return False
    
    async def ProcessInference(self, request: InferenceRequest, 
                              preferred_model: Optional[str] = None) -> InferenceResponse:
        """
        处理推理请求
        根据负载均衡策略自动选择最合适的模型
        
        Args:
            request: 推理请求
            preferred_model: 偏好的模型ID
            
        Returns:
            InferenceResponse: 推理响应
        """
        # 选择合适的驱动
        driver_id = await self._select_optimal_driver(request, preferred_model)
        if not driver_id:
            raise ResourceExhaustedError("No available drivers")
        
        driver_instance = self._drivers[driver_id]
        
        try:
            # 更新驱动状态
            driver_instance.Status = DriverStatus.BUSY
            start_time = datetime.now()
            
            # 执行推理
            response = await driver_instance.Driver.ProcessInference(request)
            
            # 更新统计信息
            processing_time = (datetime.now() - start_time).total_seconds()
            await self._update_driver_metrics(driver_id, processing_time, True)
            
            # 设置响应中的模型ID
            response.ModelId = driver_id
            response.ProcessingTime = processing_time
            
            driver_instance.Status = DriverStatus.READY
            driver_instance.LastUsed = datetime.now()
            
            return response
            
        except Exception as e:
            # 更新错误统计
            processing_time = (datetime.now() - start_time).total_seconds()
            await self._update_driver_metrics(driver_id, processing_time, False)
            driver_instance.Status = DriverStatus.ERROR
            
            self._logger.error(f"Inference failed on driver '{driver_id}': {e}")
            raise
    
    async def GetAvailableModels(self) -> List[ModelSpecification]:
        """获取所有可用模型的规格列表"""
        with self._lock:
            return [instance.Specification for instance in self._drivers.values()]
    
    async def GetDriverStatus(self, model_id: str) -> Optional[ModelHealthStatus]:
        """获取指定驱动的健康状态"""
        if model_id not in self._drivers:
            return None
        
        return await self._drivers[model_id].Driver.GetHealthStatus()
    
    async def GetAllDriverStatus(self) -> Dict[str, ModelHealthStatus]:
        """获取所有驱动的健康状态"""
        status_dict = {}
        for model_id, instance in self._drivers.items():
            try:
                status_dict[model_id] = await instance.Driver.GetHealthStatus()
            except Exception as e:
                self._logger.error(f"Failed to get status for driver '{model_id}': {e}")
        
        return status_dict
    
    async def GetPerformanceMetrics(self) -> Dict[str, Dict[str, float]]:
        """获取所有驱动的性能指标"""
        metrics_dict = {}
        for model_id, instance in self._drivers.items():
            try:
                metrics_dict[model_id] = await instance.Driver.GetPerformanceMetrics()
            except Exception as e:
                self._logger.error(f"Failed to get metrics for driver '{model_id}': {e}")
        
        return metrics_dict
    
    def SetLoadBalanceStrategy(self, strategy: LoadBalanceStrategy):
        """设置负载均衡策略"""
        self._load_balance_strategy = strategy
        self._logger.info(f"Load balance strategy set to: {strategy.value}")
    
    def RegisterEventHandler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self._event_handlers[event_type].append(handler)
    
    async def Shutdown(self):
        """关闭驱动管理器"""
        self._logger.info("Shutting down LLM Driver Manager...")
        
        # 设置关闭事件
        self._shutdown_event.set()
        
        # 等待后台任务完成
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # 卸载所有驱动
        for model_id in list(self._drivers.keys()):
            await self.UnloadDriver(model_id, force=True)
        
        self._logger.info("LLM Driver Manager shutdown complete")
    
    # 私有方法
    async def _find_model_factory(self, model_id: str) -> tuple[Optional[ILLMDriverFactory], Optional[ModelSpecification]]:
        """查找支持指定模型的工厂"""
        for factory in self._factories.values():
            supported_models = await factory.GetSupportedModels()
            for spec in supported_models:
                if spec.ModelId == model_id:
                    return factory, spec
        return None, None
    
    async def _select_optimal_driver(self, request: InferenceRequest, 
                                   preferred_model: Optional[str] = None) -> Optional[str]:
        """根据负载均衡策略选择最优驱动"""
        available_drivers = [
            driver_id for driver_id, instance in self._drivers.items()
            if instance.Status == DriverStatus.READY
        ]
        
        if not available_drivers:
            return None
        
        # 如果指定了偏好模型且可用，直接使用
        if preferred_model and preferred_model in available_drivers:
            return preferred_model
        
        # 根据策略选择
        if self._load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return await self._select_round_robin(available_drivers)
        elif self._load_balance_strategy == LoadBalanceStrategy.LEAST_LOADED:
            return await self._select_least_loaded(available_drivers)
        elif self._load_balance_strategy == LoadBalanceStrategy.FASTEST_RESPONSE:
            return await self._select_fastest_response(available_drivers)
        else:
            # 默认使用当前活动驱动
            return self._active_driver_id if self._active_driver_id in available_drivers else available_drivers[0]
    
    async def _select_round_robin(self, available_drivers: List[str]) -> str:
        """轮询选择驱动"""
        # 简单实现：按字典序循环
        return min(available_drivers)
    
    async def _select_least_loaded(self, available_drivers: List[str]) -> str:
        """选择负载最少的驱动"""
        min_load = float('inf')
        selected_driver = available_drivers[0]
        
        for driver_id in available_drivers:
            metrics = self._driver_metrics.get(driver_id, LoadBalanceMetrics())
            if metrics.CurrentLoad < min_load:
                min_load = metrics.CurrentLoad
                selected_driver = driver_id
        
        return selected_driver
    
    async def _select_fastest_response(self, available_drivers: List[str]) -> str:
        """选择响应最快的驱动"""
        min_response_time = float('inf')
        selected_driver = available_drivers[0]
        
        for driver_id in available_drivers:
            instance = self._drivers[driver_id]
            if instance.AverageResponseTime < min_response_time:
                min_response_time = instance.AverageResponseTime
                selected_driver = driver_id
        
        return selected_driver
    
    async def _update_driver_metrics(self, driver_id: str, processing_time: float, success: bool):
        """更新驱动性能指标"""
        instance = self._drivers[driver_id]
        metrics = self._driver_metrics[driver_id]
        
        # 更新计数器
        instance.RequestCount += 1
        if not success:
            instance.ErrorCount += 1
        
        # 更新处理时间
        instance.TotalProcessingTime += processing_time
        instance.AverageResponseTime = instance.TotalProcessingTime / instance.RequestCount
        
        # 更新负载均衡指标
        metrics.AverageResponseTime = instance.AverageResponseTime
        metrics.ErrorRate = instance.ErrorCount / instance.RequestCount if instance.RequestCount > 0 else 0.0
        
        # 记录历史数据
        self._performance_history[driver_id].append({
            'timestamp': datetime.now(),
            'processing_time': processing_time,
            'success': success
        })
    
    async def _switch_to_backup_driver(self, current_driver_id: str):
        """切换到备用驱动"""
        available_drivers = [
            driver_id for driver_id, instance in self._drivers.items()
            if driver_id != current_driver_id and instance.Status == DriverStatus.READY
        ]
        
        if available_drivers:
            backup_driver = available_drivers[0]  # 选择第一个可用驱动
            self._active_driver_id = backup_driver
            self._logger.info(f"Switched to backup driver: {backup_driver}")
        else:
            self._active_driver_id = None
            self._logger.warning("No backup driver available")
    
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
        """启动后台监控任务"""
        # 健康检查任务
        health_check_task = asyncio.create_task(self._health_check_loop())
        self._background_tasks.add(health_check_task)
        health_check_task.add_done_callback(self._background_tasks.discard)
        
        # 性能监控任务
        metrics_task = asyncio.create_task(self._metrics_collection_loop())
        self._background_tasks.add(metrics_task)
        metrics_task.add_done_callback(self._background_tasks.discard)
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while not self._shutdown_event.is_set():
            try:
                for driver_id, instance in list(self._drivers.items()):
                    try:
                        health_status = await instance.Driver.GetHealthStatus()
                        if health_status.Status == 'error':
                            instance.Status = DriverStatus.ERROR
                            self._logger.warning(f"Driver '{driver_id}' reported error status")
                    except Exception as e:
                        self._logger.error(f"Health check failed for driver '{driver_id}': {e}")
                        instance.Status = DriverStatus.ERROR
                
                await asyncio.sleep(self._health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # 短暂延迟后重试
    
    async def _metrics_collection_loop(self):
        """性能指标收集循环"""
        while not self._shutdown_event.is_set():
            try:
                # 收集和更新性能指标
                for driver_id in list(self._drivers.keys()):
                    try:
                        metrics = await self._drivers[driver_id].Driver.GetPerformanceMetrics()
                        # 这里可以进一步处理和存储性能指标
                    except Exception as e:
                        self._logger.error(f"Metrics collection failed for driver '{driver_id}': {e}")
                
                await asyncio.sleep(60)  # 每分钟收集一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(10)  # 短暂延迟后重试

# 全局驱动管理器实例
_global_driver_manager: Optional[LLMDriverManager] = None

def GetGlobalDriverManager() -> LLMDriverManager:
    """获取全局驱动管理器实例"""
    global _global_driver_manager
    if _global_driver_manager is None:
        _global_driver_manager = LLMDriverManager()
    return _global_driver_manager

def SetGlobalDriverManager(manager: LLMDriverManager):
    """设置全局驱动管理器实例"""
    global _global_driver_manager
    _global_driver_manager = manager