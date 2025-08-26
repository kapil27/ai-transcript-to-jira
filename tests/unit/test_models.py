"""Unit tests for data models."""

import pytest
from datetime import datetime

from src.models.task import JiraTask
from src.models.qa_item import QAItem


class TestJiraTask:
    """Test cases for JiraTask model."""
    
    def test_valid_task_creation(self):
        """Test creating a valid JIRA task."""
        task = JiraTask(
            summary="Test task",
            description="Test description",
            issue_type="Task",
            reporter="test@example.com",
            due_date="2024-12-31"
        )
        
        assert task.summary == "Test task"
        assert task.description == "Test description"
        assert task.issue_type == "Task"
        assert task.reporter == "test@example.com"
        assert task.due_date == "2024-12-31"
    
    def test_task_with_defaults(self):
        """Test creating task with default values."""
        task = JiraTask(summary="Test task")
        
        assert task.summary == "Test task"
        assert task.description == ""
        assert task.issue_type == "Task"
        assert task.reporter == "meeting@example.com"
        assert task.due_date is None
    
    def test_empty_summary_validation(self):
        """Test validation fails for empty summary."""
        with pytest.raises(ValueError, match="Task summary is required"):
            JiraTask(summary="")
    
    def test_long_summary_validation(self):
        """Test validation fails for long summary."""
        long_summary = "x" * 256
        with pytest.raises(ValueError, match="Task summary cannot exceed 255 characters"):
            JiraTask(summary=long_summary)
    
    def test_invalid_issue_type_validation(self):
        """Test validation fails for invalid issue type."""
        with pytest.raises(ValueError, match="Issue type must be one of"):
            JiraTask(summary="Test", issue_type="InvalidType")
    
    def test_invalid_email_validation(self):
        """Test validation fails for invalid email."""
        with pytest.raises(ValueError, match="Reporter must be a valid email address"):
            JiraTask(summary="Test", reporter="invalid-email")
    
    def test_invalid_date_validation(self):
        """Test validation fails for invalid date format."""
        with pytest.raises(ValueError, match="Due date must be in YYYY-MM-DD format"):
            JiraTask(summary="Test", due_date="invalid-date")
    
    def test_to_dict_conversion(self):
        """Test converting task to dictionary."""
        task = JiraTask(
            summary="Test task",
            description="Test description",
            issue_type="Bug",
            reporter="test@example.com",
            due_date="2024-12-31"
        )
        
        result = task.to_dict()
        expected = {
            'summary': 'Test task',
            'description': 'Test description',
            'issue_type': 'Bug',
            'reporter': 'test@example.com',
            'due_date': '2024-12-31'
        }
        
        assert result == expected
    
    def test_to_dict_with_none_due_date(self):
        """Test to_dict with None due_date."""
        task = JiraTask(summary="Test task")
        result = task.to_dict()
        
        assert result['due_date'] == ""


class TestQAItem:
    """Test cases for QAItem model."""
    
    def test_valid_qa_creation(self):
        """Test creating a valid Q&A item."""
        qa = QAItem(
            question="What is the deadline?",
            context="Discussion about project timeline",
            answer="End of next week",
            asked_by="user@example.com",
            answered_by="manager@example.com",
            status="answered"
        )
        
        assert qa.question == "What is the deadline?"
        assert qa.context == "Discussion about project timeline"
        assert qa.answer == "End of next week"
        assert qa.asked_by == "user@example.com"
        assert qa.answered_by == "manager@example.com"
        assert qa.status == "answered"
    
    def test_qa_with_defaults(self):
        """Test creating Q&A with default values."""
        qa = QAItem(question="What time is the meeting?")
        
        assert qa.question == "What time is the meeting?"
        assert qa.context == ""
        assert qa.answer == ""
        assert qa.asked_by == "meeting@example.com"
        assert qa.answered_by == ""
        assert qa.status == "unanswered"
    
    def test_empty_question_validation(self):
        """Test validation fails for empty question."""
        with pytest.raises(ValueError, match="Question is required"):
            QAItem(question="")
    
    def test_long_question_validation(self):
        """Test validation fails for long question."""
        long_question = "x" * 501
        with pytest.raises(ValueError, match="Question cannot exceed 500 characters"):
            QAItem(question=long_question)
    
    def test_question_without_question_mark(self):
        """Test validation fails for question without question mark."""
        with pytest.raises(ValueError, match="Question must end with a question mark"):
            QAItem(question="This is not a question")
    
    def test_invalid_asked_by_email(self):
        """Test validation fails for invalid asked_by email."""
        with pytest.raises(ValueError, match="Asked by must be a valid email address"):
            QAItem(question="What time?", asked_by="invalid-email")
    
    def test_invalid_answered_by_email(self):
        """Test validation fails for invalid answered_by email."""
        with pytest.raises(ValueError, match="Answered by must be a valid email address"):
            QAItem(question="What time?", answered_by="invalid-email")
    
    def test_invalid_status_validation(self):
        """Test validation fails for invalid status."""
        with pytest.raises(ValueError, match="Status must be one of"):
            QAItem(question="What time?", status="invalid")
    
    def test_auto_status_determination_answered(self):
        """Test status is auto-determined when answer is provided."""
        qa = QAItem(
            question="What time?",
            answer="3 PM",
            status="unanswered"  # This should be corrected to "answered"
        )
        
        assert qa.status == "answered"
    
    def test_auto_status_determination_unanswered(self):
        """Test status is auto-determined when no answer is provided."""
        qa = QAItem(
            question="What time?",
            answer="",
            status="answered"  # This should be corrected to "unanswered"
        )
        
        assert qa.status == "unanswered"
    
    def test_has_answer_method(self):
        """Test has_answer method."""
        qa_with_answer = QAItem(question="What time?", answer="3 PM")
        qa_without_answer = QAItem(question="What time?")
        
        assert qa_with_answer.has_answer() is True
        assert qa_without_answer.has_answer() is False
    
    def test_get_summary_method(self):
        """Test get_summary method."""
        qa = QAItem(question="What time is the meeting?", answer="3 PM", status="answered")
        summary = qa.get_summary()
        
        assert "What time is the meeting?" in summary
        assert "[answered]" in summary
    
    def test_get_summary_with_long_question(self):
        """Test get_summary with long question."""
        long_question = "What time is the very important meeting that we need to attend tomorrow?"
        qa = QAItem(question=long_question, status="unanswered")
        summary = qa.get_summary()
        
        assert "..." in summary
        assert "[unanswered]" in summary
        assert len(summary.split("...")[0]) <= 50
    
    def test_to_dict_conversion(self):
        """Test converting Q&A to dictionary."""
        qa = QAItem(
            question="What time?",
            context="Meeting discussion",
            answer="3 PM",
            asked_by="user@example.com",
            answered_by="manager@example.com",
            status="answered"
        )
        
        result = qa.to_dict()
        expected = {
            'question': 'What time?',
            'context': 'Meeting discussion',
            'answer': '3 PM',
            'asked_by': 'user@example.com',
            'answered_by': 'manager@example.com',
            'status': 'answered'
        }
        
        assert result == expected