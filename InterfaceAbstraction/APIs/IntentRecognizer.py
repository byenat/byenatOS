"""
ByenatOS Intent Recognition for HiNATA Write Operations
意图识别器 - 从用户对话中识别HiNATA写入操作意图

当用户通过对话框表达希望修改知识库内容的意图时，
此模块负责解析用户意图并转换为具体的HiNATA写入操作。
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import spacy
from datetime import datetime, timezone

from InterfaceAbstraction.APIs.HiNATAWriteAPI import HiNATAWriteOperation


class IntentType(Enum):
    """意图类型"""
    CREATE_HINATA = "create_hinata"
    UPDATE_HINATA = "update_hinata"
    DELETE_HINATA = "delete_hinata"
    BULK_TAG = "bulk_tag"
    BULK_RETAG = "bulk_retag"
    REORGANIZE = "reorganize"
    MERGE_DUPLICATE = "merge_duplicate"
    CLEANUP = "cleanup"
    NONE = "none"


@dataclass
class RecognizedIntent:
    """识别的意图"""
    intent_type: IntentType
    confidence: float
    operation_type: HiNATAWriteOperation
    parameters: Dict[str, Any]
    target_filter: Dict[str, Any]
    operation_data: Dict[str, Any]
    user_description: str
    suggested_confirmation: str


class IntentRecognizer:
    """意图识别器"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.intent_patterns = self._load_intent_patterns()
        self.action_keywords = self._load_action_keywords()
    
    def recognize_intent(self, user_input: str, user_context: Dict[str, Any] = None) -> RecognizedIntent:
        """识别用户意图"""
        
        # 预处理输入
        normalized_input = self._normalize_input(user_input)
        doc = self.nlp(normalized_input)
        
        # 提取关键信息
        entities = self._extract_entities(doc)
        actions = self._extract_actions(doc)
        targets = self._extract_targets(doc, entities)
        
        # 意图分类
        intent_type, confidence = self._classify_intent(normalized_input, actions, entities)
        
        # 构建操作参数
        operation_params = self._build_operation_parameters(intent_type, actions, targets, entities)
        
        # 生成确认信息
        confirmation = self._generate_confirmation(intent_type, operation_params)
        
        return RecognizedIntent(
            intent_type=intent_type,
            confidence=confidence,
            operation_type=self._map_intent_to_operation(intent_type),
            parameters=operation_params.get('parameters', {}),
            target_filter=operation_params.get('target_filter', {}),
            operation_data=operation_params.get('operation_data', {}),
            user_description=user_input,
            suggested_confirmation=confirmation
        )
    
    def _normalize_input(self, user_input: str) -> str:
        """标准化用户输入"""
        # 转小写
        normalized = user_input.lower()
        
        # 替换常见的同义词
        synonyms = {
            r'\b(notes?|annotations?)\b': 'hinata',
            r'\b(remove|delete|get rid of)\b': 'delete',
            r'\b(modify|change|edit|update)\b': 'update',
            r'\b(add|create|make)\b': 'create',
            r'\b(tag|label|categorize)\b': 'tag',
            r'\b(all my|my entire|everything)\b': 'all',
            r'\b(about|regarding|related to)\b': 'about'
        }
        
        for pattern, replacement in synonyms.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    def _extract_entities(self, doc) -> Dict[str, List[str]]:
        """提取实体"""
        entities = {
            'topics': [],
            'tags': [],
            'sources': [],
            'dates': [],
            'quantities': []
        }
        
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'EVENT']:
                entities['topics'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
            elif ent.label_ in ['CARDINAL', 'QUANTITY']:
                entities['quantities'].append(ent.text)
        
        # 提取引号中的内容作为标签
        quoted_content = re.findall(r'"([^"]+)"', doc.text)
        entities['tags'].extend(quoted_content)
        
        # 提取可能的来源
        source_patterns = [
            r'from (\w+)',
            r'in (\w+)',
            r'(\w+) app',
            r'(\w+) extension'
        ]
        
        for pattern in source_patterns:
            matches = re.findall(pattern, doc.text.lower())
            entities['sources'].extend(matches)
        
        return entities
    
    def _extract_actions(self, doc) -> List[str]:
        """提取动作词"""
        actions = []
        
        action_verbs = {
            'create', 'add', 'make', 'generate', 'build',
            'update', 'modify', 'change', 'edit', 'alter',
            'delete', 'remove', 'eliminate', 'clear',
            'tag', 'label', 'categorize', 'classify',
            'organize', 'reorganize', 'structure',
            'merge', 'combine', 'join',
            'split', 'separate', 'divide',
            'clean', 'cleanup', 'tidy'
        }
        
        for token in doc:
            if token.lemma_ in action_verbs:
                actions.append(token.lemma_)
        
        return list(set(actions))
    
    def _extract_targets(self, doc, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """提取操作目标"""
        targets = {
            'scope': 'specific',  # all, specific, filtered
            'filter_conditions': {},
            'affected_count': 0
        }
        
        text = doc.text.lower()
        
        # 检测范围
        if any(phrase in text for phrase in ['all my', 'everything', 'entire', 'whole']):
            targets['scope'] = 'all'
        elif any(phrase in text for phrase in ['some', 'certain', 'specific', 'particular']):
            targets['scope'] = 'filtered'
        
        # 构建过滤条件
        if entities['topics']:
            targets['filter_conditions']['topics'] = entities['topics']
        
        if entities['tags']:
            targets['filter_conditions']['tags'] = entities['tags']
        
        if entities['sources']:
            targets['filter_conditions']['sources'] = entities['sources']
        
        if entities['dates']:
            targets['filter_conditions']['dates'] = entities['dates']
        
        # 提取数量信息
        quantity_patterns = [
            r'(\d+)\s+(?:hinata|notes?|items?)',
            r'(?:about|around|roughly)\s+(\d+)',
            r'(\d+)\s+(?:of\s+)?(?:them|these|those)'
        ]
        
        for pattern in quantity_patterns:
            matches = re.findall(pattern, text)
            if matches:
                targets['affected_count'] = int(matches[0])
                break
        
        return targets
    
    def _classify_intent(self, text: str, actions: List[str], entities: Dict[str, List[str]]) -> Tuple[IntentType, float]:
        """分类意图"""
        
        # 规则基础的意图分类
        intent_scores = {
            IntentType.CREATE_HINATA: 0.0,
            IntentType.UPDATE_HINATA: 0.0,
            IntentType.DELETE_HINATA: 0.0,
            IntentType.BULK_TAG: 0.0,
            IntentType.BULK_RETAG: 0.0,
            IntentType.REORGANIZE: 0.0,
            IntentType.MERGE_DUPLICATE: 0.0,
            IntentType.CLEANUP: 0.0
        }
        
        # 基于动作词评分
        action_scores = {
            'create': {IntentType.CREATE_HINATA: 0.8},
            'add': {IntentType.CREATE_HINATA: 0.6, IntentType.BULK_TAG: 0.4},
            'update': {IntentType.UPDATE_HINATA: 0.8},
            'modify': {IntentType.UPDATE_HINATA: 0.7},
            'change': {IntentType.UPDATE_HINATA: 0.6},
            'delete': {IntentType.DELETE_HINATA: 0.9},
            'remove': {IntentType.DELETE_HINATA: 0.8},
            'tag': {IntentType.BULK_TAG: 0.8},
            'label': {IntentType.BULK_TAG: 0.7},
            'categorize': {IntentType.BULK_TAG: 0.7},
            'organize': {IntentType.REORGANIZE: 0.8},
            'reorganize': {IntentType.REORGANIZE: 0.9},
            'merge': {IntentType.MERGE_DUPLICATE: 0.8},
            'clean': {IntentType.CLEANUP: 0.7},
            'cleanup': {IntentType.CLEANUP: 0.8}
        }
        
        for action in actions:
            if action in action_scores:
                for intent, score in action_scores[action].items():
                    intent_scores[intent] += score
        
        # 基于关键短语评分
        phrase_patterns = {
            r'add.*tag': IntentType.BULK_TAG,
            r'retag.*all': IntentType.BULK_RETAG,
            r'delete.*all': IntentType.DELETE_HINATA,
            r'clean.*up': IntentType.CLEANUP,
            r'merge.*duplicate': IntentType.MERGE_DUPLICATE,
            r'organize.*by': IntentType.REORGANIZE,
            r'update.*note': IntentType.UPDATE_HINATA,
            r'create.*new': IntentType.CREATE_HINATA
        }
        
        for pattern, intent in phrase_patterns.items():
            if re.search(pattern, text):
                intent_scores[intent] += 0.5
        
        # 基于上下文评分
        if 'all' in text and ('tag' in actions or 'label' in actions):
            intent_scores[IntentType.BULK_TAG] += 0.3
        
        if 'duplicate' in text or 'same' in text:
            intent_scores[IntentType.MERGE_DUPLICATE] += 0.4
        
        # 选择最高分的意图
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        if best_intent[1] < 0.3:
            return IntentType.NONE, 0.0
        
        return best_intent[0], min(best_intent[1], 1.0)
    
    def _build_operation_parameters(self, intent_type: IntentType, actions: List[str], 
                                  targets: Dict[str, Any], entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """构建操作参数"""
        
        params = {
            'parameters': {},
            'target_filter': {},
            'operation_data': {}
        }
        
        # 构建目标过滤器
        if targets['scope'] == 'all':
            params['target_filter'] = {}  # 空过滤器表示所有
        else:
            if entities['topics']:
                # 基于主题过滤
                params['target_filter']['enhanced_tags'] = entities['topics']
            
            if entities['tags']:
                # 基于标签过滤
                params['target_filter']['tag'] = entities['tags'][0]  # 取第一个标签
            
            if entities['sources']:
                # 基于来源过滤
                params['target_filter']['source'] = entities['sources'][0]
            
            if entities['dates']:
                # 基于日期过滤
                params['target_filter']['date_range'] = {
                    'description': entities['dates'][0]
                }
        
        # 构建操作数据
        if intent_type == IntentType.BULK_TAG:
            params['operation_data']['tags'] = entities['tags'] or ['new_tag']
        
        elif intent_type == IntentType.BULK_RETAG:
            params['operation_data']['tags'] = entities['tags'] or []
        
        elif intent_type == IntentType.UPDATE_HINATA:
            params['operation_data']['updates'] = {}
            if entities['tags']:
                params['operation_data']['updates']['tag'] = entities['tags']
        
        elif intent_type == IntentType.CREATE_HINATA:
            params['operation_data'] = {
                'source': 'user_intent',
                'access': 'private',
                'tag': entities['tags'] or []
            }
        
        # 设置参数
        params['parameters']['estimated_count'] = targets.get('affected_count', 0)
        params['parameters']['dry_run'] = True  # 默认先试运行
        
        return params
    
    def _map_intent_to_operation(self, intent_type: IntentType) -> HiNATAWriteOperation:
        """映射意图到操作类型"""
        mapping = {
            IntentType.CREATE_HINATA: HiNATAWriteOperation.CREATE,
            IntentType.UPDATE_HINATA: HiNATAWriteOperation.UPDATE,
            IntentType.DELETE_HINATA: HiNATAWriteOperation.DELETE,
            IntentType.BULK_TAG: HiNATAWriteOperation.BULK_TAG,
            IntentType.BULK_RETAG: HiNATAWriteOperation.BULK_RETAG,
            IntentType.REORGANIZE: HiNATAWriteOperation.BATCH_UPDATE,
            IntentType.MERGE_DUPLICATE: HiNATAWriteOperation.MERGE,
            IntentType.CLEANUP: HiNATAWriteOperation.DELETE
        }
        return mapping.get(intent_type, HiNATAWriteOperation.UPDATE)
    
    def _generate_confirmation(self, intent_type: IntentType, params: Dict[str, Any]) -> str:
        """生成确认信息"""
        
        target_desc = self._describe_targets(params['target_filter'])
        operation_desc = self._describe_operation(intent_type, params['operation_data'])
        
        confirmations = {
            IntentType.CREATE_HINATA: f"创建新的HiNATA记录：{operation_desc}",
            IntentType.UPDATE_HINATA: f"更新{target_desc}的HiNATA记录：{operation_desc}",
            IntentType.DELETE_HINATA: f"删除{target_desc}的HiNATA记录",
            IntentType.BULK_TAG: f"为{target_desc}的HiNATA记录添加标签：{operation_desc}",
            IntentType.BULK_RETAG: f"重新标记{target_desc}的HiNATA记录：{operation_desc}",
            IntentType.REORGANIZE: f"重新组织{target_desc}的HiNATA记录",
            IntentType.MERGE_DUPLICATE: f"合并{target_desc}中的重复HiNATA记录",
            IntentType.CLEANUP: f"清理{target_desc}的HiNATA记录"
        }
        
        base_confirmation = confirmations.get(intent_type, "执行未知操作")
        
        estimated_count = params['parameters'].get('estimated_count', 0)
        if estimated_count > 0:
            base_confirmation += f"（预计影响 {estimated_count} 条记录）"
        
        return base_confirmation + "\n\n确认执行此操作吗？"
    
    def _describe_targets(self, target_filter: Dict[str, Any]) -> str:
        """描述操作目标"""
        if not target_filter:
            return "所有"
        
        descriptions = []
        
        if 'tag' in target_filter:
            descriptions.append(f"标签为'{target_filter['tag']}'")
        
        if 'source' in target_filter:
            descriptions.append(f"来源为'{target_filter['source']}'")
        
        if 'enhanced_tags' in target_filter:
            tags = target_filter['enhanced_tags']
            if len(tags) == 1:
                descriptions.append(f"主题为'{tags[0]}'")
            else:
                descriptions.append(f"主题包含{', '.join(tags[:2])}")
        
        if 'date_range' in target_filter:
            descriptions.append(f"时间范围为{target_filter['date_range']['description']}")
        
        return "、".join(descriptions) if descriptions else "指定条件"
    
    def _describe_operation(self, intent_type: IntentType, operation_data: Dict[str, Any]) -> str:
        """描述操作内容"""
        
        if intent_type == IntentType.BULK_TAG:
            tags = operation_data.get('tags', [])
            if tags:
                return f"添加标签 {', '.join(tags)}"
            return "添加新标签"
        
        elif intent_type == IntentType.BULK_RETAG:
            tags = operation_data.get('tags', [])
            if tags:
                return f"重新标记为 {', '.join(tags)}"
            return "清空所有标签"
        
        elif intent_type == IntentType.UPDATE_HINATA:
            updates = operation_data.get('updates', {})
            if 'tag' in updates:
                return f"更新标签为 {', '.join(updates['tag'])}"
            return "更新内容"
        
        elif intent_type == IntentType.CREATE_HINATA:
            tags = operation_data.get('tag', [])
            if tags:
                return f"标签：{', '.join(tags)}"
            return "基本信息"
        
        return "相关操作"
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """加载意图模式"""
        return {
            'create': [
                r'create.*new.*hinata',
                r'add.*new.*note',
                r'make.*new.*entry'
            ],
            'update': [
                r'update.*hinata',
                r'modify.*note',
                r'change.*content'
            ],
            'delete': [
                r'delete.*hinata',
                r'remove.*note',
                r'get rid of'
            ],
            'bulk_tag': [
                r'tag.*all',
                r'add.*tag.*to.*all',
                r'label.*everything'
            ],
            'cleanup': [
                r'clean.*up',
                r'organize.*better',
                r'tidy.*up'
            ]
        }
    
    def _load_action_keywords(self) -> Dict[str, List[str]]:
        """加载动作关键词"""
        return {
            'create': ['create', 'add', 'make', 'new', 'generate'],
            'update': ['update', 'modify', 'change', 'edit', 'alter'],
            'delete': ['delete', 'remove', 'eliminate', 'clear', 'get rid'],
            'tag': ['tag', 'label', 'categorize', 'classify'],
            'organize': ['organize', 'reorganize', 'structure', 'arrange'],
            'merge': ['merge', 'combine', 'join', 'consolidate'],
            'clean': ['clean', 'cleanup', 'tidy', 'organize']
        }


# 使用示例和测试
def test_intent_recognizer():
    """测试意图识别器"""
    recognizer = IntentRecognizer()
    
    test_cases = [
        "请帮我为所有关于机器学习的笔记添加'AI'标签",
        "删除所有来自浏览器插件的旧笔记",
        "更新我昨天创建的那个笔记，添加一些新的想法",
        "创建一个新的笔记关于Python编程",
        "清理我的知识库，删除重复的内容",
        "重新整理所有标记为'学习'的笔记",
        "合并所有相似的笔记"
    ]
    
    for test_input in test_cases:
        print(f"\n输入: {test_input}")
        intent = recognizer.recognize_intent(test_input)
        print(f"意图类型: {intent.intent_type}")
        print(f"置信度: {intent.confidence:.2f}")
        print(f"操作类型: {intent.operation_type}")
        print(f"确认信息: {intent.suggested_confirmation}")
        print("-" * 50)


if __name__ == "__main__":
    test_intent_recognizer()