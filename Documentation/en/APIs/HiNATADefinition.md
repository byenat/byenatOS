# HiNATA App Integration API Documentation

## Overview

This document describes how Apps integrate with the ByenatOS system and use HiNATA data processing services. All Apps integrated with ByenatOS must follow the HiNATA standard format and interact with the system through specified APIs.

## Core Requirements

### 1. HiNATA Format Standard
All Apps must be able to:
- **Generate** standard HiNATA format data
- **Receive** HiNATA data optimized by ByenatOS
- **Process** enhanced fields of HiNATA data

### 2. API Integration Requirements
- Use unified transmission protocol
- Implement error handling mechanisms
- Support batch data transmission
- Follow authentication and security standards

## HiNATA Standard Format

### App-side Output Format (Required Fields)

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "User highlighted text",
  "note": "User added comments or descriptions",
  "address": "Resource address or identifier",
  "tag": ["User added basic tags"],
  "access": "private|public|shared",
  "raw_data": {
    "original_text": "Original complete text",
    "user_context": "User operation context",
    "app_metadata": "App-specific metadata"
  }
}
```

### ByenatOS Enhanced Format (Return Fields)

```json
{
  "id": "hinata_20241201_001",
  "timestamp": "2024-12-01T10:30:00Z",
  "source": "app_name",
  "highlight": "User highlighted text",
  "note": "User added comments or descriptions",
  "address": "Resource address or identifier",
  "tag": ["Basic tags", "System generated tags"],
  "access": "private",
  "enhanced_tags": ["AI-generated semantic tags"],
  "recommended_highlights": ["Recommended snippets extracted from note"],
  "semantic_analysis": {
    "main_topics": ["Main topics"],
    "sentiment": "Sentiment tendency",
    "complexity_level": "Complexity level",
    "key_concepts": ["Key concepts"]
  },
  "cluster_id": "Related content cluster ID",
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

## API Interface Specification

### 1. Register App to ByenatOS

**Endpoint**: `POST /api/apps/register`

**Request Body**:
```json
{
  "app_id": "your_app_name",
  "app_version": "1.0.0",
  "app_description": "App function description",
  "supported_data_types": ["text", "image", "audio"],
  "hinata_capabilities": {
    "can_generate": true,
    "can_receive_enhanced": true,
    "supported_fields": ["highlight", "note", "tag", "address"]
  }
}
```

**Response**:
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

### 2. Submit HiNATA Data Processing

**Endpoint**: `POST /api/hinata/submit`

**Request Headers**:
```
Authorization: Bearer {app_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "app_id": "your_app_name",
  "user_id": "user_identifier",
  "hinata_batch": [
    {
      "id": "hinata_20241201_001",
      "timestamp": "2024-12-01T10:30:00Z",
      "source": "your_app_name",
      "highlight": "User selected important content",
      "note": "User's long note, possibly containing multiple points and detailed explanations...",
      "address": "https://example.com/resource",
      "tag": ["Learning", "Technology"],
      "access": "private",
      "raw_data": {
        "original_text": "Full original content",
        "user_context": "User's current operation environment",
        "app_metadata": {
          "app_specific_field": "App specific data"
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

**Response**:
```json
{
  "status": "success",
  "job_id": "processing_job_12345",
  "estimated_completion": "2024-12-01T10:31:00Z",
  "processed_count": 1,
  "message": "HiNATA data submitted for processing"
}
```

### 3. Get Enhanced HiNATA Data

**Endpoint**: `GET /api/hinata/enhanced/{job_id}`

**Request Headers**:
```
Authorization: Bearer {app_token}
```

**Response**:
```json
{
  "status": "completed",
  "job_id": "processing_job_12345",
  "enhanced_hinata": [
    {
      "id": "hinata_20241201_001",
      "timestamp": "2024-12-01T10:30:00Z",
      "source": "your_app_name",
      "highlight": "User selected important content",
      "note": "User's long note, possibly containing multiple points and detailed explanations...",
      "address": "https://example.com/resource",
      "tag": ["Learning", "Technology", "AI enhanced tag"],
      "access": "private",
      "enhanced_tags": ["Artificial Intelligence", "Deep Learning", "Technology Development"],
      "recommended_highlights": [
        "Core role of deep learning in modern AI",
        "Deep impact of technology on society",
        "Main directions of future AI applications"
      ],
      "semantic_analysis": {
        "main_topics": ["Artificial Intelligence", "Technology Development", "Social Impact"],
        "sentiment": "positive",
        "complexity_level": "intermediate",
        "key_concepts": ["Deep Learning", "AI Applications", "Technology Trends"]
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

### 4. Get Real-time Recommendations

**Endpoint**: `GET /api/hinata/recommendations`

**Query Parameters**:
```
user_id: User ID
limit: Return limit (default 10)
psp_context: Current PSP context (optional)
```

**Response**:
```json
{
  "status": "success",
  "recommendations": [
    {
      "hinata_id": "hinata_20241201_001",
      "relevance_score": 0.92,
      "reason": "Highly relevant to current PSP",
      "highlight": "Recommended key content",
      "source": "browser_app"
    }
  ]
}
```

## App-side Implementation Guide

### 1. HiNATA Data Generation

```python
class HinataGenerator:
    def __init__(self, app_id):
        self.app_id = app_id
    
    def create_hinata(self, user_data):
        """Create standard HiNATA format data"""
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
        """Generate unique HiNATA ID"""
        timestamp = int(time.time())
        return f"hinata_{self.app_id}_{timestamp}_{random.randint(1000, 9999)}"
```

### 2. API Client Implementation

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
        """Submit HiNATA batch data"""
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
        """Get enhanced HiNATA data"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/hinata/enhanced/{job_id}",
                headers=self.headers
            ) as response:
                return await response.json()
```

### 3. Error Handling

```python
class HinataError(Exception):
    pass

class ValidationError(HinataError):
    pass

class ProcessingError(HinataError):
    pass

def handle_api_response(response):
    """Process API responses and errors"""
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

## Best Practices

### 1. Data Quality Assurance
- **Integrity Check**: Ensure all required fields exist
- **Format Validation**: Validate timestamp, URL, etc. fields
- **Content Quality**: Provide meaningful highlight and note content

### 2. Performance Optimization
- **Batch Submission**: Submit multiple HiNATA in batches
- **Asynchronous Processing**: Use asynchronous APIs to avoid blocking the user interface
- **Caching Mechanism**: Cache frequently accessed enhanced data

### 3. User Experience
- **Real-time Feedback**: Display processing progress and status
- **Smart Recommendations**: Utilize enhanced data to provide personalized recommendations
- **Seamless Integration**: Make HiNATA processing transparent to users

### 4. Privacy Protection
- **Data Encryption**: Encrypt sensitive data during transmission and storage
- **Access Control**: Strictly control data access permissions
- **User Consent**: Clearly inform users about data processing methods

## Example Scenarios

### Browser Extension Integration
```javascript
// Create HiNATA when user highlights text
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

### Notes Application Integration
```python
# Create HiNATA when user saves a note
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
    
    # Submit to ByenatOS for AI enhancement
    client.submit_hinata_batch([hinata], user_id)
```

## Summary

By following this API specification, Apps can:
1. **Standardized Integration** - Use a unified HiNATA format
2. **AI Enhancement** - Obtain semantic tags and recommended highlights
3. **Smart Optimization** - Utilize ByenatOS's global optimization capabilities
4. **Seamless Experience** - Provide enhanced personalized experiences to users

This design ensures that all Apps can benefit from ByenatOS's AI enhancement capabilities while maintaining system consistency and scalability.