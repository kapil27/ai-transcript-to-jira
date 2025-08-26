"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, patch

from src.config import AppConfig, OllamaConfig
from src.services.ai_service import OllamaService
from src.services.transcript_service import TranscriptAnalysisService
from src.services.csv_service import CSVGenerationService


@pytest.fixture
def test_config():
    """Create test configuration."""
    return AppConfig(
        debug=True,
        ollama=OllamaConfig(
            model_name="test-model",
            base_url="http://localhost:11434",
            timeout=30
        ),
        max_tasks_per_transcript=5,
        max_questions_per_transcript=5,
        max_transcript_length=10000
    )


@pytest.fixture
def mock_ollama_service():
    """Create mock Ollama service."""
    mock_service = Mock(spec=OllamaService)
    mock_service.test_connection.return_value = True
    mock_service.parse_transcript.return_value = [
        {
            'summary': 'Test task',
            'description': 'Test description',
            'issue_type': 'Task',
            'reporter': 'test@example.com',
            'due_date': ''
        }
    ]
    mock_service.extract_questions.return_value = [
        {
            'question': 'What is the deadline?',
            'context': 'Project timeline discussion',
            'answer': '',
            'asked_by': 'test@example.com',
            'answered_by': '',
            'status': 'unanswered'
        }
    ]
    return mock_service


@pytest.fixture
def transcript_service(test_config, mock_ollama_service):
    """Create transcript analysis service with mocked AI service."""
    return TranscriptAnalysisService(test_config, mock_ollama_service)


@pytest.fixture
def csv_service():
    """Create CSV generation service."""
    return CSVGenerationService()


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing."""
    return """
Meeting: Sprint Planning
John: Sarah, can you implement the user authentication API?
Sarah: Sure, I can have that done by Friday.
Mike: I noticed a bug in the login form - the button is misaligned.
Lisa: What about the UI mockups? Do we have them ready?
John: Good question, we need those. Lisa, can you create them?
Mike: How should we test the authentication flow?
"""


@pytest.fixture
def sample_tasks():
    """Sample task data for testing."""
    return [
        {
            'summary': 'Implement user authentication API',
            'description': 'Add login and registration functionality',
            'issue_type': 'Task',
            'reporter': 'meeting@example.com',
            'due_date': '2024-12-31'
        },
        {
            'summary': 'Fix login button alignment',
            'description': 'Login button is misaligned in the form',
            'issue_type': 'Bug',
            'reporter': 'meeting@example.com',
            'due_date': ''
        }
    ]


@pytest.fixture
def sample_qa_items():
    """Sample Q&A data for testing."""
    return [
        {
            'question': 'What about the UI mockups?',
            'context': 'Discussion about project deliverables',
            'answer': '',
            'asked_by': 'meeting@example.com',
            'answered_by': '',
            'status': 'unanswered'
        },
        {
            'question': 'How should we test the authentication flow?',
            'context': 'Testing strategy discussion',
            'answer': '',
            'asked_by': 'meeting@example.com',
            'answered_by': '',
            'status': 'unanswered'
        }
    ]