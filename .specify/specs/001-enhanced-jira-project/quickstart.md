# Quickstart Guide: Enhanced JIRA Project Specification

**Feature**: Enhanced JIRA Project Specification and Integration
**Date**: 2024-12-28
**Estimated Setup Time**: 15-20 minutes

## Prerequisites

### 1. System Requirements
- Python 3.11+ installed
- Ollama running locally with llama3.1 model
- Redis server (for caching) - optional but recommended
- JIRA instance access with API permissions

### 2. JIRA Requirements
- **JIRA Account**: Access to JIRA Cloud or Server instance
- **API Token**: Generated from JIRA account settings
- **Project Access**: Read/Write permissions to target projects
- **Issue Creation**: Permission to create issues in selected projects

### 3. Generate JIRA API Token
1. Log in to your JIRA instance
2. Go to Account Settings → Security → API Tokens
3. Click "Create API Token"
4. Name it "AI Transcript Integration"
5. Copy the generated token (you'll need this for setup)

## Installation & Setup

### 1. Install Dependencies
```bash
# Navigate to project directory
cd /Users/knema/Project/personal-ai-tools/ai-transcript-to-jira

# Install new JIRA integration dependencies
pip install -r requirements.txt

# If requirements.txt doesn't include new packages:
pip install atlassian-python-api==3.41.5
pip install aiohttp==3.9.1
pip install fuzzywuzzy==0.18.0
pip install python-levenshtein==0.25.0
pip install cryptography==41.0.8
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your JIRA details
nano .env
```

Add the following to your `.env` file:
```bash
# Existing configuration (keep as-is)
OLLAMA_MODEL=llama3.1:latest
OLLAMA_URL=http://localhost:11434

# New JIRA Integration Settings
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your_generated_api_token_here

# JIRA Behavior Settings
JIRA_TIMEOUT=30
JIRA_MAX_RETRIES=3
JIRA_CACHE_TTL=300
JIRA_SIMILARITY_THRESHOLD=0.85
JIRA_MAX_SEARCH_RESULTS=50
JIRA_REQUESTS_PER_MINUTE=50

# Security
ENCRYPTION_KEY=generate-a-32-byte-base64-key-here
```

### 3. Generate Encryption Key
```bash
# Generate a secure encryption key for JIRA credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output and set it as `ENCRYPTION_KEY` in your `.env` file.

### 4. Database Setup
```bash
# Create database tables (if not using existing SQLite)
python -c "
from src.config import get_config
from src.utils.database import create_jira_tables
create_jira_tables(get_config())
"
```

### 5. Test JIRA Connection
```bash
# Test your JIRA credentials
python -c "
from src.services.mcp_jira_service import MCPJiraService
from src.config import get_config

config = get_config()
jira_service = MCPJiraService(config)

# Test connection
print('Testing JIRA connection...')
result = jira_service.test_connection()
print(f'Connection successful: {result}')

if result:
    projects = jira_service.get_projects()
    print(f'Found {len(projects)} accessible projects')
    for project in projects[:3]:  # Show first 3
        print(f'  - {project.key}: {project.name}')
else:
    print('Connection failed - check credentials')
"
```

## Configuration Walkthrough

### 1. JIRA Connection Setup
```bash
# Start the application
python app.py
```

Navigate to `http://localhost:5000` and:

1. **Configure JIRA Connection**:
   - Click "JIRA Settings" in the main interface
   - Enter your JIRA URL, username, and API token
   - Click "Test Connection"
   - Verify you see a green "Connected" status

2. **Select Default Project**:
   - Choose a project from the dropdown
   - Click "Load Project Context"
   - Verify you see sprints, epics, and issue types

### 2. Project Context Verification
Confirm the following information appears in the UI:
- **Active Sprints**: Current sprint name and dates
- **Available Epics**: List of open epics for task linking
- **Issue Types**: Story, Task, Bug options based on your project
- **Project Lead**: Current project administrator

### 3. Test End-to-End Workflow
1. **Upload Sample Transcript**:
   ```
   "We need to fix the login bug that users reported yesterday.
   Also, let's create a new dashboard feature for the Q3 roadmap.
   The performance issues in the search functionality should be addressed ASAP."
   ```

2. **Process with Project Context**:
   - Select your configured project
   - Click "Process with JIRA Context"
   - Wait for AI extraction (15-30 seconds)

3. **Review Enhanced Tasks**:
   - Verify tasks show suggested issue types (Bug, Story, Task)
   - Check for epic assignments if applicable
   - Review duplicate detection warnings if any

4. **Create JIRA Issues**:
   - Select tasks to create
   - Click "Create in JIRA"
   - Verify issues appear in your JIRA project

## Verification Checklist

### ✅ Basic Functionality
- [ ] Application starts without errors
- [ ] JIRA connection test succeeds
- [ ] Project list loads within 5 seconds
- [ ] Project context (sprints, epics) displays correctly

### ✅ Core Features
- [ ] Transcript processing with project context works
- [ ] Enhanced tasks show JIRA-appropriate suggestions
- [ ] Duplicate detection identifies similar existing issues
- [ ] Issue creation in JIRA succeeds

### ✅ Performance
- [ ] Project context loads in < 5 seconds
- [ ] Duplicate analysis completes in < 10 seconds
- [ ] End-to-end workflow completes in < 2 minutes

### ✅ Error Handling
- [ ] Invalid JIRA credentials show clear error message
- [ ] Network issues display user-friendly warnings
- [ ] Duplicate conflicts provide resolution options

## Common Issues & Solutions

### Issue: "Connection Failed"
**Symptoms**: Red error message when testing JIRA connection
**Solutions**:
1. Verify JIRA URL format: `https://company.atlassian.net`
2. Confirm API token is correct (not account password)
3. Check username is full email address
4. Ensure account has API access permissions

### Issue: "No Projects Found"
**Symptoms**: Empty project dropdown after successful connection
**Solutions**:
1. Verify account has project access permissions
2. Check if projects are archived or restricted
3. Contact JIRA administrator for project access

### Issue: "Slow Performance"
**Symptoms**: Long delays during project context loading
**Solutions**:
1. Enable Redis caching: `pip install redis` and start Redis server
2. Reduce `JIRA_MAX_SEARCH_RESULTS` to 25
3. Check network connectivity to JIRA instance

### Issue: "Duplicate Detection Not Working"
**Symptoms**: No duplicate warnings for obviously similar tasks
**Solutions**:
1. Lower `JIRA_SIMILARITY_THRESHOLD` to 0.7
2. Verify project has existing issues to compare against
3. Check that search permissions are enabled

### Issue: "Task Creation Fails"
**Symptoms**: Error when creating issues in JIRA
**Solutions**:
1. Verify issue creation permissions in project
2. Check required field configurations in JIRA project
3. Ensure issue types are available in project scheme

## Next Steps

### 1. Regular Usage
- Process meeting transcripts by selecting appropriate projects
- Review and adjust duplicate detection suggestions
- Monitor JIRA issue creation success rates

### 2. Advanced Configuration
- Set up project-specific contexts and templates
- Configure custom field mappings for your JIRA projects
- Adjust AI processing parameters for better accuracy

### 3. Team Deployment
- Document project-specific configuration for team members
- Set up shared JIRA connections with service account
- Create templates for common meeting types (standup, planning, retrospective)

### 4. Monitoring & Optimization
- Monitor JIRA API usage to stay within rate limits
- Review duplicate detection accuracy and adjust thresholds
- Track task creation success rates and user adoption

## Support Resources

### Documentation
- `README.md`: General application overview
- `docs/API.md`: API endpoint documentation
- `JIRA_INTEGRATION_SETUP.md`: Detailed JIRA configuration

### Logs & Debugging
```bash
# View application logs
tail -f logs/app.log

# Debug JIRA API calls
export DEBUG=true
python app.py

# Test specific JIRA operations
python -m src.services.mcp_jira_service --test
```

### Getting Help
1. Check application logs for detailed error messages
2. Verify JIRA permissions in Atlassian admin console
3. Test JIRA API access using browser or curl
4. Review project-specific issue type and field configurations

---

**🎉 Setup Complete!** Your Enhanced JIRA Project Specification feature is now ready for use. Start by processing a sample meeting transcript with your configured project context.