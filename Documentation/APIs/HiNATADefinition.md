# HiNATA App集成API文档

## 概述

本文档描述了App如何集成到ByenatOS系统并使用HiNATA数据处理服务。所有集成到ByenatOS的App都必须遵循HiNATA标准格式，并通过指定的API与系统进行交互。

## 核心要求

### 1. HiNATA格式标准
所有App都必须能够：
- **生成**标准HiNATA格式数据
- **接收**经过ByenatOS优化的HiNATA数据
- **处理**HiNATA数据的增强字段

### 2. API集成要求
- 使用统一的传输协议
- 实现错误处理机制
- 支持批量数据传输
- 遵循认证和安全标准

## HiNATA标准格式

### App端输出格式（必需字段）

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "用户高亮的文本",
  "note": "用户添加的评论或描述",
  "address": "资源地址或标识符",
  "tag": ["用户添加的基础标签"],
  "access": "private|public|shared",
  "raw_data": {
    "original_text": "原始完整文本",
    "user_context": "用户操作上下文",
    "app_metadata": "App特有的元数据"
  }
}
```

### ByenatOS增强后格式（返回字段）

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "用户高亮的文本",
  "note": "用户添加的评论或描述",
  "address": "资源地址或标识符",
  "tag": ["基础标签", "系统生成标签"],
  "access": "private",
  "enhanced_tags": ["AI生成的语义标签"],
  "recommended_highlights": ["从note中提取的推荐片段"],
  "semantic_analysis": {
    "main_topics": ["主要话题"],
    "sentiment": "情感倾向",
    "complexity_level": "复杂度级别",
    "key_concepts": ["关键概念"]
  },
  "cluster_id": "相关内容聚类ID",
  "priority_score": 0.85,
  "psp_relevance": 0.92,
  "embedding_vector": [0.1, 0.2, ...],
  "metadata": {
    "confidence": 0.95,
    "processing_time": "0.1s",
    "version": "1.0",
    "optimization_level": "enhanced",
    "ai_enhanced": true
  }
}
```

## API接口规范

### 1. 注册App到ByenatOS

**端点**: `POST /api/apps/register`

**请求体**:
```json
{
  "app_id": "your_app_name",
  "app_version": "1.0.0",
  "app_description": "App功能描述",
  "supported_data_types": ["text", "image", "audio"],
  "hinata_capabilities": {
    "can_generate": true,
    "can_receive_enhanced": true,
    "supported_fields": ["highlight", "note", "tag", "address"]
  }
}
```

**响应**:
```json
{
  "status": "success",
  "app_token": "your_app_authentication_token",
  "api_endpoints": {
    "submit_hinata": "/api/hinata/submit",
    "get_enhanced": "/api/hinata/enhanced",
    "batch_process": "/api/hinata/batch"
  }
}
```

### 2. 提交HiNATA数据处理

**端点**: `POST /api/hinata/submit`

**请求头**:
```
Authorization: Bearer {app_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "app_id": "your_app_name",
  "user_id": "user_identifier",
  "hinata_batch": [
    {
      "id": "hinata_20241201_001",
      "timestamp": "2024-12-01T10:30:00Z",
      "source": "your_app_name",
      "highlight": "用户选择的重要内容",
      "note": "用户的长篇笔记，可能包含多个要点和详细说明...",
      "address": "https://example.com/resource",
      "tag": ["学习", "技术"],
      "access": "private",
      "raw_data": {
        "original_text": "完整的原文内容",
        "user_context": "用户当前的操作环境",
        "app_metadata": {
          "app_specific_field": "App特有数据"
        }
      }
    }
  ],
  "processing_options": {
    "enable_ai_enhancement": true,
    "extract_highlights": true,
    "generate_semantic_tags": true,
    "priority_level": "normal"
  }
}
```

**响应**:
```json
{
  "status": "success",
  "job_id": "processing_job_12345",
  "estimated_completion": "2024-12-01T10:31:00Z",
  "processed_count": 1,
  "message": "HiNATA数据已提交处理"
}
```

### 3. 获取增强后的HiNATA数据

**端点**: `GET /api/hinata/enhanced/{job_id}`

**请求头**:
```
Authorization: Bearer {app_token}
```

**响应**:
```json
{
  "status": "completed",
  "job_id": "processing_job_12345",
  "enhanced_hinata": [
    {
      "id": "hinata_20241201_001",
      "timestamp": "2024-12-01T10:30:00Z",
      "source": "your_app_name",
      "highlight": "用户选择的重要内容",
      "note": "用户的长篇笔记，可能包含多个要点和详细说明...",
      "address": "https://example.com/resource",
      "tag": ["学习", "技术", "AI增强标签"],
      "access": "private",
      "enhanced_tags": ["人工智能", "深度学习", "技术发展"],
      "recommended_highlights": [
        "深度学习在现代AI中的核心作用",
        "技术发展对社会的深远影响",
        "未来AI应用的主要方向"
      ],
      "semantic_analysis": {
        "main_topics": ["人工智能", "技术发展", "社会影响"],
        "sentiment": "positive",
        "complexity_level": "intermediate",
        "key_concepts": ["深度学习", "AI应用", "技术趋势"]
      },
      "cluster_id": "cluster_ai_tech_123",
      "priority_score": 0.85,
      "psp_relevance": 0.92,
      "embedding_vector": [0.1, 0.2, 0.3, ...],
      "metadata": {
        "confidence": 0.95,
        "processing_time": "0.8s",
        "version": "1.0",
        "optimization_level": "enhanced",
        "ai_enhanced": true
      }
    }
  ],
  "processing_metrics": {
    "total_processed": 1,
    "ai_enhancements_added": 8,
    "highlights_extracted": 3,
    "processing_time": "0.8s"
  }
}
```

### 4. 实时获取推荐内容

**端点**: `GET /api/hinata/recommendations`

**请求参数**:
```
user_id: 用户ID
limit: 返回数量限制（默认10）
psp_context: 当前PSP上下文（可选）
```

**响应**:
```json
{
  "status": "success",
  "recommendations": [
    {
      "hinata_id": "hinata_20241201_001",
      "relevance_score": 0.92,
      "reason": "与当前PSP高度相关",
      "highlight": "推荐的关键内容",
      "source": "browser_app"
    }
  ]
}
```

## App端实现指南

### 1. HiNATA数据生成

```python
class HinataGenerator:
    def __init__(self, app_id):
        self.app_id = app_id
    
    def create_hinata(self, user_data):
        """创建标准HiNATA格式数据"""
        return {
            "id": self.generate_id(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": self.app_id,
            "highlight": user_data.get("selected_text", ""),
            "note": user_data.get("user_note", ""),
            "address": user_data.get("resource_url", ""),
            "tag": user_data.get("user_tags", []),
            "access": user_data.get("privacy", "private"),
            "raw_data": {
                "original_text": user_data.get("full_text", ""),
                "user_context": user_data.get("context", ""),
                "app_metadata": user_data.get("app_data", {})
            }
        }
    
    def generate_id(self):
        """生成唯一的HiNATA ID"""
        timestamp = int(time.time())
        return f"hinata_{self.app_id}_{timestamp}_{random.randint(1000, 9999)}"
```

### 2. API客户端实现

```python
class ByenatOSClient:
    def __init__(self, app_token, base_url="https://api.byenatos.local"):
        self.app_token = app_token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {app_token}",
            "Content-Type": "application/json"
        }
    
    async def submit_hinata_batch(self, hinata_list, user_id):
        """提交HiNATA批量数据"""
        payload = {
            "app_id": self.app_id,
            "user_id": user_id,
            "hinata_batch": hinata_list,
            "processing_options": {
                "enable_ai_enhancement": True,
                "extract_highlights": True,
                "generate_semantic_tags": True
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/hinata/submit",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def get_enhanced_hinata(self, job_id):
        """获取增强后的HiNATA数据"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/hinata/enhanced/{job_id}",
                headers=self.headers
            ) as response:
                return await response.json()
```

### 3. 错误处理

```python
class HinataError(Exception):
    pass

class ValidationError(HinataError):
    pass

class ProcessingError(HinataError):
    pass

def handle_api_response(response):
    """处理API响应和错误"""
    if response.get("status") == "error":
        error_type = response.get("error_type", "unknown")
        error_message = response.get("message", "Unknown error")
        
        if error_type == "validation":
            raise ValidationError(error_message)
        elif error_type == "processing":
            raise ProcessingError(error_message)
        else:
            raise HinataError(error_message)
    
    return response
```

## 最佳实践

### 1. 数据质量保证
- **完整性检查**: 确保所有必需字段都存在
- **格式验证**: 验证时间戳、URL等字段格式
- **内容质量**: 提供有意义的highlight和note内容

### 2. 性能优化
- **批量提交**: 积累多个HiNATA后批量提交
- **异步处理**: 使用异步API避免阻塞用户界面
- **缓存机制**: 缓存频繁访问的增强数据

### 3. 用户体验
- **实时反馈**: 显示处理进度和状态
- **智能推荐**: 利用增强后的数据提供个性化推荐
- **无缝集成**: 让HiNATA处理对用户透明

### 4. 隐私保护
- **数据加密**: 传输和存储时加密敏感数据
- **权限控制**: 严格控制数据访问权限
- **用户同意**: 明确告知用户数据处理方式

## 示例场景

### 浏览器扩展集成
```javascript
// 用户高亮文本时创建HiNATA
function onTextHighlight(selectedText, pageUrl) {
    const hinata = {
        id: generateId(),
        timestamp: new Date().toISOString(),
        source: "browser_extension",
        highlight: selectedText,
        note: "",
        address: pageUrl,
        tag: [],
        access: "private",
        raw_data: {
            original_text: document.body.innerText,
            user_context: window.location.href,
            app_metadata: {
                page_title: document.title,
                selection_time: Date.now()
            }
        }
    };
    
    submitToByenatOS([hinata]);
}
```

### 笔记应用集成
```python
# 用户保存笔记时创建HiNATA
def save_note(note_content, user_tags):
    hinata = {
        "id": generate_id(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "notes_app",
        "highlight": extract_key_sentence(note_content),
        "note": note_content,
        "address": f"notes://note_{note_id}",
        "tag": user_tags,
        "access": "private",
        "raw_data": {
            "original_text": note_content,
            "user_context": "note_creation",
            "app_metadata": {
                "note_type": "personal",
                "creation_method": "manual"
            }
        }
    }
    
    # 提交到ByenatOS进行AI增强
    client.submit_hinata_batch([hinata], user_id)
```

## 总结

通过遵循这个API规范，App可以：
1. **标准化集成** - 使用统一的HiNATA格式
2. **AI增强** - 获得语义标签和推荐highlights
3. **智能优化** - 利用ByenatOS的全局优化能力
4. **无缝体验** - 为用户提供增强的个性化体验

这种设计确保了所有App都能受益于ByenatOS的AI增强能力，同时保持了系统的一致性和可扩展性。