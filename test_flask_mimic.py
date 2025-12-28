#!/usr/bin/env python3
"""Mimic Flask app service initialization."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_config
from src.services import TranscriptAnalysisService

def main():
    print("Mimicking Flask app initialization...")
    print("="*60)
    
    # Get config (same as Flask app)
    config = get_config()
    print(f"Config: {config.ollama.base_url}, {config.ollama.model_name}")
    
    # Create TranscriptAnalysisService (same as APIRoutes.__init__)
    print("\nCreating TranscriptAnalysisService...")
    transcript_service = TranscriptAnalysisService(config)
    
    # Test the AI service
    print("\nTesting AI service connection...")
    try:
        ai_service = transcript_service.ai_service
        print(f"AI Service: {ai_service.__class__.__name__}")
        print(f"API URL: {ai_service.api_url}")
        
        # Call test_connection (same as get_service_status does)
        is_connected = ai_service.test_connection()
        print(f"\nConnection test result: {is_connected}")
        
        # Get full status
        status = transcript_service.get_service_status()
        print(f"\nFull status: {status}")
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

