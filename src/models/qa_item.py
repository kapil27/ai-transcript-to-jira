"""Q&A data models for meeting transcript analysis."""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class QAItem:
    """Represents a question and answer pair from a meeting transcript."""
    
    question: str
    context: str = ""
    answer: str = ""
    asked_by: str = "meeting@example.com"
    answered_by: str = ""
    status: str = "unanswered"
    
    def __post_init__(self):
        """Validate Q&A data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate Q&A data according to requirements."""
        if not self.question or not self.question.strip():
            raise ValueError("Question is required and cannot be empty")
        
        if len(self.question) > 500:
            raise ValueError("Question cannot exceed 500 characters")
        
        if not self.question.strip().endswith('?'):
            raise ValueError("Question must end with a question mark")
        
        if self.asked_by and "@" not in self.asked_by:
            raise ValueError("Asked by must be a valid email address")
        
        if self.answered_by and "@" not in self.answered_by:
            raise ValueError("Answered by must be a valid email address")
        
        valid_statuses = {"answered", "unanswered"}
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        
        # Auto-determine status based on answer presence
        if self.answer.strip() and self.status == "unanswered":
            self.status = "answered"
        elif not self.answer.strip() and self.status == "answered":
            self.status = "unanswered"
    
    def to_dict(self) -> dict:
        """Convert Q&A item to dictionary for JSON serialization."""
        return {
            'question': self.question,
            'context': self.context,
            'answer': self.answer,
            'asked_by': self.asked_by,
            'answered_by': self.answered_by,
            'status': self.status
        }
    
    def has_answer(self) -> bool:
        """Check if the question has been answered."""
        return bool(self.answer.strip())
    
    def get_summary(self) -> str:
        """Get a brief summary of the Q&A item."""
        question_preview = self.question[:50] + "..." if len(self.question) > 50 else self.question
        return f"{question_preview} [{self.status}]"