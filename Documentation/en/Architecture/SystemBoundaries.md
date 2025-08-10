# ByenatOS System Boundary Definition

## Core Principle: Operating System vs Applications

### 🔵 ByenatOS Responsibilities (Operating System Layer)

#### 1. Core System Services
- **Kernel** - Process management, memory management, device drivers
- **SystemServices** - File system, network stack, authentication services
- **Hardware** - Hardware abstraction layer and device management

#### 2. AI Infrastructure Services
- **LocalHiNATAProcessor** - HiNATA data refinement and PSP generation
- **PersonalizationEngine** - PSP management and storage
- **ApplicationFramework** - Provides development framework and APIs for Apps

#### 3. Data Processing Pipeline
```
HiNATA Data Reception → Local Model Processing → PSP Generation → PSP Storage → API Provision to Apps
```

### 🟢 Application Responsibilities (App Layer)

#### 1. User Interaction Interface
- **Chat Interface** - ChatBox App
- **Notes Interface** - Notes App  
- **Reading Interface** - ReadItLater App
- **Task Management** - Todo App

#### 2. Business Logic Processing
- **Content Generation** - Call online large models
- **User Conversation** - Process user input and responses
- **Data Display** - Visualize user data
- **Functional Operations** - Specific business function implementation

#### 3. AI Model Invocation
```
User Input → App Processing → Call Online Large Model (with PSP) → Personalized Response → User Interface Display
```

## Clear System Division of Labor

### What Does ByenatOS Provide?

1. **Stable System Kernel**
   - Process scheduling, memory management
   - File system, network services
   - Device drivers and hardware abstraction

2. **AI Data Processing Services**
   - Receive HiNATA data from Apps
   - Local model processing and analysis
   - Generate and manage PSP
   - Provide PSP to Apps via API

3. **Application Development Framework**
   - Unified App development SDK
   - HiNATA data format specification
   - PSP invocation API
   - System service interfaces

### What Does ByenatOS NOT Provide?

❌ **Direct User Interaction**
   - Does not provide chat UI
   - Does not directly render user conversation interfaces
   - Does not take on application-layer business interaction and presentation

❌ **Application Functions**
   - Not a chatbot product
   - Not a notes application
   - Not a reading tool

ℹ️ Responsibility Update: Online LLM Calls and Billing
- ✅ ByenatOS is responsible for: unified orchestration of external LLM calls (e.g., GPT, Claude) based on PSP, usage tracking, and billing settlement; returning the final result to Apps
- ✅ ByenatOS is responsible for: converting the user question and LLM answer into a HiNATA module (Question → Highlight, Answer → Note) and updating PSP on the system side
- 🟢 Apps are responsible for: forwarding user questions to ByenatOS and rendering results; Apps do not call external LLMs directly and do not handle billing

## Correct Interaction Flow

### User Flow Using ChatBox App:

```
1. User enters a question in the ChatBox App
   ↓
2. The App sends the question to ByenatOS via API (no need to fetch PSP by itself)
   ↓
3. ByenatOS combines the system-managed PSP to generate an appropriate prompt, then calls the external LLM API
   ↓
4. ByenatOS tracks usage and cost, obtains the answer, converts [Question+Answer] into HiNATA (Highlight=Question, Note=Answer), and updates PSP
   ↓
5. ByenatOS returns the answer and a billing summary to the App
   ↓
6. The App only renders the result for the user
```

## PSP Sharing & Scope (New)

- **Account-level Sharing (Default)**: Multiple Apps under the same user account share a single PSP. High-quality HiNATA updates from any App drive global PSP iteration and benefit all Apps.
- **App-level Overlay (Optional)**: An App-specific overlay can be composed on top of the account-level PSP (e.g., style preferences, UI length limits), resulting in `UserPSP + AppOverlay`.
- **Prompt Composition Order**: `SystemPSP (safety/compliance) → UserPSP (cross-App shared) → AppOverlay (optional) → RuntimeContext`.
- **Boundary & Compliance**: PSP abstracts preferences/instructions, not raw PII; cross-App sharing occurs within the same account authorization and system policy.

## Billing & Model Selection Principles (New)

- **Support User-Chosen Model (No Fee)**:
  - Users may explicitly set `ModelPreference` (e.g., Provider/Model) and provide a `UserProvidedApiKey` (or billing account reference).
  - ByenatOS only routes and tracks usage; no service fee is charged. The user pays the external provider directly.
- **Recommend Auto Mode (Fee Based on Savings Promise)**:
  - ByenatOS automatically selects the most suitable model/parameters based on PSP, context, and cost/quality policies, aiming for high quality at lower cost.
  - Inform users “save about XX% cost (EstimatedSavingPercent)”. If Auto mode does not save compared to direct external API usage, the service fee is 0.
- **Transparent & Verifiable**:
  - Responses include estimated/actual usage, cost, and saving ratio; selection rationale is explainable (model, temperature, context strategy).
- **Continuous Iteration**:
  - ByenatOS continuously improves PSP and routing to increase quality-to-cost ratio and uphold the “Auto saves more” promise.

## Model-Specific Prompt Strategy (New)

- **PSP → Model Prompt Mapping Layer**: After Auto selects a concrete model, ByenatOS transforms the generic PSP into a model-tailored prompt (PromptProfile) that exploits the model’s strengths for quality and controllability.
- **Adaptation Examples**:
  - OpenAI: strict `System` header, `JSON` mode, guarded `MaxTokens/Temperature`, function-call argument normalization.
  - Anthropic (Claude): higher weight on `System` role, concise chain-of-thought prompting, optimized long-context truncation.
  - Google (Gemini): tool/multimodal prompt structuring, upfront safety switches and content filtering notes.
- **Explainability**: Responses include `PromptProfileUsed` and `RoutingDecision` to explain why a model and strategy were chosen.
- **Business Value**: These prompt adaptations are critical to achieving higher quality at lower cost and form a core part of the service fee value.