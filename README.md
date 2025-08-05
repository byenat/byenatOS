# ByenatOS - Personal AI Middleware for the AI Era

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 Project Overview

ByenatOS is an **open-source virtual personal operating system** designed for the AI era. It's not a traditional hardware operating system, but an intelligent middleware layer between applications and users. Just like an APP is a complete computer handling user I/O (mouse, keyboard, display), ByenatOS serves as the "OS + CPU" for this computer, specifically processing data input from APPs and providing personalized intelligent output.

### ⭐ Why Choose ByenatOS?

- 🎯 **Personalized AI Middleware** - Unified personalized AI capabilities for all applications
- 🔐 **Privacy First** - Personal data processed locally, never uploaded
- 🛠️ **Developer Friendly** - Simple APIs, rich SDKs, quick integration
- 🌍 **Open Source Ecosystem** - MIT license, community-driven, business-friendly
- ⚡ **High Performance** - < 100ms PSP generation, lightweight deployment
- 🏢 **Enterprise Ready** - Private deployment and enterprise features support

## 🧠 Core Innovation: HiNATA ≈ Virtual HDD, PSP ≈ Virtual Memory

**Key Design Principle**:
- **HiNATA ≈ Virtual Hard Drive** - Unlimited storage for all historical personal data
- **PSP ≈ Virtual Memory** - Strict capacity limits (prompt length), high-quality curated content

**Why This Analogy is Critical**:
Due to online AI models' context window limitations, PSP must maximize personalized effects within limited space. This requires ByenatOS to design a "memory manager" similar to operating systems, intelligently filtering the most relevant and important information from massive HiNATA data to generate PSP.

## 🎯 PSP Strategy Management System

**Dual-Layer Strategy Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                PSP Strategy Management                      │
├─────────────────────────────────────────────────────────────┤
│ PSP Production Strategy   │ Deep analysis to generate        │
│ (Low Frequency)          │ strategy candidates from HiNATA  │
│ • Day/week level         │ • User behavior pattern mining   │
│ • Strategy library       │ • Multiple personalization       │
│   construction          │   strategy generation            │
├─────────────────────────────────────────────────────────────┤  
│ PSP Invocation Strategy  │ Intelligently select and combine │
│ (High Frequency)         │ optimal PSP                      │
│ • Per query execution    │ • Context relevance matching     │
│ • Dynamic strategy combo │ • Maximize effect within tokens  │
├─────────────────────────────────────────────────────────────┤
│ User Feedback Loop       │ Strategy iteration driven by     │
│ • Satisfaction scoring   │ satisfaction scores              │
│ • Strategy effect        │ • Dynamic strategy weight        │
│   tracking              │   adjustment                      │
└─────────────────────────────────────────────────────────────┘
```

**User Feedback-Driven Iteration**:
1. **Satisfied Feedback** → Strengthen relevant strategy weights, increase invocation probability
2. **Unsatisfied Feedback** → Reduce strategy weights, trigger new strategy generation
3. **Strategy Attribution** → Precisely identify which strategy contributed to good/bad results
4. **Effect Evaluation** → Long-term tracking of strategy performance, eliminate ineffective strategies
5. **Continuous Learning** → Continuously optimize strategy selection and combination based on feedback

## 🚀 Quick Start

### Install ByenatOS

```bash
# Quick deployment with Docker
docker run -d -p 8080:8080 byenatos/byenatos:latest

# Or compile from source
git clone https://github.com/byenatos/byenatos.git
cd byenatos
./Scripts/install.sh
```

### Integrate into Your Application

#### JavaScript/Node.js
```bash
npm install @byenatos/sdk
```

```javascript
import { ByenatOS } from '@byenatos/sdk';

const client = new ByenatOS({
  apiKey: 'your_api_key'
});

// Submit user behavior data
await client.hinata.submit({
  source: 'my-app',
  highlight: 'Content user focused on',
  note: 'Detailed context information'
});

// Get personalized prompts
const psp = await client.psp.get({
  domain: 'productivity',
  context: 'task_management'
});
```

#### Python
```bash
pip install byenatos-sdk
```

```python
from byenatos import ByenatOS

client = ByenatOS(api_key='your_api_key')

# Submit HiNATA data
client.hinata.submit({
    'source': 'my-app',
    'highlight': 'Content user focused on',
    'note': 'Detailed context information'
})

# Get personalized prompts
psp = client.psp.get(
    domain='productivity',
    context='task_management'
)
```

### Example Applications

Check out our example applications to understand integration methods:

- 📝 [Smart Journal App](https://github.com/byenatos/example-journal-app)
- 📚 [Reading Assistant App](https://github.com/byenatos/example-reading-app)
- 🎓 [Learning Companion App](https://github.com/byenatos/example-learning-app)

## 🤝 Contributing

We welcome all forms of contributions! Whether you're a developer, designer, or documentation writer.

### How to Contribute

1. 🍴 Fork the project
2. 🔧 Create a feature branch (`git checkout -b feature/amazing-feature`)
3. 💾 Commit your changes (`git commit -m 'Add amazing feature'`)
4. 📤 Push to the branch (`git push origin feature/amazing-feature`)
5. 🎯 Create a Pull Request

### Development Environment Setup

```bash
# Clone repository
git clone https://github.com/byenatos/byenatos.git
cd byenatos

# Setup development environment
./Tools/DevEnvironment/DevSetup.sh

# Run tests
./Scripts/test.sh

# Start development server
./Scripts/dev.sh
```

For more details, see [Contributing Guide](CONTRIBUTING.md).

## 🌟 Developer Ecosystem

### Get Support

- 📚 [Developer Documentation](https://docs.byenatos.org)
- 💬 [GitHub Discussions](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord Community](https://discord.gg/byenatos)
- 📧 [Email Support](mailto:support@byenatos.org)

### Developer Program

- 🆓 **Free Use** - Personal and open source projects
- 🏢 **Enterprise License** - Commercial support and advanced features
- 🎯 **Developer Certification** - Become a certified developer with special benefits
- 💰 **Monetization Support** - App store and revenue sharing

See the complete [Developer Ecosystem Program](Documentation/DeveloperEcosystem/DeveloperProgram.md).

## 📊 Project Status

### Current Stage
- 🏗️ **Alpha Stage** - Core architecture implementation in progress
- 📅 **Expected Beta** - Q2 2024
- 🎯 **Stable Release** - Q4 2024

### Roadmap
- [x] Virtual system architecture design
- [x] PSP strategy management system
- [ ] Core API implementation
- [ ] Multi-language SDK development
- [ ] Mobile support
- [ ] Enterprise features

See detailed [Project Roadmap](https://github.com/byenatos/byenatos/projects).

## 📈 Community Stats

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/byenatos/byenatos)
![GitHub forks](https://img.shields.io/github/forks/byenatos/byenatos)
![GitHub issues](https://img.shields.io/github/issues/byenatos/byenatos)
![GitHub pull requests](https://img.shields.io/github/issues-pr/byenatos/byenatos)

</div>

## 🏆 Acknowledgments

Thanks to all developers and users who contribute to ByenatOS:

- All [contributors](https://github.com/byenatos/byenatos/graphs/contributors)
- Community users providing feedback and suggestions
- Open source community best practices inspiration

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.

### Commercial Use
- ✅ **Free Use** - Personal and commercial projects
- ✅ **Modify and Distribute** - Keep copyright notice
- ✅ **Private Deployment** - Enterprise internal use
- 🏢 **Enterprise Support** - Optional commercial support services

## 🔗 Related Links

- 🌐 [Official Website](https://byenatos.org)
- 📚 [Documentation Center](https://docs.byenatos.org)  
- 👥 [Community Forum](https://community.byenatos.org)
- 🐦 [Twitter](https://twitter.com/ByenatOS)
- 📺 [YouTube](https://youtube.com/@ByenatOS)

---

<div align="center">

**⭐ If this project helps you, please give us a Star!**

*Let's build the personalized application ecosystem for the AI era together* 🚀

</div>