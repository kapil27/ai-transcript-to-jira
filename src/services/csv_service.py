"""Service for generating JIRA-compatible CSV files."""

import csv
import io
from typing import List, Dict, Any
from datetime import datetime

from ..models.task import JiraTask
from ..exceptions import CSVGenerationError, ValidationError
from ..utils import LoggerMixin


class CSVGenerationService(LoggerMixin):
    """Service for generating JIRA-compatible CSV files from task data."""
    
    def __init__(self):
        """Initialize CSV generation service."""
        self.csv_headers = ['Summary', 'Description', 'Issue Type', 'Reporter', 'Due Date']
    
    def generate_csv(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Generate JIRA-compatible CSV content from task data.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            CSV content as string
            
        Raises:
            CSVGenerationError: If CSV generation fails
            ValidationError: If task data is invalid
        """
        if not tasks:
            self.logger.warning("No tasks provided for CSV generation")
            return self._generate_empty_csv()
        
        try:
            self.logger.info(f"Generating CSV for {len(tasks)} tasks")
            
            # Validate and convert tasks to JiraTask objects
            validated_tasks = self._validate_and_convert_tasks(tasks)
            
            # Generate CSV content
            csv_content = self._create_csv_content(validated_tasks)
            
            self.logger.info("CSV generation completed successfully")
            return csv_content
            
        except Exception as e:
            self.logger.error(f"CSV generation failed: {e}")
            raise CSVGenerationError(f"Failed to generate CSV: {str(e)}")
    
    def _validate_and_convert_tasks(self, tasks: List[Dict[str, Any]]) -> List[JiraTask]:
        """Validate and convert task dictionaries to JiraTask objects."""
        validated_tasks = []
        
        for i, task_data in enumerate(tasks):
            try:
                # Convert to JiraTask (this will validate the data)
                jira_task = JiraTask(
                    summary=task_data.get('summary', ''),
                    description=task_data.get('description', ''),
                    issue_type=task_data.get('issue_type', 'Task'),
                    reporter=task_data.get('reporter', 'meeting@example.com'),
                    due_date=task_data.get('due_date', '')
                )
                validated_tasks.append(jira_task)
                
            except ValueError as e:
                self.logger.warning(f"Skipping invalid task {i+1}: {e}")
                continue
        
        if not validated_tasks:
            raise ValidationError("No valid tasks found after validation")
        
        return validated_tasks
    
    def _create_csv_content(self, tasks: List[JiraTask]) -> str:
        """Create CSV content from validated JiraTask objects."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(self.csv_headers)
        
        # Write task rows
        for task in tasks:
            row = [
                task.summary,
                task.description,
                task.issue_type,
                task.reporter,
                task.due_date or ''
            ]
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    def _generate_empty_csv(self) -> str:
        """Generate CSV with headers only."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(self.csv_headers)
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    def get_csv_filename(self, prefix: str = "jira_tasks") -> str:
        """
        Generate a unique filename for the CSV file.
        
        Args:
            prefix: Filename prefix
            
        Returns:
            Filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.csv"
    
    def validate_csv_data(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate task data before CSV generation.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'valid_tasks_count': 0,
            'invalid_tasks_count': 0
        }
        
        if not tasks:
            validation_results['is_valid'] = False
            validation_results['errors'].append("No tasks provided")
            return validation_results
        
        for i, task_data in enumerate(tasks):
            try:
                # Attempt to create JiraTask to validate
                JiraTask(
                    summary=task_data.get('summary', ''),
                    description=task_data.get('description', ''),
                    issue_type=task_data.get('issue_type', 'Task'),
                    reporter=task_data.get('reporter', 'meeting@example.com'),
                    due_date=task_data.get('due_date', '')
                )
                validation_results['valid_tasks_count'] += 1
                
            except ValueError as e:
                validation_results['invalid_tasks_count'] += 1
                validation_results['warnings'].append(f"Task {i+1}: {str(e)}")
        
        if validation_results['valid_tasks_count'] == 0:
            validation_results['is_valid'] = False
            validation_results['errors'].append("No valid tasks found")
        
        return validation_results