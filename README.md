# ByenatOS - Intelligent Information Processing & Personalized System Prompt System

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 What is ByenatOS?

ByenatOS is an **intelligent information processing system** that focuses on acquiring external information and processing it into high-quality HiNATA files, while continuously optimizing Personal System Prompts (PSP) to provide personalized AI enhancement services for developers.

**Core Functions**:
- **Information Processing**: Intelligently processes external information into structured HiNATA files (Markdown format)
- **PSP Optimization**: Dynamically optimizes Personal System Prompts based on continuously flowing HiNATA files to accurately reflect user preferences
- **Intelligent Matching**: Understands user prompts, combines with PSP to find the most relevant content from HiNATA file library
- **Personalized Output**: Combines relevant HiNATA content with optimized PSP to provide personalized enhancement for any AI model

**Core Advantages**:
- Not bound to specific AI models, generated PSP and HiNATA content can be used with any supported large model products
- Local storage of personal information, forming unified personal knowledge base across applications, ensuring privacy security

## ⭐ Why Choose ByenatOS?

- 🧠 **Intelligent Information Processing** - Automatically transforms external information into high-quality structured HiNATA files
- 🎯 **Dynamic PSP Optimization** - Continuously optimizes Personal System Prompts based on complete information to accurately reflect user preferences
- 🔍 **Smart Content Matching** - Understands user intent and precisely matches the most relevant HiNATA content
- 🔐 **Privacy First** - Local storage of HiNATA files and PSP, never uploads personal sensitive information
- 🌍 **Model Agnostic** - Generated content works with any AI model, not tied to specific service providers
- ⚡ **Lightweight & Efficient** - Focuses on information processing without AI interaction logic, excellent performance

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

### Integrate ByenatOS (5 minutes)
```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({ apiKey: 'your_api_key' });

// Get personalized prompts and relevant HiNATA content
async function getPersonalizedContent(userQuery) {
  // Get optimized Personal System Prompt
  const personalizedPrompt = await byenatOS.getPersonalizedPrompt(userQuery);
  
  // Get relevant HiNATA file content
  const relevantHiNATA = await byenatOS.getRelevantHiNATA(userQuery);
  
  return {
    systemPrompt: personalizedPrompt,
    contextData: relevantHiNATA
  };
}

// Use the retrieved content with any AI model
const { systemPrompt, contextData } = await getPersonalizedContent("Help me analyze today's work efficiency");

// You can use this content with any AI model
const response = await yourPreferredAI.chat({
  system: systemPrompt,
  context: contextData,
  user: "Help me analyze today's work efficiency"
});
```

**🎉 Done!** Your app can now retrieve personalized prompts and relevant information to enhance any AI model's performance.

## 📊 Comparison

| Traditional Information Processing | ByenatOS Intelligent Processing |
|-----------------------------------|--------------------------------|
| Manual information organization | Automatic processing into HiNATA files |
| Static prompts | Dynamically optimized PSP |
| Scattered knowledge management | Unified personal knowledge base |
| Tied to specific AI services | Works with any AI model |
| Privacy compliance risks | Local storage protection |

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

*Building intelligent information processing and personalized prompt optimization system for the AI era* 🚀

</div>