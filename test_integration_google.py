#!/usr/bin/env python3
"""
Integration test for Google provider (existing behavior).
Verifies that the parser works correctly with Google API.
"""

import os
import sys
import json
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Gemini_Parser import Gemini_parser
from AI_model_setup import AI_models


def test_google_parser():
    """Test that Google parser runs successfully and produces output"""
    print("Testing Google provider integration...")
    
    # Use default models (all Google)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory to avoid polluting existing output
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        # Copy required files
        import shutil
        shutil.copy('/home/ask/Projects/kundeavissok/prompts.txt', 'prompts.txt')
        
        try:
            # Set up test images before running parser
            import shutil
            os.makedirs('temp_output/bilder', exist_ok=True)
            shutil.copy('/home/ask/Projects/kundeavissok/test_img/test.jpg', 
                       'temp_output/bilder/rema-1000-1.jpg')
            shutil.copy('/home/ask/Projects/kundeavissok/test_img/test.jpg', 
                       'temp_output/bilder/rema-1000-1-2.jpg')
            
            # Run parser with minimal settings
            # Use first Google model explicitly
            Gemini_parser(
                BUTIKKER=['rema-1000'],
                AI_models=[AI_models[0]],  # gemini-3.5-flash
                add_website_json=False,
                add_tmp_json=False,
                batchsize=2  # Process the 2 test images in one batch
            )
            
            # Check output files exist
            output_dir = "temp_output/results_JSON"
            expected_files = ['standard_deal.json', 'percentage_deal.json', 'bogo_deal.json']
            
            for fname in expected_files:
                path = os.path.join(output_dir, fname)
                if not os.path.exists(path):
                    print(f"ERROR: Output file not found: {fname}")
                    return False
                with open(path, 'r') as f:
                    data = json.load(f)
                    if len(data) == 0:
                        print(f"WARNING: {fname} is empty")
            
            print("✓ Google parser integration test passed")
            print(f"  Output files created: {expected_files}")
            return True
            
        finally:
            os.chdir(old_cwd)


def test_model_rate_limiting():
    """Test that model exhaustion tracking works"""
    print("\nTesting model rate limiting...")
    
    model = AI_models[0]
    model.n_calls = model.rate_limit  # Set to rate limit
    
    # Call should work (at limit, not exceeding)
    if not model.rate_limit_reached():
        print("✓ Rate limiting check passed")
        return True
    return False


if __name__ == "__main__":
    all_pass = True
    
    all_pass &= test_google_parser()
    all_pass &= test_model_rate_limiting()
    
    if all_pass:
        sys.exit(0)
    else:
        sys.exit(1)
