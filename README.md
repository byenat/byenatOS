# ByenatOS - AI Operating System for App Developers

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 What is ByenatOS?

ByenatOS is a **plug-and-play AI plugin** that enables app developers to add personalized AI capabilities to any application with just a few lines of code. It can also be viewed as an **AI operating system** that helps AI-enabled applications gain memory capabilities, providing personalized AI experiences for app users.

**Core Advantages**:
- Unlike ChatGPT or Claude that only provide personalized experiences within their own products, ByenatOS can save memory locally and can be called by any product that supports memory upload, enabling users to have enhanced AI experiences across any large model product without being tied to a single model.
- If users have multiple apps simultaneously calling ByenatOS to implement AI capabilities, ByenatOS can help users collect memory across apps, forming unified personal memory.

## ⭐ Why Choose ByenatOS?

- 🚀 **Zero AI Development Experience** - Just a few lines of code to integrate personalized AI capabilities
- 🎯 **Cross-App Memory** - Unified personal memory across all apps and AI models
- 🔐 **Privacy First** - Local data processing, never uploads personal sensitive information
- 🌍 **Completely Free** - MIT license, no hidden fees
- ⚡ **Optimized for Local Models** - Engineering capabilities to ensure optimal large model performance on limited local computing power

## 🚀 Quick Start

### Get Your API Key
1. Visit [developer.byenatos.org](https://developer.byenatos.org)
2. Create a free account
3. Generate your API key

### Install SDK
```bash
# JavaScript/Node.js
npm install @byenatos/sdk

# Python
pip install byenatos-sdk
```

### Add AI to Your App (5 minutes)
```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({ apiKey: 'your_api_key' });

// Add personalized AI to your app
async function addAIChat(userMessage) {
  const personalizedPrompt = await byenatOS.getPersonalizedPrompt();
  
  const response = await openai.chat.completions.create({
    messages: [
      { role: "system", content: personalizedPrompt },
      { role: "user", content: userMessage }
    ]
  });
  
  return response.choices[0].message.content;
}

// That's it! Your app now has cross-app memory
const aiResponse = await addAIChat("Help me analyze today's work efficiency");
```

**🎉 Done!** Your app now has a plug-and-play personalized AI plugin that learns from user behavior across all applications.

## 📊 Comparison

| Traditional AI Development | ByenatOS Plugin Integration |
|---------------------------|---------------------------|
| Requires AI expertise | Zero AI development experience |
| 6-month development | Just a few lines of code |
| High training costs | Completely free |
| Product-locked memory | Cross-app unified memory |
| Privacy risks | Built-in protection |

## 🤝 Contributing

We welcome all contributions! See our [Contributing Guide](CONTRIBUTING.md).

### Development Setup

```bash
git clone https://github.com/byenatos/byenatos.git
cd byenatos
./Tools/DevEnvironment/DevSetup.sh
./Scripts/dev.sh
```

## 📚 Documentation

- 📖 [Full Documentation](https://docs.byenatos.org)
- 🏗️ [AI Plugin Architecture](Documentation/en/Architecture/AIOperatingSystemArchitecture.md)
- 🚀 [Integration Guide](Documentation/en/DeveloperGuide/IntegrationGuide.md)
- 🧠 [Core Concepts](Documentation/en/UserGuide/CoreConcepts.md)
- 💬 [GitHub Discussions](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord Community](https://discord.gg/byenatos)

## 📈 Project Status

- 🏗️ **Alpha Stage** - Core implementation in progress
- 📅 **Beta Expected** - Q2 2024
- 🎯 **Stable Release** - Q4 2024

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- 🌐 [Website](https://byenatos.org)
- 📚 [Docs](https://docs.byenatos.org)
- 🐦 [Twitter](https://twitter.com/ByenatOS)

---

<div align="center">

**⭐ If this project helps you, please give us a Star!**

*Building the plug-and-play personalized AI plugin ecosystem for the AI era* 🚀

</div>