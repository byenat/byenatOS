# ByenatOS System Integration Guide

## Overview

This document provides a complete integration guide for the ByenatOS system, including system deployment, component configuration, API integration, and best practices. Based on our designed HiNATA-PSP architecture, this guide will help you successfully deploy and integrate ByenatOS.

## System Architecture Review

ByenatOS adopts a layered architecture design with core components including:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Complete System Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│  App Ecosystem Layer: Browser App, Notes App, Chat App, Custom Apps │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway Layer: AppIntegrationAPI.py                      │
├─────────────────────────────────────────────────────────────────┤
│  Core Processing Layer:                                        │
│  ├─ HiNATAProcessor.py (Data Processing)                      │
│  ├─ PSPEngine.py (Personalization Engine)                     │
│  └─ StorageEngine.py (Storage Engine)                         │
├─────────────────────────────────────────────────────────────────┤
│  Privacy Protection Layer: PrivacyProtectionSystem.py          │
├─────────────────────────────────────────────────────────────────┤
│  Storage Infrastructure: Redis + PostgreSQL + ChromaDB + Elasticsearch │
└─────────────────────────────────────────────────────────────────┘
```

## Environment Requirements

### Hardware Requirements

**Minimum Configuration**:
- CPU: 4 cores 2.5GHz
- Memory: 8GB RAM
- Storage: 100GB SSD
- Network: 1Gbps

**Recommended Configuration**:
- CPU: 8 cores 3.0GHz
- Memory: 16GB RAM
- Storage: 500GB NVMe SSD
- Network: 10Gbps

**Production Environment**:
- CPU: 16 cores 3.5GHz
- Memory: 32GB RAM
- Storage: 1TB NVMe SSD (system) + 10TB SSD (data)
- Network: 10Gbps with redundancy

### Software Dependencies

**Operating System**:
- Linux (Ubuntu 22.04 LTS, CentOS 8+, or RHEL 8+)
- macOS 12+ (development environment)
- Windows 11 with WSL2 (development environment)

**Core Components**:
- Python 3.11+
- Redis 7.0+
- PostgreSQL 14+
- Elasticsearch 8.0+
- Docker 24.0+ & Docker Compose v2

**AI Model Components**:
- ONNX Runtime
- ChromaDB
- SentenceTransformers

## Quick Deployment

### 1. Deploy Using Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # Core service
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

  # Redis (Hot data layer)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  # PostgreSQL (Warm data layer)
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

  # Elasticsearch (Full-text search)
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

  # Nginx (Load balancing and reverse proxy)
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

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /data/chroma /data/cold_storage

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start command
CMD ["python", "-m", "uvicorn", "ApplicationFramework.APIs.AppIntegrationAPI:create_app", \
     "--host", "0.0.0.0", "--port", "8080", "--factory"]
```

Create `requirements.txt`:

```txt
# Core framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database
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

# Search and vectors
elasticsearch==8.11.0
chromadb==0.4.18

# Security and encryption
cryptography==41.0.7
PyJWT==2.8.0
bcrypt==4.1.1

# Data processing
pandas==2.1.3
aiofiles==23.2.1

# Monitoring and logging
prometheus-client==0.19.0
structlog==23.2.0

# Development tools
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
isort==5.12.0
```

### 2. Deployment Commands

```bash
# 1. Clone code
git clone https://github.com/byenatos/byenatos.git
cd byenatos

# 2. Create configuration file
cp config/config.example.yaml config/config.yaml

# 3. Initialize database
docker-compose up -d postgres
sleep 10
docker-compose exec postgres psql -U byenatos -d byenatos -f /docker-entrypoint-initdb.d/init-db.sql

# 4. Start all services
docker-compose up -d

# 5. Verify deployment
curl http://localhost:8080/health
```

## Detailed Configuration

### 1. Core System Configuration

Create `config/config.yaml`:

```yaml
# ByenatOS core configuration
system:
  name: "ByenatOS"
  version: "1.0.0"
  environment: "production"  # development, staging, production
  debug: false

# Database configuration
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

# Storage configuration
storage:
  cold_storage_path: "/data/cold_storage"
  chroma_persist_dir: "/data/chroma"
  cache_ttl: 3600
  
  # Layered storage thresholds
  hot_tier:
    max_age_days: 7
    min_influence_weight: 0.7
  
  warm_tier:
    max_age_days: 30
    min_influence_weight: 0.3

# HiNATA processing configuration
hinata_processing:
  batch_size: 100
  max_processing_time: 5.0
  cache_ttl: 3600
  priority_threshold: 0.8
  similarity_threshold: 0.7
  max_enhanced_tags: 10

# PSP configuration
psp:
  similarity_threshold: 0.7
  confidence_threshold: 0.8
  update_frequency: "realtime"
  max_psp_size: 10000
  component_ttl: 2592000  # 30 days

# API configuration
api:
  host: "0.0.0.0"
  port: 8080
  workers: 4
  
  # Rate limiting
  rate_limiting:
    default_limit: 1000  # per hour
    burst_limit: 100    # per minute
  
  # CORS
  cors:
    allow_origins: ["*"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["*"]

# Privacy and security
privacy:
  encryption_enabled: true
  pii_detection_enabled: true
  data_minimization_enabled: true
  access_logging_enabled: true
  
  # Default data retention period
  default_retention_days: 365
  
  # Audit configuration
  audit:
    log_all_access: true
    log_retention_days: 90

# AI model configuration
ai_models:
  embedding_model: "all-MiniLM-L6-v2"
  nlp_model: "en_core_web_sm"
  
  # Model cache
  model_cache_size: 1000
  model_cache_ttl: 3600

# Monitoring configuration
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

# Deployment configuration
deployment:
  cluster_mode: false
  node_id: "node-1"
  
  # Health check
  health_check:
    interval: 30
    timeout: 10
    retries: 3
```

### 2. Database Initialization Script

Create `init-db.sql`:

```sql
-- ByenatOS database initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- HiNATA data table
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

-- PSP components table
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

-- User PSP metadata table
CREATE TABLE IF NOT EXISTS user_psp (
    user_id TEXT PRIMARY KEY,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    total_components INTEGER NOT NULL,
    active_components JSONB
);

-- App registrations table
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

-- User privacy preferences table
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

-- Data access logs table
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

-- API call logs table
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

-- Composite index table
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

-- Create indexes
-- HiNATA data indexes
CREATE INDEX IF NOT EXISTS idx_hinata_user_timestamp ON hinata_data(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_user_weight ON hinata_data(user_id, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_user_source ON hinata_data(user_id, source);
CREATE INDEX IF NOT EXISTS idx_hinata_enhanced_tags ON hinata_data USING GIN(enhanced_tags);
CREATE INDEX IF NOT EXISTS idx_hinata_timestamp ON hinata_data(timestamp DESC);

-- PSP component indexes
CREATE INDEX IF NOT EXISTS idx_psp_user_type ON psp_components(user_id, component_type);
CREATE INDEX IF NOT EXISTS idx_psp_user_priority ON psp_components(user_id, priority);
CREATE INDEX IF NOT EXISTS idx_psp_last_updated ON psp_components(user_id, last_updated DESC);

-- App registration indexes
CREATE INDEX IF NOT EXISTS idx_app_api_key ON app_registrations(api_key);
CREATE INDEX IF NOT EXISTS idx_app_name ON app_registrations(app_name);
CREATE INDEX IF NOT EXISTS idx_app_created_at ON app_registrations(created_at DESC);

-- Access log indexes
CREATE INDEX IF NOT EXISTS idx_access_logs_user_timestamp ON data_access_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_logs_accessor_timestamp ON data_access_logs(accessor_id, timestamp DESC);

-- API call log indexes
CREATE INDEX IF NOT EXISTS idx_api_logs_app_timestamp ON api_call_logs(app_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint_timestamp ON api_call_logs(endpoint, created_at DESC);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_hinata_index_user_timestamp ON hinata_index(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_user_weight ON hinata_index(user_id, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_quality_weight ON hinata_index(quality_score DESC, psp_influence_weight DESC);
CREATE INDEX IF NOT EXISTS idx_hinata_index_content_hash ON hinata_index(content_hash);
CREATE INDEX IF NOT EXISTS idx_hinata_index_tags ON hinata_index USING GIN(tags);

-- Insert default configuration data
INSERT INTO user_privacy_preferences (
    user_id, policy_level, data_sharing_consent, analytics_consent,
    personalization_consent, external_sharing_consent, data_retention_days,
    allowed_apps, blocked_apps, custom_permissions, created_at, updated_at
) VALUES (
    'default_template', 'balanced', false, false, true, false, 365,
    '[]', '[]', '{}', NOW(), NOW()
) ON CONFLICT (user_id) DO NOTHING;
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream byenatos_backend {
        server byenatos-core:8080;
    }
    
    # Rate limiting configuration
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
    
    server {
        listen 80;
        server_name localhost;
        
        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name localhost;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
        
        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://byenatos_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeout settings
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # Authentication endpoints (stricter rate limiting)
        location /api/auth/ {
            limit_req zone=auth burst=5 nodelay;
            
            proxy_pass http://byenatos_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health check
        location /health {
            proxy_pass http://byenatos_backend;
            access_log off;
        }
        
        # Static files (if any)
        location /static/ {
            root /var/www;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## App Integration Examples

### 1. Python App Example

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
        """Register app with ByenatOS"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/apps/register",
                json=app_info
            ) as response:
                return await response.json()
    
    async def submit_hinata_batch(self, user_id: str, hinata_list: list) -> dict:
        """Submit HiNATA data batch"""
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
        """Get user PSP context"""
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
        """Search HiNATA data"""
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

# Usage example
async def main():
    # Initialize client
    client = ByenatOSClient(
        api_base_url="https://localhost:8080",
        api_key="byo_your_api_key_here"
    )
    
    # Create HiNATA data
    hinata = {
        "id": f"hinata_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat() + "Z",
        "source": "my_app",
        "highlight": "Important text selected by user",
        "note": "Detailed notes added by user",
        "address": "https://example.com/resource",
        "tag": ["learning", "important"],
        "access": "private",
        "raw_data": {
            "context": "App-specific context information"
        }
    }
    
    # Submit HiNATA
    result = await client.submit_hinata_batch("user123", [hinata])
    print("Submission result:", result)
    
    # Get PSP context
    psp_context = await client.get_psp_context("user123", "Help me learn machine learning")
    print("PSP context:", psp_context)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. JavaScript App Example

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

// Browser extension usage example
const client = new ByenatOSClient('https://localhost:8080', 'your_api_key');

// Listen for text selection
document.addEventListener('mouseup', async (event) => {
    const selectedText = window.getSelection().toString().trim();
    
    if (selectedText.length > 10) {  // Minimum length check
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

## Monitoring and Maintenance

### 1. Monitoring Configuration

Create `monitoring/prometheus.yml`:

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

### 2. Logging Configuration

Create `logging/logrotate.conf`:

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

### 3. Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash

# ByenatOS data backup script
BACKUP_DIR="/backup/byenatos"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup PostgreSQL
pg_dump -h localhost -U byenatos byenatos | gzip > "$BACKUP_DIR/$DATE/postgres_$DATE.sql.gz"

# Backup Redis
redis-cli --rdb "$BACKUP_DIR/$DATE/redis_$DATE.rdb"

# Backup cold storage data
tar -czf "$BACKUP_DIR/$DATE/cold_storage_$DATE.tar.gz" /data/cold_storage/

# Backup ChromaDB
tar -czf "$BACKUP_DIR/$DATE/chroma_$DATE.tar.gz" /data/chroma/

# Clean up backups older than 30 days
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Startup Failure

**Issue**: Containers cannot start or exit immediately

**Troubleshooting Steps**:
```bash
# View container logs
docker-compose logs byenatos-core

# Check configuration file
docker-compose config

# Verify dependency services
docker-compose ps
```

**Common Causes**:
- Database connection failure
- Configuration file format error
- Port conflict
- Dependency services not ready

#### 2. Slow API Response

**Issue**: API response time is too long

**Troubleshooting Steps**:
```bash
# Check system resources
docker stats

# View database connections
docker-compose exec postgres psql -U byenatos -c "SELECT * FROM pg_stat_activity;"

# Check Redis memory usage
docker-compose exec redis redis-cli info memory
```

**Optimization Suggestions**:
- Increase database connection pool size
- Optimize indexes
- Increase Redis memory
- Enable caching

#### 3. Data Storage Issues

**Issue**: Data loss or storage anomalies

**Troubleshooting Steps**:
```bash
# Check storage space
df -h

# Check database status
docker-compose exec postgres psql -U byenatos -c "SELECT pg_size_pretty(pg_database_size('byenatos'));"

# Check backup status
ls -la /backup/byenatos/
```

### 4. Performance Tuning

#### Database Optimization

```sql
-- PostgreSQL optimization configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

#### Redis Optimization

```bash
# Redis configuration optimization
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

## Security Recommendations

### 1. Network Security

- Use HTTPS/TLS 1.3
- Configure firewall rules
- Enable DDoS protection
- Regularly update SSL certificates

### 2. Data Security

- Enable database encryption
- Configure access controls
- Regular backup verification
- Implement data retention policies

### 3. Application Security

- API key rotation
- Input validation and sanitization
- Rate limiting
- Security logging

## Extension and Customization

### 1. Horizontal Scaling

```yaml
# Multi-instance deployment
version: '3.8'
services:
  byenatos-core:
    deploy:
      replicas: 3
    # ... other configurations
    
  nginx:
    # Load balancing configuration
    # ... configuration files
```

### 2. Custom Components

```python
# Custom HiNATA processor
class CustomHiNATAProcessor(HiNATAProcessor):
    async def custom_enhancement(self, hinata_data):
        # Custom enhancement logic
        pass

# Custom PSP strategy
class CustomPSPStrategy:
    def calculate_custom_weight(self, intent):
        # Custom weight calculation
        pass
```

## Conclusion

This integration guide provides a complete deployment and integration solution for the ByenatOS system. By following this guide, you can:

1. **Quick Deployment** - Use Docker Compose for one-click deployment
2. **Secure Integration** - Implement complete privacy protection mechanisms
3. **Flexible Extension** - Customize and extend according to business needs
4. **Stable Operation** - Ensure system stability through monitoring and maintenance

ByenatOS's HiNATA-PSP architecture provides a powerful technical foundation for personalized AI experiences. Through the implementation of this guide, you will be able to build a fully functional, secure, and reliable personalized operating system.

For questions, please refer to the documentation or contact the technical support team.