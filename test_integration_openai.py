#!/usr/bin/env python3
"""
Integration test for OpenAI provider (local model).
Verifies that the parser works correctly with local LLM backend.
"""

import os
import sys
import json
import tempfile
import re
import base64

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Gemini_Parser import model_api_call, encode_image_to_data_uri
from pydantic_models import FlyerBatch


def test_image_encoding():
    """Test that images are properly encoded for OpenAI"""
    print("Testing image encoding...")
    
    test_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_img", "test.jpg")
    
    try:
        # Check if test image exists
        if not os.path.exists(test_img_path):
            print(f"  WARNING: Test image not found at {test_img_path}")
            print("  Skipping image encoding test")
            return True
        
        # Test encoding
        data_uri = encode_image_to_data_uri(test_img_path)
        
        # Verify format
        match = re.match(r'data:image/jpeg;base64,(.+)', data_uri)
        if not match:
            print(f"  ERROR: Invalid data URI format: {data_uri[:100]}")
            return False
        
        # Verify it decodes correctly
        b64_data = match.group(1)
        decoded = base64.b64decode(b64_data)
        
        # Check size is reasonable
        if len(decoded) < 100 or len(decoded) > 10000000:
            print(f"  WARNING: Encoded image size seems unusual: {len(decoded)} bytes")
        
        print(f"  ✓ Image encoding: {len(decoded)} bytes encoded")
        return True
        
    except Exception as e:
        print(f"  ✗ Image encoding failed: {e}")
        return False


def test_openai_api_call():
    """Test that OpenAI API call works with local backend"""
    print("\nTesting OpenAI API call...")
    
    # Read prompt
    with open('prompts.txt', 'r', encoding='utf-8') as f:
        prompts = f.read().split('/'*5)
        prompt = prompts[1]
    
    # Use test image
    test_img_path = "/home/ask/Projects/kundeavissok/test_img/test.jpg"
    
    if not os.path.exists(test_img_path):
        print(f"  ERROR: Test image not found at {test_img_path}")
        return False
    
    try:
        # Call API
        response = model_api_call(
            provider='openai',
            model_id='/models/gemma4-12B-nvfp4',
            prompt=prompt,
            image_paths=[test_img_path],
            response_format=FlyerBatch,
            temperature=0.3,
            response_mime_type='application/json'
        )
        
        # Verify response type (should be FlyerBatch instance, not string)
        if not isinstance(response, FlyerBatch):
            print(f"  ✗ Wrong response type: {type(response)}")
            return False
        
        # Verify we got some flyers
        if len(response.flyers) == 0:
            print(f"  ⚠ No flyers returned (this may be expected for test image)")
        
        print(f"  ✓ OpenAI API call successful")
        print(f"    Model: gemma4-12B-nvfp4")
        print(f"    Flyers returned: {len(response.flyers)}")
        return True
        
    except Exception as e:
        print(f"  ✗ OpenAI API call failed: {e}")
        return False


if __name__ == "__main__":
    all_pass = True
    
    all_pass &= test_image_encoding()
    all_pass &= test_openai_api_call()
    
    if all_pass:
        sys.exit(0)
    else:
        sys.exit(1)
