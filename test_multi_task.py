#!/usr/bin/env python3
"""
Test to specifically check multi-task extraction
"""
from ollama_parser import OllamaTranscriptParser

def test_with_clear_multiple_tasks():
    """Test with a transcript that clearly has multiple tasks"""
    
    # Very clear transcript with obvious multiple tasks
    transcript = """
Sprint Planning Meeting - Aug 23, 2024

John (PM): Let's assign tasks for this sprint.

1. Sarah, can you implement the user login API?
Sarah: Yes, I'll do the authentication API with JWT tokens.

2. Mike, there's a bug with the mobile login button.
Mike: I see it, the button is misaligned. I'll fix that CSS issue.

3. We need to update the documentation for the new API endpoints.
John: Sarah, can you handle the docs after the API?
Sarah: Sure, I'll update the API documentation.

4. Performance testing is needed for the dashboard.
Mike: I can run performance tests and optimize slow queries.

Action items:
- Sarah: Build authentication API 
- Mike: Fix mobile login CSS bug
- Sarah: Update API documentation  
- Mike: Performance testing and optimization
"""

    try:
        parser = OllamaTranscriptParser()
        print("Processing transcript with multiple clear tasks...")
        tasks = parser.parse_transcript(transcript)
        
        print(f"\n✅ Extracted {len(tasks)} tasks:")
        print("-" * 60)
        
        for i, task in enumerate(tasks, 1):
            print(f"Task {i}:")
            print(f"  Summary: {task['summary']}")
            print(f"  Type: {task['issue_type']}")
            print(f"  Reporter: {task['reporter']}")
            print(f"  Description: {task['description'][:80]}...")
            print()
        
        if len(tasks) >= 3:
            print("🎉 SUCCESS: Found multiple tasks!")
            return True
        else:
            print(f"⚠️  WARNING: Only found {len(tasks)} task(s), expected at least 3")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Multi-Task Extraction")
    print("=" * 40)
    test_with_clear_multiple_tasks()