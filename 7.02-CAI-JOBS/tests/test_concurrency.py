
import requests
import json
import random
import sys
import threading
import time

BASE_URL = "http://127.0.0.1:8000"

def send_webhook(session_id: str, data: dict, results_list: list):
    url = f"{BASE_URL}/api/webhooks/{session_id}"
    try:
        response = requests.post(url, json=data)
        results_list.append(response.json())
    except Exception as e:
        print(f"Failed to send webhook for {session_id}: {e}")
        results_list.append(None)

def test_concurrency(num_requests=10):
    print(f"Starting concurrency test with {num_requests} requests...")
    
    threads = []
    results = []
    # Test 1: Multiple concurrent updates to the same session payload
    shared_session = f"concurrent_test_{random.randint(1000, 9999)}"
    print(f"Testing concurrent updates to session: {shared_session}")
    
    for i in range(num_requests):
        data = {
            "session_id": shared_session,
            "status": "Running",
            f"field_{i}": f"value_{i}",
            "scan_summary": "Partial scan" # This triggers history append
        }
        thread = threading.Thread(target=send_webhook, args=(shared_session, data, results))
        threads.append(thread)
        thread.start()
        
    for thread in threads:
        thread.join()
    
    print("All requests completed.")
    
    # Verify payload
    try:
        resp = requests.get(f"{BASE_URL}/api/webhooks/result/{shared_session}")
        if resp.status_code == 200:
            final_data = resp.json()
            print("Final payload retrieved.")
            
            # Check if all fields are present
            missing = []
            for i in range(num_requests):
                if f"field_{i}" not in final_data:
                    missing.append(f"field_{i}")
            
            if missing:
                print(f"FAILED: Missing fields in final payload: {missing}")
            else:
                print(f"SUCCESS: All {num_requests} concurrent updates were merged correctly.")
        else:
            print(f"FAILED: Could not retrieve final result: {resp.status_code}")
    except Exception as e:
        print(f"Error checking payload: {e}")

    # Verify history
    print("Verifying scan history...")
    try:
        resp = requests.get(f"{BASE_URL}/api/scans/history")
        if resp.status_code == 200:
            history = resp.json()
            # We expect multiple "Partial scan" entries for this session because we sent "scan_summary" in every request
            # Ideally, real usage sends final summary once, but this tests concurrent appends.
            count = sum(1 for h in history if h.get("session_id") == shared_session)
            print(f"History entries for {shared_session}: {count}")
            if count == num_requests:
                print(f"SUCCESS: History has exactly {num_requests} entries (no lost writes).")
            else:
                print(f"WARNING: History has {count} entries, expected {num_requests}.")
        else:
            print("FAILED: Could not retrieve scan history.")
    except Exception as e:
        print(f"Error checking history: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    test_concurrency()
