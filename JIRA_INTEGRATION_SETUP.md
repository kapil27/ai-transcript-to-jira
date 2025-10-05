# JIRA Integration Setup Guide

This guide will help you connect your actual JIRA project to the MCP-enhanced AI Transcript to JIRA system.

## Prerequisites

1. **JIRA Instance Access**: You need admin or project access to your JIRA instance
2. **JIRA API Token**: Required for secure authentication
3. **Project Key**: The JIRA project where you want to create tasks

## Step 1: Generate JIRA API Token

### For Atlassian Cloud:
1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label like "AI Transcript JIRA Integration"
4. Copy the generated token (save it securely - you won't see it again)

### For JIRA Server/Data Center:
1. Go to your JIRA instance → **Profile** → **Personal Access Tokens**
2. Click **Create token**
3. Set permissions for project access and issue creation
4. Copy the generated token

## Step 2: Gather JIRA Information

You'll need:
- **JIRA URL**: Your JIRA instance URL (e.g., `https://yourcompany.atlassian.net`)
- **Username**: Your JIRA username/email
- **API Token**: The token you just generated
- **Project Key**: The project where tasks will be created (e.g., "PROJ", "DEV")

## Step 3: Configure Environment Variables

Create a `.env` file in your project root with your JIRA credentials:

```bash
# JIRA Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your_generated_api_token_here
JIRA_PROJECT_KEY=PROJ

# Optional: Customize behavior
JIRA_SIMILARITY_THRESHOLD=0.85
JIRA_MAX_SEARCH_RESULTS=50

# MCP Configuration (optional)
MCP_ATLASSIAN_URL=mcp://atlassian
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_CACHE_TTL=300
```

## Step 4: Test Your JIRA Connection

### Using the Web Interface:
1. Start the application: `python app.py`
2. Open http://localhost:5000
3. Go to the JIRA Connection Test section
4. Enter your JIRA credentials
5. Click **Test Connection**

### Using the API:
```bash
curl -X POST http://localhost:5000/api/mcp/jira/connect \
  -H "Content-Type: application/json" \
  -d '{
    "jira_url": "https://yourcompany.atlassian.net",
    "username": "your.email@company.com",
    "api_token": "your_generated_api_token_here"
  }'
```

## Step 5: Verify Project Access

Test if you can access your project:

```bash
curl http://localhost:5000/api/mcp/jira/projects/PROJ/context
```

This should return comprehensive project information including:
- Project metadata
- Available issue types
- Active epics
- Recent issues
- Current sprint information

## Step 6: Process Your First Transcript

1. Upload a meeting transcript or refinement document
2. Select your JIRA project from the dropdown
3. The system will:
   - Extract tasks with project context
   - Check for duplicates against existing JIRA issues
   - Suggest appropriate issue types based on your project
   - Auto-link tasks to relevant epics
   - Validate against your project schema

## Advanced Features

### Context-Aware Task Extraction
```bash
curl -X POST http://localhost:5000/api/mcp/ai/extract-with-context \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "We need to implement user authentication...",
    "project_key": "PROJ",
    "additional_context": "Security sprint planning meeting"
  }'
```

### Smart Duplicate Detection
```bash
curl -X POST http://localhost:5000/api/mcp/smart/check-duplicates \
  -H "Content-Type: application/json" \
  -d '{
    "task": {
      "summary": "Implement login functionality",
      "description": "Create user authentication system"
    },
    "project_key": "PROJ",
    "include_resolved": false
  }'
```

### Bulk Task Creation
```bash
curl -X POST http://localhost:5000/api/mcp/jira/create-smart-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "project_key": "PROJ",
    "tasks": [
      {
        "summary": "Implement user login",
        "description": "Create authentication system",
        "issue_type": "Story"
      }
    ]
  }'
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate API tokens** regularly (every 90 days recommended)
4. **Limit token permissions** to only what's needed
5. **Monitor API usage** in your JIRA admin console

## Troubleshooting

### Common Issues:

**"Authentication failed"**
- Verify your API token is correct and not expired
- Check if your username/email is correct
- Ensure your JIRA URL includes the full domain

**"Project not found"**
- Verify the project key is correct (case-sensitive)
- Ensure you have access to the project
- Check if the project exists and is not archived

**"Permission denied"**
- Verify you have "Create Issues" permission in the project
- Check if your user account is active
- Ensure API token has required permissions

**"Connection timeout"**
- Check your network connection
- Verify JIRA URL is accessible
- Try increasing MCP_TIMEOUT in environment variables

### Debug Mode:
Set `DEBUG=true` in your environment to see detailed logging:

```bash
DEBUG=true python app.py
```

## Support

For issues with JIRA integration:
1. Check the application logs
2. Verify your JIRA permissions
3. Test the connection using JIRA's REST API browser
4. Review Atlassian's API documentation

## Next Steps

Once connected, you can:
- Process meeting transcripts with real project context
- Get intelligent duplicate detection against live JIRA data
- Create tasks with proper project schema validation
- Use context-aware AI suggestions based on your project history
- Set up automated workflows for regular meeting processing

The system now leverages your actual JIRA project data to provide enhanced, context-aware task extraction and management!