# PSP迭代机制详细设计

## 概述

Personal System Prompt (PSP) 迭代机制是ByenatOS操作系统的核心功能，通过持续分析HiNATA数据流，不断优化PSP以更准确地反映用户的真实关注和意图。

## 迭代流程架构

### 整体流程

```
HiNATA数据流 → 向量化处理 → 模式识别 → 意图提取 → PSP匹配 → 增量更新 → 验证反馈
```

### 详细步骤

#### 1. HiNATA数据流接收与注意力权重计算
```python
def receive_hinata_stream():
    """接收HiNATA数据流并计算注意力权重"""
    hinata_queue = Queue()
    attention_analyzer = UserAttentionAnalyzer()
    
    # 监听来自应用的HiNATA文件
    for hinata_file in hinata_file_monitor:
        records = parse_hinata_file(hinata_file)
        for record in records:
            # 计算注意力权重
            enhanced_record = attention_analyzer.enhance_with_attention_weight(record)
            hinata_queue.put(enhanced_record)
    
    return hinata_queue

class UserAttentionAnalyzer:
    def __init__(self):
        self.historical_data_store = HistoricalDataStore()
        self.attention_cache = AttentionCache()
    
    def enhance_with_attention_weight(self, hinata_record):
        """为HiNATA记录添加注意力权重"""
        user_id = hinata_record.get('user_id')
        
        # 获取用户历史数据
        historical_data = self.historical_data_store.get_user_history(
            user_id, 
            time_window='30d'
        )
        
        # 计算注意力权重
        attention_weight, attention_metrics = calculate_attention_weight(
            hinata_record, 
            historical_data
        )
        
        # 增强记录
        hinata_record['attention_weight'] = attention_weight
        hinata_record['attention_metrics'] = attention_metrics
        
        # 缓存结果
        self.attention_cache.cache_attention_data(hinata_record)
        
        return hinata_record
```

#### 2. 向量化处理
```python
def vectorize_hinata_records(records):
    """将HiNATA记录向量化"""
    embeddings = []
    
    for record in records:
        # 组合文本内容
        text_content = f"{record['highlight']} {record['note']}"
        
        # 生成embedding
        embedding = local_llm.embed(text_content)
        
        # 存储向量
        embeddings.append({
            'id': record['id'],
            'embedding': embedding,
            'timestamp': record['timestamp'],
            'source': record['source']
        })
    
    return embeddings
```

#### 3. 模式识别
```python
def identify_patterns(embeddings, time_window='7d'):
    """识别用户行为模式"""
    patterns = {
        'frequent_topics': [],
        'time_patterns': {},
        'source_patterns': {},
        'intent_clusters': []
    }
    
    # 按时间窗口分组
    recent_embeddings = filter_by_time(embeddings, time_window)
    
    # 聚类分析
    clusters = cluster_embeddings(recent_embeddings)
    
    # 提取模式
    for cluster in clusters:
        pattern = extract_pattern_from_cluster(cluster)
        patterns['intent_clusters'].append(pattern)
    
    return patterns
```

#### 4. 意图提取
```python
def extract_user_intent(patterns):
    """从模式中提取用户意图"""
    intents = []
    
    for pattern in patterns['intent_clusters']:
        # 使用大模型分析意图
        intent_analysis = local_llm.analyze_intent(pattern)
        
        intent = {
            'type': intent_analysis['type'],
            'priority': intent_analysis['priority'],
            'confidence': intent_analysis['confidence'],
            'context': intent_analysis['context']
        }
        
        intents.append(intent)
    
    return intents
```

#### 5. PSP匹配
```python
def match_with_existing_psp(intents, current_psp):
    """将新意图与现有PSP匹配"""
    matches = []
    
    for intent in intents:
        # 计算与现有PSP的相似度
        similarity_scores = calculate_similarity(intent, current_psp)
        
        # 找到最佳匹配
        best_match = find_best_match(similarity_scores)
        
        if best_match['score'] > SIMILARITY_THRESHOLD:
            matches.append({
                'intent': intent,
                'psp_component': best_match['component'],
                'similarity': best_match['score'],
                'action': 'update'
            })
        else:
            # 新意图，需要创建新的PSP组件
            matches.append({
                'intent': intent,
                'psp_component': None,
                'similarity': 0,
                'action': 'create'
            })
    
    return matches
```

#### 6. 基于注意力权重的增量更新
```python
def incremental_psp_update(matches, current_psp):
    """基于匹配结果和注意力权重增量更新PSP"""
    updated_psp = current_psp.copy()
    
    # 按注意力权重排序matches，优先处理高权重内容
    sorted_matches = sort_matches_by_attention_weight(matches)
    
    for match in sorted_matches:
        attention_weight = match['intent'].get('attention_weight', 0.5)
        
        if match['action'] == 'update':
            # 更新现有PSP组件
            component = match['psp_component']
            intent = match['intent']
            
            # 基于注意力权重调整融合强度
            merge_strength = calculate_merge_strength(attention_weight)
            updated_component = merge_intent_to_component(
                component, 
                intent, 
                merge_strength=merge_strength
            )
            updated_psp[component['id']] = updated_component
            
        elif match['action'] == 'create':
            # 创建新的PSP组件
            new_component = create_psp_component(
                match['intent'], 
                initial_weight=attention_weight
            )
            updated_psp[new_component['id']] = new_component
    
    # 重新计算PSP组件权重
    updated_psp = rebalance_psp_weights(updated_psp)
    
    return updated_psp

def sort_matches_by_attention_weight(matches):
    """按注意力权重排序匹配结果"""
    return sorted(
        matches, 
        key=lambda x: x['intent'].get('attention_weight', 0.5), 
        reverse=True
    )

def calculate_merge_strength(attention_weight):
    """基于注意力权重计算融合强度"""
    # 高注意力权重的内容应该有更强的影响力
    if attention_weight > 0.8:
        return 1.0  # 完全融合
    elif attention_weight > 0.6:
        return 0.8  # 强融合
    elif attention_weight > 0.4:
        return 0.6  # 中等融合
    else:
        return 0.3  # 弱融合

def merge_intent_to_component(component, intent, merge_strength=1.0):
    """将意图融合到PSP组件中"""
    updated_component = component.copy()
    
    # 更新向量表示（加权平均）
    component_vector = component['embedding']
    intent_vector = intent['embedding']
    
    # 基于注意力权重和融合强度计算新向量
    merge_weight = intent.get('attention_weight', 0.5) * merge_strength
    new_vector = weighted_vector_merge(component_vector, intent_vector, merge_weight)
    
    updated_component['embedding'] = new_vector
    
    # 更新权重信息
    updated_component['total_attention_weight'] = (
        component.get('total_attention_weight', 0) + 
        intent.get('attention_weight', 0.5)
    )
    
    # 更新支撑证据
    if 'supporting_evidence' not in updated_component:
        updated_component['supporting_evidence'] = []
    
    updated_component['supporting_evidence'].append({
        'intent_id': intent['id'],
        'attention_weight': intent.get('attention_weight', 0.5),
        'timestamp': intent['timestamp'],
        'content_summary': intent.get('content_summary', '')
    })
    
    return updated_component

def create_psp_component(intent, initial_weight=0.5):
    """创建新的PSP组件"""
    return {
        'id': generate_component_id(),
        'embedding': intent['embedding'],
        'content_description': intent.get('description', ''),
        'creation_timestamp': intent['timestamp'],
        'total_attention_weight': intent.get('attention_weight', initial_weight),
        'supporting_evidence': [{
            'intent_id': intent['id'],
            'attention_weight': intent.get('attention_weight', initial_weight),
            'timestamp': intent['timestamp'],
            'content_summary': intent.get('content_summary', '')
        }],
        'activation_threshold': calculate_activation_threshold(initial_weight)
    }

def rebalance_psp_weights(psp):
    """重新平衡PSP组件权重"""
    total_weight = sum(
        component.get('total_attention_weight', 0) 
        for component in psp.values()
    )
    
    if total_weight == 0:
        return psp
    
    # 归一化权重并设置优先级
    for component_id, component in psp.items():
        component_weight = component.get('total_attention_weight', 0)
        normalized_weight = component_weight / total_weight
        
        # 设置组件优先级
        if normalized_weight > 0.15:
            component['priority'] = 'high'
        elif normalized_weight > 0.08:
            component['priority'] = 'medium'
        else:
            component['priority'] = 'low'
        
        component['normalized_weight'] = normalized_weight
    
    return psp

def weighted_vector_merge(vector1, vector2, merge_weight):
    """加权向量融合"""
    import numpy as np
    
    # 限制merge_weight在合理范围内
    merge_weight = max(0.1, min(1.0, merge_weight))
    
    # 加权平均
    merged_vector = (
        vector1 * (1 - merge_weight) + 
        vector2 * merge_weight
    )
    
    # 归一化
    norm = np.linalg.norm(merged_vector)
    if norm > 0:
        merged_vector = merged_vector / norm
    
    return merged_vector
```

## PSP分层更新策略

### 核心记忆层更新
```python
def update_core_memory(psp, new_intents):
    """更新核心记忆层"""
    core_memory = psp['core_memory']
    
    for intent in new_intents:
        if intent['type'] == 'value_system':
            # 价值观更新需要谨慎
            if intent['confidence'] > 0.9:
                core_memory['value_system'] = merge_values(
                    core_memory['value_system'], 
                    intent
                )
        
        elif intent['type'] == 'cognitive_pattern':
            # 认知模式更新
            core_memory['cognitive_patterns'] = update_cognitive_patterns(
                core_memory['cognitive_patterns'],
                intent
            )
    
    return core_memory
```

### 工作记忆层更新
```python
def update_working_memory(psp, new_intents):
    """更新工作记忆层"""
    working_memory = psp['working_memory']
    
    # 工作记忆更新频率较高
    for intent in new_intents:
        if intent['type'] == 'priority':
            working_memory['priority_rules'] = update_priorities(
                working_memory['priority_rules'],
                intent
            )
        
        elif intent['type'] == 'active_context':
            working_memory['active_context'] = update_active_context(
                working_memory['active_context'],
                intent
            )
    
    return working_memory
```

### 学习记忆层更新
```python
def update_learning_memory(psp, feedback):
    """基于用户反馈更新学习记忆层"""
    learning_memory = psp['learning_memory']
    
    if feedback['type'] == 'success':
        # 记录成功模式
        learning_memory['success_patterns'].append({
            'pattern': feedback['pattern'],
            'timestamp': feedback['timestamp'],
            'context': feedback['context']
        })
    
    elif feedback['type'] == 'error':
        # 记录错误修正
        learning_memory['error_corrections'].append({
            'error': feedback['error'],
            'correction': feedback['correction'],
            'timestamp': feedback['timestamp']
        })
    
    return learning_memory
```

## 向量匹配算法

### 相似度计算
```python
def calculate_similarity(intent, psp_component):
    """计算意图与PSP组件的相似度"""
    # 余弦相似度
    intent_vector = intent['embedding']
    component_vector = psp_component['embedding']
    
    similarity = cosine_similarity(intent_vector, component_vector)
    
    # 考虑时间衰减
    time_decay = calculate_time_decay(intent['timestamp'])
    
    # 考虑置信度
    confidence_weight = intent['confidence']
    
    # 考虑用户注意力权重
    attention_weight = intent.get('attention_weight', 0.5)
    
    final_similarity = similarity * time_decay * confidence_weight * attention_weight
    
    return final_similarity
```

### 聚类算法
```python
def cluster_intents(intents, method='hdbscan'):
    """对意图进行聚类"""
    if method == 'hdbscan':
        # 使用HDBSCAN进行密度聚类
        clusterer = HDBSCAN(
            min_cluster_size=3,
            min_samples=2,
            metric='cosine'
        )
        
        vectors = [intent['embedding'] for intent in intents]
        cluster_labels = clusterer.fit_predict(vectors)
        
        # 组织聚类结果
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(intents[i])
        
        return clusters
```

## 验证和反馈机制

### 用户反馈收集
```python
def collect_user_feedback(psp_prediction, user_response):
    """收集用户反馈"""
    feedback = {
        'timestamp': datetime.now().isoformat(),
        'psp_component': psp_prediction['component'],
        'prediction': psp_prediction['prediction'],
        'user_response': user_response,
        'accuracy': calculate_accuracy(psp_prediction, user_response)
    }
    
    return feedback
```

### 反馈驱动的更新
```python
def feedback_driven_update(psp, feedback_history):
    """基于反馈历史更新PSP"""
    # 分析反馈模式
    feedback_patterns = analyze_feedback_patterns(feedback_history)
    
    # 识别需要调整的PSP组件
    components_to_adjust = identify_components_to_adjust(feedback_patterns)
    
    # 调整PSP组件
    for component_id in components_to_adjust:
        adjustment = calculate_adjustment(component_id, feedback_patterns)
        psp[component_id] = apply_adjustment(psp[component_id], adjustment)
    
    return psp
```

## 性能优化

### 批量处理
```python
def batch_psp_update(hinata_batch, current_psp):
    """批量更新PSP"""
    # 批量向量化
    embeddings = batch_vectorize(hinata_batch)
    
    # 批量模式识别
    patterns = batch_pattern_recognition(embeddings)
    
    # 批量意图提取
    intents = batch_intent_extraction(patterns)
    
    # 批量PSP更新
    updated_psp = batch_psp_matching(intents, current_psp)
    
    return updated_psp
```

### 缓存机制
```python
class PSPCache:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1小时
    
    def get_cached_psp(self, user_id):
        """获取缓存的PSP"""
        if user_id in self.cache:
            cached_psp, timestamp = self.cache[user_id]
            if time.time() - timestamp < self.cache_ttl:
                return cached_psp
        return None
    
    def cache_psp(self, user_id, psp):
        """缓存PSP"""
        self.cache[user_id] = (psp, time.time())
```

## 监控和指标

### 关键指标
```python
def track_psp_metrics():
    """跟踪PSP相关指标"""
    metrics = {
        'update_frequency': calculate_update_frequency(),
        'similarity_scores': track_similarity_scores(),
        'user_feedback_accuracy': track_feedback_accuracy(),
        'pattern_detection_rate': track_pattern_detection(),
        'intent_extraction_confidence': track_intent_confidence()
    }
    
    return metrics
```

### 性能监控
```python
def monitor_psp_performance():
    """监控PSP性能"""
    performance_metrics = {
        'processing_time': measure_processing_time(),
        'memory_usage': measure_memory_usage(),
        'vector_search_speed': measure_vector_search_speed(),
        'update_latency': measure_update_latency()
    }
    
    return performance_metrics
```

## 安全考虑

### 数据隐私
- PSP数据本地加密存储
- 用户授权机制
- 数据脱敏处理
- 审计日志记录

### 更新安全
- 版本控制机制
- 回滚能力
- 更新验证
- 异常处理

## 配置参数

### 更新阈值
```python
PSP_UPDATE_CONFIG = {
    'similarity_threshold': 0.7,
    'confidence_threshold': 0.8,
    'update_frequency': 'realtime',
    'batch_size': 100,
    'cache_ttl': 3600,
    'max_psp_size': 10000
}
```

### 算法参数
```python
ALGORITHM_CONFIG = {
    'embedding_dimension': 768,
    'clustering_method': 'hdbscan',
    'similarity_metric': 'cosine',
    'time_decay_factor': 0.95
}
```

这个PSP迭代机制设计确保了系统能够持续学习和适应用户的真实需求，通过向量化匹配和分层更新策略，实现了个性化体验的持续优化。 