"""Unit tests for CSV generation service."""

import pytest
import csv
import io
from datetime import datetime

from src.services.csv_service import CSVGenerationService
from src.exceptions import CSVGenerationError


class TestCSVGenerationService:
    """Test cases for CSV generation service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.csv_service = CSVGenerationService()
        self.valid_tasks = [
            {
                'summary': 'Implement user authentication',
                'description': 'Add login and registration functionality',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': '2024-12-31'
            },
            {
                'summary': 'Fix login bug',
                'description': 'Login button is not working',
                'issue_type': 'Bug',
                'reporter': 'bug@example.com',
                'due_date': ''
            }
        ]
    
    def test_generate_csv_with_valid_tasks(self):
        """Test CSV generation with valid tasks."""
        csv_content = self.csv_service.generate_csv(self.valid_tasks)
        
        # Parse the CSV to verify structure
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Check header
        assert rows[0] == ['Summary', 'Description', 'Issue Type', 'Reporter', 'Due Date']
        
        # Check first task
        assert rows[1][0] == 'Implement user authentication'
        assert rows[1][1] == 'Add login and registration functionality'
        assert rows[1][2] == 'Task'
        assert rows[1][3] == 'test@example.com'
        assert rows[1][4] == '2024-12-31'
        
        # Check second task
        assert rows[2][0] == 'Fix login bug'
        assert rows[2][2] == 'Bug'
        assert rows[2][4] == ''  # Empty due date
    
    def test_generate_csv_with_empty_tasks(self):
        """Test CSV generation with empty task list."""
        csv_content = self.csv_service.generate_csv([])
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Should only have header row
        assert len(rows) == 1
        assert rows[0] == ['Summary', 'Description', 'Issue Type', 'Reporter', 'Due Date']
    
    def test_generate_csv_with_invalid_task(self):
        """Test CSV generation with invalid task data."""
        invalid_tasks = [
            {
                'summary': '',  # Empty summary should be invalid
                'description': 'Test description',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            }
        ]
        
        with pytest.raises(CSVGenerationError, match="Failed to generate CSV"):
            self.csv_service.generate_csv(invalid_tasks)
    
    def test_generate_csv_with_mixed_valid_invalid_tasks(self):
        """Test CSV generation with mix of valid and invalid tasks."""
        mixed_tasks = [
            {
                'summary': 'Valid task',
                'description': 'This is valid',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            },
            {
                'summary': '',  # Invalid - empty summary
                'description': 'Invalid task',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            }
        ]
        
        csv_content = self.csv_service.generate_csv(mixed_tasks)
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Should have header + 1 valid task
        assert len(rows) == 2
        assert rows[1][0] == 'Valid task'
    
    def test_validate_csv_data_with_valid_tasks(self):
        """Test CSV data validation with valid tasks."""
        result = self.csv_service.validate_csv_data(self.valid_tasks)
        
        assert result['is_valid'] is True
        assert result['valid_tasks_count'] == 2
        assert result['invalid_tasks_count'] == 0
        assert len(result['errors']) == 0
    
    def test_validate_csv_data_with_empty_tasks(self):
        """Test CSV data validation with empty task list."""
        result = self.csv_service.validate_csv_data([])
        
        assert result['is_valid'] is False
        assert result['valid_tasks_count'] == 0
        assert result['invalid_tasks_count'] == 0
        assert "No tasks provided" in result['errors']
    
    def test_validate_csv_data_with_invalid_tasks(self):
        """Test CSV data validation with invalid tasks."""
        invalid_tasks = [
            {
                'summary': '',  # Empty summary
                'description': 'Test',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            }
        ]
        
        result = self.csv_service.validate_csv_data(invalid_tasks)
        
        assert result['is_valid'] is False
        assert result['valid_tasks_count'] == 0
        assert result['invalid_tasks_count'] == 1
        assert "No valid tasks found" in result['errors']
        assert len(result['warnings']) > 0
    
    def test_get_csv_filename_format(self):
        """Test CSV filename generation format."""
        filename = self.csv_service.get_csv_filename()
        
        # Should match pattern: jira_tasks_YYYYMMDD_HHMMSS.csv
        assert filename.startswith("jira_tasks_")
        assert filename.endswith(".csv")
        
        # Extract timestamp part
        timestamp_part = filename.replace("jira_tasks_", "").replace(".csv", "")
        
        # Should be able to parse as datetime
        datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
    
    def test_get_csv_filename_with_custom_prefix(self):
        """Test CSV filename generation with custom prefix."""
        filename = self.csv_service.get_csv_filename("custom_tasks")
        
        assert filename.startswith("custom_tasks_")
        assert filename.endswith(".csv")
    
    def test_csv_headers_property(self):
        """Test CSV headers are correctly defined."""
        expected_headers = ['Summary', 'Description', 'Issue Type', 'Reporter', 'Due Date']
        assert self.csv_service.csv_headers == expected_headers
    
    def test_generate_empty_csv(self):
        """Test generation of empty CSV with headers only."""
        csv_content = self.csv_service._generate_empty_csv()
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0] == self.csv_service.csv_headers
    
    def test_csv_quoting_behavior(self):
        """Test that CSV content is properly quoted."""
        tasks_with_special_chars = [
            {
                'summary': 'Task with "quotes" and, commas',
                'description': 'Description with\nnewlines and "quotes"',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            }
        ]
        
        csv_content = self.csv_service.generate_csv(tasks_with_special_chars)
        
        # Should be able to parse back correctly
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert rows[1][0] == 'Task with "quotes" and, commas'
        assert 'newlines' in rows[1][1]