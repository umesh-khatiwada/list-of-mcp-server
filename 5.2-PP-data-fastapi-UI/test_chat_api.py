#!/usr/bin/env python3
"""
Simple test script to verify the chat API is working
"""
import requests
import json

def test_chat_api():
    url = "http://localhost:8001/api/chat"
    
    test_data = {
        "message": "provide me notification settings",
        "session_id": "2403eeac-14cd-44ed-bcfc-f90319cacf4d"
    }
    
    print("🧪 Testing chat API...")
    print(f"📤 Sending: {test_data}")
    
    try:
        response = requests.post(url, json=test_data)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response data:")
            print(json.dumps(data, indent=2))
            
            # Verify response structure
            expected_keys = ["response", "session_id", "success", "timestamp"]
            for key in expected_keys:
                if key in data:
                    print(f"  ✓ {key}: {data[key]}")
                else:
                    print(f"  ❌ Missing key: {key}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the server is running on port 8001")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_chat_api()
