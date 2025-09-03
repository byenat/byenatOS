# ByenatOS API 使用示例

## 概述

本文档提供ByenatOS核心API的详细使用示例，展示如何正确获取和使用上下文组件。

## 重要概念

### 上下文构建原理

```
完整上下文 = PSP个性化组件 + HiNATA知识组件 + 用户问题 + [其他信息]
```

- **PSP个性化组件**：让AI响应更符合用户特点
- **HiNATA知识组件**：为AI提供相关知识和背景信息  
- **用户问题**：当前需要解决的具体问题

**byenatOS职责**：提供高质量的PSP和HiNATA组件
**APP职责**：根据需求组装完整上下文，与AI模型交互

## 核心API接口

### 1. 问题相关HiNATA检索API（核心新增功能）

#### 接口信息
- **端点**: `POST /api/hinata/query-relevant`
- **权限**: `HINATA_QUERY`
- **用途**: 获取上下文的知识组件，根据问题检索相关HiNATA内容

#### 请求示例

```javascript
// JavaScript SDK
const response = await byenatOS.queryRelevantHiNATA({
  user_id: 'user_123',
  question: '如何提高编程效率？',
  limit: 5,
  min_relevance_score: 0.6,
  include_metadata: true
});

console.log('知识组件:', response.relevant_hinata);
```

```python
# Python SDK
response = await byenatos.query_relevant_hinata(
    user_id='user_123',
    question='如何提高编程效率？',
    limit=5,
    min_relevance_score=0.6,
    include_metadata=True
)

print('知识组件:', response.relevant_hinata)
```

#### 响应示例

```json
{
  "user_id": "user_123",
  "question": "如何提高编程效率？",
  "relevant_hinata": [
    {
      "hinata_id": "hinata_20241201_001",
      "content_summary": "使用IDE快捷键可以显著提高编程速度...",
      "relevance_score": 0.92,
      "metadata": {
        "source": "programming_blog",
        "timestamp": "2024-11-28T10:30:00Z",
        "attention_weight": 0.85,
        "quality_score": 0.88
      }
    },
    {
      "hinata_id": "hinata_20241130_005",
      "content_summary": "代码重构的最佳实践包括...",
      "relevance_score": 0.87,
      "metadata": {
        "source": "tech_article",
        "timestamp": "2024-11-30T14:20:00Z",
        "attention_weight": 0.78,
        "quality_score": 0.91
      }
    }
  ],
  "total_results": 2,
  "query_time": 0.15
}
```

### 2. 个性化增强API

#### 接口信息
- **端点**: `POST /api/enhancement/personalized`
- **权限**: `ENHANCEMENT_ACCESS`
- **用途**: 获取构建完整上下文所需的两个核心组件（PSP个性化组件 + HiNATA知识组件）

#### 请求示例

```javascript
const response = await byenatOS.getPersonalizedEnhancement({
  user_id: 'user_123',
  question: '帮我制定学习计划',
  context_limit: 3,
  include_psp_details: false
});

console.log('PSP个性化组件:', response.personalized_prompt);
console.log('HiNATA知识组件:', response.knowledge_components);
```

#### 响应示例

```json
{
  "user_id": "user_123",
  "question": "帮我制定学习计划",
  "personalized_prompt": "You are an AI assistant that provides personalized responses. User interests: programming, machine learning, system design. Learning style: hands-on practice, visual examples. Communication style: structured, detailed. Use the provided knowledge context to give accurate answers. Combine your knowledge with the user's personalization preferences.",
  "knowledge_components": [
    {
      "content_summary": "有效的学习计划应该包含明确的目标设定...",
      "relevance_score": 0.89,
      "source": "learning_guide",
      "timestamp": "2024-11-25T09:15:00Z"
    }
  ],
  "psp_summary": {},
  "processing_time": 0.25
}
```

### 3. HiNATA提交API

#### 接口信息
- **端点**: `POST /api/hinata/submit`
- **权限**: `HINATA_SUBMIT`
- **用途**: 提交HiNATA数据批次供系统处理

#### 请求示例

```javascript
const response = await byenatOS.submitHiNATA({
  app_id: 'browser_extension',
  user_id: 'user_123',
  hinata_batch: [
    {
      id: 'hinata_20241201_001',
      timestamp: '2024-12-01T10:30:00Z',
      source: 'web_browser',
      highlight: '深度学习是机器学习的一个子领域',
      note: '这是一个重要的概念，需要深入理解',
      address: 'https://example.com/ml-guide#deep-learning',
      tag: ['机器学习', '深度学习'],
      access: 'private',
      raw_data: {
        page_title: '机器学习入门指南',
        selection_context: '周围文本上下文...'
      }
    }
  ]
});
```

### 4. PSP上下文查询API

#### 接口信息
- **端点**: `POST /api/psp/context`
- **权限**: `PSP_READ`
- **用途**: 获取用户的个性化系统提示词上下文

#### 请求示例

```javascript
const response = await byenatOS.getPSPContext({
  user_id: 'user_123',
  current_request: '我想学习新技术',
  include_details: false,
  context_type: 'prompt'
});
```

## 使用场景示例

### 场景1: 智能问答应用

```javascript
// 智能问答应用集成示例
class SmartQAApp {
  constructor(apiKey) {
    this.byenatOS = new ByenatOS({ apiKey });
  }
  
  async answerQuestion(userId, question) {
    try {
      // 方案1: 仅使用知识组件（HiNATA）
      const hinataResponse = await this.byenatOS.queryRelevantHiNATA({
        user_id: userId,
        question: question,
        limit: 5
      });
      
      // 构建简单上下文（仅包含知识组件）
      const knowledgeContext = hinataResponse.relevant_hinata
        .map(item => item.content_summary)
        .join('\n');
      
      // 构建完整上下文并调用AI模型
      const fullContext = {
        system: "You are a helpful AI assistant. Use the provided knowledge to answer accurately.",
        knowledge: knowledgeContext,
        user: question
      };
      
      return await this.callAIModel(fullContext);
      
    } catch (error) {
      console.error('问答失败:', error);
      throw error;
    }
  }
  
  async answerQuestionPersonalized(userId, question) {
    try {
      // 方案2: 使用完整的上下文组件（PSP + HiNATA）
      const enhancementResponse = await this.byenatOS.getPersonalizedEnhancement({
        user_id: userId,
        question: question,
        context_limit: 5
      });
      
      // 构建完整上下文
      const fullContext = {
        system: enhancementResponse.personalized_prompt,  // PSP个性化组件
        knowledge: this.formatKnowledgeComponents(enhancementResponse.knowledge_components),  // HiNATA知识组件
        user: question
      };
      
      return await this.callAIModel(fullContext);
      
    } catch (error) {
      console.error('个性化问答失败:', error);
      throw error;
    }
  }
  
  formatKnowledgeComponents(components) {
    // 将HiNATA知识组件格式化为上下文字符串
    return components
      .map(item => `[${item.source}] ${item.content_summary}`)
      .join('\n\n');
  }
  
  async callAIModel(fullContext) {
    // 使用完整上下文调用AI模型
    return await yourPreferredAI.chat({
      messages: [
        { role: "system", content: fullContext.system },
        { role: "user", content: `Context: ${fullContext.knowledge}\n\nQuestion: ${fullContext.user}` }
      ]
    });
  }
}
```

### 场景2: 学习助手应用

```javascript
// 学习助手应用集成示例
class LearningAssistant {
  constructor(apiKey) {
    this.byenatOS = new ByenatOS({ apiKey });
  }
  
  async generateStudyPlan(userId, subject) {
    // 获取用户在该主题的相关学习记录
    const relevantHiNATA = await this.byenatOS.queryRelevantHiNATA({
      user_id: userId,
      question: `${subject} 学习计划`,
      limit: 10
    });
    
    // 分析用户的学习偏好和历史
    const userLearningPattern = this.analyzeLearningPattern(relevantHiNATA.relevant_hinata);
    
    // 获取个性化建议
    const enhancement = await this.byenatOS.getPersonalizedEnhancement({
      user_id: userId,
      question: `为${subject}制定个性化学习计划`,
      context_limit: 5
    });
    
    return {
      studyPlan: enhancement.personalized_prompt,
      relevantResources: enhancement.relevant_context,
      learningPattern: userLearningPattern
    };
  }
  
  analyzeLearningPattern(hinataList) {
    // 分析用户的学习模式
    const sources = hinataList.map(item => item.metadata?.source);
    const topics = hinataList.map(item => item.content_summary);
    
    return {
      preferredSources: [...new Set(sources)],
      focusAreas: this.extractTopics(topics),
      studyFrequency: this.calculateFrequency(hinataList)
    };
  }
}
```

### 场景3: 内容推荐系统

```javascript
// 内容推荐系统集成示例
class ContentRecommendationSystem {
  constructor(apiKey) {
    this.byenatOS = new ByenatOS({ apiKey });
  }
  
  async recommendContent(userId, currentInterest) {
    try {
      // 获取用户相关的HiNATA内容
      const hinataResponse = await this.byenatOS.queryRelevantHiNATA({
        user_id: userId,
        question: currentInterest,
        limit: 15,
        min_relevance_score: 0.4
      });
      
      // 基于HiNATA内容生成推荐
      const recommendations = await this.generateRecommendations(
        hinataResponse.relevant_hinata,
        currentInterest
      );
      
      return {
        recommendations: recommendations,
        basedOnHistory: hinataResponse.relevant_hinata.length,
        confidence: this.calculateConfidence(recommendations)
      };
      
    } catch (error) {
      console.error('内容推荐失败:', error);
      return { recommendations: [], error: error.message };
    }
  }
  
  async generateRecommendations(hinataList, interest) {
    // 分析用户历史偏好
    const userPreferences = this.extractPreferences(hinataList);
    
    // 获取个性化推荐提示
    const enhancement = await this.byenatOS.getPersonalizedEnhancement({
      user_id: userId,
      question: `基于我的兴趣推荐${interest}相关内容`,
      context_limit: 8
    });
    
    // 使用AI生成推荐列表
    return await this.callRecommendationAI({
      userPreferences: userPreferences,
      currentInterest: interest,
      personalizedPrompt: enhancement.personalized_prompt,
      context: enhancement.relevant_context
    });
  }
}
```

## 错误处理

### 常见错误码

```javascript
// 错误处理示例
try {
  const response = await byenatOS.queryRelevantHiNATA({
    user_id: 'user_123',
    question: '测试问题'
  });
} catch (error) {
  switch (error.status) {
    case 401:
      console.error('API密钥无效');
      break;
    case 403:
      console.error('权限不足，需要HINATA_QUERY权限');
      break;
    case 429:
      console.error('请求频率过高，请稍后重试');
      break;
    case 500:
      console.error('服务器内部错误:', error.message);
      break;
    default:
      console.error('未知错误:', error);
  }
}
```

## 性能优化建议

### 1. 批量处理

```javascript
// 批量处理HiNATA提交
const batchSubmit = async (hinataList) => {
  const batchSize = 50;
  const results = [];
  
  for (let i = 0; i < hinataList.length; i += batchSize) {
    const batch = hinataList.slice(i, i + batchSize);
    const result = await byenatOS.submitHiNATA({
      app_id: 'your_app',
      user_id: 'user_123',
      hinata_batch: batch
    });
    results.push(result);
  }
  
  return results;
};
```

### 2. 缓存策略

```javascript
// 实现本地缓存以减少API调用
class HiNATACache {
  constructor(ttl = 300000) { // 5分钟TTL
    this.cache = new Map();
    this.ttl = ttl;
  }
  
  async queryWithCache(userId, question) {
    const cacheKey = `${userId}:${question}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.ttl) {
      return cached.data;
    }
    
    const result = await byenatOS.queryRelevantHiNATA({
      user_id: userId,
      question: question
    });
    
    this.cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });
    
    return result;
  }
}
```

## 最佳实践

### 1. API密钥管理

```javascript
// 安全的API密钥管理
class SecureByenatOSClient {
  constructor() {
    // 从环境变量或安全存储获取API密钥
    this.apiKey = process.env.BYENATOS_API_KEY;
    this.client = new ByenatOS({ apiKey: this.apiKey });
  }
  
  // 封装API调用，添加统一的错误处理和日志
  async safeQuery(method, params) {
    try {
      const startTime = Date.now();
      const result = await this.client[method](params);
      const duration = Date.now() - startTime;
      
      console.log(`API调用成功: ${method}, 耗时: ${duration}ms`);
      return result;
    } catch (error) {
      console.error(`API调用失败: ${method}`, error);
      throw error;
    }
  }
}
```

### 2. 用户隐私保护

```javascript
// 隐私保护的数据处理
class PrivacyAwareHiNATAProcessor {
  constructor(apiKey) {
    this.byenatOS = new ByenatOS({ apiKey });
  }
  
  async processUserData(userId, rawData) {
    // 数据脱敏处理
    const sanitizedData = this.sanitizeData(rawData);
    
    // 提交处理后的数据
    return await this.byenatOS.submitHiNATA({
      app_id: 'privacy_app',
      user_id: userId,
      hinata_batch: sanitizedData
    });
  }
  
  sanitizeData(data) {
    // 移除或脱敏敏感信息
    return data.map(item => ({
      ...item,
      highlight: this.removePII(item.highlight),
      note: this.removePII(item.note)
    }));
  }
  
  removePII(text) {
    // 移除个人识别信息
    return text
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[REDACTED]') // SSN
      .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]'); // Email
  }
}
```

---

**文档版本**: v1.0  
**创建时间**: 2024-12-01  
**更新时间**: 2024-12-01