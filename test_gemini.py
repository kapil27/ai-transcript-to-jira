#!/usr/bin/env python3
"""
Test script for Gemini API integration
"""
import os
from transcript_parser import TranscriptParser

def test_gemini_connection():
    """Test basic Gemini API connection"""
    print("Testing Gemini API connection...")
    
    # Check if API key is set
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("\nTo set your API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        print("\nGet your API key from: https://aistudio.google.com/app/apikey")
        return False
    
    try:
        parser = TranscriptParser()
        if parser.test_connection():
            print("✅ Gemini API connection successful!")
            return True
        else:
            print("❌ Gemini API connection failed")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Gemini API: {e}")
        return False

def test_transcript_parsing():
    """Test transcript parsing with sample data"""
    print("\nTesting transcript parsing...")
    
    # Sample meeting transcript
    sample_transcript = """
Meeting: Sprint Planning - August 23, 2024
Attendees: John (PM), Sarah (Dev), Mike (QA)

John: Let's go through our sprint backlog. First item is user authentication.
Sarah: I can take the user authentication API. I'll implement JWT tokens and password validation.
John: Great, when can you have that done?
Sarah: Should be ready by end of next week, so August 30th.

Mike: I noticed a bug in the login form - the button is misaligned on mobile devices.
Sarah: Oh yeah, I saw that too. Mike, can you create a ticket for that?
Mike: Sure, I'll fix the mobile styling issue this sprint.

John: We also need to update our API documentation. The endpoints have changed.
Sarah: I can handle the documentation update after I finish the auth implementation.

John: One more thing - we should research database optimization strategies for better performance.
Mike: I can look into that. Might take a couple weeks to research properly.

John: Perfect. Let me summarize - Sarah has auth API and docs, Mike has the mobile bug fix and database research.
"""
    
    try:
        parser = TranscriptParser()
        tasks = parser.parse_transcript(sample_transcript)
        
        print(f"✅ Successfully extracted {len(tasks)} tasks:")
        print("-" * 50)
        
        for i, task in enumerate(tasks, 1):
            print(f"Task {i}:")
            print(f"  Summary: {task['summary']}")
            print(f"  Type: {task['issue_type']}")
            print(f"  Reporter: {task['reporter']}")
            print(f"  Due Date: {task['due_date'] or 'Not specified'}")
            print(f"  Description: {task['description'][:100]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error parsing transcript: {e}")
        return False

def test_csv_integration():
    """Test the full pipeline: transcript -> tasks -> CSV"""
    print("Testing full pipeline integration...")
    
    try:
        from jira_csv_generator import JiraCSVGenerator
        
        # Sample transcript
        transcript = """
Team standup meeting:
Alice: I'll implement the search feature this week.
Bob: I need to fix the performance issue in the dashboard. It's loading too slowly.
Carol: Can someone update the user guide? The new features aren't documented.
Alice: I can handle the documentation after I finish search.
"""
        
        # Parse transcript
        parser = TranscriptParser()
        tasks = parser.parse_transcript(transcript)
        
        if not tasks:
            print("❌ No tasks extracted from transcript")
            return False
        
        # Generate CSV
        csv_generator = JiraCSVGenerator()
        csv_content = csv_generator.generate_csv(tasks)
        
        # Save test output
        with open('test_ai_output.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        print(f"✅ Full pipeline test successful!")
        print(f"   - Extracted {len(tasks)} tasks from transcript")
        print(f"   - Generated CSV with {len(csv_content.splitlines())} lines")
        print(f"   - Saved to 'test_ai_output.csv'")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration error: {e}")
        return False

if __name__ == "__main__":
    print("Gemini API Integration Test")
    print("=" * 40)
    
    # Test 1: API Connection
    connection_ok = test_gemini_connection()
    
    if connection_ok:
        # Test 2: Transcript Parsing
        parsing_ok = test_transcript_parsing()
        
        if parsing_ok:
            # Test 3: Full Pipeline
            pipeline_ok = test_csv_integration()
            
            if pipeline_ok:
                print("\n" + "=" * 40)
                print("🎉 All tests passed! Gemini integration is working.")
                print("\nNext steps:")
                print("1. Update the web app to include file upload")
                print("2. Integrate transcript parsing into the Flask app")
            else:
                print("\n❌ Pipeline integration failed")
        else:
            print("\n❌ Transcript parsing failed")
    else:
        print("\n❌ Cannot proceed without API connection")