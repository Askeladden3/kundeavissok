#!/usr/bin/env python3
"""
Simple test runner for Gemini_Parser integration tests.
Runs all test scripts and reports results.
"""

import subprocess
import sys
import os

TEST_SCRIPTS = [
#    "test_integration_google.py",
    "test_integration_openai.py",
    "test_model_switching.py",
    "test_image_encoding.py",
]

def run_test(script):
    """Run a single test and return (name, success, message)"""
    result = subprocess.run(
        ["/home/ask/Projects/kundeavissok/.venv/bin/python", script],
        capture_output=True,
        text=True
    )
    success = result.returncode == 0
    msg = result.stdout.strip() or result.stderr.strip()
    return script, success, msg

def main():
    print("=" * 60)
    print("Running Gemini_Parser Integration Tests")
    print("=" * 60)
    
    results = []
    passed = 0
    failed = 0
    
    for script in TEST_SCRIPTS:
        name, success, msg = run_test(script)
        results.append((script, success, msg))
        if success:
            passed += 1
            print(f"\n✓ {script}")
            print(f"  {msg}")
        else:
            failed += 1
            print(f"\n✗ {script}")
            print(f"  {msg}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
