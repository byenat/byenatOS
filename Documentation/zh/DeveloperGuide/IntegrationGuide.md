# 开发者集成指南

## 概述

本指南详细介绍了如何将ByenatOS集成到您的应用中，为应用添加个性化AI能力。

## 快速集成（5分钟）

### 步骤1：安装SDK

```bash
# JavaScript/Node.js
npm install @byenatos/sdk

# Python
pip install byenatos-sdk
```

### 步骤2：初始化客户端

```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({
  apiKey: 'your_api_key'  // 免费获取
});
```

```python
from byenatos import ByenatOS

byenatOS = ByenatOS(api_key='your_api_key')
```

### 步骤3：添加AI功能

```javascript
// 为您的应用添加个性化AI聊天功能
async function addAIChat(userMessage) {
  // 自动获取用户memory信息
  const personalizedPrompt = await byenatOS.getPersonalizedPrompt();
  
  // 调用您现有的AI服务（OpenAI、Claude等）
  const response = await openai.chat.completions.create({
    messages: [
      { role: "system", content: personalizedPrompt },
      { role: "user", content: userMessage }
    ]
  });
  
  return response.choices[0].message.content;
}

// 使用示例
const aiResponse = await addAIChat("帮我分析今天的工作效率");
```

```python
# 为您的AI功能添加memory
async def enhance_ai_response(user_message):
    personalized_prompt = await byenatOS.get_personalized_prompt()
    
    # 使用您现有的AI服务
    response = await your_ai_service.chat(
        system_prompt=personalized_prompt,
        user_message=user_message
    )
    
    return response
```

## 高级集成

### HiNATA数据生成

ByenatOS通过HiNATA格式收集用户行为数据，您可以在应用中主动提交这些数据：

```javascript
// 提交用户行为数据
await byenatOS.hinata.submit({
  source: 'my-app',
  highlight: '用户关注的内容',
  note: '详细的上下文信息',
  tag: ['productivity', 'work'],
  access: 'private'
});
```

```python
# 提交HiNATA数据
byenatOS.hinata.submit({
    'source': 'my-app',
    'highlight': '用户关注的内容',
    'note': '详细的上下文信息',
    'tag': ['productivity', 'work'],
    'access': 'private'
})
```

### 获取个性化提示

```javascript
// 获取特定领域的个性化提示
const psp = await byenatOS.psp.get({
  domain: 'productivity',
  context: 'task_management',
  recent_activity: true
});
```

```python
# 获取个性化提示
psp = byenatOS.psp.get(
    domain='productivity',
    context='task_management',
    recent_activity=True
)
```

## 应用场景示例

### 日志应用集成

```javascript
// 日志应用示例
function saveJournalEntry(title, content, tags) {
  // 保存日志到应用数据库
  saveToDatabase({ title, content, tags });
  
  // 提交到ByenatOS
  byenatOS.hinata.submit({
    source: 'journal_app',
    highlight: title,
    note: content,
    tag: [...tags, 'journal', 'personal'],
    access: 'private'
  });
}

// AI助手功能
async function journalAI(question) {
  const psp = await byenatOS.psp.get({
    domain: 'productivity_and_reflection',
    include_recent_journals: true
  });
  
  return await openai.chat.completions.create({
    messages: [
      { role: "system", content: psp },
      { role: "user", content: question }
    ]
  });
}
```

### 阅读应用集成

```javascript
// ReadItLater应用示例
function saveArticle(url, title, content, userNote) {
  // 保存文章到应用数据库
  saveArticleToDatabase({ url, title, content, userNote });
  
  // 提交到ByenatOS
  byenatOS.hinata.submit({
    source: 'readitlater_app',
    highlight: title,
    note: content + '\n用户笔记: ' + userNote,
    address: url,
    tag: extractTags(content),
    access: 'private'
  });
}

// 智能推荐功能
async function recommendArticles(currentInterests) {
  const psp = await byenatOS.psp.get({
    domain: 'reading_preferences',
    include_reading_history: true
  });
  
  const recommendations = await aiService.getRecommendations(
    `${psp}\n当前兴趣: ${currentInterests}`
  );
  
  return recommendations;
}
```

## 配置选项

### API密钥配置

```javascript
const byenatOS = new ByenatOS({
  apiKey: 'your_api_key',
  endpoint: 'https://api.byenatos.org', // 可选
  timeout: 5000, // 可选，默认5000ms
  retries: 3 // 可选，默认3次
});
```

### 环境配置

```bash
# 开发环境
export BYENATOS_API_KEY=your_dev_api_key
export BYENATOS_ENDPOINT=https://dev-api.byenatos.org

# 生产环境
export BYENATOS_API_KEY=your_prod_api_key
export BYENATOS_ENDPOINT=https://api.byenatos.org
```

## 错误处理

```javascript
try {
  const psp = await byenatOS.getPersonalizedPrompt();
  // 使用PSP
} catch (error) {
  if (error.code === 'API_KEY_INVALID') {
    console.error('API密钥无效');
  } else if (error.code === 'RATE_LIMIT_EXCEEDED') {
    console.error('请求频率超限');
  } else {
    console.error('获取个性化提示失败:', error.message);
  }
  
  // 使用默认提示作为后备
  const fallbackPrompt = "你是一个有用的AI助手。";
}
```

## 性能优化

### 缓存策略

```javascript
// 缓存PSP以减少API调用
let cachedPSP = null;
let lastUpdate = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5分钟

async function getCachedPSP() {
  const now = Date.now();
  
  if (!cachedPSP || (now - lastUpdate) > CACHE_DURATION) {
    cachedPSP = await byenatOS.getPersonalizedPrompt();
    lastUpdate = now;
  }
  
  return cachedPSP;
}
```

### 批量提交

```javascript
// 批量提交HiNATA数据以提高性能
const hinataBatch = [];

function addToBatch(data) {
  hinataBatch.push(data);
  
  if (hinataBatch.length >= 10) {
    submitBatch();
  }
}

async function submitBatch() {
  if (hinataBatch.length > 0) {
    await byenatOS.hinata.submitBatch(hinataBatch);
    hinataBatch.length = 0; // 清空数组
  }
}
```

## 最佳实践

### 1. 数据质量
- 确保提交的HiNATA数据准确反映用户行为
- 使用有意义的highlight和note
- 正确设置access权限

### 2. 用户体验
- 在后台异步提交数据，不阻塞用户操作
- 提供加载状态和错误处理
- 保持AI响应的流畅性

### 3. 隐私保护
- 只提交必要的用户数据
- 遵循数据最小化原则
- 提供用户控制选项

### 4. 性能考虑
- 使用缓存减少API调用
- 批量提交数据
- 实现适当的重试机制

## 测试指南

### 单元测试

```javascript
// 测试PSP获取
describe('ByenatOS Integration', () => {
  it('should get personalized prompt', async () => {
    const psp = await byenatOS.getPersonalizedPrompt();
    expect(psp).toBeDefined();
    expect(typeof psp).toBe('string');
  });
  
  it('should submit HiNATA data', async () => {
    const result = await byenatOS.hinata.submit({
      source: 'test-app',
      highlight: 'Test content',
      note: 'Test note'
    });
    expect(result.success).toBe(true);
  });
});
```

### 集成测试

```javascript
// 测试完整的AI交互流程
describe('AI Interaction Flow', () => {
  it('should enhance AI response with personalization', async () => {
    // 提交测试数据
    await byenatOS.hinata.submit({
      source: 'test-app',
      highlight: '测试内容',
      note: '测试笔记'
    });
    
    // 获取个性化提示
    const psp = await byenatOS.getPersonalizedPrompt();
    
    // 模拟AI调用
    const response = await mockAIService.chat({
      systemPrompt: psp,
      userMessage: '测试问题'
    });
    
    expect(response).toContain('个性化');
  });
});
```

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查API密钥是否正确
   - 确认密钥是否已激活

2. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置

3. **数据格式错误**
   - 验证HiNATA数据格式
   - 检查必需字段

4. **性能问题**
   - 检查缓存设置
   - 优化API调用频率

### 调试模式

```javascript
const byenatOS = new ByenatOS({
  apiKey: 'your_api_key',
  debug: true // 启用调试模式
});
```

## 支持资源

- 📚 [完整API文档](https://docs.byenatos.org/api)
- 💬 [GitHub讨论](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord社区](https://discord.gg/byenatos)
- 📧 [邮件支持](mailto:support@byenatos.org) 