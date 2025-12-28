#!/usr/bin/env python3
"""Test Ollama connection directly."""

import requests
import json

def test_ollama():
    url = "http://localhost:11434/api/generate"
    
    # Test 1: Simple request without format
    print("Test 1: Simple request without format parameter...")
    payload1 = {
        "model": "llama3.1:latest",
        "prompt": "Say OK",
        "stream": False
    }
    try:
        response = requests.post(url, json=payload1, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json().get('response', '')[:100]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Request with format=json
    print("Test 2: Request with format=json parameter...")
    payload2 = {
        "model": "llama3.1:latest",
        "prompt": "Return a JSON object with a field called 'test' set to 'OK'",
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(url, json=payload2, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json().get('response', '')[:100]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Request with options
    print("Test 3: Request with options parameter...")
    payload3 = {
        "model": "llama3.1:latest",
        "prompt": "Say OK",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }
    try:
        response = requests.post(url, json=payload3, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json().get('response', '')[:100]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_ollama()

