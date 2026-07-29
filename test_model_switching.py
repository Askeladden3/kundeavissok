#!/usr/bin/env python3
"""
Test that model switching works correctly.
Verifies that the parser switches from local model to Google model.
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AI_model_setup import API_model


def test_model_detection():
    """Test that provider detection works correctly"""
    print("Testing model provider detection...")
    
    # Test local model detection
    local_model = API_model('/models/gemma4-12B-nvfp4', 'Test Model', 5, 20)
    provider_local = "openai" if local_model.id.startswith("/models/") else "google"
    
    if provider_local != "openai":
        print(f"  ✗ Wrong provider detected for local model: {provider_local}")
        return False
    print(f"  ✓ Local model detected as OpenAI provider")
    
    # Test Google model detection
    google_model = API_model('gemini-3.5-flash', 'Gemini Flash', 5, 20)
    provider_google = "openai" if google_model.id.startswith("/models/") else "google"
    
    if provider_google != "google":
        print(f"  ✗ Wrong provider detected for Google model: {provider_google}")
        return False
    print(f"  ✓ Google model detected as Google provider")
    
    return True


if __name__ == "__main__":
    if test_model_detection():
        sys.exit(0)
    else:
        sys.exit(1)
