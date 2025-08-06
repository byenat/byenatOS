# Quick Start Guide

## Overview

This guide will help you get started with ByenatOS in just 5 minutes. You'll learn how to integrate personalized AI capabilities into your application.

## Prerequisites

- Basic knowledge of JavaScript/Node.js or Python
- A ByenatOS API key (free)
- An existing application or project

## Step 1: Get Your API Key

1. Visit [developer.byenatos.org](https://developer.byenatos.org)
2. Create a free account
3. Generate your API key from the dashboard

## Step 2: Install the SDK

### JavaScript/Node.js
```bash
npm install @byenatos/sdk
```

### Python
```bash
pip install byenatos-sdk
```

## Step 3: Initialize the Client

### JavaScript/Node.js
```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({
  apiKey: 'your_api_key_here'
});
```

### Python
```python
from byenatos import ByenatOS

byenatOS = ByenatOS(api_key='your_api_key_here')
```

## Step 4: Add AI to Your App

### Basic Integration

```javascript
// Add personalized AI chat to your app
async function addAIChat(userMessage) {
  // Get personalized prompt automatically
  const personalizedPrompt = await byenatOS.getPersonalizedPrompt();
  
  // Use with any AI service (OpenAI, Claude, etc.)
  const response = await openai.chat.completions.create({
    messages: [
      { role: "system", content: personalizedPrompt },
      { role: "user", content: userMessage }
    ]
  });
  
  return response.choices[0].message.content;
}

// Usage example
const aiResponse = await addAIChat("Help me analyze today's work efficiency");
```

### Python Example
```python
async def enhance_ai_response(user_message):
    personalized_prompt = await byenatOS.get_personalized_prompt()
    
    # Use with your existing AI service
    response = await your_ai_service.chat(
        system_prompt=personalized_prompt,
        user_message=user_message
    )
    
    return response
```

## Step 5: Submit User Data (Optional)

To improve personalization, submit user behavior data:

```javascript
// Submit user behavior data
await byenatOS.hinata.submit({
  source: 'my-app',
  highlight: 'Content user focuses on',
  note: 'Detailed context information',
  tag: ['productivity', 'work'],
  access: 'private'
});
```

## Complete Example

Here's a complete example of a simple chat application:

```javascript
import { ByenatOS } from '@byenatos/sdk';

class PersonalizedChatApp {
  constructor(apiKey) {
    this.byenatOS = new ByenatOS({ apiKey });
  }

  async sendMessage(message) {
    try {
      // Get personalized prompt
      const personalizedPrompt = await this.byenatOS.getPersonalizedPrompt();
      
      // Submit user message for learning
      await this.byenatOS.hinata.submit({
        source: 'chat-app',
        highlight: message,
        note: 'User message in chat',
        tag: ['chat', 'interaction'],
        access: 'private'
      });

      // Get AI response with personalization
      const response = await this.getAIResponse(personalizedPrompt, message);
      
      return response;
    } catch (error) {
      console.error('Error:', error);
      return 'Sorry, I encountered an error.';
    }
  }

  async getAIResponse(systemPrompt, userMessage) {
    // Replace with your preferred AI service
    const response = await openai.chat.completions.create({
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage }
      ]
    });
    
    return response.choices[0].message.content;
  }
}

// Usage
const chatApp = new PersonalizedChatApp('your_api_key');
const response = await chatApp.sendMessage("What should I focus on today?");
console.log(response);
```

## Testing Your Integration

### 1. Test Basic Connection
```javascript
// Test if your API key works
try {
  const psp = await byenatOS.getPersonalizedPrompt();
  console.log('✅ Connection successful!');
  console.log('Personalized prompt length:', psp.length);
} catch (error) {
  console.error('❌ Connection failed:', error.message);
}
```

### 2. Test Data Submission
```javascript
// Test data submission
try {
  await byenatOS.hinata.submit({
    source: 'test-app',
    highlight: 'Test content',
    note: 'Test note',
    tag: ['test']
  });
  console.log('✅ Data submission successful!');
} catch (error) {
  console.error('❌ Data submission failed:', error.message);
}
```

## Common Issues and Solutions

### API Key Issues
- **Problem**: "API key invalid"
- **Solution**: Check your API key in the developer dashboard

### Network Issues
- **Problem**: "Connection timeout"
- **Solution**: Check your internet connection and firewall settings

### Rate Limiting
- **Problem**: "Rate limit exceeded"
- **Solution**: Implement caching to reduce API calls

## Next Steps

1. **Read the [Core Concepts](CoreConcepts.md)** to understand how ByenatOS works
2. **Explore the [API Reference](../APIs/SystemAPIs.md)** for advanced features
3. **Check out [Best Practices](../DeveloperGuide/BestPractices.md)** for production-ready code
4. **Join our [Discord Community](https://discord.gg/byenatos)** for support

## Support

- 📚 [Full Documentation](https://docs.byenatos.org)
- 💬 [GitHub Discussions](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord Community](https://discord.gg/byenatos)
- 📧 [Email Support](mailto:support@byenatos.org)

---

**Congratulations!** You've successfully integrated ByenatOS into your application. Your users now have personalized AI experiences that learn and adapt over time. 