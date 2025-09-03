# ByenatOS - 智能信息处理与个性化提示词系统

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/byenatos/byenatos?style=social)](https://github.com/byenatos/byenatos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/byenatos/byenatos/workflows/CI/badge.svg)](https://github.com/byenatos/byenatos/actions)
[![Discord](https://img.shields.io/discord/1234567890?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/byenatos)

[English](README.md) | [中文文档](README.zh.md)

</div>

## 🚀 ByenatOS是什么？

ByenatOS是一个**智能信息处理系统**，专注于从外部获取信息并处理成高质量的HiNATA文件，同时持续优化个人系统提示词（PSP），为开发者提供个性化的AI增强服务。

**核心功能**：
- **信息处理**：将外部信息智能处理成结构化的HiNATA文件（Markdown格式）
- **PSP优化**：基于持续流入的HiNATA文件动态优化个人系统提示词，准确反映用户偏好
- **智能匹配**：理解用户提示词，结合PSP从HiNATA文件库中找到最相关的内容
- **个性化输出**：将相关HiNATA内容与优化后的PSP结合，为任何AI模型提供个性化增强

**核心优势**：
- 不绑定特定AI模型，生成的PSP和HiNATA内容可用于任何支持的大模型产品
- 本地存储个人信息，形成跨应用的统一个人知识库，确保隐私安全

## ⭐ 开发者为什么选择ByenatOS？

- 🧠 **智能信息处理** - 自动将外部信息转化为高质量的结构化HiNATA文件
- 🎯 **动态PSP优化** - 基于完整信息持续优化个人系统提示词，准确反映用户偏好
- 🔍 **智能内容匹配** - 理解用户意图，精准匹配最相关的HiNATA内容
- 🔐 **隐私优先** - 本地存储HiNATA文件和PSP，永不上传个人敏感信息
- 🌍 **模型无关** - 生成的内容适用于任何AI模型，不绑定特定服务商
- ⚡ **轻量高效** - 专注信息处理，不包含AI交互逻辑，性能优异

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

### 集成ByenatOS（5分钟）
```javascript
import { ByenatOS } from '@byenatos/sdk';

const byenatOS = new ByenatOS({ apiKey: 'your_api_key' });

// 方案1：获取问题相关的HiNATA内容（与PSP无关）
async function getRelevantHiNATA(userQuery) {
  const response = await byenatOS.queryRelevantHiNATA({
    user_id: 'user_123',
    question: userQuery,
    limit: 5
  });
  
  return response.relevant_hinata;
}

// 方案2：获取个性化增强内容（PSP + HiNATA结合）
async function getPersonalizedContent(userQuery) {
  const response = await byenatOS.getPersonalizedEnhancement({
    user_id: 'user_123',
    question: userQuery,
    context_limit: 5,
    include_psp_details: false
  });
  
  return {
    systemPrompt: response.personalized_prompt,
    contextData: response.relevant_context
  };
}

// 使用获取的内容与任何AI模型交互
const { systemPrompt, contextData } = await getPersonalizedContent("帮我分析今天的工作效率");

// 您可以将这些内容用于任何AI模型
const response = await yourPreferredAI.chat({
  system: systemPrompt,
  context: contextData,
  user: "帮我分析今天的工作效率"
});
```

**🎉 完成！** 您的应用现在可以获取个性化的提示词和相关信息，用于增强任何AI模型的表现。

## 📊 对比

| 传统信息处理 | ByenatOS智能处理 |
|------------|-----------------|
| 手动整理信息 | 自动处理成HiNATA文件 |
| 静态提示词 | 动态优化的PSP |
| 分散的知识管理 | 统一的个人知识库 |
| 绑定特定AI服务 | 适用于任何AI模型 |
| 隐私合规风险 | 本地存储保护 |

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

*为AI时代构建智能信息处理与个性化提示词优化系统* 🚀

</div>