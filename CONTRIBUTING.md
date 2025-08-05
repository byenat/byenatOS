# 贡献指南 | Contributing Guide

感谢您对ByenatOS项目的兴趣！我们欢迎所有形式的贡献，无论是代码、文档、设计还是想法。

## 快速开始

### 参与方式

1. **核心系统开发** - 贡献虚拟系统核心功能
2. **AI模型优化** - 改进本地AI处理器性能
3. **开发者工具** - 构建开发者友好的SDK和工具
4. **应用示例** - 创建集成ByenatOS的示例应用
5. **文档改进** - 完善技术文档和教程
6. **社区建设** - 帮助新贡献者融入社区

### 开发环境设置

```bash
# 1. 克隆仓库
git clone https://github.com/byenatos/byenatos.git
cd byenatos

# 2. 设置开发环境
./Tools/DevEnvironment/DevSetup.sh

# 3. 安装依赖
./Scripts/install_dependencies.sh

# 4. 构建项目
./Scripts/build.sh

# 5. 运行测试
./Scripts/test.sh
```

## 项目结构

### 核心模块
- `VirtualCore/` - 虚拟系统核心，需要Rust开发经验
- `LocalAIProcessor/` - 本地AI处理器，需要Python/ML经验
- `PersonalizationEngine/` - 个性化引擎，需要算法设计经验
- `InterfaceAbstraction/` - API接口层，需要API设计经验

### 开发者生态
- `SDK/` - 开发者工具包
- `Examples/` - 示例应用
- `Templates/` - 应用模板
- `Documentation/` - 技术文档

### 贡献领域

#### 🦀 系统核心开发 (Rust)
**技能要求**: Rust、系统编程、并发处理
**贡献机会**:
- 虚拟系统核心功能
- 性能优化
- 内存管理
- 跨平台适配

#### 🐍 AI处理器开发 (Python)
**技能要求**: Python、机器学习、NLP
**贡献机会**:
- 本地AI模型优化
- PSP策略算法
- HiNATA数据处理
- 向量化和检索

#### 🌐 API开发 (多语言)
**技能要求**: RESTful API、gRPC、多语言SDK
**贡献机会**:
- HiNATA SDK开发
- PSP API优化
- 多语言绑定
- API文档

#### 📱 应用集成 (多平台)
**技能要求**: 应用开发、平台特定知识
**贡献机会**:
- iOS/Android SDK
- Web集成库
- 桌面应用示例
- 跨平台工具

## 开发流程

### 1. 选择Issue
- 查看 [Issues](https://github.com/byenatos/byenatos/issues)
- 选择标有 `good-first-issue` 的issue开始
- 在issue中评论表明您想要处理

### 2. 创建分支
```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/issue-number
```

### 3. 开发和测试
```bash
# 开发您的功能
# 编写测试
./Scripts/test.sh

# 运行代码检查
./Scripts/lint.sh

# 确保所有测试通过
./Scripts/ci_check.sh
```

### 4. 提交Pull Request
- 确保代码符合项目规范
- 写清楚的提交消息
- 在PR描述中解释您的更改
- 链接相关的issue

## 代码规范

### Rust代码规范
```bash
# 格式化代码
cargo fmt

# 运行clippy检查
cargo clippy -- -D warnings

# 运行测试
cargo test
```

### Python代码规范
```bash
# 格式化代码
black .
isort .

# 类型检查
mypy .

# 运行测试
pytest
```

### 提交消息规范
```
<type>(<scope>): <description>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建工具或辅助工具的变动

**示例**:
```
feat(psp): add strategy feedback mechanism

实现基于用户反馈的PSP策略调整机制，支持实时策略权重更新。

- 添加FeedbackManager模块
- 实现策略效果评估算法
- 更新PSP调用策略选择逻辑

Closes #123
```

## 测试规范

### 单元测试
- 新功能必须包含单元测试
- 测试覆盖率应保持在80%以上
- 使用descriptive的测试名称

### 集成测试
- API变更需要集成测试
- 跨模块功能需要端到端测试
- 性能敏感功能需要基准测试

### 测试目录结构
```
Tests/
├── UnitTests/          # 单元测试
├── IntegrationTests/   # 集成测试
├── PerformanceTests/   # 性能测试
├── SecurityTests/      # 安全测试
└── Examples/           # 示例测试
```

## 文档贡献

### 技术文档
- API文档使用OpenAPI规范
- 架构文档使用Markdown + Mermaid图表
- 代码注释使用规范格式

### 教程和示例
- 每个新功能需要相应的使用示例
- 复杂功能需要step-by-step教程
- 示例代码需要可运行和测试

## 社区交流

### 沟通渠道
- **GitHub Issues** - 功能请求和Bug报告
- **GitHub Discussions** - 一般讨论和问答
- **Discord** - 实时交流 (链接待提供)
- **邮件列表** - 开发者通讯

### 行为规范
我们采用 [Contributor Covenant](CODE_OF_CONDUCT.md) 行为规范。

## 发布流程

### 版本规范
我们使用[语义化版本](https://semver.org/)：
- `MAJOR.MINOR.PATCH`
- 破坏性变更 → MAJOR版本
- 新功能 → MINOR版本  
- 错误修复 → PATCH版本

### 发布节奏
- **主要版本**: 每6个月
- **次要版本**: 每月
- **补丁版本**: 根据需要

## 特殊贡献机会

### 🌟 核心贡献者计划
表现出色的贡献者可以申请成为核心贡献者，获得：
- 项目决策权
- 专属Discord频道
- ByenatOS认证徽章
- 技术分享机会

### 🏆 贡献者奖励
- **月度贡献者** - 社区表彰
- **年度贡献者** - 特殊奖励
- **企业贡献者** - 商业合作机会

## 获得帮助

### 新贡献者
- 查看 `good-first-issue` 标签
- 阅读 [新贡献者指南](Documentation/NewContributor.md)
- 参加每周的新贡献者会议

### 技术支持
- 在相关Issue中提问
- 使用GitHub Discussions
- 联系维护者 (maintainers@byenatos.org)

## 许可证

通过贡献代码，您同意您的贡献将采用与项目相同的[MIT许可证](LICENSE)。

---

感谢您为ByenatOS项目做出贡献！每一个贡献都让这个AI时代的个人智能中间层变得更好。🚀

## 联系方式

- **项目主页**: https://byenatos.org
- **GitHub**: https://github.com/byenatos/byenatos
- **邮箱**: community@byenatos.org
- **社区论坛**: https://community.byenatos.org