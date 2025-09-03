# ByenatOS HiNATA Write System Documentation

## Overview

The HiNATA Write System is a comprehensive solution for handling user-initiated modifications to their personal knowledge base (HiNATA file system) through conversational interfaces. This system extends the existing read-only APIs to support write operations while maintaining security, data integrity, and user intent recognition.

## Architecture Components

### 1. Intent Recognition Layer
- **IntentRecognizer**: Analyzes natural language input to identify user intentions
- **Supported Intent Types**:
  - Create new HiNATA records
  - Update existing records
  - Delete records (soft/hard)
  - Bulk tagging operations
  - Content reorganization
  - Duplicate merging
  - Knowledge base cleanup

### 2. Write Operation Layer
- **HiNATAWriteAPI**: Core API for executing write operations
- **HiNATAWriteProcessor**: Processes and validates write requests
- **WriteOperationValidator**: Ensures data integrity and business rules

### 3. Conversational Interface Layer
- **ConversationalWriteInterface**: Bridges natural language input to write operations
- **Session Management**: Tracks user conversations and confirmations
- **Preview/Dry-run**: Allows users to preview changes before execution

### 4. Security & Permission Layer
- **WritePermissionManager**: Manages user permissions and access control
- **RiskAssessment**: Evaluates operation risk levels
- **Audit Logging**: Comprehensive operation tracking and compliance

## Key Features

### 1. Natural Language Processing
```python
# Example user inputs that are recognized:
"Please add 'AI' tags to all my machine learning notes"
"Delete all old notes from the browser extension"
"Update my Python programming note with new ideas"
"Clean up duplicate content in my knowledge base"
```

### 2. Permission-based Access Control
- **Permission Levels**: None, Read-only, Write-limited, Write-full, Admin
- **Operation Limits**: Daily operation quotas, batch size restrictions
- **Risk-based Authorization**: High-risk operations require elevated permissions

### 3. Safe Operation Execution
- **Dry-run Mode**: Preview operations before execution
- **Automatic Backups**: Create recovery points before modifications
- **Soft Delete**: Reversible deletion operations
- **Batch Processing**: Efficient handling of large-scale operations

## API Endpoints

### 1. Conversational Write Interface

#### Process Natural Language Request
```http
POST /api/conversation/write
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "user_id": "user_123",
  "user_input": "Please add 'important' tag to all my notes about Python",
  "context": {},
  "auto_confirm": false,
  "dry_run": true
}
```

**Response:**
```json
{
  "session_id": "session_1234567890",
  "status": "success",
  "intent_recognized": true,
  "intent_confidence": 0.85,
  "suggested_action": "为标签为'python'的HiNATA记录添加标签：添加标签 important（预计影响 12 条记录）\n\n确认执行此操作吗？",
  "confirmation_required": true,
  "preview_results": {
    "estimated_affected": 12,
    "preview_results": [...],
    "warnings": [],
    "dry_run": true
  }
}
```

#### Confirm and Execute Operation
```http
POST /api/conversation/confirm
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "session_id": "session_1234567890",
  "user_id": "user_123",
  "confirmed": true,
  "modifications": {}
}
```

### 2. Direct Write API

#### Create HiNATA Record
```http
POST /api/hinata/write
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "user_id": "user_123",
  "operation_type": "create",
  "intent_description": "Create new programming note",
  "hinata_data": {
    "source": "manual_entry",
    "highlight": "Key programming concepts",
    "note": "Important notes about Python programming...",
    "address": "manual://programming_note",
    "tag": ["programming", "python"],
    "access": "private"
  }
}
```

#### Bulk Tag Operation
```http
POST /api/hinata/bulk
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "user_id": "user_123",
  "operation_type": "bulk_tag",
  "intent_description": "Add AI tag to machine learning content",
  "bulk_operation": {
    "operation_type": "bulk_tag",
    "target_filter": {
      "enhanced_tags": ["machine learning"]
    },
    "operation_data": {
      "tags": ["AI", "artificial intelligence"]
    },
    "dry_run": false,
    "batch_size": 50
  }
}
```

#### Delete Records
```http
POST /api/hinata/delete
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "user_id": "user_123",
  "hinata_ids": ["hinata_123", "hinata_456"],
  "delete_reason": "Outdated information",
  "soft_delete": true
}
```

## Security Model

### Permission Levels

1. **None**: No write access
2. **Read-only**: Only read operations allowed
3. **Write-limited**: Can create and modify own content (batch size ≤ 50)
4. **Write-full**: Full write access including bulk operations (batch size ≤ 500)
5. **Admin**: Unlimited access with system management capabilities

### Risk Assessment

Operations are automatically classified by risk level:

- **Low Risk**: Single record operations
- **Medium Risk**: Small batch operations (<100 records)
- **High Risk**: Large batch operations (≥100 records)
- **Critical Risk**: Delete operations or irreversible changes

### Audit Logging

All write operations are logged with:
- User identification and session details
- Operation type and parameters
- Risk assessment results
- Permission check outcomes
- Execution results and timing
- Security flags and warnings

## Usage Examples

### Example 1: Bulk Tagging via Conversation

```python
import aiohttp
import asyncio

async def bulk_tag_conversation():
    api_key = "your_api_key"
    base_url = "https://api.byenatos.local"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Submit natural language request
    request_data = {
        "user_id": "user_123",
        "user_input": "Please add 'research' tag to all my academic papers",
        "dry_run": True
    }
    
    async with aiohttp.ClientSession() as session:
        # Process intent
        async with session.post(
            f"{base_url}/api/conversation/write",
            headers=headers,
            json=request_data
        ) as response:
            result = await response.json()
            session_id = result["session_id"]
            print(f"Preview: {result['preview_results']}")
        
        # Confirm execution
        confirm_data = {
            "session_id": session_id,
            "user_id": "user_123",
            "confirmed": True
        }
        
        async with session.post(
            f"{base_url}/api/conversation/confirm",
            headers=headers,
            json=confirm_data
        ) as response:
            execution_result = await response.json()
            print(f"Execution result: {execution_result['execution_results']}")

# Run the example
asyncio.run(bulk_tag_conversation())
```

### Example 2: Direct API Usage

```python
async def direct_write_operation():
    api_key = "your_api_key"
    base_url = "https://api.byenatos.local"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Create new HiNATA record
    create_data = {
        "user_id": "user_123",
        "operation_type": "create",
        "intent_description": "Manual note creation",
        "hinata_data": {
            "source": "manual_entry",
            "highlight": "Important insight about AI development",
            "note": "This represents a breakthrough in understanding...",
            "address": "manual://ai_insight_001",
            "tag": ["AI", "breakthrough", "research"],
            "access": "private"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/hinata/write",
            headers=headers,
            json=create_data
        ) as response:
            result = await response.json()
            print(f"Created HiNATA: {result}")

asyncio.run(direct_write_operation())
```

## Integration with Existing System

### Relationship to Current APIs

1. **AppIntegrationAPI**: Provides read access and HiNATA submission
2. **HiNATAWriteAPI**: Extends with write operations for user modifications
3. **PSPEngine**: Continues to handle PSP updates from HiNATA processing
4. **StorageEngine**: Handles both read and write operations consistently

### Data Flow

```
User Input (Natural Language)
    ↓
Intent Recognition
    ↓
Permission Validation
    ↓
Risk Assessment
    ↓
Operation Preview (Dry-run)
    ↓
User Confirmation
    ↓
Write Operation Execution
    ↓
Audit Logging
    ↓
PSP Update (if applicable)
```

## Configuration

### Environment Variables

```bash
# Database connections
POSTGRES_DSN=postgresql://user:password@localhost/byenatos
REDIS_URL=redis://localhost:6379

# API settings
WRITE_API_PORT=8081
CONVERSATION_API_PORT=8082

# Security settings
JWT_SECRET_KEY=your_jwt_secret
ENABLE_2FA=true
DEFAULT_PERMISSION_LEVEL=write_limited

# Rate limiting
DEFAULT_DAILY_LIMIT=100
DEFAULT_BATCH_SIZE_LIMIT=50
```

### Permission Configuration

```json
{
  "user_permissions": {
    "default_level": "write_limited",
    "admin_users": ["admin_123"],
    "permission_levels": {
      "write_limited": {
        "allowed_operations": ["create", "update", "bulk_tag"],
        "batch_size_limit": 50,
        "daily_limit": 100
      },
      "write_full": {
        "allowed_operations": ["create", "update", "delete", "bulk_tag", "bulk_retag", "batch_update"],
        "batch_size_limit": 500,
        "daily_limit": 1000
      }
    }
  }
}
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  hinata-write-api:
    build: .
    ports:
      - "8081:8081"
    environment:
      - POSTGRES_DSN=postgresql://user:password@postgres:5432/byenatos
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  conversation-api:
    build: .
    ports:
      - "8082:8082"
    environment:
      - POSTGRES_DSN=postgresql://user:password@postgres:5432/byenatos
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
```

### Health Checks

```bash
# Check API health
curl http://localhost:8081/health
curl http://localhost:8082/health

# Check permission system
curl -H "Authorization: Bearer {api_key}" \
  http://localhost:8081/api/permissions/user_123/status
```

## Monitoring and Maintenance

### Key Metrics

- Operation success/failure rates
- Permission denial rates
- Risk level distribution
- Processing times
- User adoption of conversational interface

### Maintenance Tasks

- Regular audit log cleanup
- Permission profile reviews
- Risk assessment model updates
- Intent recognition model training
- Performance optimization

## Best Practices

### For Application Developers

1. **Always use dry-run first** for bulk operations
2. **Implement proper error handling** for permission denials
3. **Provide clear user feedback** for operation results
4. **Use conversational interface** for better user experience
5. **Monitor operation quotas** to avoid limit exceeded errors

### For System Administrators

1. **Regularly review audit logs** for security monitoring
2. **Adjust permission levels** based on user behavior
3. **Monitor system performance** during bulk operations
4. **Keep intent recognition models** updated
5. **Implement proper backup strategies** for critical operations

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Check user permission level
   - Verify operation is in allowed operations list
   - Check daily quota limits

2. **Intent Not Recognized**
   - Use more specific language
   - Include action verbs (add, delete, update)
   - Provide context about target records

3. **Batch Size Exceeded**
   - Reduce the scope of operation
   - Use multiple smaller batches
   - Request permission level upgrade

4. **High Risk Operation Blocked**
   - Enable 2FA for the user account
   - Request admin approval
   - Use smaller batch sizes

### Support

For technical support and questions:
- Documentation: `/docs/apis/hinata-write-system`
- API Reference: `/api/docs`
- Issue Tracking: GitHub Issues
- Community: ByenatOS Developer Forum