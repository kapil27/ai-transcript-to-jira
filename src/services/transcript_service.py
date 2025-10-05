"""Service for processing meeting transcripts and extracting actionable items."""

from typing import Dict, List, Any, Tuple

from ..config import AppConfig
from ..exceptions import TranscriptError, AIServiceError
from ..utils import LoggerMixin
from .ai_service import AIService, OllamaService
from .cache_service import CacheService


class TranscriptAnalysisService(LoggerMixin):
    """Service for analyzing meeting transcripts and extracting tasks and Q&A."""
    
    def __init__(self, config: AppConfig, ai_service: AIService = None):
        """
        Initialize transcript analysis service.
        
        Args:
            config: Application configuration
            ai_service: AI service instance (optional, defaults to OllamaService)
        """
        self.config = config
        self.ai_service = ai_service or OllamaService(config)
        self._cache_service = CacheService()
    
    def analyze_transcript(self, transcript: str, context: str = "") -> Dict[str, Any]:
        """
        Analyze transcript to extract both tasks and Q&A items.
        
        Args:
            transcript: Raw meeting transcript text
            context: Additional context to enhance AI processing
            
        Returns:
            Dictionary containing tasks, qa_items, and counts
            
        Raises:
            TranscriptError: If transcript is invalid
            AIServiceError: If AI service fails
        """
        if not transcript.strip():
            raise TranscriptError("Transcript cannot be empty")
        
        # Check cache first for complete analysis
        cached_analysis = self._cache_service.get_transcript_analysis(transcript, context)
        if cached_analysis:
            self.logger.info("Returning cached transcript analysis")
            return cached_analysis
        
        self.logger.info("Starting comprehensive transcript analysis")
        
        try:
            # Extract tasks and Q&A in parallel with context
            tasks = self.ai_service.parse_transcript(transcript, context)
            qa_items = self.ai_service.extract_questions(transcript, context)
            
            result = {
                'tasks': tasks,
                'qa_items': qa_items,
                'tasks_count': len(tasks),
                'qa_count': len(qa_items),
                'success': True
            }
            
            self.logger.info(f"Analysis complete: {len(tasks)} tasks, {len(qa_items)} Q&A items")
            
            # Cache the complete analysis result
            self._cache_service.cache_transcript_analysis(transcript, context, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Transcript analysis failed: {e}")
            raise
    
    def extract_tasks_only(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Extract only tasks from transcript.
        
        Args:
            transcript: Raw meeting transcript text
            context: Additional context to enhance AI processing
            
        Returns:
            List of task dictionaries
        """
        self.logger.info("Extracting tasks only from transcript")
        return self.ai_service.parse_transcript(transcript, context)
    
    def extract_qa_only(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Extract only Q&A items from transcript.
        
        Args:
            transcript: Raw meeting transcript text
            context: Additional context to enhance AI processing
            
        Returns:
            List of Q&A dictionaries
        """
        self.logger.info("Extracting Q&A only from transcript")
        return self.ai_service.extract_questions(transcript, context)
    
    def validate_transcript(self, transcript: str) -> Tuple[bool, str]:
        """
        Validate transcript before processing.
        
        Args:
            transcript: Raw meeting transcript text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not transcript or not transcript.strip():
            return False, "Transcript cannot be empty"
        
        if len(transcript) > self.config.max_transcript_length:
            return False, f"Transcript too long (max {self.config.max_transcript_length} characters)"
        
        # Basic content validation
        word_count = len(transcript.split())
        if word_count < 10:
            return False, "Transcript too short (minimum 10 words)"
        
        return True, ""
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of the transcript analysis service.

        Returns:
            Dictionary with service status information
        """
        ai_available = self.ai_service.test_connection()

        # Check JIRA configuration
        jira_configured = all([
            self.config.jira.base_url,
            self.config.jira.username,
            self.config.jira.api_token
        ])

        return {
            'ai_service_available': ai_available,
            'ai_service_type': self.ai_service.__class__.__name__,
            'max_tasks': self.config.max_tasks_per_transcript,
            'max_questions': self.config.max_questions_per_transcript,
            'max_transcript_length': self.config.max_transcript_length,
            'jira_configured': jira_configured,
            'mcp_features_available': jira_configured
        }