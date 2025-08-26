#!/usr/bin/env python3
"""
Quick test for the simplified enhanced workflow
"""
from ollama_parser import OllamaTranscriptParser

def test_simple_enhanced():
    """Test the simplified enhanced workflow"""
    
    transcript = """
Meeting: Sprint Planning
John: Sarah, can you implement the user authentication API?
Sarah: Sure, I can have that done by Friday.
Mike: I noticed a bug in the login form - the button is misaligned.
Lisa: What about the UI mockups? Do we have them ready?
John: Good question, we need those. Lisa, can you create them?
Mike: How should we test the authentication flow?
"""

    try:
        parser = OllamaTranscriptParser()
        print("Testing simplified enhanced workflow...")
        result = parser.parse_transcript_with_qa_context(transcript)
        
        print(f"\n✅ Results:")
        print(f"Tasks: {result['tasks_count']}")
        print(f"Q&A: {result['qa_count']}")
        
        if result['tasks']:
            print("\nTasks found:")
            for i, task in enumerate(result['tasks'], 1):
                print(f"  {i}. {task['summary']}")
        
        if result['qa_items']:
            print("\nQuestions found:")
            for i, qa in enumerate(result['qa_items'], 1):
                print(f"  {i}. {qa['question']}")
                if qa.get('answer'):
                    print(f"     Answer: {qa['answer'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_simple_enhanced()