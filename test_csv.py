#!/usr/bin/env python3
"""
Test script for JIRA CSV Generator
"""
from jira_csv_generator import JiraCSVGenerator

def test_csv_generation():
    """Test the CSV generation with sample data"""
    
    # Sample task data - minimal version
    test_tasks = [
        {
            'summary': 'Implement user authentication endpoint',
            'description': 'As a user, I want to log in securely.\n\nThis should include password validation and JWT token generation.',
            'issue_type': 'Story',
            'reporter': 'scrummaster@example.com',
            'due_date': '2024-12-31'
        },
        {
            'summary': 'Fix login button styling issue',
            'description': 'The login button appears misaligned on mobile devices',
            'issue_type': 'Bug',
            'reporter': 'qa@example.com',
            'due_date': '2024-11-15'
        },
        {
            'summary': 'Research database optimization strategies',
            'description': 'Investigate ways to improve database query performance',
            'issue_type': 'Task',
            'reporter': 'tech-lead@example.com'
        }
    ]
    
    # Create CSV generator
    generator = JiraCSVGenerator()
    
    # Validate data
    print("Validating task data...")
    errors = generator.validate_task_data(test_tasks)
    if errors:
        print("Validation errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✓ All task data is valid!")
    
    # Generate CSV
    print("\nGenerating CSV...")
    try:
        csv_content = generator.generate_csv(test_tasks)
        print("✓ CSV generated successfully!")
        
        # Save to file for inspection
        with open('test_output.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print("✓ CSV saved to 'test_output.csv'")
        
        # Display first few lines
        print("\nCSV Content Preview:")
        print("-" * 50)
        lines = csv_content.split('\n')
        for i, line in enumerate(lines[:5]):  # Show first 5 lines
            print(f"{i+1}: {line}")
        if len(lines) > 5:
            print(f"... ({len(lines) - 5} more lines)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error generating CSV: {e}")
        return False

if __name__ == "__main__":
    print("Testing JIRA CSV Generator")
    print("=" * 40)
    
    success = test_csv_generation()
    
    print("\n" + "=" * 40)
    if success:
        print("✓ All tests passed! The CSV generator is working correctly.")
        print("\nNext steps:")
        print("1. Run the Flask app: python app.py")
        print("2. Open http://localhost:5000 in your browser")
        print("3. Test the web interface")
    else:
        print("✗ Tests failed. Please check the errors above.")