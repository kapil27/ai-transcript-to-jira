import os
import google.generativeai as genai
import json
from typing import List, Dict, Any, Optional

class TranscriptParser:
    """
    Uses Google Gemini API to parse meeting transcripts and extract actionable tasks.
    Follows the hybrid approach from the requirements document.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the transcript parser with Gemini API.
        
        Args:
            api_key: Google Gemini API key. If None, tries to get from environment.
        """
        if api_key:
            genai.configure(api_key=api_key)
        else:
            # Try to get from environment variable
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set or api_key not provided")
            genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash for good balance of speed and accuracy
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
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
        
        # Create a comprehensive prompt for task extraction
        prompt = self._create_extraction_prompt(transcript_text)
        
        try:
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("No response received from Gemini API")
            
            # Parse the JSON response
            tasks_data = self._parse_gemini_response(response.text)
            
            # Validate and clean the extracted tasks
            validated_tasks = self._validate_tasks(tasks_data)
            
            return validated_tasks
            
        except Exception as e:
            raise Exception(f"Error parsing transcript with Gemini: {str(e)}")
    
    def _create_extraction_prompt(self, transcript: str) -> str:
        """Create a detailed prompt for Gemini to extract tasks from transcript"""
        
        prompt = f"""
You are an expert at analyzing meeting transcripts and extracting actionable tasks for project management. 

Please analyze the following meeting transcript and extract all actionable tasks, action items, and decisions that need to be tracked in JIRA.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Look for explicit action items (e.g., "John will implement the API", "Sarah needs to fix the bug")
2. Identify implicit tasks mentioned in discussions (e.g., "We need to update the documentation")
3. Extract decisions that require follow-up work
4. Ignore general discussion points that don't lead to specific actions

For each task you identify, provide:
- summary: A clear, concise title for the task (required)
- description: Detailed description with context from the meeting
- issue_type: Choose from "Story", "Task", "Bug", or "Epic" 
- reporter: Email of person who mentioned/assigned the task (use "meeting@example.com" if unclear)
- due_date: If mentioned in transcript, format as YYYY-MM-DD, otherwise leave empty

IMPORTANT: 
- Only extract actual actionable items, not general discussion
- Be conservative - better to miss a task than create a fake one
- Summaries should be clear and specific
- Use context from the meeting to make descriptions meaningful

Respond with ONLY a valid JSON array in this exact format:
[
  {{
    "summary": "Task title here",
    "description": "Detailed description with meeting context",
    "issue_type": "Story|Task|Bug|Epic",
    "reporter": "email@example.com",
    "due_date": "YYYY-MM-DD or empty string"
  }}
]

If no actionable tasks are found, return an empty array: []
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse and validate the JSON response from Gemini"""
        try:
            # Clean the response text (remove any markdown formatting)
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            tasks_data = json.loads(clean_text)
            
            if not isinstance(tasks_data, list):
                raise ValueError("Response must be a JSON array")
            
            return tasks_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
    
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
    
    def test_connection(self) -> bool:
        """Test if the Gemini API connection is working"""
        try:
            test_response = self.model.generate_content("Hello, just testing the connection. Respond with 'OK'.")
            return bool(test_response.text and 'OK' in test_response.text.upper())
        except Exception as e:
            print(f"API connection test failed: {e}")
            return False