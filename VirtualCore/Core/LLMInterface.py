"""
ByenatOS 虚拟系统大语言模型接口规范
=================================

这个文件定义了byenatOS虚拟系统中本地AI模型的标准化接口，类似于传统操作系统中的设备驱动标准。
任何想要在byenatOS虚拟系统中运行的本地AI模型都必须实现这个接口。

类比：就像不同的硬件设备都必须符合操作系统的设备驱动标准一样，
     不同的本地AI模型也必须实现byenatOS虚拟系统的统一接口标准。

这些本地AI模型作为虚拟系统的"虚拟CPU"，专门处理个性化计算任务。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

class ModelType(Enum):
    """模型类型枚举 - 类似于CPU的架构类型"""
    TEXT_GENERATION = "text_generation"      # 文本生成模型
    CHAT_COMPLETION = "chat_completion"      # 对话模型
    CODE_GENERATION = "code_generation"      # 代码生成模型
    MULTIMODAL = "multimodal"               # 多模态模型
    EMBEDDING = "embedding"                 # 嵌入模型
    CLASSIFICATION = "classification"        # 分类模型

class ModelSize(Enum):
    """模型规模枚举 - 类似于CPU的性能等级"""
    NANO = "nano"           # <1B参数 - 类似于低功耗CPU
    MICRO = "micro"         # 1B-3B参数 - 类似于入门级CPU
    SMALL = "small"         # 3B-7B参数 - 类似于主流CPU
    MEDIUM = "medium"       # 7B-13B参数 - 类似于高性能CPU
    LARGE = "large"         # 13B-30B参数 - 类似于旗舰CPU
    HUGE = "huge"           # >30B参数 - 类似于服务器级CPU

class ComputeRequirement(Enum):
    """计算需求枚举 - 类似于CPU的功耗等级"""
    LOW = "low"             # 低算力需求 (CPU推理)
    MEDIUM = "medium"       # 中等算力需求 (集成显卡)
    HIGH = "high"           # 高算力需求 (独立显卡)
    EXTREME = "extreme"     # 极高算力需求 (多GPU/TPU)

@dataclass
class ModelSpecification:
    """
    模型规格说明 - 类似于CPU的技术规格表
    这定义了一个大语言模型的基本技术参数
    """
    ModelId: str                           # 模型唯一标识符
    ModelName: str                         # 模型显示名称
    Vendor: str                           # 厂商名称 (OpenAI, Anthropic, 本地等)
    Version: str                          # 模型版本
    ModelType: ModelType                  # 模型类型
    ModelSize: ModelSize                  # 模型规模
    ParameterCount: int                   # 参数数量
    ComputeRequirement: ComputeRequirement # 计算需求
    MaxContextLength: int                 # 最大上下文长度
    SupportedLanguages: List[str]         # 支持的语言列表
    Features: List[str]                   # 支持的特性列表
    LocalSupport: bool                    # 是否支持本地运行
    CloudSupport: bool                    # 是否支持云端调用
    LicenseType: str                      # 许可证类型
    Description: str                      # 模型描述

@dataclass
class InferenceRequest:
    """推理请求 - 标准化的模型输入格式"""
    RequestId: str                        # 请求ID
    Prompt: Union[str, List[Dict]]        # 提示词或对话历史
    MaxTokens: Optional[int] = None       # 最大生成token数
    Temperature: Optional[float] = None    # 温度参数
    TopP: Optional[float] = None          # Top-p采样
    TopK: Optional[int] = None            # Top-k采样
    StopSequences: Optional[List[str]] = None  # 停止序列
    Stream: bool = False                  # 是否流式输出
    SystemPrompt: Optional[str] = None    # 系统提示词
    Metadata: Optional[Dict[str, Any]] = None  # 附加元数据

@dataclass
class InferenceResponse:
    """推理响应 - 标准化的模型输出格式"""
    RequestId: str                        # 对应的请求ID
    Text: str                            # 生成的文本
    FinishReason: str                    # 完成原因 (completed, length, stop)
    TokensUsed: int                      # 使用的token数
    ProcessingTime: float                # 处理时间（秒）
    ModelId: str                         # 使用的模型ID
    Confidence: Optional[float] = None    # 置信度
    Metadata: Optional[Dict[str, Any]] = None  # 附加元数据

@dataclass
class ModelHealthStatus:
    """模型健康状态 - 类似于CPU的运行状态监控"""
    ModelId: str                         # 模型ID
    Status: str                          # 状态 (healthy, degraded, error, offline)
    CpuUsage: float                      # CPU使用率
    GpuUsage: float                      # GPU使用率
    MemoryUsage: float                   # 内存使用率
    ResponseTime: float                  # 平均响应时间
    ErrorRate: float                     # 错误率
    ThroughputRpm: float                 # 吞吐量（每分钟请求数）
    LastHealthCheck: datetime            # 最后健康检查时间
    ErrorMessages: List[str]             # 错误消息列表

class ILLMDriver(ABC):
    """
    大语言模型驱动接口 - 核心抽象类
    =====================================
    
    这是byenatOS中大语言模型的核心接口，类似于操作系统中的设备驱动程序接口。
    所有的大语言模型实现都必须继承并实现这个接口。
    
    设计理念：
    1. 标准化 - 统一的接口规范，确保不同模型的一致性
    2. 可插拔 - 支持热插拔，动态加载和卸载模型
    3. 可监控 - 提供详细的性能和健康状态监控
    4. 可扩展 - 支持未来新特性的扩展
    """
    
    @abstractmethod
    def GetSpecification(self) -> ModelSpecification:
        """
        获取模型规格说明
        类似于CPU的CPUID指令，返回模型的详细技术规格
        
        Returns:
            ModelSpecification: 模型的详细规格信息
        """
        pass
    
    @abstractmethod
    async def Initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化模型驱动
        类似于设备驱动的初始化过程
        
        Args:
            config: 初始化配置参数
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def Shutdown(self) -> bool:
        """
        关闭模型驱动
        类似于设备驱动的清理过程
        
        Returns:
            bool: 关闭是否成功
        """
        pass
    
    @abstractmethod
    async def ProcessInference(self, request: InferenceRequest) -> InferenceResponse:
        """
        处理推理请求 - 核心功能
        这是模型驱动的主要工作函数
        
        Args:
            request: 标准化的推理请求
            
        Returns:
            InferenceResponse: 标准化的推理响应
        """
        pass
    
    @abstractmethod
    async def ProcessInferenceStream(self, request: InferenceRequest) -> AsyncIterator[str]:
        """
        处理流式推理请求
        支持实时流式输出，提升用户体验
        
        Args:
            request: 标准化的推理请求
            
        Yields:
            str: 流式输出的文本片段
        """
        pass
    
    @abstractmethod
    async def GetHealthStatus(self) -> ModelHealthStatus:
        """
        获取模型健康状态
        类似于系统监控中的CPU状态监控
        
        Returns:
            ModelHealthStatus: 详细的健康状态信息
        """
        pass
    
    @abstractmethod
    async def ValidateConfiguration(self, config: Dict[str, Any]) -> bool:
        """
        验证配置参数
        确保配置参数的有效性
        
        Args:
            config: 配置参数
            
        Returns:
            bool: 配置是否有效
        """
        pass
    
    @abstractmethod
    async def GetPerformanceMetrics(self) -> Dict[str, float]:
        """
        获取性能指标
        类似于CPU的性能计数器
        
        Returns:
            Dict[str, float]: 性能指标字典
        """
        pass
    
    @abstractmethod
    async def WarmUp(self) -> bool:
        """
        模型预热
        类似于CPU的预热过程，准备处理请求
        
        Returns:
            bool: 预热是否成功
        """
        pass
    
    # 可选的高级功能接口
    async def SupportsBatching(self) -> bool:
        """检查是否支持批处理"""
        return False
    
    async def ProcessBatch(self, requests: List[InferenceRequest]) -> List[InferenceResponse]:
        """批处理推理请求（可选实现）"""
        raise NotImplementedError("Batch processing not supported")
    
    async def SupportsFineTuning(self) -> bool:
        """检查是否支持微调"""
        return False
    
    async def StartFineTuning(self, training_data: Any, config: Dict[str, Any]) -> str:
        """开始微调（可选实现）"""
        raise NotImplementedError("Fine-tuning not supported")

class ILLMDriverFactory(ABC):
    """
    大语言模型驱动工厂接口
    ========================
    
    用于创建和管理特定类型的模型驱动实例
    类似于设备驱动的工厂模式
    """
    
    @abstractmethod
    def GetSupportedModels(self) -> List[ModelSpecification]:
        """获取支持的模型列表"""
        pass
    
    @abstractmethod
    async def CreateDriver(self, model_id: str, config: Dict[str, Any]) -> ILLMDriver:
        """创建模型驱动实例"""
        pass
    
    @abstractmethod
    def GetFactoryInfo(self) -> Dict[str, str]:
        """获取工厂信息"""
        pass

# 预定义的常用配置常量
class LLMConfig:
    """大语言模型配置常量"""
    
    # 通用配置键
    MODEL_PATH = "model_path"
    API_KEY = "api_key"
    API_ENDPOINT = "api_endpoint"
    MAX_CONCURRENT_REQUESTS = "max_concurrent_requests"
    TIMEOUT_SECONDS = "timeout_seconds"
    CACHE_SIZE = "cache_size"
    
    # 性能配置
    GPU_DEVICE_ID = "gpu_device_id"
    CPU_THREADS = "cpu_threads"
    MEMORY_LIMIT_GB = "memory_limit_gb"
    BATCH_SIZE = "batch_size"
    
    # 安全配置
    ENABLE_SAFETY_FILTERS = "enable_safety_filters"
    MAX_OUTPUT_LENGTH = "max_output_length"
    RATE_LIMIT_RPM = "rate_limit_rpm"
    
    # 默认值
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.7

# 异常类定义
class LLMDriverException(Exception):
    """LLM驱动基础异常类"""
    pass

class ModelNotFoundError(LLMDriverException):
    """模型未找到错误"""
    pass

class ModelInitializationError(LLMDriverException):
    """模型初始化错误"""
    pass

class InferenceError(LLMDriverException):
    """推理处理错误"""
    pass

class ConfigurationError(LLMDriverException):
    """配置错误"""
    pass

class ResourceExhaustedError(LLMDriverException):
    """资源耗尽错误"""
    pass

# 工具函数
def ValidateModelSpecification(spec: ModelSpecification) -> bool:
    """验证模型规格说明的完整性"""
    required_fields = ['ModelId', 'ModelName', 'Vendor', 'Version']
    return all(getattr(spec, field, None) for field in required_fields)

def CompareModelSpecs(spec1: ModelSpecification, spec2: ModelSpecification) -> Dict[str, bool]:
    """比较两个模型规格的兼容性"""
    return {
        'same_type': spec1.ModelType == spec2.ModelType,
        'compatible_size': spec1.ComputeRequirement.value <= spec2.ComputeRequirement.value,
        'same_vendor': spec1.Vendor == spec2.Vendor,
        'newer_version': spec1.Version >= spec2.Version
    }