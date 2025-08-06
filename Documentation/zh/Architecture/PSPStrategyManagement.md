# PSP策略管理架构设计

## 概述

基于用户反馈驱动的PSP策略管理，区分PSP生产策略和PSP调用策略，实现高效的个性化迭代机制。

## 核心概念重新定义

### PSP生产策略 vs PSP调用策略

```
PSP生产策略 (Production Strategy)
├── 低频执行 (天/周级别)
├── 深度数据挖掘
├── 生成策略候选项
└── 基于长期行为模式

PSP调用策略 (Invocation Strategy)  
├── 高频执行 (每次查询)
├── 快速策略选择
├── 动态组合优化
└── 基于即时上下文
```

## 架构设计

### 1. PSP策略生产器 (PSP Producer)

```python
class PSPStrategyProducer:
    """PSP策略生产器 - 低频深度分析"""
    
    def __init__(self):
        self.pattern_analyzer = UserPatternAnalyzer()
        self.strategy_generator = StrategyGenerator()
        self.effectiveness_evaluator = EffectivenessEvaluator()
    
    def analyze_and_generate_strategies(self, hinata_data_batch):
        """分析HiNATA数据并生成PSP策略候选项"""
        
        # 1. 深度模式分析
        user_patterns = self.pattern_analyzer.analyze_patterns(
            hinata_data_batch,
            time_window='30d'
        )
        
        # 2. 生成策略候选项
        strategy_candidates = self.strategy_generator.generate_strategies(
            user_patterns
        )
        
        # 3. 评估现有策略效果
        strategy_effectiveness = self.effectiveness_evaluator.evaluate_strategies(
            existing_strategies=self.get_current_strategies(),
            user_feedback=self.get_recent_feedback()
        )
        
        # 4. 优化策略库
        optimized_strategies = self.optimize_strategy_library(
            strategy_candidates,
            strategy_effectiveness
        )
        
        return optimized_strategies

class StrategyGenerator:
    """策略生成器"""
    
    def generate_strategies(self, user_patterns):
        """基于用户模式生成PSP策略"""
        strategies = []
        
        # 生成不同类型的策略
        strategies.extend(self.generate_communication_strategies(user_patterns))
        strategies.extend(self.generate_content_strategies(user_patterns))
        strategies.extend(self.generate_context_strategies(user_patterns))
        
        return strategies
    
    def generate_communication_strategies(self, patterns):
        """生成沟通风格策略"""
        strategies = []
        
        if patterns.prefers_concise_answers:
            strategies.append(PSPStrategy(
                id="concise_communication",
                type="communication_style",
                rules=[
                    "用户偏好简洁直接的回答",
                    "避免冗长的解释",
                    "优先提供核心要点"
                ],
                confidence=patterns.communication_confidence,
                usage_contexts=["general", "technical", "quick_question"]
            ))
        
        if patterns.prefers_detailed_explanations:
            strategies.append(PSPStrategy(
                id="detailed_explanation",
                type="communication_style", 
                rules=[
                    "用户喜欢详细的解释和背景信息",
                    "提供步骤说明和原理解释",
                    "包含相关例子和对比"
                ],
                confidence=patterns.explanation_confidence,
                usage_contexts=["learning", "complex_problem", "tutorial"]
            ))
        
        return strategies
    
    def generate_content_strategies(self, patterns):
        """生成内容偏好策略"""
        strategies = []
        
        for domain in patterns.interest_domains:
            strategies.append(PSPStrategy(
                id=f"domain_{domain.name}",
                type="domain_expertise",
                rules=[
                    f"用户在{domain.name}领域有{domain.level}水平",
                    f"可以使用{domain.name}专业术语",
                    f"用户关注{domain.focus_areas}"
                ],
                confidence=domain.confidence,
                usage_contexts=[domain.name, "related_topics"]
            ))
        
        return strategies
```

### 2. PSP策略调用器 (PSP Invoker)

```python
class PSPStrategyInvoker:
    """PSP策略调用器 - 高频智能选择"""
    
    def __init__(self):
        self.strategy_selector = StrategySelector()
        self.strategy_combiner = StrategyCombiner()
        self.feedback_collector = FeedbackCollector()
        
    def invoke_psp_for_query(self, user_query, context):
        """为特定查询调用最优PSP组合"""
        
        # 1. 分析查询上下文
        query_context = self.analyze_query_context(user_query, context)
        
        # 2. 选择相关策略
        relevant_strategies = self.strategy_selector.select_strategies(
            query_context=query_context,
            available_strategies=self.get_strategy_library(),
            max_strategies=5  # 限制策略数量
        )
        
        # 3. 智能组合策略
        optimized_psp = self.strategy_combiner.combine_strategies(
            strategies=relevant_strategies,
            query_context=query_context,
            token_limit=self.get_token_limit()
        )
        
        # 4. 记录调用历史
        invocation_record = self.record_invocation(
            query=user_query,
            strategies_used=relevant_strategies,
            final_psp=optimized_psp
        )
        
        return optimized_psp, invocation_record

class StrategySelector:
    """策略选择器"""
    
    def select_strategies(self, query_context, available_strategies, max_strategies):
        """基于查询上下文选择最相关的策略"""
        
        strategy_scores = []
        
        for strategy in available_strategies:
            score = self.calculate_strategy_relevance(strategy, query_context)
            strategy_scores.append((strategy, score))
        
        # 按相关性排序并选择top N
        strategy_scores.sort(key=lambda x: x[1], reverse=True)
        selected_strategies = [s[0] for s in strategy_scores[:max_strategies]]
        
        return selected_strategies
    
    def calculate_strategy_relevance(self, strategy, query_context):
        """计算策略与查询的相关性"""
        relevance_score = 0.0
        
        # 上下文匹配
        if query_context.domain in strategy.usage_contexts:
            relevance_score += 0.4
        
        # 策略类型匹配
        if self.strategy_type_matches_query(strategy.type, query_context):
            relevance_score += 0.3
        
        # 历史效果
        historical_effectiveness = self.get_historical_effectiveness(
            strategy.id, query_context.domain
        )
        relevance_score += historical_effectiveness * 0.2
        
        # 策略置信度
        relevance_score += strategy.confidence * 0.1
        
        return relevance_score

class StrategyCombiner:
    """策略组合器"""
    
    def combine_strategies(self, strategies, query_context, token_limit):
        """智能组合多个策略为最终PSP"""
        
        # 1. 策略优先级排序
        prioritized_strategies = self.prioritize_strategies(strategies, query_context)
        
        # 2. 按token限制组合
        combined_psp = self.build_psp_within_limit(
            prioritized_strategies, token_limit
        )
        
        # 3. 优化PSP内容
        optimized_psp = self.optimize_psp_content(combined_psp)
        
        return optimized_psp
    
    def build_psp_within_limit(self, strategies, token_limit):
        """在token限制内构建PSP"""
        psp_parts = []
        current_tokens = 0
        
        for strategy in strategies:
            strategy_content = self.render_strategy_content(strategy)
            strategy_tokens = self.count_tokens(strategy_content)
            
            if current_tokens + strategy_tokens <= token_limit:
                psp_parts.append(strategy_content)
                current_tokens += strategy_tokens
            else:
                # 尝试压缩策略内容
                compressed_content = self.compress_strategy_content(
                    strategy, remaining_tokens=token_limit - current_tokens
                )
                if compressed_content:
                    psp_parts.append(compressed_content)
                break
        
        return "\n\n".join(psp_parts)
```

### 3. 用户反馈驱动的策略迭代

```python
class PSPFeedbackManager:
    """PSP反馈管理器"""
    
    def __init__(self):
        self.feedback_analyzer = FeedbackAnalyzer()
        self.strategy_optimizer = StrategyOptimizer()
        
    def process_user_feedback(self, invocation_record, feedback):
        """处理用户反馈并优化策略"""
        
        # 1. 分析反馈
        feedback_analysis = self.feedback_analyzer.analyze_feedback(
            feedback=feedback,
            invocation_record=invocation_record
        )
        
        # 2. 更新策略效果评分
        self.update_strategy_effectiveness(
            strategies_used=invocation_record.strategies_used,
            feedback_analysis=feedback_analysis
        )
        
        # 3. 优化调用策略
        self.optimize_invocation_strategy(feedback_analysis)
        
        # 4. 触发生产策略重新评估（如果需要）
        if self.should_trigger_production_update(feedback_analysis):
            self.trigger_production_strategy_update()

class FeedbackAnalyzer:
    """反馈分析器"""
    
    def analyze_feedback(self, feedback, invocation_record):
        """分析用户反馈"""
        analysis = {
            'satisfaction_score': self.extract_satisfaction_score(feedback),
            'issue_categories': self.identify_issue_categories(feedback),
            'successful_aspects': self.identify_successful_aspects(feedback),
            'strategy_attribution': self.attribute_feedback_to_strategies(
                feedback, invocation_record.strategies_used
            )
        }
        
        return analysis
    
    def extract_satisfaction_score(self, feedback):
        """提取满意度评分"""
        if feedback.type == 'explicit':
            return feedback.rating  # 1-5星评分
        elif feedback.type == 'implicit':
            # 基于用户行为推断满意度
            return self.infer_satisfaction_from_behavior(feedback.behavior)
    
    def attribute_feedback_to_strategies(self, feedback, strategies_used):
        """将反馈归因到具体策略"""
        attributions = {}
        
        for strategy in strategies_used:
            # 分析反馈中与该策略相关的部分
            strategy_relevance = self.calculate_feedback_strategy_relevance(
                feedback, strategy
            )
            attributions[strategy.id] = strategy_relevance
        
        return attributions

class StrategyOptimizer:
    """策略优化器"""
    
    def optimize_invocation_strategy(self, feedback_analysis):
        """基于反馈优化调用策略"""
        
        # 更新策略选择权重
        for strategy_id, attribution in feedback_analysis.strategy_attribution.items():
            current_weight = self.get_strategy_weight(strategy_id)
            
            if feedback_analysis.satisfaction_score > 4:
                # 满意反馈，增强策略权重
                new_weight = current_weight * 1.1
            elif feedback_analysis.satisfaction_score < 3:
                # 不满意反馈，降低策略权重
                new_weight = current_weight * 0.9
            else:
                new_weight = current_weight
            
            self.update_strategy_weight(strategy_id, new_weight)
    
    def optimize_production_strategy(self, long_term_feedback):
        """基于长期反馈优化生产策略"""
        
        # 分析长期反馈趋势
        trend_analysis = self.analyze_feedback_trends(long_term_feedback)
        
        # 识别需要改进的策略类型
        improvement_areas = self.identify_improvement_areas(trend_analysis)
        
        # 触发新策略生成
        for area in improvement_areas:
            self.trigger_new_strategy_generation(area)
```

### 4. 策略数据模型

```python
@dataclass
class PSPStrategy:
    """PSP策略数据模型"""
    id: str
    type: str  # communication_style, domain_expertise, context_preference等
    rules: List[str]
    confidence: float  # 0-1, 策略置信度
    usage_contexts: List[str]
    effectiveness_score: float = 0.5  # 基于用户反馈的效果评分
    usage_count: int = 0
    creation_time: datetime
    last_updated: datetime

@dataclass  
class InvocationRecord:
    """调用记录"""
    query: str
    strategies_used: List[PSPStrategy]
    final_psp: str
    token_count: int
    invocation_time: datetime
    context: Dict[str, Any]

@dataclass
class UserFeedback:
    """用户反馈"""
    type: str  # explicit, implicit
    rating: Optional[int]  # 1-5星评分
    behavior: Optional[Dict]  # 行为数据
    timestamp: datetime
    invocation_id: str
```

## 策略更新频率设计

### 高频更新 (每次调用)
- 策略选择权重调整
- 策略组合优化
- 即时反馈处理

### 中频更新 (每小时/每天)
- 策略效果评分更新
- 调用策略参数调优
- 短期反馈聚合分析

### 低频更新 (每周/每月)
- 新策略生成
- 策略库重构
- 长期反馈趋势分析

## 总结

通过分离PSP生产策略和调用策略，我们实现了：

1. **高效的实时响应** - 调用策略快速选择最优组合
2. **持续的策略优化** - 基于用户反馈不断改进
3. **灵活的策略管理** - 生产和调用独立优化
4. **用户反馈闭环** - 反馈直接驱动策略迭代

这个设计真正实现了"以用户反馈为驱动的个性化策略管理系统"。