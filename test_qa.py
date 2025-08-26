#!/usr/bin/env python3
"""
Test script for Q&A extraction functionality
"""
from ollama_parser import OllamaTranscriptParser

def test_qa_extraction():
    """Test Q&A extraction with a sample transcript containing questions"""
    
    # Sample transcript with clear questions and answers
    transcript = """
Sprint Planning Meeting - Aug 23, 2024
Attendees: John (PM), Sarah (Dev), Mike (QA), Lisa (Designer)

John: Let's start the sprint planning. Sarah, what's the timeline for the authentication API?
Sarah: I can complete the JWT implementation by Friday, August 30th.

Mike: How should we handle error logging in the new API?
John: Good question. Let's use our standard logging framework.
Sarah: I'll make sure to include proper error handling.

Lisa: What about the UI design for the login page?
John: We'll need to finalize that. Can you have mockups ready by Wednesday?
Lisa: Yes, I can deliver the mockups by Wednesday morning.

Mike: Are we going to implement 2FA in this sprint?
Sarah: That's a good question, but I think we should focus on basic auth first.
John: Agreed, let's save 2FA for the next sprint.

John: One more thing - what database should we use for user sessions?
Sarah: I was thinking Redis for session storage.

Mike: How do we test the authentication flow?
[No immediate answer - discussion continues on other topics]

Sarah: Oh, and what's our deployment strategy for this?
John: We'll deploy to staging first, then production after QA approval.
"""

    try:
        parser = OllamaTranscriptParser()
        print("Extracting Q&A from transcript...")
        qa_items = parser.extract_questions_and_answers(transcript)
        
        print(f"\n✅ Extracted {len(qa_items)} Q&A items:")
        print("=" * 80)
        
        for i, qa in enumerate(qa_items, 1):
            print(f"\nQ{i}: {qa['question']}")
            print(f"Asked by: {qa['asked_by']}")
            
            if qa['answer']:
                print(f"Answer: {qa['answer']}")
                print(f"Answered by: {qa['answered_by']}")
                print(f"Status: ✅ {qa['status']}")
            else:
                print("Answer: ❓ Will be provided later")
                print(f"Status: ⏳ {qa['status']}")
            
            print("-" * 40)
        
        # Count answered vs unanswered
        answered = len([qa for qa in qa_items if qa['status'] == 'answered'])
        unanswered = len([qa for qa in qa_items if qa['status'] == 'unanswered'])
        
        print(f"\n📊 Summary:")
        print(f"   Total questions: {len(qa_items)}")
        print(f"   Answered: {answered}")
        print(f"   Unanswered: {unanswered}")
        
        if len(qa_items) >= 3:
            print("\n🎉 SUCCESS: Found multiple Q&A items!")
            return True
        else:
            print(f"\n⚠️  WARNING: Only found {len(qa_items)} Q&A item(s)")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Q&A Extraction")
    print("=" * 40)
    test_qa_extraction()