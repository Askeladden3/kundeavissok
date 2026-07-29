#!/usr/bin/env python3
"""
Test image encoding functionality.
Verifies that images are properly encoded for OpenAI API.
"""

import os
import sys
import tempfile
import base64
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Gemini_Parser import encode_image_to_data_uri


def test_encode_with_pil():
    """Test encoding using PIL (the actual implementation)"""
    print("Testing image encoding with PIL...")
    
    test_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_img", "test.jpg")
    
    try:
        if not os.path.exists(test_img_path):
            print(f"  ERROR: Test image not found at {test_img_path}")
            return False
        
        # Test encoding
        data_uri = encode_image_to_data_uri(test_img_path)
        
        # Verify format
        match = re.match(r'data:image/jpeg;base64,(.+)', data_uri)
        if not match:
            print(f"  ✗ Invalid data URI format: {data_uri[:100]}")
            return False
        
        # Verify it decodes correctly
        b64_data = match.group(1)
        decoded = base64.b64decode(b64_data)
        
        # Check it's valid JPEG
        if decoded[:2] != b'\xff\xd8':
            print(f"  ✗ Decoded data doesn't look like JPEG")
            return False
        
        print(f"  ✓ Image encoding successful")
        print(f"    Original size: {os.path.getsize(test_img_path)} bytes")
        print(f"    Encoded size: {len(decoded)} bytes")
        print(f"    Data URI length: {len(data_uri)} chars")
        return True
        
    except Exception as e:
        print(f"  ✗ Image encoding failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if test_encode_with_pil():
        sys.exit(0)
    else:
        sys.exit(1)
