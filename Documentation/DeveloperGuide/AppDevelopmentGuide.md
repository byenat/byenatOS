# ByenatOS 应用程序开发指南

## 核心理念：明确的职责分工

### 🎯 ByenatOS的职责（您无需关心）
- 系统内核和硬件管理
- HiNATA数据处理和PSP生成
- 个性化数据的安全存储
- 为Apps提供API服务

### 🎨 您的App的职责（重点关注）
- **用户交互界面** - 所有的UI/UX设计和实现
- **业务逻辑处理** - 应用的核心功能
- **在线AI调用** - 调用GPT、Claude等在线大模型
- **HiNATA数据生成** - 将用户行为转换为HiNATA格式

## 标准开发模式

### 📱 典型App架构

```
┌─────────────────────────────────────────────────────────────┐
│                      您的App                                  │
├─────────────────────────────────────────────────────────────┤
│  用户界面层 (您负责)                                          │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐   │
│  │   聊天界面   │   设置页面   │   历史记录   │   用户资料   │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  业务逻辑层 (您负责)                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • 处理用户输入              • 格式化输出显示              │ │
│  │ • 调用在线AI服务           • 管理应用状态                │ │
│  │ • 生成HiNATA数据          • 处理错误和异常              │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ByenatOS API层 (系统提供)                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • 获取PSP数据              • 提交HiNATA数据              │ │
│  │ • 系统配置接口            • 性能监控接口                │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 开发流程示例

### 🔄 ChatBox App开发流程

#### 1. 用户发送消息
```typescript
// 用户在您的聊天界面输入消息
function handleUserMessage(userInput: string) {
    // 1. 显示用户消息（您的UI逻辑）
    addMessageToChat({
        role: 'user',
        content: userInput,
        timestamp: new Date()
    });
    
    // 2. 调用byenatOS获取PSP
    const psp = await byenatOS.api.getPSP();
    
    // 3. 构建发送给在线AI的请求
    const aiRequest = {
        messages: [...chatHistory, {role: 'user', content: userInput}],
        systemPrompt: psp,  // 使用byenatOS提供的个性化提示
        model: 'gpt-4'
    };
    
    // 4. 调用在线AI（您的业务逻辑）
    const aiResponse = await openai.chat.completions.create(aiRequest);
    
    // 5. 显示AI回复（您的UI逻辑）
    addMessageToChat({
        role: 'assistant', 
        content: aiResponse.choices[0].message.content,
        timestamp: new Date()
    });
    
    // 6. 生成HiNATA数据提交给byenatOS
    const hinataData = {
        id: generateId(),
        timestamp: new Date().toISOString(),
        source: 'chatbox_app',
        highlight: userInput,  // 用户的问题
        note: aiResponse.choices[0].message.content,  // AI的回复
        address: 'chatbox://conversation/' + conversationId,
        tags: ['conversation', 'ai_chat'],
        access: 'private'
    };
    
    await byenatOS.api.submitHiNATA(hinataData);
}
```

#### 2. HiNATA数据处理（byenatOS自动处理）
```
用户对话 → HiNATA数据 → byenatOS本地AI分析 → PSP更新
```

#### 3. 下次对话更个性化
```typescript
// 下次用户对话时，获取到的PSP已经包含了更多个性化信息
const updatedPSP = await byenatOS.api.getPSP();
// PSP现在可能包含：
// "用户偏好简洁的回答，经常询问技术问题，对AI很感兴趣..."
```

### 📝 Notes App开发流程

#### 1. 用户记录笔记
```typescript
function saveNote(noteContent: string, highlights: string[]) {
    // 1. 保存到应用数据库（您的业务逻辑）
    const note = await notesDB.save({
        content: noteContent,
        highlights: highlights,
        createdAt: new Date()
    });
    
    // 2. 生成HiNATA数据
    const hinataData = {
        id: `note_${note.id}`,
        timestamp: new Date().toISOString(),
        source: 'notes_app',
        highlight: highlights.join(', '),  // 用户高亮的内容
        note: noteContent,  // 完整笔记内容
        address: `notes://note/${note.id}`,
        tags: ['notes', 'user_content', ...extractTags(noteContent)],
        access: 'private'
    };
    
    // 3. 提交给byenatOS进行个性化分析
    await byenatOS.api.submitHiNATA(hinataData);
    
    // 4. 更新UI显示（您的UI逻辑）
    updateNotesListUI();
}
```

## API参考

### 🔌 ByenatOS API

```typescript
interface ByenatOSAPI {
    // PSP相关
    getPSP(): Promise<string>;
    getPSPByCategory(category: 'core_memory' | 'working_memory' | 'learning_memory' | 'context_memory'): Promise<string>;
    
    // HiNATA数据提交
    submitHiNATA(data: HiNATAData): Promise<boolean>;
    submitHiNATABatch(dataList: HiNATAData[]): Promise<boolean>;
    
    // 系统信息
    getSystemStatus(): Promise<SystemStatus>;
    getProcessingStats(): Promise<ProcessingStats>;
}

interface HiNATAData {
    id: string;
    timestamp: string;
    source: string;      // 您的App标识
    highlight: string;   // 用户关注的重点内容
    note: string;       // 详细内容或用户备注
    address: string;    // 数据来源地址
    tags: string[];     // 分类标签
    access: 'public' | 'private' | 'restricted';
}
```

### 🌐 在线AI调用示例

```typescript
// OpenAI调用示例
async function callOpenAI(userMessage: string) {
    const psp = await byenatOS.api.getPSP();
    
    return await openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
            {role: 'system', content: psp},  // 使用个性化提示
            {role: 'user', content: userMessage}
        ]
    });
}

// Anthropic调用示例  
async function callClaude(userMessage: string) {
    const psp = await byenatOS.api.getPSP();
    
    return await anthropic.messages.create({
        model: 'claude-3-sonnet-20240229',
        system: psp,  // 使用个性化提示
        messages: [{role: 'user', content: userMessage}]
    });
}
```

## 最佳实践

### ✅ 推荐做法

1. **及时提交HiNATA数据**
   ```typescript
   // 用户每次重要操作后都提交
   await byenatOS.api.submitHiNATA(generateHiNATAData(userAction));
   ```

2. **充分利用PSP**
   ```typescript
   // 每次AI调用都使用PSP
   const psp = await byenatOS.api.getPSP();
   const response = await callAI(userInput, psp);
   ```

3. **合理的HiNATA格式**
   ```typescript
   // highlight: 用户重点关注的内容
   // note: 详细信息或上下文
   {
       highlight: "AI个性化技术",
       note: "用户对这个话题很感兴趣，询问了技术实现细节"
   }
   ```

### ❌ 避免的错误

1. **不要试图直接处理个性化逻辑**
   ```typescript
   // 错误：自己分析用户偏好
   const userPreference = analyzeUserBehavior(userData);
   
   // 正确：使用byenatOS的PSP
   const psp = await byenatOS.api.getPSP();
   ```

2. **不要忽略HiNATA数据提交**
   ```typescript
   // 错误：只调用AI，不提交数据
   const response = await callAI(userInput);
   
   // 正确：调用AI后提交HiNATA数据
   const response = await callAI(userInput, psp);
   await byenatOS.api.submitHiNATA(hinataData);
   ```

3. **不要在App中存储个人敏感数据**
   ```typescript
   // 错误：在App中分析和存储用户隐私数据
   localStorage.setItem('userPersonality', personalityData);
   
   // 正确：让byenatOS处理，通过API获取
   const psp = await byenatOS.api.getPSP();
   ```

## 示例项目

### 🚀 ChatBox App (完整示例)

```typescript
class ChatBoxApp {
    private byenatOS: ByenatOSAPI;
    private conversationHistory: Message[] = [];
    
    constructor() {
        this.byenatOS = new ByenatOSAPI();
    }
    
    async sendMessage(userInput: string) {
        // 1. 添加用户消息到界面
        this.addMessage('user', userInput);
        
        // 2. 获取个性化提示
        const psp = await this.byenatOS.getPSP();
        
        // 3. 构建AI请求
        const messages = [
            ...this.conversationHistory,
            {role: 'user', content: userInput}
        ];
        
        // 4. 调用在线AI
        const aiResponse = await this.callOpenAI(messages, psp);
        
        // 5. 显示AI回复
        this.addMessage('assistant', aiResponse);
        
        // 6. 提交HiNATA数据
        await this.submitHiNATAData(userInput, aiResponse);
    }
    
    private async callOpenAI(messages: Message[], systemPrompt: string) {
        // 您的AI调用逻辑
        const response = await openai.chat.completions.create({
            model: 'gpt-4',
            messages: [
                {role: 'system', content: systemPrompt},
                ...messages
            ]
        });
        return response.choices[0].message.content;
    }
    
    private async submitHiNATAData(userInput: string, aiResponse: string) {
        const hinataData: HiNATAData = {
            id: `chat_${Date.now()}`,
            timestamp: new Date().toISOString(),
            source: 'chatbox_app',
            highlight: userInput,
            note: aiResponse,
            address: `chatbox://conversation/${this.conversationId}`,
            tags: ['conversation', 'ai_chat'],
            access: 'private'
        };
        
        await this.byenatOS.submitHiNATA(hinataData);
    }
    
    private addMessage(role: string, content: string) {
        // 您的UI更新逻辑
        const message = {role, content, timestamp: new Date()};
        this.conversationHistory.push(message);
        this.updateChatUI(message);
    }
}
```

## 总结

记住这个简单的分工：

- **byenatOS** = 后台管家，处理个性化数据，您看不见但一直在工作
- **您的App** = 前台接待，处理用户交互，调用AI服务

这种分工让您专注于业务逻辑和用户体验，而个性化能力由byenatOS自动提供！