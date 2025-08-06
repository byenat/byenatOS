# ByenatOS - AI Operating System for App Developers

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 What is ByenatOS?

ByenatOS is an **AI operating system** that gives any app personalized AI capabilities with just a few lines of code, without requiring AI expertise.

**Core Value**: In the AI era, each app with AI capabilities is like a computer. ByenatOS is the operating system for this computer, providing personalized AI by calling local large models (CPU).

**Key Advantage**: Unlike ChatGPT or Claude that only provide personalized experience within their own products, ByenatOS collects memory across all apps to create unified personal memory, enabling enhanced AI experience across any large model product.

## ⭐ Why Choose ByenatOS?

- 🚀 **Zero AI Experience Required** - Just a few lines of code
- 🎯 **Cross-App Memory** - Unified personal memory across all apps and AI models
- 🔐 **Privacy First** - Local data processing, never uploaded
- 🌍 **Completely Free** - MIT license, no hidden fees
- ⚡ **Lightweight** - < 100ms response, no performance impact

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

**🎉 Done!** Your app now has personalized AI that learns from user behavior across all applications.

## 📊 Comparison

| Traditional AI Development | ByenatOS Integration |
|---------------------------|---------------------|
| Requires AI expertise | Zero AI experience |
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
- 🏗️ [AI Operating System Architecture](Documentation/en/Architecture/AIOperatingSystemArchitecture.md)
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

*Building the personalized AI ecosystem for the AI era* 🚀

</div>