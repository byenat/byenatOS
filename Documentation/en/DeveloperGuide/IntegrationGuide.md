# Developer Integration Guide

## Overview

This guide details how to integrate ByenatOS into your application to add personalized AI capabilities.

## Quick Integration (5 Minutes)

### Step 1: Install SDK

```bash
# JavaScript/Node.js
npm install @byenatos/sdk

# Python
pip install byenatos-sdk
```

### Step 2: Initialize Client

```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({
  apiKey: 'your_api_key'  // Get for free
});
```

```python
from byenatos import ByenatOS

byenatOS = ByenatOS(api_key='your_api_key')
```

### Step 3: Add AI Functionality

```javascript
// Add personalized AI chat functionality to your app
async function addAIChat(userMessage) {
  // Automatically get user memory information
  const personalizedPrompt = await byenatOS.getPersonalizedPrompt();
  
  // Call your existing AI service (OpenAI, Claude, etc.)
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

```python
# Add memory to your AI functionality
async def enhance_ai_response(user_message):
    personalized_prompt = await byenatOS.get_personalized_prompt()
    
    # Use your existing AI service
    response = await your_ai_service.chat(
        system_prompt=personalized_prompt,
        user_message=user_message
    )
    
    return response
```

## Advanced Integration

### HiNATA Data Generation

ByenatOS collects user behavior data through the HiNATA format. You can actively submit this data in your application:

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

```python
# Submit HiNATA data
byenatOS.hinata.submit({
    'source': 'my-app',
    'highlight': 'Content user focuses on',
    'note': 'Detailed context information',
    'tag': ['productivity', 'work'],
    'access': 'private'
})
```

### Get Personalized Prompts

```javascript
// Get personalized prompts for a specific domain
const psp = await byenatOS.psp.get({
  domain: 'productivity',
  context: 'task_management',
  recent_activity: true
});
```

```python
# Get personalized prompts
psp = byenatOS.psp.get(
    domain='productivity',
    context='task_management',
    recent_activity=True
)
```

## Application Scenario Examples

### Log Application Integration

```javascript
// Log application example
function saveJournalEntry(title, content, tags) {
  // Save log to application database
  saveToDatabase({ title, content, tags });
  
  // Submit to ByenatOS
  byenatOS.hinata.submit({
    source: 'journal_app',
    highlight: title,
    note: content,
    tag: [...tags, 'journal', 'personal'],
    access: 'private'
  });
}

// AI assistant functionality
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

### Reading Application Integration

```javascript
// ReadItLater application example
function saveArticle(url, title, content, userNote) {
  // Save article to application database
  saveArticleToDatabase({ url, title, content, userNote });
  
  // Submit to ByenatOS
  byenatOS.hinata.submit({
    source: 'readitlater_app',
    highlight: title,
    note: content + '\nUser note: ' + userNote,
    address: url,
    tag: extractTags(content),
    access: 'private'
  });
}

// Smart recommendation functionality
async function recommendArticles(currentInterests) {
  const psp = await byenatOS.psp.get({
    domain: 'reading_preferences',
    include_reading_history: true
  });
  
  const recommendations = await aiService.getRecommendations(
    `${psp}\nCurrent interests: ${currentInterests}`
  );
  
  return recommendations;
}
```

## Configuration Options

### API Key Configuration

```javascript
const byenatOS = new ByenatOS({
  apiKey: 'your_api_key',
  endpoint: 'https://api.byenatos.org', // Optional
  timeout: 5000, // Optional, default 5000ms
  retries: 3 // Optional, default 3 times
});
```

### Environment Configuration

```bash
# Development environment
export BYENATOS_API_KEY=your_dev_api_key
export BYENATOS_ENDPOINT=https://dev-api.byenatos.org

# Production environment
export BYENATOS_API_KEY=your_prod_api_key
export BYENATOS_ENDPOINT=https://api.byenatos.org
```

## Error Handling

```javascript
try {
  const psp = await byenatOS.getPersonalizedPrompt();
  // Use PSP
} catch (error) {
  if (error.code === 'API_KEY_INVALID') {
    console.error('API key invalid');
  } else if (error.code === 'RATE_LIMIT_EXCEEDED') {
    console.error('Rate limit exceeded');
  } else {
    console.error('Failed to get personalized prompt:', error.message);
  }
  
  // Use default prompt as fallback
  const fallbackPrompt = "You are a helpful AI assistant.";
}
```

## Performance Optimization

### Caching Strategy

```javascript
// Cache PSP to reduce API calls
let cachedPSP = null;
let lastUpdate = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

async function getCachedPSP() {
  const now = Date.now();
  
  if (!cachedPSP || (now - lastUpdate) > CACHE_DURATION) {
    cachedPSP = await byenatOS.getPersonalizedPrompt();
    lastUpdate = now;
  }
  
  return cachedPSP;
}
```

### Batch Submission

```javascript
// Batch submit HiNATA data for better performance
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
    hinataBatch.length = 0; // Clear array
  }
}
```

## Best Practices

### 1. Data Quality
- Ensure HiNATA data submitted accurately reflects user behavior
- Use meaningful highlights and notes
- Set correct access permissions

### 2. User Experience
- Submit data asynchronously in the background, do not block user operations
- Provide loading states and error handling
- Maintain smooth AI responses

### 3. Privacy Protection
- Only submit necessary user data
- Follow data minimization principles
- Provide user control options

### 4. Performance Considerations
- Use caching to reduce API calls
- Batch submit data
- Implement appropriate retry mechanisms

## Test Guidelines

### Unit Tests

```javascript
// Test PSP retrieval
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

### Integration Tests

```javascript
// Test complete AI interaction flow
describe('AI Interaction Flow', () => {
  it('should enhance AI response with personalization', async () => {
    // Submit test data
    await byenatOS.hinata.submit({
      source: 'test-app',
      highlight: 'Test content',
      note: 'Test note'
    });
    
    // Get personalized prompt
    const psp = await byenatOS.getPersonalizedPrompt();
    
    // Simulate AI call
    const response = await mockAIService.chat({
      systemPrompt: psp,
      userMessage: 'Test question'
    });
    
    expect(response).toContain('personalized');
  });
});
```

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Check if API key is correct
   - Confirm if key is activated

2. **Network Connection Issues**
   - Check network connection
   - Confirm firewall settings

3. **Data Format Errors**
   - Validate HiNATA data format
   - Check required fields

4. **Performance Issues**
   - Check cache settings
   - Optimize API call frequency

### Debug Mode

```javascript
const byenatOS = new ByenatOS({
  apiKey: 'your_api_key',
  debug: true // Enable debug mode
});
```

## Support Resources

- 📚 [Full API Documentation](https://docs.byenatos.org/api)
- 💬 [GitHub Discussions](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord Community](https://discord.gg/byenatos)
- 📧 [Email Support](mailto:support@byenatos.org) 