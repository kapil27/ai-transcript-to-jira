# JIRA CSV Generator

A modular application for extracting actionable tasks and Q&A items from meeting transcripts and generating JIRA-compatible CSV files using local AI processing.

## Features

- **Meeting Transcript Analysis**: Extract actionable tasks and questions from meeting transcripts
- **Local AI Processing**: Uses Ollama for private, local AI processing (no data sent to cloud services)
- **JIRA CSV Export**: Generate JIRA-compatible CSV files for easy import
- **Web Interface**: User-friendly web interface with progress tracking
- **Modular Architecture**: Clean, testable code following best practices

## Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally
- Llama 3.1 model downloaded in Ollama

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jira_project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start Ollama and ensure the model is available:
```bash
ollama pull llama3.1:latest
ollama serve
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Architecture

### Project Structure

```
jira_project/
├── src/
│   ├── api/                 # API routes and handlers
│   ├── config/              # Configuration management
│   ├── models/              # Data models (JiraTask, QAItem)
│   ├── services/            # Business logic services
│   ├── utils/               # Utility functions and classes
│   └── exceptions.py        # Custom exception classes
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Pytest configuration
├── templates/               # Web interface templates
├── static/                  # Static assets (CSS, JS)
└── docs/                    # Documentation
```

### Core Components

#### Services
- **TranscriptAnalysisService**: Orchestrates transcript processing
- **OllamaService**: Handles AI communication with Ollama
- **CSVGenerationService**: Generates JIRA-compatible CSV files

#### Models
- **JiraTask**: Represents a JIRA task with validation
- **QAItem**: Represents a question-answer pair with context

#### Configuration
- Environment-based configuration management
- Configurable AI service parameters
- Processing limits and validation rules

## API Endpoints

### Health Check
- `GET /api/health` - Service health status

### Transcript Processing
- `POST /api/parse-transcript` - Extract tasks only
- `POST /api/extract-qa` - Extract Q&A only  
- `POST /api/process-enhanced` - Extract both tasks and Q&A

### CSV Generation
- `POST /api/generate-csv` - Generate CSV file from tasks

### Service Status
- `GET /api/status` - Get service status and configuration

## Configuration

Configuration can be set via environment variables:

```bash
# Application settings
DEBUG=false
HOST=127.0.0.1
PORT=5000
SECRET_KEY=your-secret-key

# Ollama settings
OLLAMA_MODEL=llama3.1:latest
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT=60

# Processing limits
MAX_TASKS=10
MAX_QUESTIONS=8
MAX_TRANSCRIPT_LENGTH=50000

# JIRA settings
DEFAULT_REPORTER=meeting@example.com
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=src
```

## Development

### Setting up development environment

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests before committing:
```bash
pytest
```

3. Format code:
```bash
black src/ tests/
```

### Adding new features

1. Create tests first (TDD approach)
2. Implement the feature following the existing patterns
3. Update documentation as needed
4. Ensure all tests pass

## Security Considerations

- All AI processing is done locally using Ollama
- No transcript data is sent to external services
- Input validation prevents malicious data processing
- Configurable processing limits prevent resource exhaustion

## Troubleshooting

### Common Issues

1. **Ollama connection failed**
   - Ensure Ollama is running: `ollama serve`
   - Check if the model is available: `ollama list`
   - Verify the OLLAMA_URL configuration

2. **No tasks extracted**
   - Check transcript content (minimum 10 words)
   - Ensure transcript contains actionable items
   - Try the iterative extraction mode

3. **CSV generation fails**
   - Verify task data has required fields (summary)
   - Check for validation errors in logs
   - Ensure proper email format for reporter field

### Logs

Application logs provide detailed information about:
- AI service communication
- Task extraction process
- Validation errors
- Performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.