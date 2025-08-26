# API Documentation

This document describes the REST API endpoints for the JIRA CSV Generator application.

## Base URL

```
http://localhost:5000/api
```

## Authentication

Currently, no authentication is required for API endpoints.

## Endpoints

### Health Check

#### GET /health

Check if the API service is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "JIRA CSV Generator API",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### Service Status

#### GET /status

Get detailed status information about the service and its dependencies.

**Response:**
```json
{
  "ai_service_available": true,
  "ai_service_type": "OllamaService",
  "max_tasks": 10,
  "max_questions": 8,
  "max_transcript_length": 50000
}
```

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `500 Internal Server Error`: Failed to get service status

---

### Transcript Processing

#### POST /parse-transcript

Extract actionable tasks from a meeting transcript.

**Request Body:**
```json
{
  "transcript": "Meeting: Sprint Planning\nJohn: Sarah, can you implement the user authentication API?\nSarah: Sure, I can have that done by Friday."
}
```

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "summary": "Implement user authentication API",
      "description": "Add login and registration functionality",
      "issue_type": "Task",
      "reporter": "meeting@example.com",
      "due_date": "2024-12-31"
    }
  ],
  "count": 1
}
```

**Status Codes:**
- `200 OK`: Tasks extracted successfully
- `400 Bad Request`: Invalid transcript data
- `503 Service Unavailable`: AI service unavailable

---

#### POST /extract-qa

Extract questions and answers from a meeting transcript.

**Request Body:**
```json
{
  "transcript": "Meeting: Sprint Planning\nLisa: What about the UI mockups? Do we have them ready?\nJohn: Good question, we need those."
}
```

**Response:**
```json
{
  "success": true,
  "qa_items": [
    {
      "question": "What about the UI mockups?",
      "context": "Discussion about project deliverables",
      "answer": "",
      "asked_by": "meeting@example.com",
      "answered_by": "",
      "status": "unanswered"
    }
  ],
  "count": 1
}
```

**Status Codes:**
- `200 OK`: Q&A extracted successfully
- `400 Bad Request`: Invalid transcript data
- `503 Service Unavailable`: AI service unavailable

---

#### POST /process-enhanced

Process transcript to extract both tasks and Q&A items in a single request.

**Request Body:**
```json
{
  "transcript": "Meeting: Sprint Planning\nJohn: Sarah, can you implement the user authentication API?\nLisa: What about the UI mockups?"
}
```

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "summary": "Implement user authentication API",
      "description": "Add login and registration functionality",
      "issue_type": "Task",
      "reporter": "meeting@example.com",
      "due_date": ""
    }
  ],
  "qa_items": [
    {
      "question": "What about the UI mockups?",
      "context": "Discussion about project deliverables",
      "answer": "",
      "asked_by": "meeting@example.com",
      "answered_by": "",
      "status": "unanswered"
    }
  ],
  "tasks_count": 1,
  "qa_count": 1
}
```

**Status Codes:**
- `200 OK`: Processing completed successfully
- `400 Bad Request`: Invalid transcript data
- `503 Service Unavailable`: AI service unavailable

---

### CSV Generation

#### POST /generate-csv

Generate a JIRA-compatible CSV file from task data.

**Request Body:**
```json
{
  "tasks": [
    {
      "summary": "Implement user authentication",
      "description": "Add login and registration functionality",
      "issue_type": "Task",
      "reporter": "meeting@example.com",
      "due_date": "2024-12-31"
    }
  ]
}
```

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename=jira_tasks_20241201_143000.csv`

CSV content:
```csv
"Summary","Description","Issue Type","Reporter","Due Date"
"Implement user authentication","Add login and registration functionality","Task","meeting@example.com","2024-12-31"
```

**Status Codes:**
- `200 OK`: CSV generated successfully
- `400 Bad Request`: Invalid task data
- `500 Internal Server Error`: CSV generation failed

---

## Error Handling

All endpoints return error responses in the following format:

```json
{
  "error": "Error description"
}
```

### Common Error Types

1. **Validation Errors (400)**:
   - Empty or missing transcript
   - Transcript too long (exceeds max_transcript_length)
   - Invalid task data (missing required fields)

2. **Service Errors (503)**:
   - AI service (Ollama) unavailable
   - AI service timeout

3. **Server Errors (500)**:
   - Unexpected processing errors
   - CSV generation failures

## Request/Response Examples

### Successful Task Extraction

**Request:**
```bash
curl -X POST http://localhost:5000/api/parse-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "John: Can you fix the login bug by tomorrow? Sarah: Sure, I will handle it."
  }'
```

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "summary": "Fix login bug",
      "description": "Login functionality needs to be fixed",
      "issue_type": "Bug",
      "reporter": "meeting@example.com",
      "due_date": "2024-12-02"
    }
  ],
  "count": 1
}
```

### Error Response

**Request:**
```bash
curl -X POST http://localhost:5000/api/parse-transcript \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": ""
  }'
```

**Response:**
```json
{
  "error": "Transcript cannot be empty"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

## Data Validation

### Transcript Validation
- Must not be empty
- Must be at least 10 words
- Must not exceed max_transcript_length (default: 50,000 characters)

### Task Validation
- Summary is required and cannot be empty
- Summary cannot exceed 255 characters
- Issue type must be one of: Story, Task, Bug, Epic
- Reporter must be a valid email address
- Due date must be in YYYY-MM-DD format (if provided)

### Q&A Validation
- Question is required and cannot be empty
- Question must end with a question mark
- Question cannot exceed 500 characters
- Asked by and answered by must be valid email addresses (if provided)
- Status must be either "answered" or "unanswered"