# ByenatOS 系统集成指南

## 概述

本文档提供了ByenatOS系统的完整集成指南，包括系统部署、组件配置、API集成和最佳实践。基于我们设计的HiNATA-PSP架构，本指南将帮助您成功部署和集成ByenatOS。

## 系统架构回顾

ByenatOS采用分层架构设计，核心组件包括：

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│  App生态层: Browser App, Notes App, Chat App, Custom Apps      │
├─────────────────────────────────────────────────────────────────┤
│  API网关层: AppIntegrationAPI.py                               │
├─────────────────────────────────────────────────────────────────┤
│  核心处理层:                                                     │
│  ├─ HiNATAProcessor.py (数据处理)                               │
│  ├─ PSPEngine.py (个性化引擎)                                   │
│  └─ StorageEngine.py (存储引擎)                                 │
├─────────────────────────────────────────────────────────────────┤
│  隐私保护层: PrivacyProtectionSystem.py                        │
├─────────────────────────────────────────────────────────────────┤
│  存储基础设施: Redis + PostgreSQL + ChromaDB + Elasticsearch    │
└─────────────────────────────────────────────────────────────────┘
```

## 环境要求

### 硬件要求

**最小配置**：
- CPU: 4核心 2.5GHz
- 内存: 8GB RAM
- 存储: 100GB SSD
- 网络: 1Gbps

**推荐配置**：
- CPU: 8核心 3.0GHz
- 内存: 16GB RAM
- 存储: 500GB NVMe SSD
- 网络: 10Gbps

**生产环境**：
- CPU: 16核心 3.5GHz
- 内存: 32GB RAM
- 存储: 1TB NVMe SSD (系统) + 10TB SSD (数据)
- 网络: 10Gbps with redundancy

### 软件依赖

**操作系统**：
- Linux (Ubuntu 22.04 LTS, CentOS 8+, 或 RHEL 8+)
- macOS 12+ (开发环境)
- Windows 11 with WSL2 (开发环境)

**核心组件**：
- Python 3.11+
- Redis 7.0+
- PostgreSQL 14+
- Elasticsearch 8.0+
- Docker 24.0+ & Docker Compose v2

**AI模型组件**：
- ONNX Runtime
- ChromaDB
- SentenceTransformers

## 快速部署

### 1. 使用Docker Compose部署（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # 核心服务
  byenatos-core:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_DSN=postgresql://byenatos:password@postgres:5432/byenatos
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - CHROMA_PERSIST_DIR=/data/chroma
      - COLD_STORAGE_PATH=/data/cold_storage
    volumes:
      - ./data:/data
      - ./config:/app/config
    depends_on:
      - redis
      - postgres
      - elasticsearch
    restart: unless-stopped

  # Redis (热数据层)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  # PostgreSQL (温数据层)
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=byenatos
      - POSTGRES_USER=byenatos
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    restart: unless-stopped

  # Elasticsearch (全文搜索)
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    restart: unless-stopped

  # Nginx (负载均衡和反向代理)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - byenatos-core
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  es_data:
```

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /data/chroma /data/cold_storage

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "ApplicationFramework.APIs.AppIntegrationAPI:create_app", \
     "--host", "0.0.0.0", "--port", "8080", "--factory"]
```

创建 `requirements.txt`：

```txt
# 核心框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# 数据库
asyncpg==0.29.0
aioredis==2.0.1
sqlalchemy==2.0.23

# AI/ML
torch==2.1.0
sentence-transformers==2.2.2
transformers==4.35.0
scikit-learn==1.3.2
numpy==1.24.3
spacy==3.7.2

# 搜索和向量
elasticsearch==8.11.0
chromadb==0.4.18

# 安全和加密
cryptography==41.0.7
PyJWT==2.8.0
bcrypt==4.1.1

# 数据处理
pandas==2.1.3
aiofiles==23.2.1

# 监控和日志
prometheus-client==0.19.0
structlog==23.2.0

# 开发工具
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
isort==5.12.0
```

### 2. 部署命令

```bash
# 1. 克隆代码
git clone https://github.com/byenatos/byenatos.git
cd byenatos

# 2. 创建配置文件
cp config/config.example.yaml config/config.yaml

# 3. 初始化数据库
docker-compose up -d postgres
sleep 10
docker-compose exec postgres psql -U byenatos -d byenatos -f /docker-entrypoint-initdb.d/init-db.sql

# 4. 启动所有服务
docker-compose up -d

# 5. 验证部署
curl http://localhost:8080/health
```

## 详细配置

### 1. 核心系统配置

创建 `config/config.yaml`：

```yaml
# ByenatOS 核心配置
system:
  name: "ByenatOS"
  version: "1.0.0"
  environment: "production"  # development, staging, production
  debug: false

# 数据库配置
database:
  redis:
    url: "redis://localhost:6379"
    pool_size: 10
    timeout: 30
  
  postgres:
    dsn: "postgresql://byenatos:password@localhost:5432/byenatos"
    pool_size: 20
    max_overflow: 30
    
  elasticsearch:
    url: "http://localhost:9200"
    timeout: 30
    max_retries: 3

# 存储配置
storage:
  cold_storage_path: "/data/cold_storage"
  chroma_persist_dir: "/data/chroma"
  cache_ttl: 3600
  
  # 分层存储阈值
  hot_tier:
    max_age_days: 7
    min_influence_weight: 0.7
  
  warm_tier:
    max_age_days: 30
    min_influence_weight: 0.3

# HiNATA处理配置
hinata_processing:
  batch_size: 100
  max_processing_time: 5.0
  cache_ttl: 3600
  priority_threshold: 0.8
  similarity_threshold: 0.7
  max_enhanced_tags: 10

# PSP配置
psp:
  similarity_threshold: 0.7
  confidence_threshold: 0.8
  update_frequency: "realtime"
  max_psp_size: 10000
  component_ttl: 2592000  # 30 days

# API配置
api:
  host: "0.0.0.0"
  port: 8080
  workers: 4
  
  # 速率限制
  rate_limiting:
    default_limit: 1000  # per hour
    burst_limit: 100    # per minute
  
  # CORS
  cors:
    allow_origins: ["*"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["*"]

# 隐私和安全
privacy:
  encryption_enabled: true
  pii_detection_enabled: true
  data_minimization_enabled: true
  access_logging_enabled: true
  
  # 默认数据保留期
  default_retention_days: 365
  
  # 审计配置
  audit:
    log_all_access: true
    log_retention_days: 90

# AI模型配置
ai_models:
  embedding_model: "all-MiniLM-L6-v2"
  nlp_model: "en_core_web_sm"
  
  # 模型缓存
  model_cache_size: 1000
  model_cache_ttl: 3600

# 监控配置
monitoring:
  prometheus:
    enabled: true
    port: 9090
    
  logging:
    level: "INFO"
    format: "json"
    file: "/var/log/byenatos/system.log"
    max_size: "100MB"
    backup_count: 10

# 部署配置
deployment:
  cluster_mode: false
  node_id: "node-1"
  
  # 健康检查
  health_check:
    interval: 30
    timeout: 10
    retries: 3
```

### 2. 数据库初始化脚本

创建 `init-db.sql`：

```sql
-- ByenatOS 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- HiNATA数据表
CREATE TABLE IF NOT EXISTS hinata_data (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source TEXT NOT NULL,
    highlight TEXT NOT NULL,
    note TEXT NOT NULL,
    address TEXT NOT NULL,
    tags JSONB,
    access_level TEXT NOT NULL,
    enhanced_tags JSONB,
    recommended_highlights JSONB,
    semantic_analysis JSONB,
    quality_score REAL,
    attention_weight REAL,
    psp_influence_weight REAL,
    embedding_vector JSONB,
    processing_metadata JSONB,
    storage_tier TEXT DEFAULT 'warm',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PSP组件表
CREATE TABLE IF NOT EXISTS psp_components (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    component_type TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding JSONB,
    confidence REAL NOT NULL,
    total_attention_weight REAL NOT NULL,
    normalized_weight REAL NOT NULL,
    priority TEXT NOT NULL,
    activation_threshold REAL NOT NULL,
    supporting_evidence JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activated TIMESTAMP WITH TIME ZONE,
    related_components JSONB,
    source_apps JSONB,
    evolution_history JSONB,
    PRIMARY KEY (id, user_id)
);

-- 用户PSP元信息表
CREATE TABLE IF NOT EXISTS user_psp (
    user_id TEXT PRIMARY KEY,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    total_components INTEGER NOT NULL,
    active_components JSONB
);

-- App注册表
CREATE TABLE IF NOT EXISTS app_registrations (
    app_id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    app_version TEXT NOT NULL,
    developer TEXT NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    webhook_url TEXT,
    rate_limit INTEGER DEFAULT 1000,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- 用户隐私偏好表
CREATE TABLE IF NOT EXISTS user_privacy_preferences (
    user_id TEXT PRIMARY KEY,
    policy_level TEXT NOT NULL,
    data_sharing_consent BOOLEAN NOT NULL,
    analytics_consent BOOLEAN NOT NULL,
    personalization_consent BOOLEAN NOT NULL,
    external_sharing_consent BOOLEAN NOT NULL,
    data_retention_days INTEGER NOT NULL,
    allowed_apps JSONB,
    blocked_apps JSONB,
    custom_permissions JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 数据访问日志表
CREATE TABLE IF NOT EXISTS data_access_logs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    accessor_id TEXT NOT NULL,
    accessor_type TEXT NOT NULL,
    data_type TEXT NOT NULL,
    data_id TEXT NOT NULL,
    access_type TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address TEXT,
    purpose TEXT,
    result TEXT NOT NULL
);

-- API调用日志表
CREATE TABLE IF NOT EXISTS api_call_logs (
    id SERIAL PRIMARY KEY,
    app_id TEXT NOT NULL,
    user_id TEXT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_time REAL NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 复合索引表
CREATE TABLE IF NOT EXISTS hinata_index (
    hinata_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    source TEXT NOT NULL,
    psp_influence_weight REAL NOT NULL,
    attention_weight REAL NOT NULL,
    quality_score REAL NOT NULL,
    storage_tier TEXT NOT NULL,
    tags JSONB,
    content_hash TEXT NOT NULL
);

-- 创建索引
-- HiNATA数据索引
CREATE INDEX IF NOT EXISTS idx_hinata_user_timestamp ON hinata_data(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_user_weight ON hinata_data(user_id, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_user_source ON hinata_data(user_id, source);
CREATE INDEX IF NOT EXISTS idx_hinata_enhanced_tags ON hinata_data USING GIN(enhanced_tags);
CREATE INDEX IF NOT EXISTS idx_hinata_timestamp ON hinata_data(timestamp DESC);

-- PSP组件索引
CREATE INDEX IF NOT EXISTS idx_psp_user_type ON psp_components(user_id, component_type);
CREATE INDEX IF NOT EXISTS idx_psp_user_priority ON psp_components(user_id, priority);
CREATE INDEX IF NOT EXISTS idx_psp_last_updated ON psp_components(user_id, last_updated DESC);

-- App注册索引
CREATE INDEX IF NOT EXISTS idx_app_api_key ON app_registrations(api_key);
CREATE INDEX IF NOT EXISTS idx_app_name ON app_registrations(app_name);
CREATE INDEX IF NOT EXISTS idx_app_created_at ON app_registrations(created_at DESC);

-- 访问日志索引
CREATE INDEX IF NOT EXISTS idx_access_logs_user_timestamp ON data_access_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_logs_accessor_timestamp ON data_access_logs(accessor_id, timestamp DESC);

-- API调用日志索引
CREATE INDEX IF NOT EXISTS idx_api_logs_app_timestamp ON api_call_logs(app_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint_timestamp ON api_call_logs(endpoint, created_at DESC);

-- 复合索引
CREATE INDEX IF NOT EXISTS idx_hinata_index_user_timestamp ON hinata_index(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_user_weight ON hinata_index(user_id, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_quality_weight ON hinata_index(quality_score DESC, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_content_hash ON hinata_index(content_hash);
CREATE INDEX IF NOT EXISTS idx_hinata_index_tags ON hinata_index USING GIN(tags);

-- 插入默认配置数据
INSERT INTO user_privacy_preferences (
    user_id, policy_level, data_sharing_consent, analytics_consent,
    personalization_consent, external_sharing_consent, data_retention_days,
    allowed_apps, blocked_apps, custom_permissions, created_at, updated_at
) VALUES (
    'default_template', 'balanced', false, false, true, false, 365,
    '[]', '[]', '{}', NOW(), NOW()
) ON CONFLICT (user_id) DO NOTHING;
```

### 3. Nginx配置

创建 `nginx.conf`：

```nginx
events {
    worker_connections 1024;
}

http {
    upstream byenatos_backend {
        server byenatos-core:8080;
    }
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
    
    server {
        listen 80;
        server_name localhost;
        
        # 重定向到HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name localhost;
        
        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        
        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
        
        # API接口
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://byenatos_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # 认证接口（更严格的限流）
        location /api/auth/ {
            limit_req zone=auth burst=5 nodelay;
            
            proxy_pass http://byenatos_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # 健康检查
        location /health {
            proxy_pass http://byenatos_backend;
            access_log off;
        }
        
        # 静态文件（如果有）
        location /static/ {
            root /var/www;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## App集成示例

### 1. Python App示例

```python
import asyncio
import aiohttp
import json
from datetime import datetime

class ByenatOSClient:
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    async def register_app(self, app_info: dict) -> dict:
        """注册App到ByenatOS"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/apps/register",
                json=app_info
            ) as response:
                return await response.json()
    
    async def submit_hinata_batch(self, user_id: str, hinata_list: list) -> dict:
        """提交HiNATA数据批次"""
        payload = {
            "app_id": "my_app",
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
                f"{self.api_base_url}/api/hinata/submit",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def get_psp_context(self, user_id: str, current_request: str = "") -> dict:
        """获取用户PSP上下文"""
        payload = {
            "user_id": user_id,
            "current_request": current_request,
            "include_details": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/psp/context",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def search_hinata(self, user_id: str, query: str, filters: dict = None) -> dict:
        """搜索HiNATA数据"""
        payload = {
            "user_id": user_id,
            "query_text": query,
            "filters": filters or {},
            "limit": 10
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/hinata/search",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()

# 使用示例
async def main():
    # 初始化客户端
    client = ByenatOSClient(
        api_base_url="https://localhost:8080",
        api_key="byo_your_api_key_here"
    )
    
    # 创建HiNATA数据
    hinata = {
        "id": f"hinata_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat() + "Z",
        "source": "my_app",
        "highlight": "用户选择的重要文本",
        "note": "用户添加的详细笔记",
        "address": "https://example.com/resource",
        "tag": ["学习", "重要"],
        "access": "private",
        "raw_data": {
            "context": "应用特定的上下文信息"
        }
    }
    
    # 提交HiNATA
    result = await client.submit_hinata_batch("user123", [hinata])
    print("提交结果:", result)
    
    # 获取PSP上下文
    psp_context = await client.get_psp_context("user123", "帮我学习机器学习")
    print("PSP上下文:", psp_context)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. JavaScript App示例

```javascript
class ByenatOSClient {
    constructor(apiBaseUrl, apiKey) {
        this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async submitHiNATA(userId, hiNATAData) {
        const payload = {
            app_id: 'my_browser_extension',
            user_id: userId,
            hinata_batch: [hiNATAData],
            processing_options: {
                enable_ai_enhancement: true,
                extract_highlights: true,
                generate_semantic_tags: true
            }
        };
        
        const response = await fetch(`${this.apiBaseUrl}/api/hinata/submit`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return await response.json();
    }
    
    async getPSPContext(userId, currentRequest = '') {
        const payload = {
            user_id: userId,
            current_request: currentRequest,
            include_details: false
        };
        
        const response = await fetch(`${this.apiBaseUrl}/api/psp/context`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return await response.json();
    }
    
    createHiNATAFromSelection(selectedText, pageUrl, userNote = '') {
        return {
            id: `hinata_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date().toISOString(),
            source: 'browser_extension',
            highlight: selectedText,
            note: userNote,
            address: pageUrl,
            tag: [],
            access: 'private',
            raw_data: {
                page_title: document.title,
                user_agent: navigator.userAgent,
                selection_time: Date.now()
            }
        };
    }
}

// 浏览器扩展使用示例
const client = new ByenatOSClient('https://localhost:8080', 'your_api_key');

// 监听文本选择
document.addEventListener('mouseup', async (event) => {
    const selectedText = window.getSelection().toString().trim();
    
    if (selectedText.length > 10) {  // 最小长度检查
        const hiNATA = client.createHiNATAFromSelection(
            selectedText,
            window.location.href
        );
        
        try {
            const result = await client.submitHiNATA('current_user_id', hiNATA);
            console.log('HiNATA submitted:', result);
        } catch (error) {
            console.error('Failed to submit HiNATA:', error);
        }
    }
});
```

## 监控和维护

### 1. 监控配置

创建 `monitoring/prometheus.yml`：

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'byenatos'
    static_configs:
      - targets: ['byenatos-core:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'elasticsearch'
    static_configs:
      - targets: ['elasticsearch:9200']
```

### 2. 日志配置

创建 `logging/logrotate.conf`：

```bash
/var/log/byenatos/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 byenatos byenatos
    postrotate
        systemctl reload byenatos
    endscript
}
```

### 3. 备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash

# ByenatOS 数据备份脚本
BACKUP_DIR="/backup/byenatos"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR/$DATE"

# 备份PostgreSQL
pg_dump -h localhost -U byenatos byenatos | gzip > "$BACKUP_DIR/$DATE/postgres_$DATE.sql.gz"

# 备份Redis
redis-cli --rdb "$BACKUP_DIR/$DATE/redis_$DATE.rdb"

# 备份冷存储数据
tar -czf "$BACKUP_DIR/$DATE/cold_storage_$DATE.tar.gz" /data/cold_storage/

# 备份ChromaDB
tar -czf "$BACKUP_DIR/$DATE/chroma_$DATE.tar.gz" /data/chroma/

# 清理30天前的备份
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
```

## 故障排除

### 常见问题和解决方案

#### 1. 服务启动失败

**问题**: 容器无法启动或立即退出

**排查步骤**:
```bash
# 查看容器日志
docker-compose logs byenatos-core

# 检查配置文件
docker-compose config

# 验证依赖服务
docker-compose ps
```

**常见原因**:
- 数据库连接失败
- 配置文件格式错误
- 端口冲突
- 依赖服务未就绪

#### 2. API响应缓慢

**问题**: API响应时间过长

**排查步骤**:
```bash
# 检查系统资源
docker stats

# 查看数据库连接
docker-compose exec postgres psql -U byenatos -c "SELECT * FROM pg_stat_activity;"

# 检查Redis内存使用
docker-compose exec redis redis-cli info memory
```

**优化建议**:
- 增加数据库连接池大小
- 优化索引
- 增加Redis内存
- 启用缓存

#### 3. 数据存储问题

**问题**: 数据丢失或存储异常

**排查步骤**:
```bash
# 检查存储空间
df -h

# 检查数据库状态
docker-compose exec postgres psql -U byenatos -c "SELECT pg_size_pretty(pg_database_size('byenatos'));"

# 检查备份状态
ls -la /backup/byenatos/
```

### 4. 性能调优

#### 数据库优化

```sql
-- PostgreSQL优化配置
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

#### Redis优化

```bash
# Redis配置优化
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

## 安全建议

### 1. 网络安全

- 使用HTTPS/TLS 1.3
- 配置防火墙规则
- 启用DDoS防护
- 定期更新SSL证书

### 2. 数据安全

- 启用数据库加密
- 配置访问控制
- 定期备份验证
- 实施数据保留策略

### 3. 应用安全

- API密钥轮换
- 输入验证和清理
- 速率限制
- 安全日志记录

## 扩展和定制

### 1. 水平扩展

```yaml
# 多实例部署
version: '3.8'
services:
  byenatos-core:
    deploy:
      replicas: 3
    # ... 其他配置
    
  nginx:
    # 负载均衡配置
    # ... 配置文件
```

### 2. 自定义组件

```python
# 自定义HiNATA处理器
class CustomHiNATAProcessor(HiNATAProcessor):
    async def custom_enhancement(self, hinata_data):
        # 自定义增强逻辑
        pass

# 自定义PSP策略
class CustomPSPStrategy:
    def calculate_custom_weight(self, intent):
        # 自定义权重计算
        pass
```

## 结论

本集成指南提供了ByenatOS系统的完整部署和集成方案。通过遵循本指南，您可以：

1. **快速部署** - 使用Docker Compose实现一键部署
2. **安全集成** - 实施完整的隐私保护机制
3. **灵活扩展** - 根据业务需求定制和扩展
4. **稳定运行** - 通过监控和维护确保系统稳定

ByenatOS的HiNATA-PSP架构为个性化AI体验提供了强大的技术基础，通过本指南的实施，您将能够构建一个功能完整、安全可靠的个性化操作系统。

如有问题，请参考文档或联系技术支持团队。