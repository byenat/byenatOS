"""
ByenatOS 本地HiNATA处理器 - 虚拟系统的专用AI处理单元
===============================================

作为byenatOS虚拟系统的"虚拟CPU"核心组件，这是专门为个性化计算设计的本地AI处理器，
运行在现有操作系统之上，仅负责两个核心功能：
1. HiNATA内容的智能细化处理
2. HiNATA到PSP (Personal System Prompt) 的个性化转化

其他所有通用AI交互场景都由App调用在线大模型处理。
本处理器专注于个性化计算，相当于传统OS中专门处理特定计算的协处理器。
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

@dataclass
class HiNATARecord:
    """HiNATA数据记录"""
    Id: str
    Timestamp: datetime
    Source: str
    Highlight: str           # 用户重点关注的内容
    Note: str               # 用户添加的详细信息
    Address: str            # 数据来源地址
    Tags: List[str]         # 分类检索标签
    Access: str             # public|private|restricted

@dataclass
class RefinedHiNATA:
    """细化后的HiNATA数据"""
    OriginalId: str
    RefinedContent: str      # 细化后的内容
    ExtractedConcepts: List[str]  # 提取的关键概念
    UserIntentions: List[str]     # 识别的用户意图
    PersonalityInsights: Dict[str, float]  # 个性化洞察
    Confidence: float

class PSPCategory(Enum):
    """PSP分类"""
    CORE_MEMORY = "core_memory"           # 核心记忆层
    WORKING_MEMORY = "working_memory"     # 工作记忆层  
    LEARNING_MEMORY = "learning_memory"   # 学习记忆层
    CONTEXT_MEMORY = "context_memory"     # 上下文记忆层

@dataclass
class PSPComponent:
    """PSP组件"""
    Category: PSPCategory
    ComponentType: str       # PersonalRules, CognitivePatterns等
    Content: str            # 实际的PSP内容
    Priority: int           # 优先级 (1-100)
    LastUpdated: datetime
    SourceHiNATAIds: List[str]

class LocalHiNATAProcessor:
    """
    本地HiNATA处理器
    ===============
    
    专门用于本地模型的HiNATA处理，功能聚焦：
    - 接收HiNATA数据并进行细化处理
    - 将细化后的数据转换为PSP组件
    - 导出PSP为可用的系统提示词
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化本地处理器
        
        Args:
            model_config: 本地模型配置
        """
        self.model_config = model_config
        self.is_initialized = False
        
        # PSP存储
        self.psp_components: Dict[str, PSPComponent] = {}
        
        # 统计
        self.processed_count = 0
        self.generated_psp_count = 0
        
        self._logger = logging.getLogger(__name__)
    
    async def Initialize(self) -> bool:
        """初始化处理器"""
        try:
            # 这里可以加载本地模型、初始化配置等
            self._logger.info("Initializing Local HiNATA Processor")
            
            # 模拟初始化过程
            await asyncio.sleep(1)
            
            self.is_initialized = True
            self._logger.info("Local HiNATA Processor initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize processor: {e}")
            return False
    
    async def RefineHiNATAContent(self, hinata_record: HiNATARecord) -> RefinedHiNATA:
        """
        细化HiNATA内容
        
        这是本地模型的第一个核心功能：
        - 分析用户的Highlight和Note
        - 提取关键概念和意图
        - 识别个性化特征
        
        Args:
            hinata_record: 原始HiNATA记录
            
        Returns:
            RefinedHiNATA: 细化后的数据
        """
        if not self.is_initialized:
            raise RuntimeError("Processor not initialized")
        
        try:
            # 构建分析提示词
            analysis_prompt = self._build_refinement_prompt(hinata_record)
            
            # 调用本地模型进行分析（这里模拟）
            analysis_result = await self._call_local_model_for_refinement(analysis_prompt)
            
            # 创建细化结果
            refined = RefinedHiNATA(
                OriginalId=hinata_record.Id,
                RefinedContent=analysis_result.get('refined_content', ''),
                ExtractedConcepts=analysis_result.get('concepts', []),
                UserIntentions=analysis_result.get('intentions', []),
                PersonalityInsights=analysis_result.get('personality_insights', {}),
                Confidence=analysis_result.get('confidence', 0.0)
            )
            
            self.processed_count += 1
            self._logger.info(f"Refined HiNATA record {hinata_record.Id}")
            
            return refined
            
        except Exception as e:
            self._logger.error(f"Failed to refine HiNATA content: {e}")
            raise
    
    async def GeneratePSPFromHiNATA(self, refined_hinata_list: List[RefinedHiNATA]) -> List[PSPComponent]:
        """
        从细化的HiNATA数据生成PSP组件
        
        这是本地模型的第二个核心功能：
        - 分析细化后的HiNATA数据
        - 生成个性化的系统提示组件
        - 按照PSP分类进行组织
        
        Args:
            refined_hinata_list: 细化后的HiNATA数据列表
            
        Returns:
            List[PSPComponent]: 生成的PSP组件列表
        """
        if not self.is_initialized:
            raise RuntimeError("Processor not initialized")
        
        try:
            # 构建PSP生成提示词
            psp_prompt = self._build_psp_generation_prompt(refined_hinata_list)
            
            # 调用本地模型生成PSP（这里模拟）
            psp_result = await self._call_local_model_for_psp(psp_prompt)
            
            # 解析并创建PSP组件
            new_components = []
            for comp_data in psp_result.get('components', []):
                component = PSPComponent(
                    Category=PSPCategory(comp_data['category']),
                    ComponentType=comp_data['type'],
                    Content=comp_data['content'],
                    Priority=comp_data['priority'],
                    LastUpdated=datetime.now(),
                    SourceHiNATAIds=[h.OriginalId for h in refined_hinata_list]
                )
                
                # 存储组件
                component_id = f"{component.Category.value}_{len(new_components)}"
                self.psp_components[component_id] = component
                new_components.append(component)
            
            self.generated_psp_count += len(new_components)
            self._logger.info(f"Generated {len(new_components)} PSP components")
            
            return new_components
            
        except Exception as e:
            self._logger.error(f"Failed to generate PSP components: {e}")
            raise
    
    async def ExportPSPAsSystemPrompt(self) -> str:
        """
        导出PSP为系统提示词
        
        将所有PSP组件格式化为可供在线大模型使用的系统提示词
        
        Returns:
            str: 格式化的系统提示词
        """
        if not self.psp_components:
            return "# Personal System Prompt\n\n当前暂无个性化配置。"
        
        prompt_sections = ["# Personal System Prompt", ""]
        
        # 按分类组织PSP组件
        categories = {
            PSPCategory.CORE_MEMORY: "## 核心个性化规则",
            PSPCategory.WORKING_MEMORY: "## 当前工作焦点", 
            PSPCategory.LEARNING_MEMORY: "## 学习和适应偏好",
            PSPCategory.CONTEXT_MEMORY: "## 上下文和环境特征"
        }
        
        for category, title in categories.items():
            category_components = [
                comp for comp in self.psp_components.values() 
                if comp.Category == category
            ]
            
            if category_components:
                prompt_sections.append(title)
                
                # 按优先级排序
                category_components.sort(key=lambda x: x.Priority, reverse=True)
                
                for component in category_components:
                    prompt_sections.append(f"- {component.Content}")
                
                prompt_sections.append("")  # 空行分隔
        
        return "\n".join(prompt_sections)
    
    async def ProcessHiNATABatch(self, hinata_records: List[HiNATARecord]) -> str:
        """
        批量处理HiNATA记录并生成更新的PSP
        
        这是完整的处理流程：
        HiNATA原始数据 → 细化处理 → PSP生成 → 系统提示词导出
        
        Args:
            hinata_records: HiNATA记录列表
            
        Returns:
            str: 更新后的系统提示词
        """
        if not hinata_records:
            return await self.ExportPSPAsSystemPrompt()
        
        try:
            # 步骤1: 细化HiNATA内容
            refined_list = []
            for record in hinata_records:
                refined = await self.RefineHiNATAContent(record)
                refined_list.append(refined)
            
            # 步骤2: 生成PSP组件
            await self.GeneratePSPFromHiNATA(refined_list)
            
            # 步骤3: 导出更新的系统提示词
            updated_prompt = await self.ExportPSPAsSystemPrompt()
            
            self._logger.info(f"Processed batch of {len(hinata_records)} HiNATA records")
            
            return updated_prompt
            
        except Exception as e:
            self._logger.error(f"Failed to process HiNATA batch: {e}")
            raise
    
    def GetProcessingStats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            "processed_hinata_count": self.processed_count,
            "generated_psp_count": self.generated_psp_count,
            "current_psp_components": len(self.psp_components),
            "is_initialized": self.is_initialized
        }
    
    # 私有方法
    def _build_refinement_prompt(self, hinata_record: HiNATARecord) -> str:
        """构建HiNATA细化处理的提示词"""
        return f"""
你是byenatOS的本地HiNATA细化处理器。请分析以下用户数据：

**用户重点关注内容**: {hinata_record.Highlight}
**用户添加的笔记**: {hinata_record.Note}
**来源**: {hinata_record.Source}
**标签**: {', '.join(hinata_record.Tags)}

请提取和分析：
1. 核心概念和主题
2. 用户的潜在意图
3. 体现的个性特征和偏好

以JSON格式返回：
{{
    "refined_content": "细化总结的内容",
    "concepts": ["概念1", "概念2"],
    "intentions": ["意图1", "意图2"], 
    "personality_insights": {{"特征1": 0.8, "特征2": 0.6}},
    "confidence": 0.9
}}
"""
    
    def _build_psp_generation_prompt(self, refined_hinata_list: List[RefinedHiNATA]) -> str:
        """构建PSP生成的提示词"""
        
        # 汇总所有细化数据
        all_concepts = []
        all_intentions = []
        all_insights = {}
        
        for refined in refined_hinata_list:
            all_concepts.extend(refined.ExtractedConcepts)
            all_intentions.extend(refined.UserIntentions)
            for key, value in refined.PersonalityInsights.items():
                all_insights[key] = max(all_insights.get(key, 0), value)
        
        return f"""
你是byenatOS的PSP生成器。基于以下用户数据分析，生成Personal System Prompt组件：

**提取的概念**: {', '.join(set(all_concepts))}
**用户意图**: {', '.join(set(all_intentions))}
**个性洞察**: {json.dumps(all_insights, ensure_ascii=False)}

请生成适当的PSP组件，按以下分类：
- core_memory: 核心个性化规则、认知模式、价值观、偏好
- working_memory: 当前优先级、活跃上下文、近期模式、会话目标
- learning_memory: 成功模式、错误纠正、适应日志、反馈整合
- context_memory: 领域知识、关系映射、环境特征、时间模式

以JSON格式返回：
{{
    "components": [
        {{
            "category": "core_memory",
            "type": "PersonalRules", 
            "content": "具体的个性化规则内容",
            "priority": 85
        }}
    ]
}}
"""
    
    async def _call_local_model_for_refinement(self, prompt: str) -> Dict[str, Any]:
        """调用本地模型进行HiNATA细化（模拟实现）"""
        # 这里应该调用实际的本地模型
        # 例如 llama.cpp, transformers, onnx等
        
        await asyncio.sleep(0.3)  # 模拟处理时间
        
        # 模拟返回结果
        return {
            "refined_content": "用户对AI技术和个性化服务表现出浓厚兴趣",
            "concepts": ["AI技术", "个性化", "用户体验", "效率提升"],
            "intentions": ["学习AI知识", "寻找提效工具", "个性化定制"],
            "personality_insights": {"好奇心": 0.9, "技术导向": 0.8, "效率追求": 0.85},
            "confidence": 0.87
        }
    
    async def _call_local_model_for_psp(self, prompt: str) -> Dict[str, Any]:
        """调用本地模型进行PSP生成（模拟实现）"""
        # 这里应该调用实际的本地模型
        
        await asyncio.sleep(0.5)  # 模拟处理时间
        
        # 模拟返回结果
        return {
            "components": [
                {
                    "category": "core_memory",
                    "type": "PersonalRules",
                    "content": "用户偏好简洁高效的AI交互，关注实用性和技术细节",
                    "priority": 90
                },
                {
                    "category": "working_memory",
                    "type": "ActiveContext", 
                    "content": "当前专注于AI技术在个人工作流程中的应用和优化",
                    "priority": 80
                },
                {
                    "category": "learning_memory",
                    "type": "SuccessPatterns",
                    "content": "对技术概念的快速理解和应用能力较强",
                    "priority": 75
                }
            ]
        }

# 全局实例管理
_global_processor: Optional[LocalHiNATAProcessor] = None

def GetGlobalProcessor() -> Optional[LocalHiNATAProcessor]:
    """获取全局处理器实例"""
    return _global_processor

async def InitializeGlobalProcessor(config: Dict[str, Any]) -> bool:
    """初始化全局处理器"""
    global _global_processor
    
    try:
        _global_processor = LocalHiNATAProcessor(config)
        return await _global_processor.Initialize()
    except Exception as e:
        logging.error(f"Failed to initialize global processor: {e}")
        return False

def SetGlobalProcessor(processor: LocalHiNATAProcessor):
    """设置全局处理器实例"""
    global _global_processor
    _global_processor = processor