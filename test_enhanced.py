#!/usr/bin/env python3
"""
Test script for enhanced Q&A + Task workflow
"""
from ollama_parser import OllamaTranscriptParser

def test_enhanced_workflow():
    """Test the enhanced workflow that combines Q&A context with task extraction"""
    
    # Rich transcript with questions, answers, and implied tasks
    transcript = """
Product Planning Meeting - August 23, 2024
Attendees: John (PM), Sarah (Dev), Mike (QA), Lisa (Designer)

John: Let's discuss the upcoming authentication feature. Sarah, what's your timeline?
Sarah: I can complete the JWT implementation by Friday, August 30th.

Mike: How should we handle password complexity requirements?
Sarah: Good question. Let's use standard complexity - 8 chars minimum, mixed case, numbers.

Lisa: What about the login page design? Do we have wireframes?
John: We need those. Lisa, can you create mockups by Wednesday?
Lisa: Yes, I'll have login and signup mockups ready by Wednesday morning.

Mike: Are we implementing 2FA in this release?
John: That's a great question. What do you think Sarah?
Sarah: I think we should focus on basic auth first, then 2FA in the next sprint.

Sarah: I'll also need to update the API documentation after implementation.

Mike: How do we test the authentication flow end-to-end?
[No immediate answer - discussion moves to other topics]

John: One more thing - what database should we use for user sessions?
Sarah: Redis would be good for session storage, it's fast and handles expiration well.

Lisa: Should the login form have a "Remember Me" checkbox?
[Question raised but not answered during meeting]

John: Let's make sure we have proper error handling for failed logins.
Sarah: Absolutely, I'll add rate limiting and clear error messages.
"""

    try:
        parser = OllamaTranscriptParser()
        print("Testing enhanced workflow...")
        result = parser.parse_transcript_with_qa_context(transcript)
        
        print(f"\n🚀 Enhanced Processing Results:")
        print("=" * 80)
        
        print(f"\n📋 TASKS EXTRACTED ({result['tasks_count']}):")
        print("-" * 40)
        for i, task in enumerate(result['tasks'], 1):
            print(f"\nTask {i}:")
            print(f"  Summary: {task['summary']}")
            print(f"  Type: {task['issue_type']}")
            print(f"  Reporter: {task['reporter']}")
            if task['due_date']:
                print(f"  Due: {task['due_date']}")
            print(f"  Description: {task['description'][:100]}...")
        
        print(f"\n❓ QUESTIONS EXTRACTED ({result['qa_count']}):")
        print("-" * 40)
        for i, qa in enumerate(result['qa_items'], 1):
            print(f"\nQ{i}: {qa['question']}")
            if qa.get('context'):
                print(f"  Context: {qa['context']}")
            if qa['answer']:
                print(f"  Answer: {qa['answer']}")
                print(f"  Status: ✅ {qa['status']}")
            else:
                print(f"  Status: ⏳ {qa['status']} - Needs follow-up")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total tasks: {result['tasks_count']}")
        print(f"   Total questions: {result['qa_count']}")
        answered = len([qa for qa in result['qa_items'] if qa['status'] == 'answered'])
        unanswered = len([qa for qa in result['qa_items'] if qa['status'] == 'unanswered'])
        print(f"   Answered questions: {answered}")
        print(f"   Unanswered questions: {unanswered}")
        
        if result['tasks_count'] >= 3 and result['qa_count'] >= 3:
            print("\n🎉 SUCCESS: Enhanced workflow working well!")
            return True
        else:
            print(f"\n⚠️  WARNING: Expected more tasks/questions")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Enhanced Q&A + Task Workflow")
    print("=" * 40)
    test_enhanced_workflow()