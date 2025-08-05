# 用户注意力权重系统设计

## 概述

用户注意力权重系统是ByenatOS的核心组件，通过分析用户的HiNATA行为模式，量化用户对不同内容的真实关注度，并将这些权重信息集成到PSP迭代机制中，确保操作系统能够准确理解和响应用户的真实需求。

## 系统架构

### 整体设计原则

1. **行为驱动权重** - 基于用户的实际行为计算注意力权重
2. **多维度评估** - 从频率、深度、时间、重访等多个维度分析用户关注
3. **实时更新** - 随着新的HiNATA数据流实时调整权重
4. **PSP集成** - 将权重信息直接应用到PSP迭代和决策中

### 核心组件

```
HiNATA数据流 → 注意力模式分析 → 权重计算 → PSP权重融合 → 个性化体验优化
```

## 注意力权重计算机制

### 权重因子定义

#### 1. Highlight频率权重 (30%)
**定义**: 用户对相似内容进行highlight的频率
**计算逻辑**:
```python
def calculate_highlight_frequency_weight(similarity_count):
    """
    similarity_count: 相似highlight的数量
    返回值: 0.1 - 1.0
    """
    if similarity_count <= 1:
        return 0.1  # 首次关注
    elif similarity_count <= 3:
        return 0.4  # 初步关注
    elif similarity_count <= 5:
        return 0.7  # 持续关注
    else:
        return 1.0  # 深度关注
```

#### 2. Note密度权重 (25%)
**定义**: 同一主题或地址下用户添加note的数量和质量
**计算逻辑**:
```python
def calculate_note_density_weight(note_count, avg_note_length):
    """
    note_count: 同一地址的note数量
    avg_note_length: 平均note长度
    返回值: 0.2 - 1.0
    """
    base_weight = min(note_count / 5.0, 1.0)  # 基于数量
    quality_bonus = min(avg_note_length / 200.0, 0.3)  # 基于质量
    
    return max(0.2, base_weight + quality_bonus)
```

#### 3. 地址重访权重 (30%)
**定义**: 用户对同一资源地址的重复访问和操作
**计算逻辑**:
```python
def calculate_revisit_weight(visit_count, time_span_days):
    """
    visit_count: 访问次数
    time_span_days: 时间跨度（天）
    返回值: 0.1 - 1.0
    """
    frequency_weight = min(visit_count / 6.0, 1.0)
    persistence_bonus = min(time_span_days / 30.0, 0.2)
    
    return max(0.1, frequency_weight + persistence_bonus)
```

#### 4. 时间投入权重 (15%)
**定义**: 用户在相关主题上投入的总时间
**计算逻辑**:
```python
def calculate_time_investment_weight(total_seconds):
    """
    total_seconds: 总投入时间（秒）
    返回值: 0.1 - 1.0
    """
    # 使用对数函数避免时间过长导致权重过高
    normalized_time = math.log(total_seconds + 1) / math.log(3600)  # 以1小时为基准
    return min(max(0.1, normalized_time), 1.0)
```

### 综合权重计算

```python
def calculate_comprehensive_attention_weight(metrics):
    """计算综合注意力权重"""
    highlight_weight = calculate_highlight_frequency_weight(metrics['highlight_frequency'])
    note_weight = calculate_note_density_weight(metrics['note_count'], metrics['avg_note_length'])
    revisit_weight = calculate_revisit_weight(metrics['address_revisit'], metrics['time_span'])
    time_weight = calculate_time_investment_weight(metrics['time_investment'])
    
    # 加权平均
    attention_weight = (
        highlight_weight * 0.30 +
        note_weight * 0.25 +
        revisit_weight * 0.30 +
        time_weight * 0.15
    )
    
    # 应用交互深度调节因子
    depth_multiplier = get_depth_multiplier(metrics['interaction_depth'])
    final_weight = min(attention_weight * depth_multiplier, 1.0)
    
    return final_weight

def get_depth_multiplier(interaction_depth):
    """根据交互深度获取调节因子"""
    multipliers = {
        'low': 0.8,
        'medium': 1.0,
        'high': 1.2
    }
    return multipliers.get(interaction_depth, 1.0)
```

## 操作系统级集成机制

### 1. 实时权重更新服务

```python
class AttentionWeightService:
    def __init__(self):
        self.weight_calculator = AttentionWeightCalculator()
        self.historical_analyzer = HistoricalDataAnalyzer()
        self.psp_integrator = PSPIntegrator()
        
    def process_hinata_stream(self, hinata_record):
        """处理单个HiNATA记录"""
        # 1. 计算注意力权重
        attention_weight = self.weight_calculator.calculate(
            hinata_record, 
            self.historical_analyzer.get_context(hinata_record['user_id'])
        )
        
        # 2. 更新记录
        hinata_record['attention_weight'] = attention_weight
        
        # 3. 触发PSP更新
        self.psp_integrator.update_with_attention_weight(hinata_record)
        
        # 4. 通知相关服务
        self.notify_attention_update(hinata_record)
        
        return hinata_record
```

### 2. 历史数据分析器

```python
class HistoricalDataAnalyzer:
    def __init__(self):
        self.data_store = VectorDatabase()
        self.cache = LRUCache(maxsize=1000)
        
    def get_context(self, user_id, time_window='30d'):
        """获取用户历史上下文"""
        cache_key = f"{user_id}_{time_window}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 查询历史数据
        historical_data = self.data_store.query_user_history(
            user_id=user_id,
            time_range=time_window,
            include_fields=['highlight', 'note', 'address', 'timestamp', 'attention_weight']
        )
        
        # 构建上下文
        context = self.build_attention_context(historical_data)
        self.cache[cache_key] = context
        
        return context
    
    def build_attention_context(self, historical_data):
        """构建注意力上下文"""
        return {
            'highlight_patterns': self.extract_highlight_patterns(historical_data),
            'address_frequencies': self.calculate_address_frequencies(historical_data),
            'topic_time_investment': self.calculate_topic_time_investment(historical_data),
            'interaction_trends': self.analyze_interaction_trends(historical_data)
        }
```

### 3. PSP权重集成器

```python
class PSPIntegrator:
    def __init__(self):
        self.psp_manager = PSPManager()
        self.weight_aggregator = WeightAggregator()
        
    def update_with_attention_weight(self, hinata_record):
        """基于注意力权重更新PSP"""
        user_id = hinata_record['user_id']
        attention_weight = hinata_record['attention_weight']
        
        # 获取当前PSP
        current_psp = self.psp_manager.get_user_psp(user_id)
        
        # 提取意图
        intent = extract_intent_from_hinata(hinata_record)
        intent['attention_weight'] = attention_weight
        
        # 匹配PSP组件
        matches = match_intent_with_psp(intent, current_psp)
        
        # 基于注意力权重更新PSP
        updated_psp = self.apply_attention_weighted_update(matches, current_psp)
        
        # 保存更新后的PSP
        self.psp_manager.update_user_psp(user_id, updated_psp)
        
    def apply_attention_weighted_update(self, matches, current_psp):
        """应用注意力权重的PSP更新"""
        # 按注意力权重排序
        weighted_matches = sorted(
            matches, 
            key=lambda x: x['intent'].get('attention_weight', 0), 
            reverse=True
        )
        
        for match in weighted_matches:
            attention_weight = match['intent']['attention_weight']
            
            if attention_weight > 0.7:  # 高权重内容
                # 强化更新，提高影响力
                self.apply_strong_update(match, current_psp)
            elif attention_weight > 0.4:  # 中等权重内容
                # 标准更新
                self.apply_standard_update(match, current_psp)
            else:  # 低权重内容
                # 轻微更新，避免噪音
                self.apply_light_update(match, current_psp)
        
        return current_psp
```

## 系统性能优化

### 1. 缓存策略

```python
class AttentionWeightCache:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.local_cache = LRUCache(maxsize=500)
        
    def get_cached_weight(self, hinata_hash):
        """获取缓存的权重"""
        # 首先检查本地缓存
        if hinata_hash in self.local_cache:
            return self.local_cache[hinata_hash]
        
        # 检查Redis缓存
        cached_data = self.redis_client.get(f"attention_weight:{hinata_hash}")
        if cached_data:
            weight_data = json.loads(cached_data)
            self.local_cache[hinata_hash] = weight_data
            return weight_data
        
        return None
    
    def cache_weight(self, hinata_hash, weight_data, ttl=3600):
        """缓存权重数据"""
        # 本地缓存
        self.local_cache[hinata_hash] = weight_data
        
        # Redis缓存
        self.redis_client.setex(
            f"attention_weight:{hinata_hash}",
            ttl,
            json.dumps(weight_data)
        )
```

### 2. 批量处理

```python
class BatchAttentionProcessor:
    def __init__(self, batch_size=50):
        self.batch_size = batch_size
        self.pending_records = []
        
    def add_record(self, hinata_record):
        """添加记录到批处理队列"""
        self.pending_records.append(hinata_record)
        
        if len(self.pending_records) >= self.batch_size:
            self.process_batch()
    
    def process_batch(self):
        """批量处理记录"""
        if not self.pending_records:
            return
        
        # 按用户分组
        user_groups = group_by_user(self.pending_records)
        
        # 并行处理每个用户的数据
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for user_id, records in user_groups.items():
                future = executor.submit(self.process_user_batch, user_id, records)
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                future.result()
        
        # 清空队列
        self.pending_records.clear()
```

## 应用场景示例

### 场景1：技术学习追踪

```python
# 用户对"机器学习"主题的注意力演化
timeline = [
    {
        "day": 1,
        "hinata_count": 2,
        "attention_weight": 0.3,
        "action": "初次接触，简单highlight"
    },
    {
        "day": 3,
        "hinata_count": 5,
        "attention_weight": 0.6,
        "action": "深入阅读，添加详细note"
    },
    {
        "day": 7,
        "hinata_count": 8,
        "attention_weight": 0.8,
        "action": "重访资源，多次highlight同一概念"
    },
    {
        "day": 14,
        "hinata_count": 12,
        "attention_weight": 0.95,
        "action": "持续学习，跨资源关联思考"
    }
]

# PSP演化结果
psp_evolution = {
    "core_interest": "机器学习",
    "weight_progression": [0.3, 0.6, 0.8, 0.95],
    "psp_influence": "从边缘兴趣发展为核心关注点",
    "system_adaptation": "优先推荐相关内容，调整工作流程"
}
```

### 场景2：项目研究深度

```python
# 用户研究"区块链技术"的注意力分布
attention_analysis = {
    "total_hinata_count": 25,
    "unique_sources": 8,
    "time_span_days": 21,
    "metrics": {
        "highlight_frequency": 15,  # 相似概念被highlight 15次
        "note_count": 12,           # 12条详细笔记
        "address_revisit": 6,       # 重访6个关键资源
        "time_investment": 3600,    # 投入1小时深度思考
        "interaction_depth": "high"
    },
    "calculated_weight": 0.92,
    "psp_impact": "成为核心工作记忆组件"
}
```

## 监控和调优

### 权重质量评估

```python
class AttentionWeightQualityMonitor:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        
    def evaluate_weight_quality(self, user_id, time_period='7d'):
        """评估权重质量"""
        metrics = {
            'weight_distribution': self.analyze_weight_distribution(user_id, time_period),
            'psp_correlation': self.measure_psp_correlation(user_id, time_period),
            'user_satisfaction': self.get_user_feedback_score(user_id, time_period),
            'prediction_accuracy': self.measure_prediction_accuracy(user_id, time_period)
        }
        
        return self.calculate_quality_score(metrics)
    
    def suggest_optimizations(self, quality_metrics):
        """建议优化策略"""
        suggestions = []
        
        if quality_metrics['weight_distribution']['variance'] > 0.8:
            suggestions.append("调整权重因子比例，减少方差")
        
        if quality_metrics['psp_correlation'] < 0.7:
            suggestions.append("优化PSP集成算法")
        
        if quality_metrics['user_satisfaction'] < 0.8:
            suggestions.append("增加用户反馈权重")
        
        return suggestions
```

## 总结

用户注意力权重系统通过以下机制确保ByenatOS能够准确理解用户的真实关注：

### 核心优势

1. **多维度分析** - 综合考虑频率、深度、时间、重访等因素
2. **实时更新** - 随着用户行为实时调整权重和PSP
3. **PSP集成** - 直接影响操作系统的个性化决策
4. **性能优化** - 通过缓存和批处理确保系统效率

### 系统效果

- **提高PSP准确性** - 基于真实关注度调整个人系统提示
- **优化资源分配** - 将计算资源投入到用户真正关心的内容
- **增强用户体验** - 提供更精准的个性化服务
- **减少信息噪音** - 过滤低权重信息，突出重要内容

这个注意力权重系统是ByenatOS实现真正个性化操作系统体验的关键基础设施。