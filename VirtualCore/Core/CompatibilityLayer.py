"""
ByenatOS 大语言模型兼容层
========================

这是byenatOS的模型兼容性管理系统，类似于操作系统的设备驱动兼容层。
它负责处理不同厂商大语言模型之间的API差异，提供统一的接口抽象。

类比：就像显卡驱动兼容层可以让不同厂商的显卡（NVIDIA、AMD、Intel）
     使用统一的图形API一样，这个兼容层让不同的LLM可以使用统一的接口。
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Union, Callable, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import importlib
import sys
from pathlib import Path

from .LLMInterface import (
    ILLMDriver, ILLMDriverFactory, ModelSpecification, 
    InferenceRequest, InferenceResponse, ModelHealthStatus,
    ModelType, ModelSize, ComputeRequirement, LLMDriverException,
    LLMConfig
)

class VendorType(Enum):
    """支持的厂商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    META = "meta"
    HUGGINGFACE = "huggingface"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    TENCENT = "tencent"
    BYTEDANCE = "bytedance"
    LOCAL = "local"
    CUSTOM = "custom"

class APIFormat(Enum):
    """API格式类型"""
    OPENAI_CHAT = "openai_chat"           # OpenAI Chat Completions格式
    OPENAI_COMPLETION = "openai_completion" # OpenAI Legacy Completions格式
    ANTHROPIC_MESSAGES = "anthropic_messages" # Anthropic Messages格式
    GOOGLE_PALM = "google_palm"           # Google PaLM格式
    HUGGINGFACE = "huggingface"          # HuggingFace格式
    OLLAMA = "ollama"                    # Ollama格式
    LLAMACPP = "llamacpp"                # llama.cpp格式
    VLLM = "vllm"                        # vLLM格式
    CUSTOM = "custom"                    # 自定义格式

@dataclass
class VendorProfile:
    """厂商配置档案"""
    VendorType: VendorType
    Name: str
    APIFormat: APIFormat
    BaseURL: Optional[str] = None
    AuthenticationMethod: str = "api_key"  # api_key, oauth, bearer, custom
    RequiredHeaders: Dict[str, str] = field(default_factory=dict)
    DefaultParameters: Dict[str, Any] = field(default_factory=dict)
    RateLimits: Dict[str, int] = field(default_factory=dict)  # requests per minute/hour
    MaxTokens: int = 4096
    SupportedFeatures: List[str] = field(default_factory=list)
    RequestTransforms: Dict[str, str] = field(default_factory=dict)
    ResponseTransforms: Dict[str, str] = field(default_factory=dict)
    ErrorMappings: Dict[str, str] = field(default_factory=dict)
    Metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompatibilityRule:
    """兼容性规则"""
    RuleId: str
    SourceFormat: APIFormat
    TargetFormat: APIFormat
    TransformFunction: str  # 转换函数名称
    Conditions: Dict[str, Any] = field(default_factory=dict)
    Priority: int = 0
    Enabled: bool = True

class IFormatTransformer(ABC):
    """格式转换器接口"""
    
    @abstractmethod
    async def TransformRequest(self, request: InferenceRequest, 
                             source_profile: VendorProfile, 
                             target_profile: VendorProfile) -> Dict[str, Any]:
        """转换推理请求格式"""
        pass
    
    @abstractmethod
    async def TransformResponse(self, response: Dict[str, Any], 
                              source_profile: VendorProfile, 
                              target_profile: VendorProfile) -> InferenceResponse:
        """转换推理响应格式"""
        pass
    
    @abstractmethod
    def GetSupportedFormats(self) -> List[APIFormat]:
        """获取支持的格式列表"""
        pass

class OpenAITransformer(IFormatTransformer):
    """OpenAI格式转换器"""
    
    async def TransformRequest(self, request: InferenceRequest, 
                             source_profile: VendorProfile, 
                             target_profile: VendorProfile) -> Dict[str, Any]:
        """转换到OpenAI格式"""
        
        if target_profile.APIFormat == APIFormat.OPENAI_CHAT:
            # 转换为Chat Completions格式
            messages = []
            
            if request.SystemPrompt:
                messages.append({"role": "system", "content": request.SystemPrompt})
            
            if isinstance(request.Prompt, str):
                messages.append({"role": "user", "content": request.Prompt})
            elif isinstance(request.Prompt, list):
                messages.extend(request.Prompt)
            
            openai_request = {
                "model": target_profile.Metadata.get("model_name", "gpt-3.5-turbo"),
                "messages": messages,
                "stream": request.Stream
            }
            
            # 添加可选参数
            if request.MaxTokens:
                openai_request["max_tokens"] = request.MaxTokens
            if request.Temperature is not None:
                openai_request["temperature"] = request.Temperature
            if request.TopP is not None:
                openai_request["top_p"] = request.TopP
            if request.StopSequences:
                openai_request["stop"] = request.StopSequences
            
            return openai_request
            
        elif target_profile.APIFormat == APIFormat.OPENAI_COMPLETION:
            # 转换为Legacy Completions格式
            prompt_text = request.Prompt
            if isinstance(request.Prompt, list):
                # 简单合并对话历史
                prompt_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                                       for msg in request.Prompt])
            
            if request.SystemPrompt:
                prompt_text = f"{request.SystemPrompt}\n\n{prompt_text}"
            
            return {
                "model": target_profile.Metadata.get("model_name", "text-davinci-003"),
                "prompt": prompt_text,
                "max_tokens": request.MaxTokens or 1024,
                "temperature": request.Temperature or 0.7,
                "top_p": request.TopP or 1.0,
                "stop": request.StopSequences,
                "stream": request.Stream
            }
        
        raise ValueError(f"Unsupported target format: {target_profile.APIFormat}")
    
    async def TransformResponse(self, response: Dict[str, Any], 
                              source_profile: VendorProfile, 
                              target_profile: VendorProfile) -> InferenceResponse:
        """转换OpenAI响应格式"""
        
        if "choices" not in response:
            raise ValueError("Invalid OpenAI response format")
        
        choice = response["choices"][0]
        
        # 处理Chat Completions响应
        if "message" in choice:
            text = choice["message"].get("content", "")
            finish_reason = choice.get("finish_reason", "completed")
        # 处理Legacy Completions响应
        elif "text" in choice:
            text = choice["text"]
            finish_reason = choice.get("finish_reason", "completed")
        else:
            text = ""
            finish_reason = "error"
        
        # 提取使用统计
        usage = response.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        
        return InferenceResponse(
            RequestId="",  # 将在上层设置
            Text=text,
            FinishReason=finish_reason,
            TokensUsed=tokens_used,
            ProcessingTime=0.0,  # 将在上层设置
            ModelId="",  # 将在上层设置
            Metadata={
                "usage": usage,
                "model": response.get("model", ""),
                "original_response": response
            }
        )
    
    def GetSupportedFormats(self) -> List[APIFormat]:
        return [APIFormat.OPENAI_CHAT, APIFormat.OPENAI_COMPLETION]

class AnthropicTransformer(IFormatTransformer):
    """Anthropic格式转换器"""
    
    async def TransformRequest(self, request: InferenceRequest, 
                             source_profile: VendorProfile, 
                             target_profile: VendorProfile) -> Dict[str, Any]:
        """转换到Anthropic格式"""
        
        messages = []
        
        if isinstance(request.Prompt, str):
            messages.append({"role": "user", "content": request.Prompt})
        elif isinstance(request.Prompt, list):
            # 转换消息格式
            for msg in request.Prompt:
                role = msg.get("role", "user")
                # Anthropic使用 "user" 和 "assistant"
                if role == "system":
                    # 系统消息可以作为第一条用户消息的前缀
                    content = msg.get("content", "")
                    if messages and messages[0]["role"] == "user":
                        messages[0]["content"] = f"{content}\n\n{messages[0]['content']}"
                    else:
                        messages.insert(0, {"role": "user", "content": content})
                else:
                    messages.append({
                        "role": "assistant" if role == "assistant" else "user",
                        "content": msg.get("content", "")
                    })
        
        anthropic_request = {
            "model": target_profile.Metadata.get("model_name", "claude-3-sonnet-20240229"),
            "messages": messages,
            "max_tokens": request.MaxTokens or 1024,
            "stream": request.Stream
        }
        
        # 系统提示单独处理
        if request.SystemPrompt:
            anthropic_request["system"] = request.SystemPrompt
        
        # 添加可选参数
        if request.Temperature is not None:
            anthropic_request["temperature"] = request.Temperature
        if request.TopP is not None:
            anthropic_request["top_p"] = request.TopP
        if request.StopSequences:
            anthropic_request["stop_sequences"] = request.StopSequences
        
        return anthropic_request
    
    async def TransformResponse(self, response: Dict[str, Any], 
                              source_profile: VendorProfile, 
                              target_profile: VendorProfile) -> InferenceResponse:
        """转换Anthropic响应格式"""
        
        if "content" not in response:
            raise ValueError("Invalid Anthropic response format")
        
        # Anthropic返回content数组
        content_blocks = response["content"]
        text = ""
        
        for block in content_blocks:
            if block.get("type") == "text":
                text += block.get("text", "")
        
        finish_reason = response.get("stop_reason", "completed")
        if finish_reason == "end_turn":
            finish_reason = "completed"
        
        # 提取使用统计
        usage = response.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        
        return InferenceResponse(
            RequestId="",
            Text=text,
            FinishReason=finish_reason,
            TokensUsed=tokens_used,
            ProcessingTime=0.0,
            ModelId="",
            Metadata={
                "usage": usage,
                "model": response.get("model", ""),
                "original_response": response
            }
        )
    
    def GetSupportedFormats(self) -> List[APIFormat]:
        return [APIFormat.ANTHROPIC_MESSAGES]

class HuggingFaceTransformer(IFormatTransformer):
    """HuggingFace格式转换器"""
    
    async def TransformRequest(self, request: InferenceRequest, 
                             source_profile: VendorProfile, 
                             target_profile: VendorProfile) -> Dict[str, Any]:
        """转换到HuggingFace格式"""
        
        # 构建输入文本
        input_text = ""
        
        if request.SystemPrompt:
            input_text += f"System: {request.SystemPrompt}\n\n"
        
        if isinstance(request.Prompt, str):
            input_text += f"User: {request.Prompt}\nAssistant:"
        elif isinstance(request.Prompt, list):
            for msg in request.Prompt:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                input_text += f"{role.capitalize()}: {content}\n"
            input_text += "Assistant:"
        
        hf_request = {
            "inputs": input_text,
            "parameters": {
                "max_new_tokens": request.MaxTokens or 512,
                "temperature": request.Temperature or 0.7,
                "top_p": request.TopP or 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        if request.StopSequences:
            hf_request["parameters"]["stop"] = request.StopSequences
        
        return hf_request
    
    async def TransformResponse(self, response: Dict[str, Any], 
                              source_profile: VendorProfile, 
                              target_profile: VendorProfile) -> InferenceResponse:
        """转换HuggingFace响应格式"""
        
        if isinstance(response, list) and len(response) > 0:
            result = response[0]
            text = result.get("generated_text", "")
        elif "generated_text" in response:
            text = response["generated_text"]
        else:
            text = ""
        
        return InferenceResponse(
            RequestId="",
            Text=text,
            FinishReason="completed",
            TokensUsed=len(text.split()),  # 简单估算
            ProcessingTime=0.0,
            ModelId="",
            Metadata={"original_response": response}
        )
    
    def GetSupportedFormats(self) -> List[APIFormat]:
        return [APIFormat.HUGGINGFACE]

class CompatibilityLayer:
    """
    大语言模型兼容层
    ==============
    
    核心功能：
    1. 厂商识别 - 自动识别不同厂商的模型和API格式
    2. 格式转换 - 在不同API格式之间进行转换
    3. 参数映射 - 映射不同厂商的参数名称和值
    4. 错误处理 - 统一处理不同厂商的错误格式
    5. 特性适配 - 处理不同模型支持的特性差异
    6. 性能优化 - 优化不同厂商API的调用方式
    """
    
    def __init__(self):
        """初始化兼容层"""
        
        # 厂商配置档案
        self._vendor_profiles: Dict[str, VendorProfile] = {}
        
        # 格式转换器
        self._transformers: Dict[APIFormat, IFormatTransformer] = {}
        
        # 兼容性规则
        self._compatibility_rules: List[CompatibilityRule] = []
        
        # 错误映射
        self._error_mappings: Dict[str, Dict[str, str]] = {}
        
        # 参数映射
        self._parameter_mappings: Dict[APIFormat, Dict[str, str]] = {}
        
        # 缓存
        self._format_cache: Dict[str, APIFormat] = {}
        self._transform_cache: Dict[str, Any] = {}
        
        # 日志记录
        self._logger = logging.getLogger(__name__)
        
        # 初始化
        self._initialize_default_profiles()
        self._initialize_transformers()
        self._initialize_compatibility_rules()
    
    def RegisterVendorProfile(self, profile: VendorProfile) -> bool:
        """
        注册厂商配置档案
        
        Args:
            profile: 厂商配置档案
            
        Returns:
            bool: 注册是否成功
        """
        try:
            vendor_key = f"{profile.VendorType.value}_{profile.APIFormat.value}"
            self._vendor_profiles[vendor_key] = profile
            
            self._logger.info(f"Registered vendor profile: {vendor_key}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register vendor profile: {e}")
            return False
    
    def RegisterTransformer(self, transformer: IFormatTransformer) -> bool:
        """
        注册格式转换器
        
        Args:
            transformer: 格式转换器实例
            
        Returns:
            bool: 注册是否成功
        """
        try:
            supported_formats = transformer.GetSupportedFormats()
            for format_type in supported_formats:
                self._transformers[format_type] = transformer
            
            self._logger.info(f"Registered transformer for formats: {[f.value for f in supported_formats]}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register transformer: {e}")
            return False
    
    async def DetectModelFormat(self, model_spec: ModelSpecification) -> APIFormat:
        """
        检测模型的API格式
        
        Args:
            model_spec: 模型规格说明
            
        Returns:
            APIFormat: 检测到的API格式
        """
        # 检查缓存
        cache_key = f"{model_spec.Vendor}_{model_spec.ModelId}"
        if cache_key in self._format_cache:
            return self._format_cache[cache_key]
        
        # 基于厂商名称检测
        vendor_lower = model_spec.Vendor.lower()
        
        if "openai" in vendor_lower:
            format_type = APIFormat.OPENAI_CHAT
        elif "anthropic" in vendor_lower or "claude" in vendor_lower:
            format_type = APIFormat.ANTHROPIC_MESSAGES
        elif "google" in vendor_lower or "palm" in vendor_lower or "gemini" in vendor_lower:
            format_type = APIFormat.GOOGLE_PALM
        elif "huggingface" in vendor_lower or "hf" in vendor_lower:
            format_type = APIFormat.HUGGINGFACE
        elif "ollama" in vendor_lower:
            format_type = APIFormat.OLLAMA
        elif "llama" in vendor_lower and "cpp" in vendor_lower:
            format_type = APIFormat.LLAMACPP
        elif "vllm" in vendor_lower:
            format_type = APIFormat.VLLM
        elif "local" in vendor_lower:
            format_type = APIFormat.HUGGINGFACE  # 默认本地模型使用HF格式
        else:
            format_type = APIFormat.CUSTOM
        
        # 缓存结果
        self._format_cache[cache_key] = format_type
        
        self._logger.info(f"Detected format {format_type.value} for model {model_spec.ModelId}")
        return format_type
    
    async def TransformRequest(self, request: InferenceRequest, 
                             source_format: APIFormat, 
                             target_format: APIFormat) -> Dict[str, Any]:
        """
        转换推理请求格式
        
        Args:
            request: 原始推理请求
            source_format: 源格式
            target_format: 目标格式
            
        Returns:
            Dict[str, Any]: 转换后的请求数据
        """
        if source_format == target_format:
            # 格式相同，直接返回
            return self._request_to_dict(request)
        
        # 查找转换器
        transformer = self._transformers.get(target_format)
        if not transformer:
            raise ValueError(f"No transformer found for target format: {target_format}")
        
        # 获取厂商配置
        source_profile = self._get_profile_by_format(source_format)
        target_profile = self._get_profile_by_format(target_format)
        
        # 执行转换
        transformed_request = await transformer.TransformRequest(
            request, source_profile, target_profile
        )
        
        return transformed_request
    
    async def TransformResponse(self, response: Dict[str, Any], 
                              source_format: APIFormat, 
                              target_format: APIFormat) -> InferenceResponse:
        """
        转换推理响应格式
        
        Args:
            response: 原始响应数据
            source_format: 源格式
            target_format: 目标格式
            
        Returns:
            InferenceResponse: 转换后的响应
        """
        if source_format == target_format:
            # 格式相同，需要从dict转换为InferenceResponse
            return self._dict_to_response(response)
        
        # 查找转换器
        transformer = self._transformers.get(source_format)
        if not transformer:
            raise ValueError(f"No transformer found for source format: {source_format}")
        
        # 获取厂商配置
        source_profile = self._get_profile_by_format(source_format)
        target_profile = self._get_profile_by_format(target_format)
        
        # 执行转换
        transformed_response = await transformer.TransformResponse(
            response, source_profile, target_profile
        )
        
        return transformed_response
    
    def MapParameterName(self, param_name: str, 
                        source_format: APIFormat, 
                        target_format: APIFormat) -> str:
        """
        映射参数名称
        
        Args:
            param_name: 源参数名称
            source_format: 源格式
            target_format: 目标格式
            
        Returns:
            str: 映射后的参数名称
        """
        # 获取参数映射表
        source_mapping = self._parameter_mappings.get(source_format, {})
        target_mapping = self._parameter_mappings.get(target_format, {})
        
        # 反向查找目标格式中的参数名
        for target_param, standard_param in target_mapping.items():
            if source_mapping.get(param_name) == standard_param:
                return target_param
        
        # 如果没有找到映射，返回原始名称
        return param_name
    
    def MapErrorCode(self, error_code: str, vendor_type: VendorType) -> str:
        """
        映射错误代码
        
        Args:
            error_code: 原始错误代码
            vendor_type: 厂商类型
            
        Returns:
            str: 标准化的错误代码
        """
        vendor_errors = self._error_mappings.get(vendor_type.value, {})
        return vendor_errors.get(error_code, error_code)
    
    def GetCompatibilityInfo(self, model_spec: ModelSpecification) -> Dict[str, Any]:
        """
        获取模型兼容性信息
        
        Args:
            model_spec: 模型规格说明
            
        Returns:
            Dict[str, Any]: 兼容性信息
        """
        info = {
            "model_id": model_spec.ModelId,
            "vendor": model_spec.Vendor,
            "detected_format": None,
            "supported_features": [],
            "limitations": [],
            "recommendations": []
        }
        
        try:
            # 检测格式
            format_type = asyncio.run(self.DetectModelFormat(model_spec))
            info["detected_format"] = format_type.value
            
            # 获取厂商配置
            profile = self._get_profile_by_format(format_type)
            if profile:
                info["supported_features"] = profile.SupportedFeatures.copy()
                info["max_tokens"] = profile.MaxTokens
                info["rate_limits"] = profile.RateLimits.copy()
            
            # 分析限制和建议
            info["limitations"] = self._analyze_limitations(model_spec, format_type)
            info["recommendations"] = self._generate_recommendations(model_spec, format_type)
            
        except Exception as e:
            self._logger.error(f"Failed to get compatibility info: {e}")
            info["error"] = str(e)
        
        return info
    
    def GetSupportedVendors(self) -> List[str]:
        """获取支持的厂商列表"""
        return [vendor.value for vendor in VendorType]
    
    def GetSupportedFormats(self) -> List[str]:
        """获取支持的API格式列表"""
        return [format_type.value for format_type in APIFormat]
    
    # 私有方法实现
    def _initialize_default_profiles(self):
        """初始化默认厂商配置档案"""
        
        # OpenAI配置
        openai_profile = VendorProfile(
            VendorType=VendorType.OPENAI,
            Name="OpenAI",
            APIFormat=APIFormat.OPENAI_CHAT,
            BaseURL="https://api.openai.com/v1",
            AuthenticationMethod="api_key",
            RequiredHeaders={"Authorization": "Bearer {api_key}"},
            DefaultParameters={"temperature": 0.7, "max_tokens": 1024},
            RateLimits={"requests_per_minute": 3500, "tokens_per_minute": 90000},
            MaxTokens=4096,
            SupportedFeatures=["chat", "completion", "streaming", "function_calling"],
            Metadata={"model_name": "gpt-3.5-turbo"}
        )
        self.RegisterVendorProfile(openai_profile)
        
        # Anthropic配置
        anthropic_profile = VendorProfile(
            VendorType=VendorType.ANTHROPIC,
            Name="Anthropic",
            APIFormat=APIFormat.ANTHROPIC_MESSAGES,
            BaseURL="https://api.anthropic.com/v1",
            AuthenticationMethod="api_key",
            RequiredHeaders={"x-api-key": "{api_key}", "anthropic-version": "2023-06-01"},
            DefaultParameters={"max_tokens": 1024},
            RateLimits={"requests_per_minute": 1000, "tokens_per_minute": 40000},
            MaxTokens=8192,
            SupportedFeatures=["chat", "streaming", "system_prompts"],
            Metadata={"model_name": "claude-3-sonnet-20240229"}
        )
        self.RegisterVendorProfile(anthropic_profile)
        
        # HuggingFace配置
        hf_profile = VendorProfile(
            VendorType=VendorType.HUGGINGFACE,
            Name="Hugging Face",
            APIFormat=APIFormat.HUGGINGFACE,
            BaseURL="https://api-inference.huggingface.co/models",
            AuthenticationMethod="api_key",
            RequiredHeaders={"Authorization": "Bearer {api_key}"},
            DefaultParameters={"temperature": 0.7, "max_new_tokens": 512},
            MaxTokens=2048,
            SupportedFeatures=["text_generation", "chat"],
            Metadata={"model_name": "microsoft/DialoGPT-medium"}
        )
        self.RegisterVendorProfile(hf_profile)
        
        # 本地模型配置
        local_profile = VendorProfile(
            VendorType=VendorType.LOCAL,
            Name="Local Model",
            APIFormat=APIFormat.HUGGINGFACE,
            BaseURL="http://localhost:8000",
            AuthenticationMethod="none",
            DefaultParameters={"temperature": 0.7, "max_new_tokens": 512},
            MaxTokens=4096,
            SupportedFeatures=["text_generation", "chat", "streaming"],
            Metadata={"model_name": "local-model"}
        )
        self.RegisterVendorProfile(local_profile)
    
    def _initialize_transformers(self):
        """初始化格式转换器"""
        
        # 注册OpenAI转换器
        openai_transformer = OpenAITransformer()
        self.RegisterTransformer(openai_transformer)
        
        # 注册Anthropic转换器
        anthropic_transformer = AnthropicTransformer()
        self.RegisterTransformer(anthropic_transformer)
        
        # 注册HuggingFace转换器
        hf_transformer = HuggingFaceTransformer()
        self.RegisterTransformer(hf_transformer)
    
    def _initialize_compatibility_rules(self):
        """初始化兼容性规则"""
        
        # OpenAI到其他格式的规则
        self._compatibility_rules.extend([
            CompatibilityRule(
                RuleId="openai_to_anthropic",
                SourceFormat=APIFormat.OPENAI_CHAT,
                TargetFormat=APIFormat.ANTHROPIC_MESSAGES,
                TransformFunction="openai_to_anthropic_transform",
                Priority=10,
                Enabled=True
            ),
            CompatibilityRule(
                RuleId="openai_to_huggingface",
                SourceFormat=APIFormat.OPENAI_CHAT,
                TargetFormat=APIFormat.HUGGINGFACE,
                TransformFunction="openai_to_hf_transform",
                Priority=10,
                Enabled=True
            )
        ])
        
        # 初始化参数映射
        self._parameter_mappings = {
            APIFormat.OPENAI_CHAT: {
                "max_tokens": "max_tokens",
                "temperature": "temperature", 
                "top_p": "top_p",
                "stop": "stop_sequences"
            },
            APIFormat.ANTHROPIC_MESSAGES: {
                "max_tokens": "max_tokens",
                "temperature": "temperature",
                "top_p": "top_p", 
                "stop_sequences": "stop_sequences"
            },
            APIFormat.HUGGINGFACE: {
                "max_new_tokens": "max_tokens",
                "temperature": "temperature",
                "top_p": "top_p",
                "stop": "stop_sequences"
            }
        }
        
        # 初始化错误映射
        self._error_mappings = {
            VendorType.OPENAI.value: {
                "invalid_request_error": "bad_request",
                "authentication_error": "unauthorized",
                "permission_error": "forbidden",
                "not_found_error": "not_found",
                "rate_limit_error": "rate_limited",
                "api_error": "server_error"
            },
            VendorType.ANTHROPIC.value: {
                "invalid_request": "bad_request",
                "authentication_error": "unauthorized",
                "permission_denied": "forbidden",
                "not_found": "not_found",
                "rate_limit_exceeded": "rate_limited",
                "server_error": "server_error"
            }
        }
    
    def _get_profile_by_format(self, format_type: APIFormat) -> VendorProfile:
        """根据格式获取厂商配置"""
        for profile in self._vendor_profiles.values():
            if profile.APIFormat == format_type:
                return profile
        
        # 返回默认配置
        return VendorProfile(
            VendorType=VendorType.CUSTOM,
            Name="Custom",
            APIFormat=format_type
        )
    
    def _request_to_dict(self, request: InferenceRequest) -> Dict[str, Any]:
        """将InferenceRequest转换为字典"""
        return {
            "request_id": request.RequestId,
            "prompt": request.Prompt,
            "max_tokens": request.MaxTokens,
            "temperature": request.Temperature,
            "top_p": request.TopP,
            "top_k": request.TopK,
            "stop_sequences": request.StopSequences,
            "stream": request.Stream,
            "system_prompt": request.SystemPrompt,
            "metadata": request.Metadata
        }
    
    def _dict_to_response(self, response_dict: Dict[str, Any]) -> InferenceResponse:
        """将字典转换为InferenceResponse"""
        return InferenceResponse(
            RequestId=response_dict.get("request_id", ""),
            Text=response_dict.get("text", ""),
            FinishReason=response_dict.get("finish_reason", "completed"),
            TokensUsed=response_dict.get("tokens_used", 0),
            ProcessingTime=response_dict.get("processing_time", 0.0),
            ModelId=response_dict.get("model_id", ""),
            Confidence=response_dict.get("confidence"),
            Metadata=response_dict.get("metadata", {})
        )
    
    def _analyze_limitations(self, model_spec: ModelSpecification, 
                           format_type: APIFormat) -> List[str]:
        """分析模型限制"""
        limitations = []
        
        # 基于模型规模分析限制
        if model_spec.ModelSize == ModelSize.NANO:
            limitations.append("Limited reasoning capabilities due to small model size")
            limitations.append("May have difficulty with complex multi-turn conversations")
        
        # 基于计算需求分析限制
        if model_spec.ComputeRequirement == ComputeRequirement.HIGH:
            limitations.append("Requires high-end GPU for optimal performance")
            limitations.append("May have slower inference on CPU-only systems")
        
        # 基于API格式分析限制
        if format_type == APIFormat.HUGGINGFACE:
            limitations.append("May not support advanced features like function calling")
        
        return limitations
    
    def _generate_recommendations(self, model_spec: ModelSpecification, 
                                format_type: APIFormat) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于模型类型的建议
        if model_spec.ModelType == ModelType.CODE_GENERATION:
            recommendations.append("Optimize prompts for code generation tasks")
            recommendations.append("Use appropriate stop sequences for code blocks")
        
        # 基于API格式的建议
        if format_type == APIFormat.OPENAI_CHAT:
            recommendations.append("Use system prompts for better control")
            recommendations.append("Enable streaming for better user experience")
        
        # 性能优化建议
        if model_spec.ComputeRequirement == ComputeRequirement.LOW:
            recommendations.append("Consider using this model for high-throughput scenarios")
        
        return recommendations

# 全局兼容层实例
_global_compatibility_layer: Optional[CompatibilityLayer] = None

def GetGlobalCompatibilityLayer() -> CompatibilityLayer:
    """获取全局兼容层实例"""
    global _global_compatibility_layer
    if _global_compatibility_layer is None:
        _global_compatibility_layer = CompatibilityLayer()
    return _global_compatibility_layer

def SetGlobalCompatibilityLayer(layer: CompatibilityLayer):
    """设置全局兼容层实例"""
    global _global_compatibility_layer
    _global_compatibility_layer = layer