# PSP Memory Management Architecture Design

## Overview

Based on the core insight of "HiNATA ≈ Virtual Hard Drive, PSP ≈ Virtual Memory", this document details the design of the PSP memory manager, ensuring maximum personalized effects under strict prompt length limitations.

## Design Principles

### Core Challenges

**Prompt Length Limitations**:
- GPT-4: 128K tokens (~96K Chinese characters)
- Claude-3: 200K tokens (~150K Chinese characters)
- Other models: Usually 4K-32K tokens

**Design Goals**:
Intelligently filter the most valuable personalized information from massive HiNATA "hard drive" data within limited PSP "memory" space.

## PSP Memory Manager Architecture

### 1. Layered Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PSP Virtual Memory Management            │
├─────────────────────────────────────────────────────────────┤
│ CoreMemory (20%)                                            │
│ • Long-term stable core personalization rules               │
│ • Update frequency: Daily/Weekly level                      │
│ • Example: "User prefers concise direct answers, avoids lengthy explanations" │
├─────────────────────────────────────────────────────────────┤
│ WorkingMemory (40%)                                         │
│ • Current active work context and preferences               │
│ • Update frequency: Hourly level                            │
│ • Example: "Recently focused on Python async programming, working on Web development project" │
├─────────────────────────────────────────────────────────────┤
│ ContextMemory (30%)                                         │
│ • Dynamic relevant information based on current query       │
│ • Update frequency: Query level                             │
│ • Example: "User just queried Django, may need related framework comparison" │
├─────────────────────────────────────────────────────────────┤
│ BufferMemory (10%)                                          │
│ • Real-time buffer for latest behavioral data              │
│ • Update frequency: Real-time                               │
│ • Example: "5 minutes ago marked machine learning article in ReadItLater" │
└─────────────────────────────────────────────────────────────┘
```

### 2. Intelligent Content Filtering Algorithm

#### Comprehensive Scoring Formula

```python
def calculate_psp_score(hinata_item, current_context):
    """Calculate PSP relevance score for HiNATA item"""
    
    # Importance score (0-1)
    importance_score = calculate_importance_score(hinata_item)
    
    # Relevance score (0-1)
    relevance_score = calculate_semantic_similarity(
        hinata_item, current_context
    )
    
    # Freshness score (0-1)
    freshness_score = calculate_freshness_score(hinata_item.timestamp)
    
    # Frequency score (0-1)
    frequency_score = calculate_access_frequency(hinata_item.id)
    
    # Weighted comprehensive score
    final_score = (
        importance_score * 0.3 +
        relevance_score * 0.35 +
        freshness_score * 0.2 +
        frequency_score * 0.15
    )
    
    return final_score
```

#### Importance Scoring Mechanism

```python
def calculate_importance_score(hinata_item):
    """Calculate importance score for HiNATA item"""
    score = 0.5  # Base score
    
    # User explicitly marked
    if hinata_item.get('user_marked_important'):
        score += 0.3
    
    # User actively added tags
    if len(hinata_item.get('tag', [])) > 2:
        score += 0.1
    
    # User added detailed notes
    note_length = len(hinata_item.get('note', ''))
    if note_length > 100:
        score += min(0.2, note_length / 1000)
    
    # 被多次访问
    access_count = get_access_count(hinata_item.id)
    if access_count > 1:
        score += min(0.1, access_count / 20)
    
    return min(1.0, score)
```

### 3. LRU Replacement Strategy

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

### 4. Predictive Loading Mechanism

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

### 5. Content Compression Optimization

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

## Implementation Priorities

### Phase 1: Basic Memory Manager
- [x] Design layered memory architecture
- [ ] Implement basic LRU replacement algorithm
- [ ] Establish token counting and limit mechanisms
- [ ] Implement basic importance scoring

### Phase 2: Intelligent Filtering Algorithm  
- [ ] Implement semantic similarity calculation
- [ ] Establish freshness scoring mechanism
- [ ] Implement comprehensive scoring algorithm
- [ ] Optimize content filtering effect

### Phase 3: Advanced Optimization
- [ ] Implement predictive loading mechanism
- [ ] Integrate local summarization model
- [ ] Establish compression optimization algorithm
- [ ] Implement adaptive tuning

### Phase 4: Performance Optimization
- [ ] Optimize memory usage efficiency
- [ ] Implement batch processing mechanism
- [ ] Establish performance monitoring metrics
- [ ] Conduct large-scale testing validation

## Technology Stack

### Core Components
- **Memory Management**: Python + Redis (LRU Cache)
- **Semantic Calculation**: Sentence-Transformers + FAISS
- **Content Compression**: Lightweight Transformer summarization model
- **Pattern Recognition**: scikit-learn + Custom Algorithm

### Performance Metrics
- **PSP Generation Latency**: < 100ms
- **Memory Usage Efficiency**: > 80%
- **Personalization Accuracy**: > 85%
- **Token Utilization**: > 90%

## Summary

By treating PSP as "virtual memory" and designing a dedicated memory manager, we can maximize personalized effects under strict prompt length limitations. This design draws upon the mature concepts of operating system memory management, providing a scalable and efficient personalized processing core for byenatOS.

---

*This design embodies the core innovation of byenatOS as a "virtual operating system": abstracting personalized AI processing into a memory management problem and providing a system-level solution.* 🧠