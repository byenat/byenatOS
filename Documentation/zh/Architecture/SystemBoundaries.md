# ByenatOS 系统边界定义

## 核心原则：操作系统 vs 应用程序

### 🔵 ByenatOS的职责（操作系统层）

#### 1. 核心系统服务
- **Kernel** - 进程管理、内存管理、设备驱动
- **SystemServices** - 文件系统、网络栈、认证服务
- **Hardware** - 硬件抽象层和设备管理

#### 2. AI基础设施服务
- **LocalHiNATAProcessor** - HiNATA数据细化和PSP生成
- **PersonalizationEngine** - PSP管理和存储
- **ApplicationFramework** - 为App提供开发框架和API

#### 3. 数据处理流水线
```
HiNATA数据接收 → 本地模型处理 → PSP生成 → PSP存储 → API提供给Apps
```

### 🟢 应用程序的职责（App层）

#### 1. 用户交互界面
- **聊天界面** - ChatBox App
- **笔记界面** - Notes App  
- **阅读界面** - ReadItLater App
- **任务管理** - Todo App

#### 2. 业务逻辑处理
- **内容生成** - 调用在线大模型
- **用户对话** - 处理用户输入和响应
- **数据展示** - 可视化用户数据
- **功能操作** - 具体业务功能实现

#### 3. AI模型调用
```
用户输入 → App处理 → 调用在线大模型(带PSP) → 个性化响应 → 用户界面显示
```

## 明确的系统分工

### ByenatOS提供什么？

1. **稳定的系统内核**
   - 进程调度、内存管理
   - 文件系统、网络服务
   - 设备驱动和硬件抽象

2. **AI数据处理服务**
   - 接收来自Apps的HiNATA数据
   - 本地模型处理和分析
   - 生成和管理PSP
   - 通过API提供PSP给Apps

3. **应用开发框架**
   - 统一的App开发SDK
   - HiNATA数据格式规范
   - PSP调用API
   - 系统服务接口

### ByenatOS不提供什么？

❌ **直接的用户交互**
   - 不提供聊天界面
   - 不直接呈现用户对话UI
   - 不承担应用层的业务交互与展示

❌ **应用程序功能**
   - 不是聊天机器人产品
   - 不是笔记应用
   - 不是阅读工具

ℹ️ 职责更新：在线AI调用与计费
- ✅ ByenatOS 负责：基于PSP进行外部大模型（如 GPT、Claude 等）的统一编排调用、用量统计与计费结算；并将结果返回给应用
- ✅ ByenatOS 负责：将用户问题与大模型回答组合为 HiNATA 模块（Question → Highlight，Answer → Note），并纳入系统侧的PSP迭代
- 🟢 应用负责：将用户问题转交给 ByenatOS、接收并展示结果；应用层不直接与外部大模型交互，也不做计费

## 正确的交互流程

### 用户使用ChatBox App的流程：

```
1. 用户在 ChatBox App 中输入问题
   ↓
2. App 将问题通过 API 发送至 ByenatOS（无需自行获取PSP）
   ↓
3. ByenatOS 结合系统管理的 PSP 生成合理 Prompt，并调用外部大模型 API
   ↓
4. ByenatOS 记录用量与费用、产出回答，并将【问题+回答】转为 HiNATA（Highlight=问题，Note=回答），更新PSP
   ↓
5. ByenatOS 将回答与计费摘要返回给 App
   ↓
6. App 仅负责展示给用户
```

### 用户使用Notes App的流程：

```
1. 用户在Notes App中记录笔记和高亮
   ↓
2. Notes App生成HiNATA数据发送给byenatOS
   ↓
3. byenatOS本地模型分析用户的记录习惯
   ↓
4. 更新PSP中的用户偏好和兴趣
   ↓
5. 其他Apps调用PSP时能获得更个性化的体验
```

## API边界定义

### ByenatOS对外提供的API：

```python
# PSP相关API
GET /api/psp/current - 获取当前PSP
POST /api/hinata/submit - 提交HiNATA数据
GET /api/psp/stats - 获取处理统计

# 系统服务API  
GET /api/system/status - 系统状态
POST /api/system/config - 系统配置

# LLM编排与计费API（新增）
POST /api/llm/chat - 基于PSP进行对话推理（由ByenatOS调用外部大模型并计费）
GET  /api/billing/usage - 查询用户或应用的推理用量与费用汇总
```

### Apps需要实现的功能：

```python
# 用户交互
handle_user_input()
display_response()
manage_ui_state()

# 业务逻辑
process_user_request()
call_online_llm()
format_response()

# 与byenatOS交互
submit_hinata_data()
get_current_psp()
```

## 重要提醒

1. **byenatOS是平台，不是产品**
   - 类似于Windows/macOS，提供基础服务
   - 用户不直接使用byenatOS，而是使用运行在其上的Apps

2. **个性化是通过PSP实现的**
   - byenatOS只负责生成和管理PSP
   - Apps负责将PSP应用到实际的用户交互中（现由 byenatOS 统一完成外部大模型调用与计费）

3. **AI能力的分工（更新）**
   - 本地AI（byenatOS）：数据分析、个性化建模、PSP管理、QnA→HiNATA转化
   - 在线AI（由byenatOS统一调用）：内容生成、对话交互、用量与计费

4. **数据流向（更新）**
   - Apps → byenatOS：用户请求（问题）、已有HiNATA数据
   - byenatOS → 在线AI：由PSP增强后的 Prompt
   - 在线AI → byenatOS：模型响应与用量信息
   - byenatOS → Apps：个性化响应与计费摘要

## PSP共享与作用域（新增）

- **账号级共享（默认）**：同一用户账号下的多个 App 共享同一份 PSP，这意味着任一 App 的高质量 HiNATA 更新都将推动全局 PSP 的迭代，其他 App 可直接受益。
- **App级叠加（可选）**：在账号级 PSP 之上可叠加 App 专属的偏好或约束（如输出风格、UI 长度限制），形成 `UserPSP + AppOverlay` 的合成策略。
- **Prompt 组装顺序**：`SystemPSP (安全/合规) → UserPSP (跨App共享) → AppOverlay (选用) → RuntimeContext`。
- **边界与合规**：PSP 为“个性化指令/偏好”的抽象，不回传可识别的隐私原始数据；跨 App 共享基于同一账号的授权与系统策略。

## 计费与模型选择原则（新增）

- **支持用户自选模型（不收手续费）**：
  - 用户可在请求中明确 `ModelPreference`（如 Provider/Model），并提供 `UserProvidedApiKey`（或账单账户引用）。
  - ByenatOS 仅代路由与用量统计，不收取任何手续费；费用由用户与外部提供商结算。
- **推荐 Auto 模式（按省钱承诺计费）**：
  - ByenatOS 基于 PSP、上下文与成本/质量策略自动选择最合适的模型与参数，目标是在保证高质量的前提下降低费用。
  - 提示用户“可节省约 XX% 成本（EstimatedSavingPercent）”。若最终 Auto 模式未比用户自行直连更省钱，则手续费为 0。
- **透明与可验证**：
  - 返回中包含预计/实际用量、费用与节省比例；选择理由可解释（例如模型、温度、上下文截取策略）。
- **持续迭代**：
  - ByenatOS 持续优化 PSP 与路由策略，以提升质量/成本比，兑现“Auto 更省钱”的长期承诺。

## 模型定制化 Prompt 策略（新增）

- **PSP→模型提示映射层**：当选择 Auto 路由到具体模型后，ByenatOS 会基于该模型的特性将通用 PSP 转换为“模型定制化 Prompt（PromptProfile）”，以最大化质量与可控性。
- **适配策略示例**：
  - OpenAI：严格 `System` 指令头、`JSON` 模式、`MaxTokens/Temperature` 上限保护、函数调用参数规范化。
  - Anthropic（Claude）：更强的 `System` 角色权重、对“思维链”提示的精简、对超长上下文的截取策略优化。
  - Google（Gemini）：工具调用/多模态提示段落结构化、对安全策略开关与内容过滤的前置说明。
- **可解释性**：响应中返回 `PromptProfileUsed` 与 `RoutingDecision`，便于用户理解“为何选择该模型、为何采用该提示策略”。
- **商业价值**：模型定制化 Prompt 是获得更高质量/更低成本的关键优化点，也是收取服务费的核心价值来源之一。

这种清晰的边界确保了：
- byenatOS专注于操作系统的核心职责
- Apps获得强大的个性化能力
- 用户获得一致的个性化体验
- 开发者有清晰的开发指引