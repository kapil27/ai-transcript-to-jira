import requests
import json
from typing import List, Dict, Any

class OllamaTranscriptParser:
    """
    Uses Ollama (local AI) to parse meeting transcripts and extract actionable tasks.
    Completely private and runs locally.
    """
    
    def __init__(self, model_name: str = "llama3.1:latest", base_url: str = "http://localhost:11434"):
        """
        Initialize the transcript parser with Ollama.
        
        Args:
            model_name: Name of the Ollama model to use
            base_url: Ollama server URL
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def parse_transcript(self, transcript_text: str) -> List[Dict[str, Any]]:
        """
        Parse meeting transcript to extract actionable tasks.
        
        Args:
            transcript_text: Raw meeting transcript text
            
        Returns:
            List of task dictionaries compatible with our CSV generator
        """
        if not transcript_text.strip():
            raise ValueError("Transcript text cannot be empty")
        
        try:
            # First, try the multi-task extraction approach
            prompt = self._create_extraction_prompt(transcript_text)
            response_text = self._call_ollama(prompt)
            
            if not response_text:
                raise ValueError("No response received from Ollama")
            
            tasks_data = self._parse_ollama_response(response_text)
            validated_tasks = self._validate_tasks(tasks_data)
            
            # If we only got one task, try the iterative approach
            if len(validated_tasks) <= 1:
                print("Trying iterative extraction to find more tasks...")
                iterative_tasks = self._extract_tasks_iteratively(transcript_text)
                if len(iterative_tasks) > len(validated_tasks):
                    validated_tasks = iterative_tasks
            
            return validated_tasks
            
        except Exception as e:
            raise Exception(f"Error parsing transcript with Ollama: {str(e)}")
    
    def _extract_tasks_iteratively(self, transcript: str) -> List[Dict[str, Any]]:
        """Try to extract tasks by asking for a numbered list first"""
        
        # First ask for a simple list of tasks
        list_prompt = f"""Read this meeting transcript and list all actionable tasks/assignments:

{transcript}

List each task on a new line starting with a number:
1. Task description here
2. Another task description
3. etc.

Only list actual work items that need to be done by someone."""

        try:
            list_response = self._call_ollama(list_prompt, use_json_format=False)
            if not list_response:
                return []
            
            # Parse the numbered list
            lines = list_response.strip().split('\n')
            task_descriptions = []
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or 
                           line.startswith('- ') or line.startswith('* ')):
                    # Clean up the task description
                    task_desc = line.split('.', 1)[-1].strip() if '.' in line else line[2:].strip()
                    if task_desc:
                        task_descriptions.append(task_desc)
            
            # Now convert each description to a proper task object
            all_tasks = []
            for desc in task_descriptions[:6]:  # Limit to 6 tasks max
                task_prompt = f"""Convert this task description into a JSON object:

Task: {desc}

Return ONLY a JSON object in this format:
{{
    "summary": "Brief title for the task",
    "description": "Detailed description",
    "issue_type": "Task",
    "reporter": "meeting@example.com",
    "due_date": ""
}}"""

                try:
                    task_response = self._call_ollama(task_prompt)
                    if task_response:
                        task_data = self._parse_single_task(task_response)
                        if task_data:
                            all_tasks.append(task_data)
                except:
                    continue
            
            return self._validate_tasks(all_tasks)
            
        except Exception:
            return []
    
    def _parse_single_task(self, response_text: str) -> Dict[str, Any]:
        """Parse a single task JSON object"""
        try:
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            task_data = json.loads(clean_text)
            return task_data if isinstance(task_data, dict) else None
            
        except:
            return None
    
    def _call_ollama(self, prompt: str, use_json_format: bool = True) -> str:
        """Make API call to Ollama"""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Lower temperature for more consistent output
                "top_p": 0.9
            }
        }
        
        # Only use JSON format for structured outputs
        if use_json_format:
            payload["format"] = "json"
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API call failed: {e}")
    
    def _create_extraction_prompt(self, transcript: str) -> str:
        """Create a detailed prompt for Ollama to extract tasks from transcript"""
        
        prompt = f"""Extract actionable tasks from this meeting transcript. Return results as a JSON array.

TRANSCRIPT:
{transcript}

Find ALL tasks, action items, and assignments mentioned. Each task should be a separate JSON object.

Return ONLY a JSON array in this exact format:
[
  {{
    "summary": "Task title",
    "description": "Task description with context",
    "issue_type": "Task",
    "reporter": "meeting@example.com",
    "due_date": ""
  }}
]

Look for:
- Explicit assignments ("John will do X")
- Work items mentioned ("We need to update Y")
- Bug reports ("There's an issue with Z")
- Follow-up tasks from decisions

Return multiple objects in the array - one for each task found. If no tasks, return []."""
        
        return prompt
    
    def _parse_ollama_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse and validate the JSON response from Ollama"""
        try:
            # Clean the response text
            clean_text = response_text.strip()
            
            # Sometimes the model wraps JSON in markdown
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            
            # Parse JSON
            tasks_data = json.loads(clean_text)
            
            # Handle case where model returns single object instead of array (but warn)
            if isinstance(tasks_data, dict):
                print("Warning: Model returned single object instead of array. Converting to array.")
                tasks_data = [tasks_data]
            elif not isinstance(tasks_data, list):
                raise ValueError(f"Response must be a JSON array, got: {type(tasks_data)}")
            
            return tasks_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from Ollama: {e}")
    
    def _validate_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean the extracted task data"""
        validated_tasks = []
        
        for i, task in enumerate(tasks_data):
            try:
                # Ensure required fields
                if not task.get('summary', '').strip():
                    print(f"Warning: Skipping task {i+1} - missing summary")
                    continue
                
                # Clean and validate task data
                clean_task = {
                    'summary': task['summary'].strip(),
                    'description': task.get('description', '').strip(),
                    'issue_type': self._validate_issue_type(task.get('issue_type', 'Task')),
                    'reporter': self._validate_email(task.get('reporter', 'meeting@example.com')),
                    'due_date': self._validate_date(task.get('due_date', ''))
                }
                
                validated_tasks.append(clean_task)
                
            except Exception as e:
                print(f"Warning: Skipping invalid task {i+1}: {e}")
                continue
        
        return validated_tasks
    
    def _validate_issue_type(self, issue_type: str) -> str:
        """Validate and normalize issue type"""
        valid_types = ['Story', 'Task', 'Bug', 'Epic']
        if issue_type in valid_types:
            return issue_type
        return 'Task'  # Default fallback
    
    def _validate_email(self, email: str) -> str:
        """Validate and normalize email address"""
        if email and '@' in email:
            return email.strip()
        return 'meeting@example.com'  # Default fallback
    
    def _validate_date(self, date_str: str) -> str:
        """Validate date format"""
        if not date_str or not date_str.strip():
            return ''
        
        # Basic validation - should be YYYY-MM-DD format
        try:
            from datetime import datetime
            datetime.strptime(date_str.strip(), '%Y-%m-%d')
            return date_str.strip()
        except ValueError:
            return ''  # Invalid date format, return empty
    
    def extract_questions_and_answers(self, transcript_text: str) -> List[Dict[str, Any]]:
        """
        Extract questions and their answers from meeting transcript.
        
        Args:
            transcript_text: Raw meeting transcript text
            
        Returns:
            List of Q&A dictionaries with question, answer (if provided), and status
        """
        if not transcript_text.strip():
            raise ValueError("Transcript text cannot be empty")
        
        try:
            # Use iterative approach for Q&A extraction (more reliable)
            return self._extract_qa_iteratively(transcript_text)
            
        except Exception as e:
            raise Exception(f"Error extracting Q&A with Ollama: {str(e)}")
    
    def _extract_qa_iteratively(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract Q&A by first finding questions, then finding answers"""
        
        # First, find all questions in the transcript
        questions_prompt = f"""Read this meeting transcript and list all questions asked by anyone:

{transcript}

List each question on a new line starting with a number:
1. Question text here?
2. Another question?
3. etc.

Only list actual questions (ending with ?). If no questions found, respond with "No questions found"."""

        try:
            questions_response = self._call_ollama(questions_prompt, use_json_format=False)
            if not questions_response or "No questions found" in questions_response:
                return []
            
            # Parse the numbered list of questions
            lines = questions_response.strip().split('\n')
            questions = []
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or 
                           line.startswith('- ') or line.startswith('* ')):
                    # Clean up the question
                    question_text = line.split('.', 1)[-1].strip() if '.' in line else line[2:].strip()
                    if question_text and question_text.endswith('?'):
                        questions.append(question_text)
            
            # Now for each question, find if there's an answer
            all_qa = []
            for question in questions[:8]:  # Limit to 8 questions max
                qa_prompt = f"""For this specific question from the meeting transcript, extract detailed information:

TRANSCRIPT:
{transcript}

QUESTION: {question}

Extract information about this question including context around when it was asked.

Return ONLY a JSON object in this format:
{{
    "question": "{question}",
    "context": "Background context about what was being discussed when this question was asked",
    "answer": "The answer text if found, or empty string if no answer",
    "asked_by": "email@example.com",
    "answered_by": "email@example.com or empty if no answer",
    "status": "answered or unanswered"
}}

For context, include what topic/feature was being discussed when the question was asked. This helps understand what the question is about."""

                try:
                    qa_response = self._call_ollama(qa_prompt)
                    if qa_response:
                        qa_data = self._parse_single_task(qa_response)
                        if qa_data and qa_data.get('question'):
                            # Validate the Q&A item with rich context
                            validated_qa = {
                                'question': qa_data.get('question', '').strip(),
                                'context': qa_data.get('context', '').strip(),
                                'answer': qa_data.get('answer', '').strip(),
                                'asked_by': self._validate_email(qa_data.get('asked_by', 'meeting@example.com')),
                                'answered_by': self._validate_email(qa_data.get('answered_by', '')),
                                'status': 'answered' if qa_data.get('answer', '').strip() else 'unanswered'
                            }
                            
                            all_qa.append(validated_qa)
                except:
                    continue
            
            return all_qa
            
        except Exception:
            return []
    
    def _validate_qa_data(self, qa_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean Q&A data"""
        validated_qa = []
        
        for i, qa in enumerate(qa_data):
            try:
                # Ensure required fields
                if not qa.get('question', '').strip():
                    print(f"Warning: Skipping Q&A {i+1} - missing question")
                    continue
                
                # Clean and validate Q&A data
                clean_qa = {
                    'question': qa['question'].strip(),
                    'answer': qa.get('answer', '').strip(),
                    'asked_by': self._validate_email(qa.get('asked_by', 'meeting@example.com')),
                    'answered_by': self._validate_email(qa.get('answered_by', '')),
                    'status': 'answered' if qa.get('answer', '').strip() else 'unanswered'
                }
                
                validated_qa.append(clean_qa)
                
            except Exception as e:
                print(f"Warning: Skipping invalid Q&A {i+1}: {e}")
                continue
        
        return validated_qa

    def parse_transcript_with_qa_context(self, transcript_text: str) -> Dict[str, Any]:
        """
        Parse transcript extracting both tasks and questions, using Q&A context to enhance task creation.
        
        Args:
            transcript_text: Raw meeting transcript text
            
        Returns:
            Dictionary containing both tasks and qa_items with enhanced context
        """
        if not transcript_text.strip():
            raise ValueError("Transcript text cannot be empty")
        
        try:
            # Extract both tasks and Q&A in parallel approach
            # First get tasks using the regular method
            enhanced_tasks = self.parse_transcript(transcript_text)
            
            # Then get Q&A items  
            qa_items = self.extract_questions_and_answers(transcript_text)
            
            return {
                'tasks': enhanced_tasks,
                'qa_items': qa_items,
                'tasks_count': len(enhanced_tasks),
                'qa_count': len(qa_items)
            }
            
        except Exception as e:
            raise Exception(f"Error parsing transcript with Q&A context: {str(e)}")

    def test_connection(self) -> bool:
        """Test if the Ollama API connection is working"""
        try:
            test_response = self._call_ollama("Hello, just testing the connection. Respond with 'OK'.")
            return bool(test_response and 'OK' in test_response.upper())
        except Exception as e:
            print(f"Ollama connection test failed: {e}")
            return False