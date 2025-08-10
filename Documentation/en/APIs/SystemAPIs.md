# ByenatOS System API Documentation

## API Overview

ByenatOS provides a modern system API designed for AI-era application development. The API adopts a layered architecture, including traditional system calls, AI-enhanced services, and modern application interfaces.

## Core System APIs

### 1. Kernel System Calls (Kernel Syscalls)

#### Process Management
```rust
// Create process
fn sys_create_process(
    executable_path: &str,
    args: &[&str],
    env: &[(&str, &str)],
    options: ProcessOptions
) -> Result<ProcessId, SystemError>;

// Process communication
fn sys_send_message(
    target_pid: ProcessId,
    message: &[u8],
    priority: MessagePriority
) -> Result<(), SystemError>;

// AI-enhanced process scheduling
fn sys_set_ai_scheduling(
    pid: ProcessId,
    ai_hints: AISchedulingHints
) -> Result<(), SystemError>;
```

#### Memory Management
```rust
// Smart memory allocation
fn sys_smart_alloc(
    size: usize,
    usage_pattern: MemoryPattern,
    ai_prediction: Option<AccessPattern>
) -> Result<*mut u8, SystemError>;

// Memory access pattern learning
fn sys_memory_learn_pattern(
    addr: *const u8,
    size: usize,
    access_type: AccessType
) -> Result<(), SystemError>;
```

#### File System
```rust
// AI-assisted file operations
fn sys_smart_file_open(
    path: &str,
    intent: FileIntent,
    ai_context: Option<&str>
) -> Result<FileDescriptor, SystemError>;

// Intelligent file search
fn sys_semantic_file_search(
    query: &str,
    scope: SearchScope,
    filters: FileFilters
) -> Result<Vec<FileInfo>, SystemError>;
```

### 2. AI Services API

#### Natural Language Processing
```typescript
interface NaturalLanguageAPI {
  // Intent recognition
  recognizeIntent(text: string): Promise<IntentResult>;
  
  // Text generation
  generateText(prompt: string, options: GenerationOptions): Promise<string>;
  
  // Language translation
  translate(text: string, targetLang: string): Promise<string>;
  
  // Sentiment analysis
  analyzeSentiment(text: string): Promise<SentimentResult>;
}
```

#### Computer Vision
```typescript
interface ComputerVisionAPI {
  // Image recognition
  recognizeImage(imageData: ImageData): Promise<RecognitionResult>;
  
  // Real-time video analysis
  analyzeVideoStream(stream: MediaStream): AsyncIterator<FrameAnalysis>;
  
  // Screen content understanding
  analyzeScreen(region?: Rectangle): Promise<ScreenAnalysis>;
  
  // Text recognition (OCR)
  extractText(imageData: ImageData, language?: string): Promise<TextResult>;
}
```

#### Personal Assistant
```typescript
interface PersonalAssistantAPI {
  // Voice interaction
  startVoiceSession(): Promise<VoiceSession>;
  
  // Task execution
  executeTask(task: TaskDescription): Promise<TaskResult>;
  
  // Smart suggestions
  getSuggestions(context: UserContext): Promise<Suggestion[]>;
  
  // Learning user preferences
  updateUserPreferences(feedback: UserFeedback): Promise<void>;
}
```

### 3. User Interface API (UI Framework API)

#### Window Management
```typescript
interface WindowManagerAPI {
  // Create smart window
  createSmartWindow(config: WindowConfig): Promise<SmartWindow>;
  
  // AI layout optimization
  optimizeLayout(constraints: LayoutConstraints): Promise<Layout>;
  
  // Multi-screen management
  manageMultiDisplay(displays: Display[]): Promise<DisplayConfig>;
}
```

#### Theme and Style
```typescript
interface ThemeAPI {
  // Adaptive theme
  applyAdaptiveTheme(preferences: ThemePreferences): Promise<void>;
  
  // AI color suggestions
  suggestColors(context: DesignContext): Promise<ColorPalette>;
  
  // Dynamic style adjustment
  adjustStyleForAccessibility(requirements: A11yRequirements): Promise<void>;
}
```

#### Input Handling
```typescript
interface InputAPI {
  // Multi-modal input
  registerMultiModalHandler(handler: MultiModalHandler): void;
  
  // Gesture recognition
  recognizeGesture(inputData: GestureData): Promise<GestureResult>;
  
  // Voice commands
  processVoiceCommand(audio: AudioData): Promise<CommandResult>;
  
  // Eye tracking
  trackEyeMovement(): AsyncIterator<EyePosition>;
}
```

### 4. Security API (Security API)

#### Authentication
```rust
// Biometric authentication
fn biometric_authenticate(
    method: BiometricMethod,
    challenge: &[u8]
) -> Result<AuthToken, SecurityError>;

// AI anomaly detection
fn detect_security_anomaly(
    user_behavior: &UserBehavior,
    context: &SecurityContext
) -> Result<ThreatLevel, SecurityError>;
```

#### Data Protection
```rust
// Smart encryption
fn smart_encrypt(
    data: &[u8],
    context: EncryptionContext,
    ai_optimization: bool
) -> Result<EncryptedData, SecurityError>;

// Privacy protection
fn anonymize_data(
    data: &PersonalData,
    anonymization_level: PrivacyLevel
) -> Result<AnonymizedData, SecurityError>;
```

### 5. Network API (Network API)

#### Intelligent Network Management
```typescript
interface NetworkAPI {
  // AI network optimization
  optimizeConnection(requirements: QoSRequirements): Promise<Connection>;
  
  // Predictive caching
  enablePredictiveCache(patterns: UsagePattern[]): Promise<void>;
  
  // Secure communication
  establishSecureChannel(peer: PeerInfo): Promise<SecureChannel>;
  
  // P2P collaboration
  joinP2PNetwork(networkId: string): Promise<P2PSession>;
}
```

## AI Enhanced Features
## LLM Orchestration & Billing (New)

To keep system boundaries clear and Apps lightweight, ByenatOS centrally handles external LLM calls and billing. Apps only submit questions and render results.

### Capabilities
- **PSP Fusion**: Compose prompts on the system side (PSP + runtime context)
- **Model Orchestration**: Select suitable external models (e.g., `gpt-4o`, `claude-3`)
- **Usage & Billing**: Track tokens/latency and aggregate by tenant/user
- **Result Archival**: Convert QnA to HiNATA (Question→Highlight, Answer→Note) to drive PSP iteration

### REST APIs

```
POST /api/llm/chat
Body: {
  "Question": string,
  "Context"?: object,
  "ModelPreference"?: { "Provider"?: "openai"|"anthropic"|"auto", "Model"?: string },
  "UserProvidedApiKey"?: string, // required when user enforces self-chosen model
  "Format"?: "text"|"markdown"|"json"
}

Response: {
  "Answer": string,
  "Usage": { "PromptTokens": number, "CompletionTokens": number, "TotalTokens": number, "LatencyMs": number },
  "Billing": { "Currency": "USD", "EstimatedCost": number, "EstimatedSavingPercent"?: number, "Fee"?: number },
  "RoutingDecision"?: { "SelectedModel": string, "Reason": string, "Alternatives"?: string[] },
  "PromptProfileUsed"?: { "Vendor": string, "Profile": string },
  "Hinata": { "Id": string, "Highlight": string, "Note": string }
}

GET /api/billing/usage?UserId=...&AppId=...&From=ISODate&To=ISODate
Response: {
  "Summary": { "TotalRequests": number, "TotalTokens": number, "TotalCost": number, "Currency": "USD" },
  "Breakdown": Array<{ "Date": string, "Requests": number, "Tokens": number, "Cost": number }>
}
```

### Best Practices
- Apps should not hold external model API keys
- Route all conversations via `POST /api/llm/chat` for unified billing and compliance
- Significant conversations will generate HiNATA for personalization learning
- When user provides `UserProvidedApiKey` and enforces a specific model, no service fee is charged; if Auto does not save cost, the fee is also 0

### PSP API Scope (New)

To support multi-App PSP sharing under the same account, PSP APIs accept a scope parameter and optional App overlay:

```
GET /api/psp/current?UserId=...&AppId=...&Scope=account|app

Notes:
- Scope=account (default): return the account-level shared PSP
- Scope=app: return the composed PSP (account PSP + specified App overlay)
```

App overlays are declared via HiNATA submissions or configuration endpoints and are composed during prompt generation.


### 1. Context-Aware API
```typescript
interface ContextAPI {
  // Get current context
  getCurrentContext(): Promise<ApplicationContext>;
  
  // Predict user intent
  predictUserIntent(history: ActionHistory): Promise<IntentPrediction>;
  
  // Environment awareness
  getEnvironmentInfo(): Promise<EnvironmentContext>;
}
```

### 2. Learning and Adaptation API
```typescript
interface LearningAPI {
  // User behavior learning
  learnUserBehavior(actions: UserAction[]): Promise<void>;
  
  // Performance optimization learning
  optimizePerformance(metrics: PerformanceMetrics): Promise<OptimizationPlan>;
  
  // Personalized recommendations
  getPersonalizedRecommendations(context: UserContext): Promise<Recommendation[]>;
}
```

### 3. Automation API
```typescript
interface AutomationAPI {
  // Create smart automation
  createSmartAutomation(trigger: AutomationTrigger, actions: Action[]): Promise<AutomationId>;
  
  // Workflow optimization
  optimizeWorkflow(workflow: Workflow): Promise<OptimizedWorkflow>;
  
  // Batch operation suggestions
  suggestBatchOperations(files: FileInfo[]): Promise<BatchOperation[]>;
}
```

## Developer Tools API

### 1. Debugging and Analysis
```typescript
interface DeveloperAPI {
  // AI code analysis
  analyzeCode(code: string, language: string): Promise<CodeAnalysis>;
  
  // Performance analysis
  profileApplication(appId: string): Promise<PerformanceProfile>;
  
  // Intelligent error diagnosis
  diagnoseError(error: Error, context: ErrorContext): Promise<Diagnosis>;
}
```

### 2. Application Market API
```typescript
interface AppStoreAPI {
  // Intelligent app recommendations
  recommendApps(userProfile: UserProfile): Promise<AppRecommendation[]>;
  
  // Automatic update management
  manageAutoUpdates(preferences: UpdatePreferences): Promise<void>;
  
  // Compatibility check
  checkCompatibility(appId: string): Promise<CompatibilityReport>;
}
```

## Error Handling

### Error Types
```rust
#[derive(Debug)]
pub enum SystemError {
    InvalidParameter(String),
    PermissionDenied,
    ResourceExhausted,
    AIServiceUnavailable,
    NetworkError(NetworkErrorType),
    SecurityViolation(SecurityError),
    HardwareFailure(HardwareError),
}
```

### Error Recovery
```typescript
interface ErrorRecoveryAPI {
  // Intelligent error recovery
  recoverFromError(error: SystemError): Promise<RecoveryResult>;
  
  // Smart retry mechanism
  enableSmartRetry(operation: Operation): Promise<void>;
  
  // Failure prediction
  predictFailure(system: SystemComponent): Promise<FailurePrediction>;
}
```

## Performance and Optimization

### Performance Metrics
- **API Response Time**: < 10ms (Local call)
- **AI Service Latency**: < 100ms (Lightweight model)
- **Memory Usage**: Minimize memory allocation
- **Power Efficiency**: AI-optimized power management

### Best Practices
1. **Batch Operations**: Use batch APIs as much as possible
2. **Asynchronous Programming**: Use async/await pattern
3. **Caching Strategy**: Utilize AI predictive caching
4. **Error Handling**: Implement a complete error recovery mechanism
5. **Performance Monitoring**: Use built-in performance analysis tools

## Compatibility

### Backward Compatibility
- Supports traditional POSIX APIs
- Linux system call compatibility layer
- Windows API compatibility layer (partial)

### Cross-Platform Support
- x86_64 and ARM64 architectures
- Containerized application support
- Web application compatibility

## Security Considerations

### API Permissions
- Capability-based security model
- Principle of least privilege
- Dynamic permission management
- AI-assisted permission suggestions

### Data Protection
- End-to-end encrypted API calls
- Local-first data processing
- Privacy-protected AI training
- User-controlled data streams