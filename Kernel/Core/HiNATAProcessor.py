"""
ByenatOS HiNATA Data Processing Engine
HiNATA数据处理引擎 - 虚拟系统核心组件

作为byenatOS虚拟系统的"虚拟CPU"，专门负责接收、验证、增强和处理来自各App的HiNATA数据流
运行在现有操作系统之上，作为智能中间件的核心处理单元
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

import aioredis
import asyncpg
from sentence_transformers import SentenceTransformer
import spacy


class HiNATAProcessingStatus(Enum):
    """HiNATA处理状态"""
    RECEIVED = "received"
    VALIDATED = "validated"
    ENHANCED = "enhanced"
    SCORED = "scored"
    STORED = "stored"
    INDEXED = "indexed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HiNATAData:
    """标准HiNATA数据结构"""
    id: str
    timestamp: str
    source: str
    highlight: str
    note: str
    address: str
    tag: List[str]
    access: str
    raw_data: Dict[str, Any]
    
    # 系统增强字段
    enhanced_tags: Optional[List[str]] = None
    recommended_highlights: Optional[List[str]] = None
    semantic_analysis: Optional[Dict[str, Any]] = None
    attention_weight: Optional[float] = None
    attention_metrics: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    psp_influence_weight: Optional[float] = None
    embedding_vector: Optional[List[float]] = None
    processing_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """处理结果"""
    status: HiNATAProcessingStatus
    hinata_id: str
    processing_time: float
    error_message: Optional[str] = None
    enhancements_applied: Optional[List[str]] = None


class HiNATAValidator:
    """HiNATA格式验证器"""
    
    REQUIRED_FIELDS = ['id', 'timestamp', 'source', 'highlight', 'note', 'address', 'tag', 'access']
    ACCESS_LEVELS = ['private', 'public', 'shared']
    
    def validate(self, hinata_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证HiNATA数据格式"""
        errors = []
        
        # 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in hinata_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # 验证数据类型
        if not isinstance(hinata_data['tag'], list):
            errors.append("Field 'tag' must be a list")
        
        if hinata_data['access'] not in self.ACCESS_LEVELS:
            errors.append(f"Invalid access level: {hinata_data['access']}")
        
        # 验证时间戳格式
        try:
            datetime.fromisoformat(hinata_data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            errors.append("Invalid timestamp format")
        
        # 验证内容长度
        if len(hinata_data['highlight']) > 10000:
            errors.append("Highlight text too long (max 10000 characters)")
        
        if len(hinata_data['note']) > 50000:
            errors.append("Note text too long (max 50000 characters)")
        
        return len(errors) == 0, errors
    
    def standardize(self, hinata_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化HiNATA数据"""
        standardized = hinata_data.copy()
        
        # 标准化时间戳
        if 'timestamp' in standardized:
            dt = datetime.fromisoformat(standardized['timestamp'].replace('Z', '+00:00'))
            standardized['timestamp'] = dt.isoformat()
        
        # 清理和标准化标签
        if 'tag' in standardized:
            standardized['tag'] = [tag.strip().lower() for tag in standardized['tag'] if tag.strip()]
        
        # 确保raw_data存在
        if 'raw_data' not in standardized:
            standardized['raw_data'] = {}
        
        return standardized


class AIEnhancer:
    """AI增强处理器"""
    
    def __init__(self):
        import os
        self.small_model_mode = os.getenv('SMALL_MODEL_MODE', 'true').lower() == 'true'
        if self.small_model_mode:
            self.nlp_model = None
            self.embedding_model = None
        else:
            self.nlp_model = spacy.load("en_core_web_sm")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    async def enhance_hinata(self, hinata: HiNATAData) -> HiNATAData:
        """使用AI模型增强HiNATA数据"""
        enhanced = hinata
        
        # 1. 生成语义标签
        enhanced.enhanced_tags = await self._generate_semantic_tags(hinata)
        
        # 2. 提取推荐highlights
        enhanced.recommended_highlights = await self._extract_recommended_highlights(hinata)
        
        # 3. 语义分析
        enhanced.semantic_analysis = await self._analyze_semantics(hinata)
        
        # 4. 生成向量表示
        enhanced.embedding_vector = await self._generate_embedding(hinata)
        
        return enhanced
    
    async def _generate_semantic_tags(self, hinata: HiNATAData) -> List[str]:
        """生成语义标签"""
        combined_text = f"{hinata.highlight} {hinata.note}"
        if self.small_model_mode:
            # 简化：基于词频的粗略关键词
            words = [w.strip('.,:;!?()').lower() for w in combined_text.split()]
            words = [w for w in words if len(w) > 3]
            top = list(dict.fromkeys(words))[:8]
            return top
        doc = self.nlp_model(combined_text)
        tags = []
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT']:
                tags.append(ent.text.lower())
        keywords = [token.lemma_.lower() for token in doc 
                   if token.pos_ in ['NOUN', 'ADJ'] and len(token.text) > 3]
        tags.extend(keywords[:5])
        return list(set(tags))
    
    async def _extract_recommended_highlights(self, hinata: HiNATAData) -> List[str]:
        """从note中提取推荐的highlight片段"""
        if len(hinata.note) < 100:
            return [hinata.note]
        if self.small_model_mode:
            # 简化：按句子长度与关键词启发
            sentences = [s.strip() for s in hinata.note.split('.') if s.strip()]
            scores = []
            for s in sentences:
                score = 0
                l = len(s.split())
                if 12 <= l <= 40:
                    score += 2
                for w in ['important', 'key', 'main', 'crucial', 'significant']:
                    if w in s.lower():
                        score += 1
                scores.append((s, score))
            scores.sort(key=lambda x: x[1], reverse=True)
            return [s for s, sc in scores[:3] if sc > 0]
        doc = self.nlp_model(hinata.note)
        sentences = [sent.text.strip() for sent in doc.sents]
        scored_sentences = []
        for sentence in sentences:
            score = 0
            if 20 <= len(sentence.split()) <= 40:
                score += 2
            special_words = ['important', 'key', 'main', 'crucial', 'significant']
            for word in special_words:
                if word in sentence.lower():
                    score += 1
            scored_sentences.append((sentence, score))
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sent[0] for sent in scored_sentences[:3] if sent[1] > 0]
    
    async def _analyze_semantics(self, hinata: HiNATAData) -> Dict[str, Any]:
        """分析内容语义特征"""
        combined_text = f"{hinata.highlight} {hinata.note}"
        if self.small_model_mode:
            # 简化分析
            text_lower = combined_text.lower()
            positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful']
            negative_words = ['bad', 'terrible', 'awful', 'horrible', 'disappointing']
            pos_count = sum(w in text_lower for w in positive_words)
            neg_count = sum(w in text_lower for w in negative_words)
            sentiment = 'positive' if pos_count > neg_count else ('negative' if neg_count > pos_count else 'neutral')
            words = [w for w in combined_text.split() if len(w) > 4]
            avg_sentence_length = max(1, len(words)) / max(1, len(combined_text.split('.')))
            complexity = 'high' if avg_sentence_length > 20 else ('medium' if avg_sentence_length > 10 else 'low')
            return {
                'main_topics': list(dict.fromkeys(words))[:3],
                'sentiment': sentiment,
                'complexity_level': complexity,
                'key_concepts': list(dict.fromkeys(words))[:5]
            }
        doc = self.nlp_model(combined_text)
        topics = []
        for ent in doc.ents:
            if ent.label_ in ['PRODUCT', 'ORG', 'GPE']:
                topics.append(ent.text)
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'disappointing']
        text_lower = combined_text.lower()
        pos_count = sum(word in text_lower for word in positive_words)
        neg_count = sum(word in text_lower for word in negative_words)
        sentiment = "positive" if pos_count > neg_count else ("negative" if neg_count > pos_count else "neutral")
        avg_sentence_length = len(combined_text.split()) / max(len(list(doc.sents)), 1)
        if avg_sentence_length > 20:
            complexity = "high"
        elif avg_sentence_length > 10:
            complexity = "medium"
        else:
            complexity = "low"
        return {
            "main_topics": topics[:3],
            "sentiment": sentiment,
            "complexity_level": complexity,
            "key_concepts": [token.lemma_ for token in doc if token.pos_ == 'NOUN'][:5]
        }
    
    async def _generate_embedding(self, hinata: HiNATAData) -> List[float]:
        """生成向量表示"""
        combined_text = f"{hinata.highlight} {hinata.note}"
        if self.small_model_mode:
            # 生成一个稳定的伪向量（hash 到固定维度），用于开发最小可跑
            import hashlib
            h = hashlib.sha256(combined_text.encode()).digest()
            # 生成 32 维简单向量
            vec = [(b - 128) / 128.0 for b in h[:32]]
            return vec
        embedding = self.embedding_model.encode(combined_text)
        return embedding.tolist()


class QualityScorer:
    """HiNATA质量评分器"""
    
    def calculate_quality_score(self, hinata: HiNATAData) -> float:
        """计算HiNATA质量分数"""
        factors = {
            'content_depth': self._assess_content_depth(hinata),
            'information_value': self._assess_information_value(hinata),
            'user_engagement': self._assess_user_engagement(hinata),
            'complexity': self._assess_complexity(hinata),
            'novelty': self._assess_novelty(hinata)
        }
        
        # 加权平均
        quality_score = (
            factors['content_depth'] * 0.25 +
            factors['information_value'] * 0.25 +
            factors['user_engagement'] * 0.20 +
            factors['complexity'] * 0.15 +
            factors['novelty'] * 0.15
        )
        
        return min(max(quality_score, 0.0), 1.0)
    
    def _assess_content_depth(self, hinata: HiNATAData) -> float:
        """评估内容深度"""
        highlight_length = len(hinata.highlight.split())
        note_length = len(hinata.note.split())
        
        # 基于长度的深度评分
        depth_score = 0.0
        
        if highlight_length > 10:
            depth_score += 0.3
        elif highlight_length > 5:
            depth_score += 0.2
        else:
            depth_score += 0.1
        
        if note_length > 50:
            depth_score += 0.4
        elif note_length > 20:
            depth_score += 0.3
        elif note_length > 10:
            depth_score += 0.2
        else:
            depth_score += 0.1
        
        # 标签丰富度
        tag_count = len(hinata.tag)
        if tag_count > 3:
            depth_score += 0.3
        elif tag_count > 1:
            depth_score += 0.2
        else:
            depth_score += 0.1
        
        return min(depth_score, 1.0)
    
    def _assess_information_value(self, hinata: HiNATAData) -> float:
        """评估信息价值"""
        combined_text = f"{hinata.highlight} {hinata.note}".lower()
        
        # 信息密度指标
        info_indicators = [
            'how to', 'why', 'because', 'explain', 'steps', 'process',
            'important', 'key', 'main', 'significant', 'crucial'
        ]
        
        indicator_count = sum(indicator in combined_text for indicator in info_indicators)
        info_score = min(indicator_count * 0.2, 1.0)
        
        return info_score
    
    def _assess_user_engagement(self, hinata: HiNATAData) -> float:
        """评估用户参与度"""
        engagement_score = 0.0
        
        # 基于note长度的参与度
        note_length = len(hinata.note.split())
        if note_length > 100:
            engagement_score += 0.5
        elif note_length > 50:
            engagement_score += 0.3
        elif note_length > 20:
            engagement_score += 0.2
        else:
            engagement_score += 0.1
        
        # 基于标签数量的参与度
        tag_count = len(hinata.tag)
        if tag_count > 5:
            engagement_score += 0.3
        elif tag_count > 2:
            engagement_score += 0.2
        else:
            engagement_score += 0.1
        
        # 检查是否有结构化内容
        if any(marker in hinata.note for marker in ['1.', '2.', '-', '*', ':']):
            engagement_score += 0.2
        
        return min(engagement_score, 1.0)
    
    def _assess_complexity(self, hinata: HiNATAData) -> float:
        """评估内容复杂度"""
        combined_text = f"{hinata.highlight} {hinata.note}"
        
        # 平均句子长度
        sentences = combined_text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        if avg_sentence_length > 20:
            complexity_score = 0.8
        elif avg_sentence_length > 15:
            complexity_score = 0.6
        elif avg_sentence_length > 10:
            complexity_score = 0.4
        else:
            complexity_score = 0.2
        
        return complexity_score
    
    def _assess_novelty(self, hinata: HiNATAData) -> float:
        """评估内容新颖性（简化版）"""
        # 这里应该与历史数据比较，暂时简化处理
        
        # 基于来源多样性
        if hinata.source.endswith('_chatbot'):
            novelty_score = 0.6  # AI对话有一定新颖性
        elif 'browser' in hinata.source:
            novelty_score = 0.5  # 浏览器内容
        else:
            novelty_score = 0.7  # 其他来源可能更新颖
        
        return novelty_score


class AttentionWeightCalculator:
    """注意力权重计算器"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def calculate_attention_weight(self, hinata: HiNATAData, user_id: str) -> Tuple[float, Dict[str, Any]]:
        """计算用户注意力权重"""
        
        # 获取用户历史数据
        historical_data = await self._get_user_historical_data(user_id, days=30)
        
        # 计算各维度权重
        metrics = {
            'highlight_frequency': await self._calculate_highlight_frequency(hinata, historical_data),
            'note_density': await self._calculate_note_density(hinata, historical_data),
            'address_revisit': await self._calculate_address_revisit(hinata, historical_data),
            'time_investment': await self._calculate_time_investment(hinata, historical_data),
            'interaction_depth': await self._evaluate_interaction_depth(hinata, historical_data)
        }
        
        # 综合权重计算
        highlight_weight = self._normalize_frequency_weight(metrics['highlight_frequency'])
        note_weight = self._normalize_density_weight(metrics['note_density'])
        revisit_weight = self._normalize_revisit_weight(metrics['address_revisit'])
        time_weight = self._normalize_time_weight(metrics['time_investment'])
        
        attention_weight = (
            highlight_weight * 0.30 +
            note_weight * 0.25 +
            revisit_weight * 0.30 +
            time_weight * 0.15
        )
        
        # 应用交互深度调节
        depth_multiplier = self._get_depth_multiplier(metrics['interaction_depth'])
        final_weight = min(attention_weight * depth_multiplier, 1.0)
        
        return final_weight, metrics
    
    async def _get_user_historical_data(self, user_id: str, days: int) -> List[Dict[str, Any]]:
        """获取用户历史数据"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT highlight, note, address, timestamp, attention_weight, enhanced_tags
                FROM hinata_data 
                WHERE user_id = $1 AND timestamp >= NOW() - INTERVAL '%s days'
                ORDER BY timestamp DESC
            """ % days
            
            rows = await conn.fetch(query, user_id)
            return [dict(row) for row in rows]
    
    async def _calculate_highlight_frequency(self, hinata: HiNATAData, historical_data: List[Dict]) -> int:
        """计算相似highlight的频率"""
        current_highlight = hinata.highlight.lower()
        similar_count = 0
        
        for historical in historical_data:
            similarity = self._text_similarity(current_highlight, historical['highlight'].lower())
            if similarity > 0.7:  # 相似度阈值
                similar_count += 1
        
        return similar_count
    
    async def _calculate_note_density(self, hinata: HiNATAData, historical_data: List[Dict]) -> int:
        """计算同一地址的note密度"""
        current_address = hinata.address
        note_count = 0
        
        for historical in historical_data:
            if historical['address'] == current_address and historical['note'].strip():
                note_count += 1
        
        return note_count
    
    async def _calculate_address_revisit(self, hinata: HiNATAData, historical_data: List[Dict]) -> int:
        """计算地址重访次数"""
        current_address = hinata.address
        visit_count = 0
        
        for historical in historical_data:
            if historical['address'] == current_address:
                visit_count += 1
        
        return visit_count
    
    async def _calculate_time_investment(self, hinata: HiNATAData, historical_data: List[Dict]) -> float:
        """计算时间投入（秒）"""
        # 简化计算：基于相关内容的数量估算时间投入
        related_count = 0
        
        for historical in historical_data:
            if self._is_topic_related(hinata, historical):
                related_count += 1
        
        # 估算：每个相关HiNATA代表5分钟投入
        estimated_time = related_count * 300
        return min(estimated_time, 3600)  # 最大1小时
    
    async def _evaluate_interaction_depth(self, hinata: HiNATAData, historical_data: List[Dict]) -> str:
        """评估交互深度"""
        factors = []
        
        # note长度因子
        if len(hinata.note) > 200:
            factors.append("detailed_note")
        
        # 标签丰富度因子
        if len(hinata.tag) > 3:
            factors.append("rich_tagging")
        
        # 相关内容数量因子
        related_count = sum(1 for h in historical_data if self._is_topic_related(hinata, h))
        if related_count > 5:
            factors.append("extensive_exploration")
        
        # 时间跨度因子
        time_span = self._calculate_topic_time_span(hinata, historical_data)
        if time_span > 7:  # 超过7天
            factors.append("sustained_interest")
        
        # 确定深度级别
        if len(factors) >= 3:
            return "high"
        elif len(factors) >= 2:
            return "medium"
        else:
            return "low"
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _is_topic_related(self, hinata1: HiNATAData, hinata2: Dict) -> bool:
        """判断两个HiNATA是否主题相关"""
        tags1 = set(hinata1.tag + (hinata1.enhanced_tags or []))
        tags2 = set(hinata2.get('enhanced_tags', []))
        
        if not tags1 or not tags2:
            return False
        
        overlap = len(tags1.intersection(tags2))
        return overlap >= 2  # 至少有2个共同标签
    
    def _calculate_topic_time_span(self, hinata: HiNATAData, historical_data: List[Dict]) -> int:
        """计算主题的时间跨度（天）"""
        current_time = datetime.fromisoformat(hinata.timestamp.replace('Z', '+00:00'))
        
        related_times = []
        for historical in historical_data:
            if self._is_topic_related(hinata, historical):
                hist_time = datetime.fromisoformat(historical['timestamp'].replace('Z', '+00:00'))
                related_times.append(hist_time)
        
        if not related_times:
            return 0
        
        earliest = min(related_times)
        time_span = (current_time - earliest).days
        return time_span
    
    def _normalize_frequency_weight(self, frequency: int) -> float:
        """归一化频率权重"""
        if frequency <= 1:
            return 0.1
        elif frequency <= 3:
            return 0.4
        elif frequency <= 5:
            return 0.7
        else:
            return 1.0
    
    def _normalize_density_weight(self, density: int) -> float:
        """归一化密度权重"""
        if density <= 1:
            return 0.2
        elif density <= 3:
            return 0.6
        elif density <= 5:
            return 0.8
        else:
            return 1.0
    
    def _normalize_revisit_weight(self, revisit: int) -> float:
        """归一化重访权重"""
        if revisit <= 1:
            return 0.1
        elif revisit <= 3:
            return 0.5
        elif revisit <= 6:
            return 0.8
        else:
            return 1.0
    
    def _normalize_time_weight(self, time_seconds: float) -> float:
        """归一化时间权重"""
        if time_seconds < 30:
            return 0.1
        elif time_seconds < 120:
            return 0.4
        elif time_seconds < 300:
            return 0.7
        else:
            return 1.0
    
    def _get_depth_multiplier(self, interaction_depth: str) -> float:
        """获取交互深度调节因子"""
        multipliers = {
            'low': 0.8,
            'medium': 1.0,
            'high': 1.2
        }
        return multipliers.get(interaction_depth, 1.0)


class HiNATAProcessor:
    """HiNATA处理引擎主类"""
    
    def __init__(self, redis_url: str, postgres_dsn: str):
        self.validator = HiNATAValidator()
        self.enhancer = AIEnhancer()
        self.quality_scorer = QualityScorer()
        
        self.redis_url = redis_url
        self.postgres_dsn = postgres_dsn
        self.redis_pool = None
        self.db_pool = None
        self.attention_calculator = None
        
    async def initialize(self):
        """初始化处理器"""
        self.redis_pool = aioredis.from_url(self.redis_url)
        self.db_pool = await asyncpg.create_pool(self.postgres_dsn)
        self.attention_calculator = AttentionWeightCalculator(self.db_pool)
    
    async def process_hinata_batch(self, hinata_batch: List[Dict[str, Any]], user_id: str) -> List[ProcessingResult]:
        """批量处理HiNATA数据"""
        results = []
        
        for hinata_dict in hinata_batch:
            start_time = time.time()
            
            try:
                result = await self._process_single_hinata(hinata_dict, user_id)
                processing_time = time.time() - start_time
                result.processing_time = processing_time
                results.append(result)
                
            except Exception as e:
                processing_time = time.time() - start_time
                error_result = ProcessingResult(
                    status=HiNATAProcessingStatus.FAILED,
                    hinata_id=hinata_dict.get('id', 'unknown'),
                    processing_time=processing_time,
                    error_message=str(e)
                )
                results.append(error_result)
        
        return results
    
    async def _process_single_hinata(self, hinata_dict: Dict[str, Any], user_id: str) -> ProcessingResult:
        """处理单个HiNATA"""
        
        # 1. 验证格式
        is_valid, errors = self.validator.validate(hinata_dict)
        if not is_valid:
            raise ValueError(f"Validation failed: {errors}")
        
        # 2. 标准化
        standardized = self.validator.standardize(hinata_dict)
        hinata = HiNATAData(**standardized)
        
        # 3. AI增强
        enhanced_hinata = await self.enhancer.enhance_hinata(hinata)
        
        # 4. 质量评分
        quality_score = self.quality_scorer.calculate_quality_score(enhanced_hinata)
        enhanced_hinata.quality_score = quality_score
        
        # 5. 注意力权重计算
        attention_weight, attention_metrics = await self.attention_calculator.calculate_attention_weight(
            enhanced_hinata, user_id
        )
        enhanced_hinata.attention_weight = attention_weight
        enhanced_hinata.attention_metrics = attention_metrics
        
        # 6. 计算PSP影响权重
        psp_influence_weight = self._calculate_psp_influence_weight(quality_score, attention_weight)
        enhanced_hinata.psp_influence_weight = psp_influence_weight
        
        # 7. 添加处理元数据
        enhanced_hinata.processing_metadata = {
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'processor_version': '1.0.0',
            'enhancements_applied': ['semantic_tags', 'recommended_highlights', 'embedding', 'quality_score', 'attention_weight']
        }
        
        # 8. 存储和索引
        await self._store_and_index(enhanced_hinata, user_id)
        
        return ProcessingResult(
            status=HiNATAProcessingStatus.COMPLETED,
            hinata_id=enhanced_hinata.id,
            processing_time=0.0,  # 将在外层设置
            enhancements_applied=enhanced_hinata.processing_metadata['enhancements_applied']
        )
    
    def _calculate_psp_influence_weight(self, quality_score: float, attention_weight: float) -> float:
        """计算PSP影响权重"""
        base_influence = (quality_score * 0.6 + attention_weight * 0.4)
        
        # 确保最小影响不为0，最大影响不超过1
        min_influence = 0.05
        max_influence = 1.0
        
        final_influence = min_influence + (max_influence - min_influence) * base_influence
        return final_influence
    
    async def _store_and_index(self, hinata: HiNATAData, user_id: str):
        """存储和建立索引"""
        
        # 确定存储层级
        storage_tier = self._determine_storage_tier(hinata)
        
        # 存储数据
        if storage_tier == "hot":
            await self._store_in_hot_layer(hinata, user_id)
        elif storage_tier == "warm":
            await self._store_in_warm_layer(hinata, user_id)
        else:
            await self._store_in_cold_layer(hinata, user_id)
        
        # 建立索引
        await self._build_indexes(hinata, user_id)
    
    def _determine_storage_tier(self, hinata: HiNATAData) -> str:
        """确定存储层级"""
        influence_weight = hinata.psp_influence_weight or 0
        created_time = datetime.fromisoformat(hinata.timestamp.replace('Z', '+00:00'))
        recency_days = (datetime.now(timezone.utc) - created_time).days
        
        if influence_weight > 0.7 or recency_days < 7:
            return "hot"
        elif influence_weight > 0.3 or recency_days < 30:
            return "warm"
        else:
            return "cold"
    
    async def _store_in_hot_layer(self, hinata: HiNATAData, user_id: str):
        """存储到热数据层（Redis）"""
        hinata_data = asdict(hinata)
        
        # 存储完整数据
        await self.redis_pool.setex(
            f"hinata:full:{hinata.id}",
            7 * 24 * 3600,  # 7天TTL
            json.dumps(hinata_data, ensure_ascii=False)
        )
        
        # 用户索引
        await self.redis_pool.zadd(
            f"user:hot_hinata:{user_id}",
            {hinata.id: hinata.psp_influence_weight or 0}
        )
        
        # 主题索引
        for tag in (hinata.enhanced_tags or []):
            await self.redis_pool.zadd(
                f"topic:hot_hinata:{tag}",
                {hinata.id: hinata.psp_influence_weight or 0}
            )
    
    async def _store_in_warm_layer(self, hinata: HiNATAData, user_id: str):
        """存储到温数据层（PostgreSQL）"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO hinata_data 
                (id, user_id, timestamp, source, highlight, note, address, tags, access_level,
                 enhanced_tags, quality_score, attention_weight, psp_influence_weight, 
                 embedding_vector, processing_metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ''', 
                hinata.id, user_id, hinata.timestamp, hinata.source, 
                hinata.highlight, hinata.note, hinata.address,
                json.dumps(hinata.tag), hinata.access,
                json.dumps(hinata.enhanced_tags or []),
                hinata.quality_score, hinata.attention_weight, hinata.psp_influence_weight,
                json.dumps(hinata.embedding_vector or []),
                json.dumps(hinata.processing_metadata or {})
            )
    
    async def _store_in_cold_layer(self, hinata: HiNATAData, user_id: str):
        """存储到冷数据层（文件系统）"""
        # 这里应该实现Parquet文件存储
        # 为了简化，暂时也存储到PostgreSQL
        await self._store_in_warm_layer(hinata, user_id)
    
    async def _build_indexes(self, hinata: HiNATAData, user_id: str):
        """建立多维度索引"""
        
        # 这里应该调用向量数据库、全文搜索引擎等建立索引
        # 为了简化，现在只在PostgreSQL中建立基础索引
        
        async with self.db_pool.acquire() as conn:
            # 更新索引表
            await conn.execute('''
                INSERT INTO hinata_index 
                (hinata_id, user_id, timestamp, source, psp_influence_weight, 
                 attention_weight, quality_score, storage_tier, tags, content_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''',
                hinata.id, user_id, hinata.timestamp, hinata.source,
                hinata.psp_influence_weight, hinata.attention_weight, hinata.quality_score,
                self._determine_storage_tier(hinata),
                json.dumps((hinata.tag or []) + (hinata.enhanced_tags or [])),
                hashlib.md5(f"{hinata.highlight}{hinata.note}".encode()).hexdigest()
            )
    
    async def close(self):
        """关闭连接"""
        if self.redis_pool:
            await self.redis_pool.close()
        if self.db_pool:
            await self.db_pool.close()


# 使用示例
async def main():
    """使用示例"""
    processor = HiNATAProcessor(
        redis_url="redis://localhost:6379",
        postgres_dsn="postgresql://user:password@localhost/byenatos"
    )
    
    await processor.initialize()
    
    # 示例HiNATA数据
    sample_hinata = {
        "id": "hinata_20241201_001",
        "timestamp": "2024-12-01T10:30:00Z",
        "source": "browser_extension",
        "highlight": "Machine learning models require careful validation",
        "note": "This is an important point about ML validation. We need to use cross-validation and hold-out test sets to ensure our models generalize well to unseen data.",
        "address": "https://example.com/ml-guide",
        "tag": ["machine-learning", "validation"],
        "access": "private",
        "raw_data": {
            "page_title": "Complete ML Guide",
            "selection_context": "Chapter 3: Model Validation"
        }
    }
    
    # 处理HiNATA
    results = await processor.process_hinata_batch([sample_hinata], "user_123")
    
    for result in results:
        print(f"Processed {result.hinata_id}: {result.status}")
        print(f"Processing time: {result.processing_time:.3f}s")
        if result.enhancements_applied:
            print(f"Enhancements: {result.enhancements_applied}")
    
    await processor.close()


if __name__ == "__main__":
    asyncio.run(main())