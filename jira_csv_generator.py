import csv
import io
from datetime import datetime
from typing import List, Dict, Any

class JiraCSVGenerator:
    """
    Generates JIRA-compatible CSV files from structured task data.
    Follows JIRA CSV import specifications from the requirements document.
    """
    
    def __init__(self):
        # Standard JIRA fields mapping - minimal version
        self.field_mapping = {
            'summary': 'Summary',
            'description': 'Description',
            'issue_type': 'Issue Type',
            'reporter': 'Reporter',
            'due_date': 'Due Date'
        }
    
    def generate_csv(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Generate JIRA-compatible CSV content from task data.
        
        Args:
            tasks: List of task dictionaries with JIRA field data
            
        Returns:
            CSV content as string
        """
        if not tasks:
            raise ValueError("No tasks provided")
        
        # Determine which fields are present in the data
        all_fields = set()
        for task in tasks:
            all_fields.update(task.keys())
        
        # Create header row with proper JIRA field names - minimal version
        headers = []
        field_order = ['summary', 'description', 'issue_type', 'reporter', 'due_date']
        
        # Add standard fields in order
        for field in field_order:
            if field in all_fields:
                headers.append(self.field_mapping[field])
        
        # Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(headers)
        
        # Write data rows
        for task in tasks:
            row = []
            
            # Add standard fields
            for field in field_order:
                if field in all_fields:
                    value = task.get(field, '')
                    if field == 'due_date' and value:
                        # Ensure consistent date format
                        if isinstance(value, str):
                            value = self._format_date(value)
                    elif field == 'description' and value:
                        # Handle newlines and user mentions in description
                        value = self._format_description(value)
                    row.append(str(value) if value else '')
            
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to JIRA-compatible format (YYYY-MM-DD)"""
        try:
            # Try to parse various date formats and convert to YYYY-MM-DD
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            # If no format matches, return as-is
            return date_str
        except:
            return date_str
    
    def _format_description(self, description: str) -> str:
        """
        Format description field for JIRA import.
        Handles newlines and user mentions.
        """
        # Replace literal \n with actual newlines
        description = description.replace('\\n', '\n')
        
        # Note: User mentions should be in format [~email:user@example.com]
        # This is handled by the caller when creating the task data
        
        return description
    
    def validate_task_data(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Validate task data for JIRA compatibility.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for i, task in enumerate(tasks):
            # Summary is mandatory
            if not task.get('summary'):
                errors.append(f"Task {i+1}: Summary is required")
            
            # Validate email format for reporter
            reporter = task.get('reporter')
            if reporter and '@' not in reporter:
                errors.append(f"Task {i+1}: reporter should be a valid email address")
            
            # Validate date format for due_date
            due_date = task.get('due_date')
            if due_date:
                try:
                    self._format_date(due_date)
                except:
                    errors.append(f"Task {i+1}: Invalid date format for due_date")
        
        return errors