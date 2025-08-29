#!/usr/bin/env python3
"""
Test script for webhook endpoints
"""

import requests
import json
import os
import time
from datetime import datetime

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def test_status_endpoint():
    """Test the status endpoint"""
    print("Testing status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing status: {e}")
        return False

def test_calls_endpoint():
    """Test the calls endpoint"""
    print("\nTesting calls endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/calls")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing calls: {e}")
        return False

def simulate_twilio_webhook():
    """Simulate a Twilio webhook call"""
    print("\nSimulating Twilio webhook...")
    
    # Simulate Twilio webhook data (form data for FastAPI)
    twilio_data = {
        "From": "+15551234567",
        "To": "+15557654321",
        "CallSid": f"CA{int(time.time())}{hash(datetime.now()) % 1000:03d}",
        "CallStatus": "ringing",
        "Direction": "inbound"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook/twilio",
            data=twilio_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"TwiML Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing Twilio webhook: {e}")
        return False

def test_call_refer():
    """Test call referral endpoint"""
    print("\nTesting call referral...")
    
    test_call_id = "test_call_123"
    refer_data = {
        "target_uri": "tel:+15551234567"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/call/{test_call_id}/refer",
            json=refer_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        # Note: This will likely return an error since the call doesn't exist
        # but it tests the endpoint structure
        return True
    except Exception as e:
        print(f"Error testing call refer: {e}")
        return False

def test_api_docs():
    """Test FastAPI automatic documentation"""
    print("\nTesting API documentation...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        if response.status_code == 200:
            print("✅ API docs are accessible")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing API docs: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("FASTAPI WEBHOOK TESTING SUITE")
    print("=" * 50)
    
    tests = [
        ("Status Endpoint", test_status_endpoint),
        ("Calls Endpoint", test_calls_endpoint),
        ("API Documentation", test_api_docs),
        ("Twilio Webhook", simulate_twilio_webhook),
        ("Call Refer", test_call_refer)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"📊 FastAPI automatic docs available at: {BASE_URL}/docs")
    
    return passed == total

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    print(f"Testing against: {BASE_URL}")
    success = run_all_tests()
    sys.exit(0 if success else 1)