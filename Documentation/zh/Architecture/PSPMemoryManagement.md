# PSP内存管理架构设计

## 概述

基于"HiNATA≈虚拟硬盘，PSP≈虚拟内存"的核心洞察，本文档详细设计PSP内存管理器，确保在严格的prompt长度限制下最大化个性化效果。

## 设计原理

### 核心挑战

**Prompt长度限制**：
- GPT-4: 128K tokens (~96K中文字符)
- Claude-3: 200K tokens (~150K中文字符)  
- 其他模型: 通常4K-32K tokens

**设计目标**：
在有限的PSP"内存"空间内，从海量HiNATA"硬盘"数据中智能筛选出最有价值的个性化信息。

## PSP内存管理器架构

### 1. 分层内存架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PSP虚拟内存管理                           │
├─────────────────────────────────────────────────────────────┤
│ CoreMemory (20%)                                            │
│ • 长期稳定的核心个性化规则                                    │
│ • 更新频率: 天/周级别                                        │
│ • 示例: "用户偏好简洁直接的回答，避免冗长解释"                 │
├─────────────────────────────────────────────────────────────┤
│ WorkingMemory (40%)                                         │
│ • 当前活跃的工作上下文和偏好                                  │
│ • 更新频率: 小时级别                                         │
│ • 示例: "最近关注Python异步编程，正在进行Web开发项目"         │
├─────────────────────────────────────────────────────────────┤
│ ContextMemory (30%)                                         │
│ • 基于当前查询的动态相关信息                                  │
│ • 更新频率: 查询级别                                         │
│ • 示例: "用户刚刚查询过Django，可能需要相关框架对比"          │
├─────────────────────────────────────────────────────────────┤
│ BufferMemory (10%)                                          │
│ • 最新行为数据的实时缓冲区                                    │
│ • 更新频率: 实时                                            │
│ • 示例: "5分钟前在ReadItLater标记了机器学习文章"             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 智能内容筛选算法

#### 综合评分公式

```python
def calculate_psp_score(hinata_item, current_context):
    """计算HiNATA项目的PSP相关性评分"""
    
    # 重要性评分 (0-1)
    importance_score = calculate_importance_score(hinata_item)
    
    # 相关性评分 (0-1) 
    relevance_score = calculate_semantic_similarity(
        hinata_item, current_context
    )
    
    # 时效性评分 (0-1)
    freshness_score = calculate_freshness_score(hinata_item.timestamp)
    
    # 频率评分 (0-1)
    frequency_score = calculate_access_frequency(hinata_item.id)
    
    # 加权综合评分
    final_score = (
        importance_score * 0.3 +
        relevance_score * 0.35 + 
        freshness_score * 0.2 +
        frequency_score * 0.15
    )
    
    return final_score
```

#### 重要性评分机制

```python
def calculate_importance_score(hinata_item):
    """计算HiNATA项目的重要性评分"""
    score = 0.5  # 基础分
    
    # 用户明确标记
    if hinata_item.get('user_marked_important'):
        score += 0.3
    
    # 用户主动添加标签
    if len(hinata_item.get('tag', [])) > 2:
        score += 0.1
    
    # 用户添加了详细笔记
    note_length = len(hinata_item.get('note', ''))
    if note_length > 100:
        score += min(0.2, note_length / 1000)
    
    # 被多次访问
    access_count = get_access_count(hinata_item.id)
    if access_count > 1:
        score += min(0.1, access_count / 20)
    
    return min(1.0, score)
```

### 3. LRU替换策略

```python
class PSPMemoryManager:
    def __init__(self, max_tokens=50000):  # 预留50K tokens给PSP
        self.max_tokens = max_tokens
        self.core_memory = LRUCache(max_tokens * 0.2)
        self.working_memory = LRUCache(max_tokens * 0.4) 
        self.context_memory = LRUCache(max_tokens * 0.3)
        self.buffer_memory = LRUCache(max_tokens * 0.1)
        
    def update_psp(self, query_context):
        """基于查询上下文动态更新PSP内容"""
        
        # 1. 保持CoreMemory稳定
        # 核心记忆很少变化
        
        # 2. 更新WorkingMemory
        relevant_patterns = self.find_relevant_patterns(query_context)
        self.working_memory.update(relevant_patterns)
        
        # 3. 动态加载ContextMemory
        context_items = self.search_relevant_hinata(query_context)
        self.context_memory.clear()
        for item in context_items[:10]:  # 限制数量
            self.context_memory.put(item.id, item.compressed_content)
            
        # 4. 更新BufferMemory
        recent_items = self.get_recent_hinata(minutes=10)
        self.buffer_memory.update(recent_items)
    
    def generate_psp(self):
        """生成最终的PSP文本"""
        psp_parts = []
        
        # 按重要性顺序组装PSP
        psp_parts.append("## 核心个性化规则")
        psp_parts.extend(self.core_memory.get_all())
        
        psp_parts.append("## 当前工作上下文") 
        psp_parts.extend(self.working_memory.get_all())
        
        psp_parts.append("## 相关背景信息")
        psp_parts.extend(self.context_memory.get_all())
        
        psp_parts.append("## 最新行为数据")
        psp_parts.extend(self.buffer_memory.get_all())
        
        final_psp = "\n".join(psp_parts)
        
        # 确保不超过token限制
        return self.truncate_to_limit(final_psp)
```

### 4. 预测性加载机制

```python
class PSPPredictiveLoader:
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.pattern_recognizer = PatternRecognizer()
        
    def predict_relevant_content(self, query_context):
        """基于查询上下文预测相关内容"""
        
        # 分析查询模式
        query_patterns = self.pattern_recognizer.analyze_query(query_context)
        
        # 预测相关领域
        related_domains = self.predict_related_domains(query_patterns)
        
        # 预取相关HiNATA数据
        predicted_items = []
        for domain in related_domains:
            domain_items = self.search_domain_hinata(domain, limit=5)
            predicted_items.extend(domain_items)
        
        # 预加载到ContextMemory
        self.memory_manager.preload_context(predicted_items)
        
    def predict_related_domains(self, query_patterns):
        """基于查询模式预测相关领域"""
        # 使用语义向量和历史模式识别相关领域
        # 实现略...
        pass
```

### 5. 内容压缩优化

```python
class ContentCompressor:
    def __init__(self):
        self.summarizer = LocalSummarizer()  # 本地摘要模型
        
    def compress_hinata_content(self, hinata_item):
        """压缩HiNATA内容，提高信息密度"""
        
        original_note = hinata_item.get('note', '')
        highlight = hinata_item.get('highlight', '')
        
        # 对长内容进行智能摘要
        if len(original_note) > 200:
            # 提取关键信息
            key_points = self.extract_key_points(original_note)
            
            # 生成简洁摘要
            summary = self.summarizer.summarize(
                original_note, 
                max_length=100,
                focus_keywords=[highlight]
            )
            
            compressed_content = f"关键点: {', '.join(key_points)}\n摘要: {summary}"
        else:
            compressed_content = original_note
            
        return {
            'id': hinata_item['id'],
            'highlight': highlight,
            'compressed_content': compressed_content,
            'original_length': len(original_note),
            'compressed_length': len(compressed_content),
            'compression_ratio': len(compressed_content) / len(original_note)
        }
```

## 实现优先级

### 阶段一：基础内存管理器
- [x] 设计分层内存架构
- [ ] 实现基础的LRU替换算法
- [ ] 建立token计数和限制机制
- [ ] 实现基础的重要性评分

### 阶段二：智能筛选算法  
- [ ] 实现语义相似度计算
- [ ] 建立时效性评分机制
- [ ] 实现综合评分算法
- [ ] 优化内容筛选效果

### 阶段三：高级优化
- [ ] 实现预测性加载机制
- [ ] 集成本地摘要模型
- [ ] 建立压缩优化算法
- [ ] 实现自适应调优

### 阶段四：性能优化
- [ ] 优化内存使用效率
- [ ] 实现批量处理机制
- [ ] 建立性能监控指标
- [ ] 进行大规模测试验证

## 技术栈

### 核心组件
- **内存管理**: Python + Redis (LRU Cache)
- **语义计算**: Sentence-Transformers + FAISS
- **内容压缩**: 轻量级Transformer摘要模型
- **模式识别**: scikit-learn + 自定义算法

### 性能指标
- **PSP生成延迟**: < 100ms
- **内存使用效率**: > 80%
- **个性化准确率**: > 85%
- **token利用率**: > 90%

## 总结

通过将PSP视为"虚拟内存"并设计专门的内存管理器，我们能够在严格的prompt长度限制下最大化个性化效果。这个设计借鉴了操作系统内存管理的成熟理念，为byenatOS提供了一个可扩展、高效的个性化处理核心。

---

*这个设计体现了byenatOS作为"虚拟操作系统"的核心创新：将个性化AI处理抽象为内存管理问题，并提供系统级的解决方案。* 🧠