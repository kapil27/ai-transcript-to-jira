#!/usr/bin/env python3
"""Direct test of OllamaService."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_config
from src.services.ai_service import OllamaService

def main():
    print("Testing OllamaService directly...")
    print("="*60)
    
    # Get config
    config = get_config()
    print(f"Config loaded:")
    print(f"  - Ollama URL: {config.ollama.base_url}")
    print(f"  - Ollama Model: {config.ollama.model_name}")
    print(f"  - Ollama Timeout: {config.ollama.timeout}")
    print()
    
    # Create service
    service = OllamaService(config)
    print(f"Service API URL: {service.api_url}")
    print()
    
    # Test connection
    print("Testing connection...")
    try:
        is_connected = service.test_connection()
        print(f"Connection test result: {is_connected}")
    except Exception as e:
        print(f"Connection test exception: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test simple transcript parsing
    print("Testing transcript parsing...")
    try:
        transcript = "John said we need to update the documentation. Sarah will review the code."
        tasks = service.parse_transcript(transcript)
        print(f"Successfully parsed {len(tasks)} tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. {task.get('summary', 'N/A')}")
    except Exception as e:
        print(f"Parsing exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

