"""AI service abstraction for transcript analysis."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

from ..config import AppConfig
from ..exceptions import AIServiceError, TranscriptError
from ..utils import LoggerMixin
from .cache_service import CacheService, cached_ai_response


class AIService(ABC, LoggerMixin):
    """Abstract base class for AI services."""
    
    @abstractmethod
    def parse_transcript(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract tasks from transcript."""
        pass
    
    @abstractmethod
    def extract_questions(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract questions and answers from transcript."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the AI service is available."""
        pass


class OllamaService(AIService):
    """Ollama AI service implementation."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize Ollama service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.api_url = f"{config.ollama.base_url}/api/generate"
        self._cache_service = CacheService()
    
    @cached_ai_response("parse_transcript")
    def parse_transcript(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Extract actionable tasks from meeting transcript.
        
        Args:
            transcript: Raw meeting transcript text
            context: Additional context to enhance AI processing
            
        Returns:
            List of task dictionaries
            
        Raises:
            TranscriptError: If transcript is invalid
            AIServiceError: If AI service fails
        """
        if not transcript.strip():
            raise TranscriptError("Transcript text cannot be empty")
        
        if len(transcript) > self.config.max_transcript_length:
            raise TranscriptError(f"Transcript too long (max {self.config.max_transcript_length} chars)")
        
        try:
            self.logger.info("Starting task extraction from transcript")
            
            # Try multi-task extraction first with context
            prompt = self._create_task_extraction_prompt(transcript, context)
            response_text = self._call_ollama(prompt)
            
            if not response_text:
                raise AIServiceError("No response received from Ollama")
            
            tasks = self._parse_ollama_response(response_text)
            validated_tasks = self._validate_tasks(tasks)
            
            # If only one task found, try iterative approach
            if len(validated_tasks) <= 1:
                self.logger.info("Trying iterative extraction for more tasks")
                iterative_tasks = self._extract_tasks_iteratively(transcript, context)
                if len(iterative_tasks) > len(validated_tasks):
                    validated_tasks = iterative_tasks
            
            self.logger.info(f"Extracted {len(validated_tasks)} tasks")
            return validated_tasks[:self.config.max_tasks_per_transcript]
            
        except Exception as e:
            self.logger.error(f"Error parsing transcript: {e}")
            raise AIServiceError(f"Failed to parse transcript: {str(e)}")
    
    @cached_ai_response("extract_questions")
    def extract_questions(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Extract questions and answers from meeting transcript.
        
        Args:
            transcript: Raw meeting transcript text
            context: Additional context to enhance AI processing
            
        Returns:
            List of Q&A dictionaries
            
        Raises:
            TranscriptError: If transcript is invalid
            AIServiceError: If AI service fails
        """
        if not transcript.strip():
            raise TranscriptError("Transcript text cannot be empty")
        
        try:
            self.logger.info("Starting Q&A extraction from transcript")
            qa_items = self._extract_qa_iteratively(transcript, context)
            self.logger.info(f"Extracted {len(qa_items)} Q&A items")
            return qa_items[:self.config.max_questions_per_transcript]
            
        except Exception as e:
            self.logger.error(f"Error extracting Q&A: {e}")
            raise AIServiceError(f"Failed to extract Q&A: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test if Ollama service is available."""
        try:
            self.logger.info("Testing Ollama connection")
            test_response = self._call_ollama("Say OK", use_json_format=False)
            # Just check if we got any valid response
            is_connected = bool(test_response and len(test_response.strip()) > 0)
            self.logger.info(f"Ollama connection test: {'SUCCESS' if is_connected else 'FAILED'} (response: {test_response[:50] if test_response else 'None'})")
            return is_connected
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            return False
    
    def _call_ollama(self, prompt: str, use_json_format: bool = True) -> str:
        """Make API call to Ollama."""
        payload = {
            "model": self.config.ollama.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.ollama.temperature,
                "top_p": self.config.ollama.top_p
            }
        }
        
        if use_json_format:
            payload["format"] = "json"
        
        try:
            self.logger.debug(f"Calling Ollama at {self.api_url} with model {self.config.ollama.model_name}")
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=self.config.ollama.timeout
            )
            self.logger.debug(f"Ollama response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama API call failed: {e}, URL: {self.api_url}, Payload: {payload}")
            raise AIServiceError(f"Ollama API call failed: {e}")
    
    def _create_task_extraction_prompt(self, text: str, context: str = "") -> str:
        """Create prompt for task extraction from various document types."""
        document_type = self._detect_document_type(text)

        if document_type == "refinement":
            base_prompt = f"""Extract actionable tasks from this refinement document. Return results as a JSON array.

REFINEMENT DOCUMENT:
{text}

Find ALL implementable tasks, development items, and technical requirements. Each task should be a separate JSON object.

Return ONLY a JSON array in this exact format:
[
  {{
    "summary": "Task title (clear and actionable)",
    "description": "Detailed task description with acceptance criteria",
    "issue_type": "Story"
  }}
]

Look for:
- User stories and feature requirements
- Technical specifications to implement
- Bug fixes and improvements mentioned
- API endpoints to create/modify
- UI/UX changes needed
- Database schema changes
- Testing requirements
- Documentation updates

Focus on breaking down large features into specific, implementable tasks.
Return multiple objects in the array - one for each task found. If no tasks, return []."""
        else:
            base_prompt = f"""Extract actionable tasks from this meeting transcript or document. Return results as a JSON array.

DOCUMENT:
{text}

Find ALL tasks, action items, and assignments mentioned. Each task should be a separate JSON object.

Return ONLY a JSON array in this exact format:
[
  {{
    "summary": "Task title (clear and actionable)",
    "description": "Task description with context and details",
    "issue_type": "Task"
  }}
]

Look for:
- Explicit assignments ("John will do X")
- Work items mentioned ("We need to update Y")
- Bug reports ("There's an issue with Z")
- Follow-up tasks from decisions
- Action items and deliverables
- Research tasks and investigations

Return multiple objects in the array - one for each task found. If no tasks, return []."""

        if context.strip():
            return f"""{base_prompt}

ADDITIONAL CONTEXT:
{context}

Use this context to:
- Better understand technical terms and project-specific language
- Improve task descriptions with relevant background
- Categorize tasks more accurately based on project context
- Add appropriate details based on team roles and project requirements"""

        return base_prompt

    def _detect_document_type(self, text: str) -> str:
        """
        Detect if document is a refinement doc or meeting transcript.

        Returns:
            "refinement" for product requirement/specification docs
            "meeting" for meeting transcripts, notes, or general documents
        """
        if not text or len(text.strip()) < 10:
            return "meeting"  # Default for short/empty text

        text_lower = text.lower()

        # Strong refinement document indicators
        strong_refinement_indicators = [
            'user story', 'acceptance criteria', 'epic', 'feature requirement',
            'technical specification', 'api specification', 'user acceptance criteria',
            'definition of done', 'business requirement', 'functional requirement',
            'non-functional requirement', 'product requirement', 'feature spec'
        ]

        # Weaker refinement indicators
        weak_refinement_indicators = [
            'feature', 'requirement', 'specification', 'api endpoint',
            'database schema', 'mockup', 'wireframe', 'prototype',
            'design system', 'user journey', 'workflow', 'use case'
        ]

        # Meeting transcript indicators
        meeting_indicators = [
            'said:', 'discussed', 'agreed', 'decided', 'meeting started',
            'meeting ended', 'action item', 'follow up', 'next steps',
            'assigned to', 'will do', 'take care of', 'transcript',
            'attendees', 'agenda', 'minutes'
        ]

        # Name patterns that suggest dialogue/transcript
        dialogue_patterns = [
            ':', 'john:', 'sarah:', 'alex:', 'mike:', 'emma:', 'team:',
            'manager:', 'lead:', 'dev:', 'qa:', 'pm:'
        ]

        # Calculate scores
        strong_refinement_score = sum(2 for indicator in strong_refinement_indicators if indicator in text_lower)
        weak_refinement_score = sum(1 for indicator in weak_refinement_indicators if indicator in text_lower)
        meeting_score = sum(1 for indicator in meeting_indicators if indicator in text_lower)

        # Check for dialogue patterns (strong meeting indicator)
        dialogue_count = sum(1 for pattern in dialogue_patterns if pattern in text_lower)
        if dialogue_count >= 3:  # Multiple speakers suggest meeting transcript
            meeting_score += 5

        # Check document structure patterns
        if 'as a user' in text_lower or 'given when then' in text_lower:
            strong_refinement_score += 3

        # Count line breaks and structure (refinement docs tend to be more structured)
        lines = text.split('\n')
        if len(lines) > 10:
            # Look for structured document patterns
            structured_lines = sum(1 for line in lines if line.strip().startswith(('#', '-', '*', '1.', '2.', '3.')))
            if structured_lines > len(lines) * 0.3:  # 30% of lines are structured
                weak_refinement_score += 2

        total_refinement_score = strong_refinement_score + weak_refinement_score

        # Decision logic: require clear evidence for refinement classification
        if strong_refinement_score >= 2 or total_refinement_score >= 4:
            return "refinement"
        elif meeting_score >= 2 or dialogue_count >= 2:
            return "meeting"
        else:
            # Default to meeting for ambiguous cases
            return "meeting"

    @cached_ai_response("extract_tasks_iteratively")
    def _extract_tasks_iteratively(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """Extract tasks using iterative approach."""
        base_list_prompt = f"""Read this meeting transcript and list all actionable tasks/assignments:

{transcript}

List each task on a new line starting with a number:
1. Task description here
2. Another task description
3. etc.

Only list actual work items that need to be done by someone."""

        if context.strip():
            list_prompt = f"""{base_list_prompt}

ADDITIONAL CONTEXT:
{context}

Use this context to better understand the project and identify relevant tasks."""
        else:
            list_prompt = base_list_prompt

        try:
            list_response = self._call_ollama(list_prompt, use_json_format=False)
            if not list_response:
                return []

            # Parse numbered list
            lines = list_response.strip().split('\n')
            task_descriptions = []

            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                           line.startswith('- ') or line.startswith('* ')):
                    task_desc = line.split('.', 1)[-1].strip() if '.' in line else line[2:].strip()
                    if task_desc:
                        task_descriptions.append(task_desc)

            # Convert descriptions to task objects
            all_tasks = []
            for desc in task_descriptions[:self.config.max_tasks_per_transcript]:
                base_task_prompt = f"""Convert this task description into a JSON object:

Task: {desc}

Return ONLY a JSON object in this format:
{{
    "summary": "Brief title for the task",
    "description": "Detailed description",
    "issue_type": "Task"
}}"""

                if context.strip():
                    task_prompt = f"""{base_task_prompt}

ADDITIONAL CONTEXT:
{context}

Use this context to enhance the task description and ensure proper categorization."""
                else:
                    task_prompt = base_task_prompt

                try:
                    task_response = self._call_ollama(task_prompt)
                    if task_response:
                        task_data = self._parse_single_task(task_response)
                        if task_data:
                            all_tasks.append(task_data)
                except (json.JSONDecodeError, KeyError, AIServiceError) as e:
                    self.logger.debug(f"Failed to parse task '{desc[:50]}...': {e}")
                    continue

            return self._validate_tasks(all_tasks)

        except Exception as e:
            self.logger.debug(f"Task extraction failed: {e}")
            return []
    
    @cached_ai_response("extract_qa_iteratively")
    def _extract_qa_iteratively(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        """Extract Q&A using iterative approach."""
        base_questions_prompt = f"""Read this meeting transcript and list all questions asked by anyone:

{transcript}

List each question on a new line starting with a number:
1. Question text here?
2. Another question?
3. etc.

Only list actual questions (ending with ?). If no questions found, respond with "No questions found"."""

        if context.strip():
            questions_prompt = f"""{base_questions_prompt}

ADDITIONAL CONTEXT:
{context}

Use this context to better understand domain-specific questions and their importance."""
        else:
            questions_prompt = base_questions_prompt

        try:
            questions_response = self._call_ollama(questions_prompt, use_json_format=False)
            if not questions_response or "No questions found" in questions_response:
                return []

            # Parse numbered list of questions
            lines = questions_response.strip().split('\n')
            questions = []

            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or
                           line.startswith('- ') or line.startswith('* ')):
                    question_text = line.split('.', 1)[-1].strip() if '.' in line else line[2:].strip()
                    if question_text and question_text.endswith('?'):
                        questions.append(question_text)

            # Process each question for context
            all_qa = []
            for question in questions[:self.config.max_questions_per_transcript]:
                base_qa_prompt = f"""For this specific question from the meeting transcript, extract detailed information:

TRANSCRIPT:
{transcript}

QUESTION: {question}

Extract information about this question including context around when it was asked.

Return ONLY a JSON object in this format:
{{
    "question": "{question}",
    "context": "Background context about what was being discussed when this question was asked",
    "answer": "The answer text if found, or empty string if no answer",
    "asked_by": "{self.config.default_reporter}",
    "answered_by": "{self.config.default_reporter} or empty if no answer",
    "status": "answered or unanswered"
}}

For context, include what topic/feature was being discussed when the question was asked."""

                if context.strip():
                    qa_prompt = f"""{base_qa_prompt}

ADDITIONAL CONTEXT:
{context}

Use this additional context to provide richer background information and better understand the question's relevance to the project."""
                else:
                    qa_prompt = base_qa_prompt

                try:
                    qa_response = self._call_ollama(qa_prompt)
                    if qa_response:
                        qa_data = self._parse_single_task(qa_response)
                        if qa_data and qa_data.get('question'):
                            validated_qa = {
                                'question': qa_data.get('question', '').strip(),
                                'context': qa_data.get('context', '').strip(),
                                'answer': qa_data.get('answer', '').strip(),
                                'asked_by': self._validate_email(qa_data.get('asked_by', self.config.default_reporter)),
                                'answered_by': self._validate_email(qa_data.get('answered_by', '')),
                                'status': 'answered' if qa_data.get('answer', '').strip() else 'unanswered'
                            }
                            all_qa.append(validated_qa)
                except (json.JSONDecodeError, KeyError, AIServiceError) as e:
                    self.logger.debug(f"Failed to parse Q&A for '{question[:50]}...': {e}")
                    continue

            return all_qa

        except Exception as e:
            self.logger.debug(f"Q&A extraction failed: {e}")
            return []
    
    def _parse_ollama_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse JSON response from Ollama."""
        try:
            clean_text = response_text.strip()
            
            # Remove markdown formatting
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            tasks_data = json.loads(clean_text)
            
            # Handle single object response
            if isinstance(tasks_data, dict):
                self.logger.warning("Model returned single object instead of array")
                tasks_data = [tasks_data]
            elif not isinstance(tasks_data, list):
                raise ValueError(f"Response must be a JSON array, got: {type(tasks_data)}")
            
            return tasks_data
            
        except json.JSONDecodeError as e:
            raise AIServiceError(f"Invalid JSON response: {e}")
    
    def _parse_single_task(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse single task JSON object."""
        try:
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            task_data = json.loads(clean_text)
            return task_data if isinstance(task_data, dict) else None
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            self.logger.debug(f"Failed to parse task JSON: {e}")
            return None
    
    def _validate_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean task data."""
        validated_tasks = []
        
        for i, task in enumerate(tasks_data):
            try:
                if not task.get('summary', '').strip():
                    self.logger.warning(f"Skipping task {i+1} - missing summary")
                    continue
                
                clean_task = {
                    'summary': task['summary'].strip(),
                    'description': task.get('description', '').strip(),
                    'issue_type': self._validate_issue_type(task.get('issue_type', 'Task')),
                    'reporter': self._validate_email(task.get('reporter', self.config.default_reporter)),
                    'due_date': self._validate_date(task.get('due_date', ''))
                }
                
                validated_tasks.append(clean_task)
                
            except Exception as e:
                self.logger.warning(f"Skipping invalid task {i+1}: {e}")
                continue
        
        return validated_tasks
    
    def _validate_issue_type(self, issue_type: str) -> str:
        """Validate issue type."""
        if issue_type in self.config.valid_issue_types:
            return issue_type
        return 'Task'
    
    def _validate_email(self, email: str) -> str:
        """Validate email address."""
        if email and '@' in email:
            return email.strip()
        return self.config.default_reporter
    
    def _validate_date(self, date_str: str) -> str:
        """Validate date format (YYYY-MM-DD)."""
        if not date_str or not date_str.strip():
            return ''
        
        try:
            datetime.strptime(date_str.strip(), '%Y-%m-%d')
            return date_str.strip()
        except ValueError:
            self.logger.debug(f"Invalid date format: {date_str}")
            return ''