# ByenatOS - 为APP开发者设计的AI操作系统

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 ByenatOS是什么？

ByenatOS是一个**即插即用的 AI 插件**，让应用开发者通过几行代码就能让任何应用获得个性化 AI 能力，同时也可以将其视为是**AI操作系统**，帮助具有 AI 功能的应用获得memory能力，为应用用户提供个性化的 AI 能力。

**核心优势**：
- 与ChatGPT或Claude只能在各自产品内提供个性化AI体验不同，ByenatOS可以在本地保存 memory，对于支持上传 memory的产品都可以调用，让用户在任何大模型相关产品中都能获得增强的AI体验。同时用户不用绑定在单个大模型上。
- 如果用户有多个 APP 同时调用 byenatOS 来实现 AI 能力。则 byenatOS 可以帮助用户跨APP收集memory，形成统一的个人memory。

## ⭐ 开发者为什么选择ByenatOS？

- 🚀 **零AI开发经验** - 只需几行代码即可接入个性化AI能力
- 🎯 **跨APP memory** - 统一的个人memory，支持在不同应用和AI模型中调用
- 🔐 **隐私优先** - 本地数据处理，永不上传个人敏感信息
- 🌍 **完全免费** - MIT许可证，无隐藏费用
- ⚡ **即插即用** - 作为AI插件，轻松集成到任何应用中

## 🚀 快速开始

### 获取API密钥
1. 访问 [developer.byenatos.org](https://developer.byenatos.org)
2. 创建免费账户
3. 生成您的API密钥

### 安装SDK
```bash
# JavaScript/Node.js
npm install @byenatos/sdk

# Python
pip install byenatos-sdk
```

### 为您的应用添加AI（5分钟）
```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({ apiKey: 'your_api_key' });

// 为您的应用添加个性化AI
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

// 就这么简单！您的应用现在拥有跨APP memory
const aiResponse = await addAIChat("帮我分析今天的工作效率");
```

**🎉 完成！** 您的应用现在拥有了即插即用的个性化AI插件，可以从所有应用程序的用户行为中学习。

## 📊 对比

| 传统AI开发 | ByenatOS插件集成 |
|------------|----------------|
| 需要AI专业知识 | 零AI开发经验 |
| 6个月开发周期 | 只需几行代码 |
| 高昂训练成本 | 完全免费 |
| 产品锁定的memory | 跨APP统一memory |
| 隐私合规风险 | 内置保护 |

## 🤝 贡献

我们欢迎所有贡献！参见我们的[贡献指南](CONTRIBUTING.md)。

### 开发环境设置

```bash
git clone https://github.com/byenatos/byenatos.git
cd byenatos
./Tools/DevEnvironment/DevSetup.sh
./Scripts/dev.sh
```

## 📚 文档

- 📖 [完整文档](https://docs.byenatos.org)
- 🏗️ [AI插件架构](Documentation/en/Architecture/AIOperatingSystemArchitecture.md)
- 🚀 [集成指南](Documentation/en/DeveloperGuide/IntegrationGuide.md)
- 🧠 [核心概念](Documentation/en/UserGuide/CoreConcepts.md)
- 💬 [GitHub讨论](https://github.com/byenatos/byenatos/discussions)
- 🎮 [Discord社区](https://discord.gg/byenatos)

## 📈 项目状态

- 🏗️ **Alpha阶段** - 核心实现进行中
- 📅 **预计Beta** - 2024年Q2
- 🎯 **稳定版本** - 2024年Q4

## 📄 许可证

MIT许可证 - 详见[LICENSE](LICENSE)。

## 🔗 链接

- 🌐 [官网](https://byenatos.org)
- 📚 [文档](https://docs.byenatos.org)
- 🐦 [Twitter](https://twitter.com/ByenatOS)

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**

*为AI时代构建即插即用的个性化AI插件生态* 🚀

</div>