# ByenatOS Application Development Guide

## Core Philosophy: Clear Responsibility Division

### 🎯 ByenatOS Responsibilities (You Don't Need to Worry About)
- System kernel and hardware management
- HiNATA data processing and PSP generation
- Secure storage of personalized data
- Providing API services for Apps

### 🎨 Your App's Responsibilities (Focus Here)
- **User Interface** - All UI/UX design and implementation
- **Business Logic Processing** - Core functionality of the application
- **Online AI Calls** - Calling GPT, Claude and other online large models
- **HiNATA Data Generation** - Converting user behavior to HiNATA format

## Standard Development Pattern

### 📱 Typical App Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Your App                               │
├─────────────────────────────────────────────────────────────┤
│  User Interface Layer (Your Responsibility)                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐   │
│  │  Chat UI    │ Settings    │ History     │ User Profile│   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer (Your Responsibility)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Process user input           • Format output display  │ │
│  │ • Call online AI services      • Manage app state       │ │
│  │ • Generate HiNATA data        • Handle errors/exceptions│ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ByenatOS API Layer (System Provided)                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • Get PSP data                • Submit HiNATA data     │ │
│  │ • System config interface     • Performance monitoring  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Development Flow Examples

### 🔄 ChatBox App Development Flow

#### 1. User Sends Message
```typescript
// User inputs message in your chat interface
function handleUserMessage(userInput: string) {
    // 1. Display user message (Your UI logic)
    addMessageToChat({
        role: 'user',
        content: userInput,
        timestamp: new Date()
    });
    
    // 2. Call byenatOS to get PSP
    const psp = await byenatOS.api.getPSP();
    
    // 3. Build request to send to online AI
    const aiRequest = {
        messages: [...chatHistory, {role: 'user', content: userInput}],
        systemPrompt: psp,  // Use personalized prompt from byenatOS
        model: 'gpt-4'
    };
    
    // 4. Call online AI (Your business logic)
    const aiResponse = await openai.chat.completions.create(aiRequest);
    
    // 5. Display AI response (Your UI logic)
    addMessageToChat({
        role: 'assistant', 
        content: aiResponse.choices[0].message.content,
        timestamp: new Date()
    });
    
    // 6. Generate HiNATA data and submit to byenatOS
    const hinataData = {
        id: generateId(),
        timestamp: new Date().toISOString(),
        source: 'chatbox_app',
        highlight: userInput,  // User's question
        note: aiResponse.choices[0].message.content,  // AI's response
        address: 'chatbox://conversation/' + conversationId,
        tags: ['conversation', 'ai_chat'],
        access: 'private'
    };
    
    await byenatOS.api.submitHiNATA(hinataData);
}
```

#### 2. HiNATA Data Processing (byenatOS automatically processes)
```
User Conversation → HiNATA Data → byenatOS Local AI Analysis → PSP Update
```

#### 3. Next Conversation More Personalized
```typescript
// Next time user converses, the obtained PSP already contains more personalized information
const updatedPSP = await byenatOS.api.getPSP();
// PSP might now include:
// "User prefers concise answers, often asks technical questions, very interested in AI..."
```

### 📝 Notes App Development Flow

#### 1. User Records Note
```typescript
function saveNote(noteContent: string, highlights: string[]) {
    // 1. Save to app database (Your business logic)
    const note = await notesDB.save({
        content: noteContent,
        highlights: highlights,
        createdAt: new Date()
    });
    
    // 2. Generate HiNATA data
    const hinataData = {
        id: `note_${note.id}`,
        timestamp: new Date().toISOString(),
        source: 'notes_app',
        highlight: highlights.join(', '),  // User highlighted content
        note: noteContent,  // Complete note content
        address: `notes://note/${note.id}`,
        tags: ['notes', 'user_content', ...extractTags(noteContent)],
        access: 'private'
    };
    
    // 3. Submit to byenatOS for personalized analysis
    await byenatOS.api.submitHiNATA(hinataData);
    
    // 4. Update UI display (Your UI logic)
    updateNotesListUI();
}
```

## API Reference

### 🔌 ByenatOS API

```typescript
interface ByenatOSAPI {
    // PSP related
    getPSP(): Promise<string>;
    getPSPByCategory(category: 'core_memory' | 'working_memory' | 'learning_memory' | 'context_memory'): Promise<string>;
    
    // HiNATA data submission
    submitHiNATA(data: HiNATAData): Promise<boolean>;
    submitHiNATABatch(dataList: HiNATAData[]): Promise<boolean>;
    
    // System information
    getSystemStatus(): Promise<SystemStatus>;
    getProcessingStats(): Promise<ProcessingStats>;
}

interface HiNATAData {
    id: string;
    timestamp: string;
    source: string;      // Your App identifier
    highlight: string;   // Content user focuses on
    note: string;       // Detailed content or user notes
    address: string;    // Data source address
    tags: string[];     // Classification tags
    access: 'public' | 'private' | 'restricted';
}
```

### 🌐 Online AI Call Examples

```typescript
// OpenAI call example
async function callOpenAI(userMessage: string) {
    const psp = await byenatOS.api.getPSP();
    
    return await openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
            {role: 'system', content: psp},  // Use personalized prompt
            {role: 'user', content: userMessage}
        ]
    });
}

// Anthropic call example  
async function callClaude(userMessage: string) {
    const psp = await byenatOS.api.getPSP();
    
    return await anthropic.messages.create({
        model: 'claude-3-sonnet-20240229',
        system: psp,  // Use personalized prompt
        messages: [{role: 'user', content: userMessage}]
    });
}
```

## Best Practices

### ✅ Recommended Practices

1. **Submit HiNATA Data Promptly**
   ```typescript
   // Submit after each important user action
   await byenatOS.api.submitHiNATA(generateHiNATAData(userAction));
   ```

2. **Fully Utilize PSP**
   ```typescript
   // Use PSP for every AI call
   const psp = await byenatOS.api.getPSP();
   const response = await callAI(userInput, psp);
   ```

3. **Reasonable HiNATA Format**
   ```typescript
   // highlight: Content user focuses on
   // note: Detailed information or context
   {
       highlight: "AI Personalization Technology",
       note: "User is very interested in this topic, asked about technical implementation details"
   }
   ```

### ❌ Avoid These Mistakes

1. **Don't Try to Handle Personalization Logic Directly**
   ```typescript
   // Wrong: Analyze user preferences yourself
   const userPreference = analyzeUserBehavior(userData);
   
   // Correct: Use byenatOS PSP
   const psp = await byenatOS.api.getPSP();
   ```

2. **Don't Ignore HiNATA Data Submission**
   ```typescript
   // Wrong: Only call AI, don't submit data
   const response = await callAI(userInput);
   
   // Correct: Call AI then submit HiNATA data
   const response = await callAI(userInput, psp);
   await byenatOS.api.submitHiNATA(hinataData);
   ```

3. **Don't Store Personal Sensitive Data in App**
   ```typescript
   // Wrong: Analyze and store user privacy data in app
   localStorage.setItem('userPersonality', personalityData);
   
   // Correct: Let byenatOS handle it, get through API
   const psp = await byenatOS.api.getPSP();
   ```

## Example Projects

### 🚀 ChatBox App (Complete Example)

```typescript
class ChatBoxApp {
    private byenatOS: ByenatOSAPI;
    private conversationHistory: Message[] = [];
    
    constructor() {
        this.byenatOS = new ByenatOSAPI();
    }
    
    async sendMessage(userInput: string) {
        // 1. Add user message to interface
        this.addMessage('user', userInput);
        
        // 2. Get personalized prompt
        const psp = await this.byenatOS.getPSP();
        
        // 3. Build AI request
        const messages = [
            ...this.conversationHistory,
            {role: 'user', content: userInput}
        ];
        
        // 4. Call online AI
        const aiResponse = await this.callOpenAI(messages, psp);
        
        // 5. Display AI response
        this.addMessage('assistant', aiResponse);
        
        // 6. Submit HiNATA data
        await this.submitHiNATAData(userInput, aiResponse);
    }
    
    private async callOpenAI(messages: Message[], systemPrompt: string) {
        // Your AI call logic
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
        // Your UI update logic
        const message = {role, content, timestamp: new Date()};
        this.conversationHistory.push(message);
        this.updateChatUI(message);
    }
}
```

## Summary

Remember this simple division of labor:

- **byenatOS** = Backend butler, handles personalized data, you can't see it but it's always working
- **Your App** = Frontend reception, handles user interaction, calls AI services

This division lets you focus on business logic and user experience, while personalization capabilities are automatically provided by byenatOS!