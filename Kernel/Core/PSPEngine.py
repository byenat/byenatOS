"""
ByenatOS Personal System Prompt (PSP) Engine
PSP引擎 - 虚拟系统的个性化核心组件

作为byenatOS虚拟系统的个性化引擎核心，负责从HiNATA数据中提取用户意图，
生成和维护个性化系统提示。相当于传统OS中的系统调度器，但专门用于个性化计算。
运行在现有操作系统之上，为各App提供统一的个性化服务。
"""

import asyncio
import json
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque

import asyncpg
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity


class PSPComponentType(Enum):
    """PSP组件类型"""
    CORE_INTEREST = "core_interest"
    CURRENT_GOAL = "current_goal"
    LEARNING_PREFERENCE = "learning_preference"
    COMMUNICATION_STYLE = "communication_style"
    WORK_CONTEXT = "work_context"
    PERSONAL_VALUE = "personal_value"


class PSPUpdateAction(Enum):
    """PSP更新动作"""
    CREATE = "create"
    UPDATE = "update"
    STRENGTHEN = "strengthen"
    WEAKEN = "weaken"
    MERGE = "merge"
    SPLIT = "split"
    ARCHIVE = "archive"


@dataclass
class PSPComponent:
    """PSP组件"""
    id: str
    component_type: PSPComponentType
    description: str
    embedding: List[float]
    confidence: float
    total_attention_weight: float
    normalized_weight: float
    priority: str  # high, medium, low
    activation_threshold: float
    
    # 支撑证据
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    
    # 时间信息
    created_at: str = ""
    last_updated: str = ""
    last_activated: str = ""
    
    # 关联信息
    related_components: List[str] = field(default_factory=list)
    source_apps: Set[str] = field(default_factory=set)
    
    # 演化历史
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UserIntent:
    """用户意图"""
    id: str
    hinata_id: str
    description: str
    embedding: List[float]
    confidence: float
    attention_weight: float
    intent_type: PSPComponentType
    extracted_at: str
    source_app: str
    context: Dict[str, Any]


@dataclass
class PSPContext:
    """PSP上下文"""
    user_id: str
    core_memory: Dict[str, PSPComponent]
    working_memory: Dict[str, PSPComponent]
    learning_memory: Dict[str, PSPComponent]
    context_memory: Dict[str, PSPComponent]
    
    # 元信息
    last_updated: str = ""
    total_components: int = 0
    active_components: List[str] = field(default_factory=list)
    
    def get_all_components(self) -> Dict[str, PSPComponent]:
        """获取所有PSP组件"""
        all_components = {}
        all_components.update(self.core_memory)
        all_components.update(self.working_memory)
        all_components.update(self.learning_memory)
        all_components.update(self.context_memory)
        return all_components
    
    def get_high_priority_components(self) -> List[PSPComponent]:
        """获取高优先级组件"""
        components = []
        for comp in self.get_all_components().values():
            if comp.priority == "high":
                components.append(comp)
        return sorted(components, key=lambda x: x.normalized_weight, reverse=True)


class IntentExtractor:
    """意图提取器"""
    
    def __init__(self):
        self.intent_patterns = self._load_intent_patterns()
    
    def extract_intent_from_hinata(self, hinata_data: Dict[str, Any]) -> List[UserIntent]:
        """从HiNATA数据中提取用户意图"""
        intents = []
        
        # 1. 基于内容的意图提取
        content_intents = self._extract_content_based_intents(hinata_data)
        intents.extend(content_intents)
        
        # 2. 基于行为的意图提取
        behavior_intents = self._extract_behavior_based_intents(hinata_data)
        intents.extend(behavior_intents)
        
        # 3. 基于上下文的意图提取
        context_intents = self._extract_context_based_intents(hinata_data)
        intents.extend(context_intents)
        
        return intents
    
    def _extract_content_based_intents(self, hinata_data: Dict[str, Any]) -> List[UserIntent]:
        """基于内容提取意图"""
        intents = []
        
        highlight = hinata_data.get('highlight', '')
        note = hinata_data.get('note', '')
        enhanced_tags = hinata_data.get('enhanced_tags', [])
        
        # 学习意图检测
        learning_keywords = ['learn', 'understand', 'study', 'tutorial', 'guide', 'how to']
        if any(keyword in (highlight + note).lower() for keyword in learning_keywords):
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_learning",
                hinata_id=hinata_data['id'],
                description=f"Learning interest in: {', '.join(enhanced_tags[:3])}",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=0.8,
                attention_weight=hinata_data.get('attention_weight', 0.5),
                intent_type=PSPComponentType.CORE_INTEREST,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=hinata_data.get('source', ''),
                context={'topics': enhanced_tags, 'content_type': 'learning'}
            )
            intents.append(intent)
        
        # 工作相关意图检测
        work_keywords = ['project', 'task', 'deadline', 'meeting', 'work', 'job', 'career']
        if any(keyword in (highlight + note).lower() for keyword in work_keywords):
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_work",
                hinata_id=hinata_data['id'],
                description=f"Work-related activity: {highlight[:100]}",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=0.7,
                attention_weight=hinata_data.get('attention_weight', 0.5),
                intent_type=PSPComponentType.WORK_CONTEXT,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=hinata_data.get('source', ''),
                context={'work_area': enhanced_tags, 'priority': 'medium'}
            )
            intents.append(intent)
        
        return intents
    
    def _extract_behavior_based_intents(self, hinata_data: Dict[str, Any]) -> List[UserIntent]:
        """基于行为模式提取意图"""
        intents = []
        
        attention_weight = hinata_data.get('attention_weight', 0.5)
        attention_metrics = hinata_data.get('attention_metrics', {})
        
        # 高关注度内容表明核心兴趣
        if attention_weight > 0.7:
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_core",
                hinata_id=hinata_data['id'],
                description=f"High attention on: {hinata_data.get('highlight', '')[:100]}",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=attention_weight,
                attention_weight=attention_weight,
                intent_type=PSPComponentType.CORE_INTEREST,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=hinata_data.get('source', ''),
                context={'attention_metrics': attention_metrics, 'intensity': 'high'}
            )
            intents.append(intent)
        
        # 重复访问表明持续目标
        revisit_count = attention_metrics.get('address_revisit', 0)
        if revisit_count > 3:
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_goal",
                hinata_id=hinata_data['id'],
                description=f"Persistent goal related to: {hinata_data.get('address', '')}",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=min(revisit_count / 10.0, 1.0),
                attention_weight=attention_weight,
                intent_type=PSPComponentType.CURRENT_GOAL,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=hinata_data.get('source', ''),
                context={'revisit_count': revisit_count, 'persistence': 'high'}
            )
            intents.append(intent)
        
        return intents
    
    def _extract_context_based_intents(self, hinata_data: Dict[str, Any]) -> List[UserIntent]:
        """基于上下文提取意图"""
        intents = []
        
        source = hinata_data.get('source', '')
        semantic_analysis = hinata_data.get('semantic_analysis', {})
        
        # 基于来源App的意图推断
        if 'chatbot' in source or 'chat' in source:
            # AI交互表明学习偏好
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_learning_style",
                hinata_id=hinata_data['id'],
                description="AI-assisted learning preference",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=0.6,
                attention_weight=hinata_data.get('attention_weight', 0.5),
                intent_type=PSPComponentType.LEARNING_PREFERENCE,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=source,
                context={'interaction_type': 'ai_chat', 'topics': semantic_analysis.get('main_topics', [])}
            )
            intents.append(intent)
        
        # 基于情感的沟通风格推断
        sentiment = semantic_analysis.get('sentiment', 'neutral')
        if sentiment != 'neutral':
            intent = UserIntent(
                id=f"intent_{hinata_data['id']}_communication",
                hinata_id=hinata_data['id'],
                description=f"Communication style: {sentiment}",
                embedding=hinata_data.get('embedding_vector', []),
                confidence=0.5,
                attention_weight=hinata_data.get('attention_weight', 0.5),
                intent_type=PSPComponentType.COMMUNICATION_STYLE,
                extracted_at=datetime.now(timezone.utc).isoformat(),
                source_app=source,
                context={'sentiment': sentiment, 'style_indicator': True}
            )
            intents.append(intent)
        
        return intents
    
    def _load_intent_patterns(self) -> Dict[str, Any]:
        """加载意图识别模式"""
        return {
            'learning_patterns': [
                r'how to .+',
                r'learn .+',
                r'understand .+',
                r'explain .+',
                r'tutorial .+',
                r'guide .+'
            ],
            'goal_patterns': [
                r'need to .+',
                r'want to .+',
                r'plan to .+',
                r'working on .+',
                r'project .+',
                r'goal .+'
            ],
            'preference_patterns': [
                r'prefer .+',
                r'like .+',
                r'favorite .+',
                r'best .+',
                r'usually .+',
                r'always .+'
            ]
        }


class PSPMatcher:
    """PSP匹配器"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def match_intents_with_psp(self, intents: List[UserIntent], current_psp: PSPContext) -> List[Dict[str, Any]]:
        """将意图与现有PSP匹配"""
        matches = []
        
        for intent in intents:
            best_match = self._find_best_component_match(intent, current_psp)
            
            if best_match:
                match_info = {
                    'intent': intent,
                    'psp_component': best_match['component'],
                    'similarity': best_match['similarity'],
                    'action': self._determine_update_action(intent, best_match),
                    'merge_strength': self._calculate_merge_strength(intent.attention_weight)
                }
            else:
                match_info = {
                    'intent': intent,
                    'psp_component': None,
                    'similarity': 0.0,
                    'action': PSPUpdateAction.CREATE,
                    'merge_strength': 1.0
                }
            
            matches.append(match_info)
        
        return matches
    
    def _find_best_component_match(self, intent: UserIntent, psp: PSPContext) -> Optional[Dict[str, Any]]:
        """寻找最佳匹配的PSP组件"""
        if not intent.embedding:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        # 在相同类型的组件中寻找匹配
        target_memory = self._get_target_memory(intent.intent_type, psp)
        
        for component_id, component in target_memory.items():
            if not component.embedding:
                continue
            
            similarity = self._calculate_similarity(intent.embedding, component.embedding)
            
            if similarity > best_similarity and similarity > self.similarity_threshold:
                best_similarity = similarity
                best_match = {
                    'component': component,
                    'similarity': similarity
                }
        
        return best_match
    
    def _get_target_memory(self, intent_type: PSPComponentType, psp: PSPContext) -> Dict[str, PSPComponent]:
        """获取目标记忆层"""
        if intent_type in [PSPComponentType.CORE_INTEREST, PSPComponentType.PERSONAL_VALUE]:
            return psp.core_memory
        elif intent_type in [PSPComponentType.CURRENT_GOAL, PSPComponentType.WORK_CONTEXT]:
            return psp.working_memory
        elif intent_type == PSPComponentType.LEARNING_PREFERENCE:
            return psp.learning_memory
        else:
            return psp.context_memory
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算向量相似度"""
        if not embedding1 or not embedding2:
            return 0.0
        
        vec1 = np.array(embedding1).reshape(1, -1)
        vec2 = np.array(embedding2).reshape(1, -1)
        
        similarity = cosine_similarity(vec1, vec2)[0][0]
        return max(0.0, similarity)  # 确保非负
    
    def _determine_update_action(self, intent: UserIntent, match_info: Dict[str, Any]) -> PSPUpdateAction:
        """确定更新动作"""
        similarity = match_info['similarity']
        component = match_info['component']
        
        if similarity > 0.9:
            # 高度相似，强化现有组件
            return PSPUpdateAction.STRENGTHEN
        elif similarity > 0.8:
            # 相似但有差异，更新组件
            return PSPUpdateAction.UPDATE
        elif similarity > 0.7:
            # 中等相似，合并信息
            return PSPUpdateAction.MERGE
        else:
            # 相似度不够，创建新组件
            return PSPUpdateAction.CREATE
    
    def _calculate_merge_strength(self, attention_weight: float) -> float:
        """计算合并强度"""
        if attention_weight > 0.8:
            return 1.0  # 完全融合
        elif attention_weight > 0.6:
            return 0.8  # 强融合
        elif attention_weight > 0.4:
            return 0.6  # 中等融合
        else:
            return 0.3  # 弱融合


class PSPUpdater:
    """PSP更新器"""
    
    def __init__(self):
        self.component_id_counter = 0
    
    def update_psp_with_matches(self, matches: List[Dict[str, Any]], current_psp: PSPContext) -> PSPContext:
        """基于匹配结果更新PSP"""
        updated_psp = current_psp
        
        # 按注意力权重排序，优先处理高权重意图
        sorted_matches = sorted(
            matches,
            key=lambda x: x['intent'].attention_weight,
            reverse=True
        )
        
        for match in sorted_matches:
            action = match['action']
            intent = match['intent']
            
            if action == PSPUpdateAction.CREATE:
                self._create_new_component(intent, updated_psp)
            elif action == PSPUpdateAction.UPDATE:
                self._update_existing_component(match, updated_psp)
            elif action == PSPUpdateAction.STRENGTHEN:
                self._strengthen_component(match, updated_psp)
            elif action == PSPUpdateAction.MERGE:
                self._merge_into_component(match, updated_psp)
        
        # 重新平衡权重
        updated_psp = self._rebalance_component_weights(updated_psp)
        
        # 更新元信息
        updated_psp.last_updated = datetime.now(timezone.utc).isoformat()
        updated_psp.total_components = len(updated_psp.get_all_components())
        updated_psp.active_components = self._identify_active_components(updated_psp)
        
        return updated_psp
    
    def _create_new_component(self, intent: UserIntent, psp: PSPContext):
        """创建新的PSP组件"""
        component = PSPComponent(
            id=self._generate_component_id(),
            component_type=intent.intent_type,
            description=intent.description,
            embedding=intent.embedding,
            confidence=intent.confidence,
            total_attention_weight=intent.attention_weight,
            normalized_weight=0.0,  # 将在重新平衡时计算
            priority="medium",  # 将在重新平衡时确定
            activation_threshold=self._calculate_activation_threshold(intent.attention_weight),
            supporting_evidence=[{
                'intent_id': intent.id,
                'hinata_id': intent.hinata_id,
                'attention_weight': intent.attention_weight,
                'timestamp': intent.extracted_at,
                'source_app': intent.source_app
            }],
            created_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            source_apps={intent.source_app}
        )
        
        # 添加到相应的记忆层
        target_memory = self._get_target_memory_for_update(intent.intent_type, psp)
        target_memory[component.id] = component
    
    def _update_existing_component(self, match: Dict[str, Any], psp: PSPContext):
        """更新现有PSP组件"""
        component = match['psp_component']
        intent = match['intent']
        merge_strength = match['merge_strength']
        
        # 更新向量表示
        if component.embedding and intent.embedding:
            new_embedding = self._weighted_vector_merge(
                component.embedding,
                intent.embedding,
                merge_strength
            )
            component.embedding = new_embedding
        
        # 更新权重信息
        component.total_attention_weight += intent.attention_weight
        
        # 添加支撑证据
        component.supporting_evidence.append({
            'intent_id': intent.id,
            'hinata_id': intent.hinata_id,
            'attention_weight': intent.attention_weight,
            'timestamp': intent.extracted_at,
            'source_app': intent.source_app,
            'update_type': 'update'
        })
        
        # 更新时间和来源
        component.last_updated = datetime.now(timezone.utc).isoformat()
        component.source_apps.add(intent.source_app)
        
        # 记录演化历史
        component.evolution_history.append({
            'action': 'update',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'intent_id': intent.id,
            'merge_strength': merge_strength
        })
    
    def _strengthen_component(self, match: Dict[str, Any], psp: PSPContext):
        """强化PSP组件"""
        component = match['psp_component']
        intent = match['intent']
        
        # 增加权重和置信度
        component.total_attention_weight += intent.attention_weight * 1.2  # 强化因子
        component.confidence = min(component.confidence + 0.1, 1.0)
        
        # 添加强化证据
        component.supporting_evidence.append({
            'intent_id': intent.id,
            'hinata_id': intent.hinata_id,
            'attention_weight': intent.attention_weight,
            'timestamp': intent.extracted_at,
            'source_app': intent.source_app,
            'update_type': 'strengthen'
        })
        
        component.last_activated = datetime.now(timezone.utc).isoformat()
        component.last_updated = datetime.now(timezone.utc).isoformat()
        
        # 记录强化历史
        component.evolution_history.append({
            'action': 'strengthen',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'intent_id': intent.id,
            'strength_boost': 1.2
        })
    
    def _merge_into_component(self, match: Dict[str, Any], psp: PSPContext):
        """合并信息到PSP组件"""
        component = match['psp_component']
        intent = match['intent']
        merge_strength = match['merge_strength']
        
        # 轻微调整向量表示
        if component.embedding and intent.embedding:
            new_embedding = self._weighted_vector_merge(
                component.embedding,
                intent.embedding,
                merge_strength * 0.5  # 降低合并强度
            )
            component.embedding = new_embedding
        
        # 累积权重
        component.total_attention_weight += intent.attention_weight * 0.8  # 部分累积
        
        # 添加合并证据
        component.supporting_evidence.append({
            'intent_id': intent.id,
            'hinata_id': intent.hinata_id,
            'attention_weight': intent.attention_weight,
            'timestamp': intent.extracted_at,
            'source_app': intent.source_app,
            'update_type': 'merge'
        })
        
        component.last_updated = datetime.now(timezone.utc).isoformat()
    
    def _get_target_memory_for_update(self, intent_type: PSPComponentType, psp: PSPContext) -> Dict[str, PSPComponent]:
        """获取用于更新的目标记忆层"""
        if intent_type in [PSPComponentType.CORE_INTEREST, PSPComponentType.PERSONAL_VALUE]:
            return psp.core_memory
        elif intent_type in [PSPComponentType.CURRENT_GOAL, PSPComponentType.WORK_CONTEXT]:
            return psp.working_memory
        elif intent_type == PSPComponentType.LEARNING_PREFERENCE:
            return psp.learning_memory
        else:
            return psp.context_memory
    
    def _weighted_vector_merge(self, vector1: List[float], vector2: List[float], merge_weight: float) -> List[float]:
        """加权向量融合"""
        if not vector1 or not vector2:
            return vector1 or vector2 or []
        
        # 限制merge_weight在合理范围内
        merge_weight = max(0.1, min(1.0, merge_weight))
        
        vec1 = np.array(vector1)
        vec2 = np.array(vector2)
        
        # 加权平均
        merged_vector = vec1 * (1 - merge_weight) + vec2 * merge_weight
        
        # 归一化
        norm = np.linalg.norm(merged_vector)
        if norm > 0:
            merged_vector = merged_vector / norm
        
        return merged_vector.tolist()
    
    def _calculate_activation_threshold(self, attention_weight: float) -> float:
        """计算激活阈值"""
        # 高注意力权重的组件更容易被激活
        base_threshold = 0.5
        adjustment = (attention_weight - 0.5) * 0.3
        return max(0.1, min(0.9, base_threshold - adjustment))
    
    def _rebalance_component_weights(self, psp: PSPContext) -> PSPContext:
        """重新平衡PSP组件权重"""
        all_components = psp.get_all_components()
        
        if not all_components:
            return psp
        
        # 计算总权重
        total_weight = sum(comp.total_attention_weight for comp in all_components.values())
        
        if total_weight == 0:
            return psp
        
        # 归一化权重并设置优先级
        for component in all_components.values():
            component.normalized_weight = component.total_attention_weight / total_weight
            
            # 设置优先级
            if component.normalized_weight > 0.15:
                component.priority = "high"
            elif component.normalized_weight > 0.08:
                component.priority = "medium"
            else:
                component.priority = "low"
        
        return psp
    
    def _identify_active_components(self, psp: PSPContext) -> List[str]:
        """识别活跃组件"""
        active_components = []
        current_time = datetime.now(timezone.utc)
        
        for component_id, component in psp.get_all_components().items():
            # 高优先级组件总是活跃
            if component.priority == "high":
                active_components.append(component_id)
                continue
            
            # 最近更新的组件
            last_updated = datetime.fromisoformat(component.last_updated.replace('Z', '+00:00'))
            if (current_time - last_updated).days < 7:
                active_components.append(component_id)
                continue
            
            # 最近激活的组件
            if component.last_activated:
                last_activated = datetime.fromisoformat(component.last_activated.replace('Z', '+00:00'))
                if (current_time - last_activated).days < 3:
                    active_components.append(component_id)
        
        return active_components
    
    def _generate_component_id(self) -> str:
        """生成组件ID"""
        self.component_id_counter += 1
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return f"psp_comp_{timestamp}_{self.component_id_counter}"


class PSPContextGenerator:
    """PSP上下文生成器"""
    
    def generate_prompt_context(self, psp: PSPContext, current_request: str = "") -> Dict[str, Any]:
        """为当前请求生成PSP上下文"""
        
        # 获取高优先级组件
        high_priority_components = psp.get_high_priority_components()
        
        # 获取相关组件
        relevant_components = self._get_relevant_components(psp, current_request)
        
        # 构建上下文
        context = {
            "core_interests": self._extract_core_interests(psp.core_memory),
            "current_goals": self._extract_current_goals(psp.working_memory),
            "learning_preferences": self._extract_learning_preferences(psp.learning_memory),
            "communication_style": self._extract_communication_style(psp.context_memory),
            "work_context": self._extract_work_context(psp.working_memory),
            "high_priority_focus": [comp.description for comp in high_priority_components[:3]],
            "relevant_context": [comp.description for comp in relevant_components[:5]],
            "active_components_count": len(psp.active_components),
            "last_updated": psp.last_updated
        }
        
        return context
    
    def _get_relevant_components(self, psp: PSPContext, current_request: str) -> List[PSPComponent]:
        """获取与当前请求相关的组件"""
        if not current_request:
            return []
        
        # 这里应该实现基于语义相似度的组件检索
        # 为了简化，返回最近更新的活跃组件
        all_components = psp.get_all_components()
        active_components = [all_components[comp_id] for comp_id in psp.active_components 
                           if comp_id in all_components]
        
        # 按最后更新时间排序
        active_components.sort(
            key=lambda x: datetime.fromisoformat(x.last_updated.replace('Z', '+00:00')),
            reverse=True
        )
        
        return active_components[:5]
    
    def _extract_core_interests(self, core_memory: Dict[str, PSPComponent]) -> List[str]:
        """提取核心兴趣"""
        interests = []
        for component in core_memory.values():
            if component.component_type == PSPComponentType.CORE_INTEREST and component.priority in ["high", "medium"]:
                interests.append(component.description)
        return interests[:5]
    
    def _extract_current_goals(self, working_memory: Dict[str, PSPComponent]) -> List[str]:
        """提取当前目标"""
        goals = []
        for component in working_memory.values():
            if component.component_type == PSPComponentType.CURRENT_GOAL and component.priority in ["high", "medium"]:
                goals.append(component.description)
        return goals[:3]
    
    def _extract_learning_preferences(self, learning_memory: Dict[str, PSPComponent]) -> List[str]:
        """提取学习偏好"""
        preferences = []
        for component in learning_memory.values():
            if component.component_type == PSPComponentType.LEARNING_PREFERENCE:
                preferences.append(component.description)
        return preferences[:3]
    
    def _extract_communication_style(self, context_memory: Dict[str, PSPComponent]) -> List[str]:
        """提取沟通风格"""
        styles = []
        for component in context_memory.values():
            if component.component_type == PSPComponentType.COMMUNICATION_STYLE:
                styles.append(component.description)
        return styles[:2]
    
    def _extract_work_context(self, working_memory: Dict[str, PSPComponent]) -> List[str]:
        """提取工作上下文"""
        work_context = []
        for component in working_memory.values():
            if component.component_type == PSPComponentType.WORK_CONTEXT:
                work_context.append(component.description)
        return work_context[:3]


class PSPEngine:
    """PSP引擎主类"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.intent_extractor = IntentExtractor()
        self.psp_matcher = PSPMatcher()
        self.psp_updater = PSPUpdater()
        self.context_generator = PSPContextGenerator()
        
        # 缓存用户PSP
        self.psp_cache = {}
        self.cache_ttl = 3600  # 1小时
    
    async def process_hinata_for_psp_update(self, hinata_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """处理HiNATA数据进行PSP更新"""
        
        # 1. 提取用户意图
        intents = self.intent_extractor.extract_intent_from_hinata(hinata_data)
        
        if not intents:
            return {"status": "no_intents_found", "updates": 0}
        
        # 2. 获取当前PSP
        current_psp = await self.get_user_psp(user_id)
        
        # 3. 匹配意图与PSP
        matches = self.psp_matcher.match_intents_with_psp(intents, current_psp)
        
        # 4. 更新PSP
        updated_psp = self.psp_updater.update_psp_with_matches(matches, current_psp)
        
        # 5. 保存更新后的PSP
        await self.save_user_psp(user_id, updated_psp)
        
        # 6. 更新缓存
        self.psp_cache[user_id] = {
            'psp': updated_psp,
            'timestamp': time.time()
        }
        
        return {
            "status": "success",
            "intents_processed": len(intents),
            "updates_applied": len(matches),
            "active_components": len(updated_psp.active_components)
        }
    
    async def get_user_psp(self, user_id: str) -> PSPContext:
        """获取用户PSP"""
        
        # 检查缓存
        if user_id in self.psp_cache:
            cached = self.psp_cache[user_id]
            if time.time() - cached['timestamp'] < self.cache_ttl:
                return cached['psp']
        
        # 从数据库加载
        psp = await self._load_psp_from_database(user_id)
        
        # 更新缓存
        self.psp_cache[user_id] = {
            'psp': psp,
            'timestamp': time.time()
        }
        
        return psp
    
    async def get_psp_context_for_prompt(self, user_id: str, current_request: str = "") -> Dict[str, Any]:
        """为prompt生成获取PSP上下文"""
        psp = await self.get_user_psp(user_id)
        return self.context_generator.generate_prompt_context(psp, current_request)
    
    async def save_user_psp(self, user_id: str, psp: PSPContext):
        """保存用户PSP"""
        async with self.db_pool.acquire() as conn:
            
            # 保存PSP元信息
            await conn.execute('''
                INSERT INTO user_psp (user_id, last_updated, total_components, active_components)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    last_updated = EXCLUDED.last_updated,
                    total_components = EXCLUDED.total_components,
                    active_components = EXCLUDED.active_components
            ''', user_id, psp.last_updated, psp.total_components, json.dumps(psp.active_components))
            
            # 保存所有组件
            all_components = psp.get_all_components()
            for component in all_components.values():
                await self._save_psp_component(conn, user_id, component)
    
    async def _save_psp_component(self, conn, user_id: str, component: PSPComponent):
        """保存PSP组件"""
        await conn.execute('''
            INSERT INTO psp_components 
            (id, user_id, component_type, description, embedding, confidence, 
             total_attention_weight, normalized_weight, priority, activation_threshold,
             supporting_evidence, created_at, last_updated, last_activated,
             related_components, source_apps, evolution_history)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            ON CONFLICT (id, user_id) DO UPDATE SET
                description = EXCLUDED.description,
                embedding = EXCLUDED.embedding,
                confidence = EXCLUDED.confidence,
                total_attention_weight = EXCLUDED.total_attention_weight,
                normalized_weight = EXCLUDED.normalized_weight,
                priority = EXCLUDED.priority,
                activation_threshold = EXCLUDED.activation_threshold,
                supporting_evidence = EXCLUDED.supporting_evidence,
                last_updated = EXCLUDED.last_updated,
                last_activated = EXCLUDED.last_activated,
                related_components = EXCLUDED.related_components,
                source_apps = EXCLUDED.source_apps,
                evolution_history = EXCLUDED.evolution_history
        ''', 
            component.id, user_id, component.component_type.value, component.description,
            json.dumps(component.embedding), component.confidence,
            component.total_attention_weight, component.normalized_weight, component.priority,
            component.activation_threshold, json.dumps(component.supporting_evidence),
            component.created_at, component.last_updated, component.last_activated,
            json.dumps(component.related_components), json.dumps(list(component.source_apps)),
            json.dumps(component.evolution_history)
        )
    
    async def _load_psp_from_database(self, user_id: str) -> PSPContext:
        """从数据库加载PSP"""
        async with self.db_pool.acquire() as conn:
            
            # 加载PSP元信息
            psp_row = await conn.fetchrow(
                'SELECT * FROM user_psp WHERE user_id = $1', user_id
            )
            
            # 加载所有组件
            component_rows = await conn.fetch(
                'SELECT * FROM psp_components WHERE user_id = $1', user_id
            )
            
            # 构建PSP上下文
            psp = PSPContext(
                user_id=user_id,
                core_memory={},
                working_memory={},
                learning_memory={},
                context_memory={}
            )
            
            if psp_row:
                psp.last_updated = psp_row['last_updated']
                psp.total_components = psp_row['total_components']
                psp.active_components = json.loads(psp_row['active_components'] or '[]')
            
            # 加载组件到相应记忆层
            for row in component_rows:
                component = self._row_to_component(row)
                target_memory = self._get_memory_by_component_type(component.component_type, psp)
                target_memory[component.id] = component
            
            return psp
    
    def _row_to_component(self, row) -> PSPComponent:
        """将数据库行转换为PSP组件"""
        return PSPComponent(
            id=row['id'],
            component_type=PSPComponentType(row['component_type']),
            description=row['description'],
            embedding=json.loads(row['embedding'] or '[]'),
            confidence=row['confidence'],
            total_attention_weight=row['total_attention_weight'],
            normalized_weight=row['normalized_weight'],
            priority=row['priority'],
            activation_threshold=row['activation_threshold'],
            supporting_evidence=json.loads(row['supporting_evidence'] or '[]'),
            created_at=row['created_at'],
            last_updated=row['last_updated'],
            last_activated=row['last_activated'] or '',
            related_components=json.loads(row['related_components'] or '[]'),
            source_apps=set(json.loads(row['source_apps'] or '[]')),
            evolution_history=json.loads(row['evolution_history'] or '[]')
        )
    
    def _get_memory_by_component_type(self, component_type: PSPComponentType, psp: PSPContext) -> Dict[str, PSPComponent]:
        """根据组件类型获取对应记忆层"""
        if component_type in [PSPComponentType.CORE_INTEREST, PSPComponentType.PERSONAL_VALUE]:
            return psp.core_memory
        elif component_type in [PSPComponentType.CURRENT_GOAL, PSPComponentType.WORK_CONTEXT]:
            return psp.working_memory
        elif component_type == PSPComponentType.LEARNING_PREFERENCE:
            return psp.learning_memory
        else:
            return psp.context_memory


# 使用示例
async def main():
    """使用示例"""
    import asyncpg
    
    # 创建数据库连接池
    db_pool = await asyncpg.create_pool("postgresql://user:password@localhost/byenatos")
    
    # 初始化PSP引擎
    psp_engine = PSPEngine(db_pool)
    
    # 示例HiNATA数据
    sample_hinata = {
        "id": "hinata_20241201_001",
        "timestamp": "2024-12-01T10:30:00Z",
        "source": "browser_extension",
        "highlight": "Machine learning models require careful validation",
        "note": "This is crucial for ensuring our models work well in production. I need to learn more about cross-validation techniques.",
        "enhanced_tags": ["machine-learning", "validation", "production"],
        "attention_weight": 0.8,
        "attention_metrics": {"highlight_frequency": 3, "note_count": 2},
        "embedding_vector": [0.1, 0.2, 0.3] * 256  # 简化的768维向量
    }
    
    # 处理HiNATA更新PSP
    result = await psp_engine.process_hinata_for_psp_update(sample_hinata, "user_123")
    print(f"PSP Update Result: {result}")
    
    # 获取PSP上下文用于prompt生成
    context = await psp_engine.get_psp_context_for_prompt("user_123", "How do I validate ML models?")
    print(f"PSP Context: {context}")
    
    await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())