# HiNATA 文件格式规范

## 概述

HiNATA (Highlight, Note, Address, Tag, Access) 是ByenatOS操作系统的核心数据格式，用于收集和管理用户的个性化信息。本规范定义了HiNATA文件的格式、存储方式和处理流程。

## 文件格式选择

### 主格式：JSON Lines (JSONL)

**选择理由**：
- **大模型友好**：JSON格式易于大语言模型解析和处理
- **流式处理**：支持逐行读取，适合大量数据处理
- **扩展性**：易于添加新字段而不破坏现有数据
- **压缩友好**：LZ4压缩效果良好，减少存储空间

### 文件扩展名
- 主文件：`.hinata` 或 `.jsonl`
- 压缩文件：`.hinata.lz4`
- 索引文件：`.hinata.idx`

## 数据格式规范

### 基础字段

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "用户重点关注或标记的内容",
  "note": "用户添加的笔记和注释信息",
  "address": "数据来源的地址或位置信息",
  "tag": ["分类", "检索标签"],
  "access": "public|private|restricted",
  "embedding_vector": [0.1, 0.2, ...],
  "metadata": {
    "confidence": 0.95,
    "processing_time": "0.1s",
    "version": "1.0"
  }
}
```

### 字段详细说明

#### 必需字段

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `id` | string | 唯一标识符 | "hinata_20241201_001" |
| `timestamp` | string | ISO 8601时间戳 | "2024-12-01T10:30:00Z" |
| `source` | string | 数据来源应用 | "browser", "email", "calendar" |
| `highlight` | string | 用户主动标记的内容片段 | "重要会议安排" |
| `note` | string | 用户添加的详细内容或评论 | "需要准备演示材料" |
| `address` | string | 数据来源地址 | "https://example.com/meeting" |
| `tag` | array | 分类标签数组 | ["工作", "会议", "重要"] |
| `access` | string | 访问权限级别 | "public", "private", "restricted" |

#### Highlight和Note的具象定义

**Highlight（高亮）**：
- **定义**：用户主动标记、选择或关注的内容片段，通常是信息的"标题"或"关键词"
- **特征**：简洁、突出、具有标识性
- **作用**：作为信息的快速识别和检索入口

**Note（笔记）**：
- **定义**：用户添加的详细内容、评论、解释或完整信息
- **特征**：详细、完整、具有解释性
- **作用**：提供完整的信息内容和上下文

#### 典型应用场景示例

**场景1：文章阅读**
```json
{
  "highlight": "人工智能在医疗领域的应用前景广阔",
  "note": "这个观点很有道理，AI确实能提高诊断准确性，但需要考虑伦理问题"
}
```

**场景2：文章收藏**
```json
{
  "highlight": "《人工智能发展报告2024》",
  "note": "完整文章内容：人工智能技术在过去一年中取得了重大突破...（全文）"
}
```

**场景3：照片记录**
```json
{
  "highlight": "团队建设活动合影",
  "note": "照片内容：团队成员在户外进行团建活动，大家都很开心"
}
```

**场景4：评论嵌套**
```json
{
  "highlight": "这个观点很有道理，AI确实能提高诊断准确性，但需要考虑伦理问题",
  "note": "同意，特别是数据隐私保护方面需要更多关注"
}
```

#### 可选字段

| 字段名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| `embedding_vector` | array | 向量表示 | [0.1, 0.2, 0.3, ...] |
| `metadata` | object | 元数据信息 | 见下方详细说明 |

### 元数据字段

```json
{
  "confidence": 0.95,
  "processing_time": "0.1s",
  "version": "1.0",
  "user_id": "user_123",
  "session_id": "session_456",
  "device_info": {
    "platform": "macOS",
    "app_version": "1.2.3"
  },
  "context": {
    "location": "office",
    "time_of_day": "morning",
    "activity": "work"
  }
}
```

## 存储架构

### 文件组织

```
/data/hinata/
├── raw/                    # 原始HiNATA文件
│   ├── 2024/
│   │   ├── 12/
│   │   │   ├── 01/
│   │   │   │   ├── hinata_20241201_001.hinata
│   │   │   │   ├── hinata_20241201_002.hinata
│   │   │   │   └── ...
├── processed/              # 处理后的文件
│   ├── embeddings/         # 向量数据
│   ├── compressed/         # 压缩文件
│   └── indexed/           # 索引文件
└── database/              # 数据库文件
    ├── hinata.db          # SQLite主数据库
    └── vectors.faiss      # FAISS向量数据库
```

### 压缩策略

**LZ4压缩**：
- 压缩比：约2-3倍
- 解压速度：极快
- 内存占用：低
- 适用场景：实时读写

**压缩命令示例**：
```bash
# 压缩
lz4 hinata_20241201_001.hinata hinata_20241201_001.hinata.lz4

# 解压
lz4 -d hinata_20241201_001.hinata.lz4 hinata_20241201_001.hinata
```

## 处理流程

### 1. 数据接收
```python
def receive_hinata_data(data_stream):
    """接收HiNATA数据流"""
    for line in data_stream:
        hinata_record = json.loads(line)
        validate_hinata_format(hinata_record)
        store_hinata_record(hinata_record)
```

### 2. 格式验证
```python
def validate_hinata_format(record):
    """验证HiNATA格式"""
    required_fields = ['id', 'timestamp', 'source', 'highlight', 'note', 'address', 'tag', 'access']
    
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    
    # 验证时间戳格式
    datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
    
    # 验证访问权限
    valid_access = ['public', 'private', 'restricted']
    if record['access'] not in valid_access:
        raise ValueError(f"Invalid access level: {record['access']}")
```

### 3. Embedding生成
```python
def generate_embedding(hinata_record):
    """生成HiNATA记录的向量表示"""
    text_content = f"{hinata_record['highlight']} {hinata_record['note']}"
    
    # 使用本地大模型生成embedding
    embedding = local_llm.embed(text_content)
    
    return {
        **hinata_record,
        'embedding_vector': embedding.tolist()
    }
```

### 4. 向量存储
```python
def store_embedding(hinata_record):
    """存储embedding到向量数据库"""
    # 存储到FAISS
    faiss_index.add(np.array([hinata_record['embedding_vector']]))
    
    # 存储到SQLite用于快速检索
    db.execute("""
        INSERT INTO hinata_embeddings 
        (id, embedding, timestamp, source) 
        VALUES (?, ?, ?, ?)
    """, (hinata_record['id'], 
          json.dumps(hinata_record['embedding_vector']),
          hinata_record['timestamp'],
          hinata_record['source']))
```

## 性能优化

### 批量处理
```python
def batch_process_hinata(batch_size=1000):
    """批量处理HiNATA数据"""
    batch = []
    
    for record in hinata_stream:
        batch.append(record)
        
        if len(batch) >= batch_size:
            process_batch(batch)
            batch = []
    
    # 处理剩余记录
    if batch:
        process_batch(batch)
```

### 内存管理
```python
def stream_process_hinata(file_path):
    """流式处理HiNATA文件"""
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line)
            yield process_single_record(record)
```

## 安全考虑

### 数据加密
- 敏感字段使用AES-256加密
- 密钥存储在硬件安全模块(HSM)中
- 传输过程使用TLS加密

### 访问控制
- 基于用户权限的数据访问
- 审计日志记录所有访问
- 数据脱敏处理

## 版本兼容性

### 版本管理
- 主版本号：格式重大变更
- 次版本号：新增字段
- 修订号：bug修复

### 向后兼容
- 新版本必须支持旧格式
- 缺失字段使用默认值
- 版本检测和自动升级

## 示例文件

### 基础示例
```json
{"id":"hinata_20241201_001","timestamp":"2024-12-01T10:30:00Z","source":"browser","highlight":"人工智能在医疗领域的应用前景广阔","note":"这个观点很有道理，AI确实能提高诊断准确性，但需要考虑伦理问题","address":"https://example.com/ai-medical","tag":["AI","医疗","伦理"],"access":"private","metadata":{"confidence":0.95,"processing_time":"0.1s","version":"1.0"}}
```

### 完整示例
```json
{"id":"hinata_20241201_002","timestamp":"2024-12-01T11:00:00Z","source":"reader","highlight":"《人工智能发展报告2024》","note":"完整文章内容：人工智能技术在过去一年中取得了重大突破，特别是在自然语言处理、计算机视觉和强化学习等领域。这些进展为各行各业带来了新的机遇和挑战...（完整文章内容）","address":"https://example.com/ai-report-2024","tag":["AI","报告","技术"],"access":"restricted","embedding_vector":[0.1,0.2,0.3,0.4,0.5],"metadata":{"confidence":0.98,"processing_time":"0.15s","version":"1.0","user_id":"user_123","session_id":"session_456","device_info":{"platform":"macOS","app_version":"1.2.3"},"context":{"location":"office","time_of_day":"morning","activity":"work"}}}
```

### 照片记录示例
```json
{"id":"hinata_20241201_003","timestamp":"2024-12-01T12:00:00Z","source":"camera","highlight":"团队建设活动合影","note":"照片内容：团队成员在户外进行团建活动，大家都很开心，背景是美丽的山景，天气晴朗","address":"file:///photos/team-building.jpg","tag":["团队","活动","照片"],"access":"private","metadata":{"confidence":0.99,"processing_time":"0.2s","version":"1.0"}}
```

### 评论嵌套示例
```json
{"id":"hinata_20241201_004","timestamp":"2024-12-01T13:00:00Z","source":"social","highlight":"这个观点很有道理，AI确实能提高诊断准确性，但需要考虑伦理问题","note":"同意，特别是数据隐私保护方面需要更多关注，建议制定更严格的数据使用规范","address":"https://social.com/post/123","tag":["AI","伦理","隐私"],"access":"public","metadata":{"confidence":0.97,"processing_time":"0.12s","version":"1.0"}}
```

## 工具和库

### 推荐工具
- **压缩**：lz4, zstandard
- **数据库**：SQLite, PostgreSQL
- **向量数据库**：FAISS, Chroma, Pinecone
- **处理框架**：Apache Arrow, Pandas

### 开发库
```python
# HiNATA处理库
pip install hinata-processor

# 向量处理
pip install faiss-cpu  # 或 faiss-gpu
pip install chromadb

# 压缩库
pip install lz4
pip install zstandard
```

## 最佳实践

### 性能优化
1. 使用批量处理减少I/O操作
2. 启用压缩减少存储空间
3. 建立合适的索引提高查询速度
4. 定期清理过期数据

### 数据质量
1. 严格验证数据格式
2. 记录数据质量指标
3. 建立数据血缘追踪
4. 定期数据质量检查

### 监控和日志
1. 记录处理时间和性能指标
2. 监控存储空间使用情况
3. 设置错误告警机制
4. 定期生成处理报告 