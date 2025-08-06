# HiNATA File Format Specification

## Overview

HiNATA (Highlight, Note, Address, Tag, Access) is the core data format of the ByenatOS operating system, used for collecting and managing user personalized information. This specification defines the format, storage method, and processing flow of HiNATA files.

## File Format Selection

### Main Format: JSON Lines (JSONL)

**Selection Reasons**:
- **Large Model Friendly**: JSON format is easy for large language models to parse and process
- **Streaming Processing**: Supports line-by-line reading, suitable for large-scale data processing
- **Extensibility**: Easy to add new fields without breaking existing data
- **Compression Friendly**: Good LZ4 compression effect, reducing storage space

### File Extensions
- Main file: `.hinata` or `.jsonl`
- Compressed file: `.hinata.lz4`
- Index file: `.hinata.idx`

## Data Format Specification

### Basic Fields

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "Content that users focus on or mark",
  "note": "Notes and annotation information added by users",
  "address": "Address or location information of data source",
  "tag": ["category", "retrieval_tag"],
  "access": "public|private|restricted",
  "embedding_vector": [0.1, 0.2, ...],
  "metadata": {
    "confidence": 0.95,
    "processing_time": "0.1s",
    "version": "1.0"
  }
}
```

### Field Detailed Description

#### Required Fields

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `id` | string | Unique identifier | "hinata_20241201_001" |
| `timestamp` | string | ISO 8601 timestamp | "2024-12-01T10:30:00Z" |
| `source` | string | Data source application | "browser", "email", "calendar" |
| `highlight` | string | Content fragment actively marked by user | "Important meeting arrangement" |
| `note` | string | Detailed content or comments added by user | "Need to prepare presentation materials" |
| `address` | string | Data source address | "https://example.com/meeting" |
| `tag` | array | Classification tag array | ["work", "meeting", "important"] |
| `access` | string | Access permission level | "public", "private", "restricted" |

#### Concrete Definition of Highlight and Note

**Highlight**:
- **Definition**: Content fragments that users actively mark, select, or focus on, usually the "title" or "keywords" of information
- **Characteristics**: Concise, prominent, identifiable
- **Function**: Serves as a quick identification and retrieval entry point for information

**Note**:
- **Definition**: Detailed content, comments, explanations, or complete information added by users
- **Characteristics**: Detailed, complete, explanatory
- **Function**: Provides complete information content and context

#### Typical Application Scenario Examples

**Scenario 1: Article Reading**
```json
{
  "highlight": "Artificial intelligence has broad application prospects in the medical field",
  "note": "This point makes sense, AI can indeed improve diagnostic accuracy, but ethical issues need to be considered"
}
```

**Scenario 2: Article Collection**
```json
{
  "highlight": "《Artificial Intelligence Development Report 2024》",
  "note": "Complete article content: Artificial intelligence technology has made major breakthroughs in the past year... (full text)"
}
```

**Scenario 3: Photo Recording**
```json
{
  "highlight": "Team building activity group photo",
  "note": "Photo content: Team members conducting team building activities outdoors, everyone is very happy"
}
```

**Scenario 4: Nested Comments**
```json
{
  "highlight": "This point makes sense, AI can indeed improve diagnostic accuracy, but ethical issues need to be considered",
  "note": "Agree, especially data privacy protection needs more attention, suggest stricter data usage standards"
}
```

#### Optional Fields

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `embedding_vector` | array | Vector representation | [0.1, 0.2, 0.3, ...] |
| `metadata` | object | Metadata information | See detailed description below |

### Metadata Fields

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

## Storage Architecture

### File Organization

```
/data/hinata/
├── raw/                    # Raw HiNATA files
│   ├── 2024/
│   │   ├── 12/
│   │   │   ├── 01/
│   │   │   │   ├── hinata_20241201_001.hinata
│   │   │   │   ├── hinata_20241201_002.hinata
│   │   │   │   └── ...
├── processed/              # Processed files
│   ├── embeddings/         # Vector data
│   ├── compressed/         # Compressed files
│   └── indexed/           # Index files
└── database/              # Database files
    ├── hinata.db          # SQLite main database
    └── vectors.faiss      # FAISS vector database
```

### Compression Strategy

**LZ4 Compression**:
- Compression Ratio: Approx. 2-3x
- Decompression Speed: Extremely fast
- Memory Usage: Low
- Applicable Scenarios: Real-time read/write

**Compression Command Example**:
```bash
# Compress
lz4 hinata_20241201_001.hinata hinata_20241201_001.hinata.lz4

# Decompress
lz4 -d hinata_20241201_001.hinata.lz4 hinata_20241201_001.hinata
```

## Processing Flow

### 1. Data Reception
```python
def receive_hinata_data(data_stream):
    """Receives HiNATA data stream"""
    for line in data_stream:
        hinata_record = json.loads(line)
        validate_hinata_format(hinata_record)
        store_hinata_record(hinata_record)
```

### 2. Format Validation
```python
def validate_hinata_format(record):
    """Validates HiNATA format"""
    required_fields = ['id', 'timestamp', 'source', 'highlight', 'note', 'address', 'tag', 'access']
    
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate timestamp format
    datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
    
    # Validate access permission
    valid_access = ['public', 'private', 'restricted']
    if record['access'] not in valid_access:
        raise ValueError(f"Invalid access level: {record['access']}")
```

### 3. Embedding Generation
```python
def generate_embedding(hinata_record):
    """Generates vector representation for HiNATA record"""
    text_content = f"{hinata_record['highlight']} {hinata_record['note']}"
    
    # Use local large model to generate embedding
    embedding = local_llm.embed(text_content)
    
    return {
        **hinata_record,
        'embedding_vector': embedding.tolist()
    }
```

### 4. Vector Storage
```python
def store_embedding(hinata_record):
    """Stores embedding into vector database"""
    # Store in FAISS
    faiss_index.add(np.array([hinata_record['embedding_vector']]))
    
    # Store in SQLite for quick retrieval
    db.execute("""
        INSERT INTO hinata_embeddings 
        (id, embedding, timestamp, source) 
        VALUES (?, ?, ?, ?)
    """, (hinata_record['id'], 
          json.dumps(hinata_record['embedding_vector']),
          hinata_record['timestamp'],
          hinata_record['source']))
```

## Performance Optimization

### Batch Processing
```python
def batch_process_hinata(batch_size=1000):
    """Batch processes HiNATA data"""
    batch = []
    
    for record in hinata_stream:
        batch.append(record)
        
        if len(batch) >= batch_size:
            process_batch(batch)
            batch = []
    
    # Process remaining records
    if batch:
        process_batch(batch)
```

### Memory Management
```python
def stream_process_hinata(file_path):
    """Streams HiNATA file"""
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line)
            yield process_single_record(record)
```

## Security Considerations

### Data Encryption
- Sensitive fields encrypted using AES-256
- Keys stored in Hardware Security Module (HSM)
- Transmission encrypted using TLS

### Access Control
- Data access based on user permissions
- Audit logs for all accesses
- Data de-sensitization

## Version Compatibility

### Version Management
- Major version: Major format changes
- Minor version: New fields
- Revision number: Bug fixes

### Backward Compatibility
- New versions must support old formats
- Missing fields use default values
- Version detection and automatic upgrade

## Example Files

### Basic Example
```json
{"id":"hinata_20241201_001","timestamp":"2024-12-01T10:30:00Z","source":"browser","highlight":"Artificial intelligence has broad application prospects in the medical field","note":"This point makes sense, AI can indeed improve diagnostic accuracy, but ethical issues need to be considered","address":"https://example.com/ai-medical","tag":["AI","medical","ethics"],"access":"private","metadata":{"confidence":0.95,"processing_time":"0.1s","version":"1.0"}}
```

### Complete Example
```json
{"id":"hinata_20241201_002","timestamp":"2024-12-01T11:00:00Z","source":"reader","highlight":"《Artificial Intelligence Development Report 2024》","note":"Complete article content: Artificial intelligence technology has made major breakthroughs in the past year... (full text)","address":"https://example.com/ai-report-2024","tag":["AI","report","technology"],"access":"restricted","embedding_vector":[0.1,0.2,0.3,0.4,0.5],"metadata":{"confidence":0.98,"processing_time":"0.15s","version":"1.0","user_id":"user_123","session_id":"session_456","device_info":{"platform":"macOS","app_version":"1.2.3"},"context":{"location":"office","time_of_day":"morning","activity":"work"}}}
```

### Photo Recording Example
```json
{"id":"hinata_20241201_003","timestamp":"2024-12-01T12:00:00Z","source":"camera","highlight":"Team building activity group photo","note":"Photo content: Team members conducting team building activities outdoors, everyone is very happy, background is beautiful mountain scenery, sunny weather","address":"file:///photos/team-building.jpg","tag":["team","activity","photo"],"access":"private","metadata":{"confidence":0.99,"processing_time":"0.2s","version":"1.0"}}
```

### Nested Comment Example
```json
{"id":"hinata_20241201_004","timestamp":"2024-12-01T13:00:00Z","source":"social","highlight":"This point makes sense, AI can indeed improve diagnostic accuracy, but ethical issues need to be considered","note":"Agree, especially data privacy protection needs more attention, suggest stricter data usage standards","address":"https://social.com/post/123","tag":["AI","ethics","privacy"],"access":"public","metadata":{"confidence":0.97,"processing_time":"0.12s","version":"1.0"}}
```

## Tools and Libraries

### Recommended Tools
- **Compression**: lz4, zstandard
- **Database**: SQLite, PostgreSQL
- **Vector Database**: FAISS, Chroma, Pinecone
- **Processing Framework**: Apache Arrow, Pandas

### Development Libraries
```python
# HiNATA Processing Library
pip install hinata-processor

# Vector Processing
pip install faiss-cpu  # Or faiss-gpu
pip install chromadb

# Compression Library
pip install lz4
pip install zstandard
```

## Best Practices

### Performance Optimization
1. Use batch processing to reduce I/O operations
2. Enable compression to reduce storage space
3. Establish appropriate indexes for faster queries
4. Regularly clean up expired data

### Data Quality
1. Strictly validate data format
2. Record data quality metrics
3. Establish data lineage tracking
4. Regularly check data quality

### Monitoring and Logging
1. Record processing time and performance metrics
2. Monitor storage space usage
3. Set up error alert mechanisms
4. Regularly generate processing reports 