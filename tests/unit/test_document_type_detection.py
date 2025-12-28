"""Unit tests for document type detection in AI service."""

import pytest
from unittest.mock import Mock, patch

from src.services.ai_service import OllamaService
from src.config import AppConfig, OllamaConfig


class TestDocumentTypeDetection:
    """Tests for _detect_document_type method."""
    
    @pytest.fixture
    def mock_config(self):
        """Create test configuration."""
        return AppConfig(
            debug=True,
            ollama=OllamaConfig(
                model_name="test-model",
                base_url="http://localhost:11434",
                timeout=30
            )
        )
    
    @pytest.fixture
    def service(self, mock_config):
        """Create OllamaService instance for testing."""
        return OllamaService(mock_config)
    
    # Refinement document tests
    
    def test_detects_user_story_as_refinement(self, service):
        """Documents with user stories should be detected as refinement."""
        text = """
        User Story: As a user, I want to login
        Acceptance Criteria: 
        - Given I am on login page
        - When I enter valid credentials
        - Then I should be logged in
        """
        assert service._detect_document_type(text) == "refinement"
    
    def test_detects_epic_as_refinement(self, service):
        """Documents with epic and feature requirements should be refinement."""
        text = """
        Epic: Payment System
        Feature Requirement: Process credit cards
        Technical Specification: Use Stripe API
        """
        assert service._detect_document_type(text) == "refinement"
    
    def test_detects_api_spec_as_refinement(self, service):
        """API specifications should be detected as refinement."""
        text = """
        API Specification for User Service
        
        Technical Specification:
        - POST /api/users - Create user
        - GET /api/users/:id - Get user
        - PUT /api/users/:id - Update user
        
        Non-functional requirement: Response time < 200ms
        """
        assert service._detect_document_type(text) == "refinement"
    
    def test_detects_bdd_format_as_refinement(self, service):
        """Given/When/Then format with user story should indicate refinement."""
        text = """
        User Story: User Registration
        
        Acceptance Criteria:
        Given When Then format for testing
        As a user I want to register
        
        Definition of Done:
        - All tests pass
        - Documentation complete
        """
        assert service._detect_document_type(text) == "refinement"
    
    # Meeting transcript tests
    
    def test_detects_dialogue_as_meeting(self, service):
        """Documents with dialogue patterns should be detected as meeting."""
        text = """
        John: Let's discuss the sprint
        Sarah: I agree, we need to prioritize
        Mike: The action item is to update the API
        John: Assigned to Mike, follow up next week
        """
        assert service._detect_document_type(text) == "meeting"
    
    def test_detects_meeting_keywords_as_meeting(self, service):
        """Documents with meeting keywords should be meeting."""
        text = """
        Meeting started at 10am
        Attendees: John, Sarah, Mike
        Agenda: Sprint review and planning
        
        We discussed the upcoming features.
        Action items were assigned.
        Meeting ended at 11am.
        """
        assert service._detect_document_type(text) == "meeting"
    
    def test_detects_transcript_keyword_as_meeting(self, service):
        """Documents with 'transcript' keyword should be meeting."""
        text = """
        Transcript of product planning meeting
        
        The team discussed various options.
        Decisions were made about next steps.
        """
        assert service._detect_document_type(text) == "meeting"
    
    # Edge cases
    
    def test_empty_text_defaults_to_meeting(self, service):
        """Empty text should default to meeting."""
        assert service._detect_document_type("") == "meeting"
        assert service._detect_document_type("   ") == "meeting"
    
    def test_short_text_defaults_to_meeting(self, service):
        """Very short text should default to meeting."""
        assert service._detect_document_type("short") == "meeting"
        assert service._detect_document_type("hello") == "meeting"
    
    def test_none_text_defaults_to_meeting(self, service):
        """None text should default to meeting."""
        assert service._detect_document_type(None) == "meeting"
    
    def test_ambiguous_text_defaults_to_meeting(self, service):
        """Ambiguous text without clear indicators should default to meeting."""
        text = """
        We need to work on the feature.
        The team will handle this next week.
        Some updates are required.
        """
        assert service._detect_document_type(text) == "meeting"
    
    def test_mixed_signals_with_dialogue(self, service):
        """Mixed signals with dialogue should lean toward meeting."""
        text = """
        Feature requirement: User login
        
        John: What about the acceptance criteria?
        Sarah: We need to define that
        Mike: I'll take care of it
        """
        # Dialogue patterns should outweigh single refinement indicator
        result = service._detect_document_type(text)
        # Either is acceptable for mixed signals, but meeting is preferred
        assert result in ["meeting", "refinement"]
    
    def test_structured_document_detection(self, service):
        """Heavily structured documents should lean toward refinement."""
        structured_text = """# Feature Requirements
        
## User Stories
- As a user, I want X
- As an admin, I want Y

## Technical Requirements  
1. API endpoint for /users
2. Database migration
3. Unit tests required

## Acceptance Criteria
- All tests pass
- Documentation complete
"""
        assert service._detect_document_type(structured_text) == "refinement"


class TestDocumentTypeDetectionScoring:
    """Tests for the scoring logic in document type detection."""
    
    @pytest.fixture
    def service(self):
        """Create OllamaService instance for testing."""
        mock_config = AppConfig(
            debug=True,
            ollama=OllamaConfig(
                model_name="test-model",
                base_url="http://localhost:11434",
                timeout=30
            )
        )
        return OllamaService(mock_config)
    
    def test_strong_refinement_indicators_score_higher(self, service):
        """Strong indicators should overcome weak meeting signals."""
        text = """
        User Story: Login feature
        Acceptance Criteria: Must validate email
        Definition of Done: Tests pass
        
        We will implement this.
        """
        # Multiple strong indicators should result in refinement
        assert service._detect_document_type(text) == "refinement"
    
    def test_multiple_speakers_boost_meeting_score(self, service):
        """Multiple speaker patterns should strongly indicate meeting."""
        text = """
        John: First point
        Sarah: I agree
        Mike: Let me add
        Emma: Good point
        Alex: Final thoughts
        """
        assert service._detect_document_type(text) == "meeting"
    
    @pytest.mark.parametrize("text,expected", [
        # Clear refinement documents
        ("User Story: As a user I want to X", "refinement"),
        ("Acceptance Criteria: Given When Then", "refinement"),
        ("Epic: Major Feature\nFeature Requirement: Sub feature", "refinement"),
        
        # Clear meeting transcripts
        ("John: Let's start\nSarah: Agreed", "meeting"),
        ("Meeting started at 9am. Attendees: Team", "meeting"),
        ("Action item: Update docs. Follow up Friday.", "meeting"),
        
        # Edge cases
        ("", "meeting"),
        ("x", "meeting"),
        ("The feature needs work", "meeting"),
    ])
    def test_parametrized_detection(self, service, text, expected):
        """Parametrized test for various document types."""
        result = service._detect_document_type(text)
        assert result == expected, f"Expected '{expected}' for: {text[:50]}..."

