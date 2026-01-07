#!/usr/bin/env python3
"""Test script for the CAI Kubernetes Job Manager."""

import time

import requests

# Base URL for the API
BASE_URL = "http://localhost:8000"


def test_basic_session():
    """Test creating a basic session."""
    print("🧪 Testing Basic Session Creation...")

    session_data = {
        "name": "Test Security Scan",
        "prompt": "Perform a quick security assessment of localhost",
        "character_id": None,
        "token": None,
    }

    response = requests.post(f"{BASE_URL}/api/sessions", json=session_data)
    if response.status_code == 200:
        session = response.json()
        print(f"✅ Basic session created: {session['id']}")
        return session["id"]
    else:
        print(f"❌ Failed to create basic session: {response.text}")
        return None


def test_advanced_session():
    """Test creating an advanced session with multiple features."""
    print("\n🚀 Testing Advanced Session Creation...")

    advanced_session_data = {
        "name": "Advanced Parallel Security Assessment",
        "prompt": "Analyze the security posture of a web application",
        "agent_type": "redteam_agent",
        "model": "deepseek/deepseek-chat",
        "parallel_agents": [
            {
                "name": "redteam_scanner",
                "agent_type": "redteam_agent",
                "model": "deepseek/deepseek-chat",
                "initial_prompt": "Focus on vulnerability scanning and exploitation techniques",
                "alias": "redteam",
            },
            {
                "name": "blueteam_defender",
                "agent_type": "blueteam_agent",
                "model": "deepseek/deepseek-chat",
                "initial_prompt": "Focus on defensive measures and security hardening",
                "alias": "blueteam",
            },
        ],
        "cost_constraints": {
            "price_limit": 5.0,
            "max_interactions": 50,
            "max_turns": 25,
        },
        "debug_level": 1,
        "tracing_enabled": True,
        "webhook_notifications": True,
    }

    response = requests.post(f"{BASE_URL}/api/v2/sessions", json=advanced_session_data)
    if response.status_code == 200:
        session = response.json()
        print(f"✅ Advanced session created: {session['id']}")
        print(f"   Mode: {session['mode']}")
        print(f"   Jobs: {len(session['job_names'])}")
        return session["id"]
    else:
        print(f"❌ Failed to create advanced session: {response.text}")
        return None


def test_ctf_session():
    """Test creating a CTF-specific session."""
    print("\n🎯 Testing CTF Session Creation...")

    ctf_session_data = {
        "name": "CTF Web Challenge",
        "prompt": "Analyze this web application CTF challenge and find the flag",
        "agent_type": "redteam_agent",
        "model": "alias1",
        "ctf_config": {
            "ctf_name": "example_ctf",
            "challenge_name": "web_app_challenge",
            "challenge_type": "web",
            "inside_container": True,
            "time_limit_minutes": 30,
        },
        "cost_constraints": {"price_limit": 3.0, "max_turns": 20},
        "debug_level": 2,
    }

    response = requests.post(f"{BASE_URL}/api/v2/sessions", json=ctf_session_data)
    if response.status_code == 200:
        session = response.json()
        print(f"✅ CTF session created: {session['id']}")
        print(f"   Mode: {session['mode']}")
        return session["id"]
    else:
        print(f"❌ Failed to create CTF session: {response.text}")
        return None


def test_queue_session():
    """Test creating a queue-based automation session."""
    print("\n📋 Testing Queue Session Creation...")

    queue_session_data = {
        "name": "Automated Security Checklist",
        "agent_type": "bug_bounter_agent",
        "model": "alias1",
        "queue_items": [
            {
                "command": "Perform reconnaissance on the target",
                "description": "Initial recon phase",
                "agent_type": "redteam_agent",
                "expected_duration_minutes": 5,
            },
            {
                "command": "Test for common web vulnerabilities",
                "description": "OWASP Top 10 testing",
                "agent_type": "bug_bounter_agent",
                "expected_duration_minutes": 10,
            },
            {
                "command": "Generate security report",
                "description": "Report compilation",
                "agent_type": "reporting_agent",
                "expected_duration_minutes": 3,
            },
        ],
        "cost_constraints": {"price_limit": 8.0, "max_turns": 40},
    }

    response = requests.post(f"{BASE_URL}/api/v2/sessions", json=queue_session_data)
    if response.status_code == 200:
        session = response.json()
        print(f"✅ Queue session created: {session['id']}")
        print(f"   Mode: {session['mode']}")
        print(f"   Steps: {session.get('total_steps', 'N/A')}")
        return session["id"]
    else:
        print(f"❌ Failed to create queue session: {response.text}")
        return None


def monitor_session(session_id: str, session_type: str = "basic"):
    """Monitor a session until completion."""
    print(f"\n👁️  Monitoring {session_type} session: {session_id}")

    if session_type == "basic":
        endpoint = f"/api/sessions/{session_id}"
    else:
        endpoint = f"/api/v2/sessions/{session_id}"

    max_attempts = 30
    attempts = 0

    while attempts < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                session = response.json()
                status = session.get("status", "Unknown")
                print(f"   Status: {status}")

                if session_type != "basic":
                    completed = session.get("completed_steps", 0)
                    total = session.get("total_steps", 0)
                    if total > 0:
                        print(f"   Progress: {completed}/{total}")

                if status in ["Completed", "Failed"]:
                    break

            time.sleep(5)
            attempts += 1

        except Exception as e:
            print(f"   Error checking status: {e}")
            break

    # Get final results
    if session_type != "basic":
        print("📊 Getting session results...")
        results_response = requests.get(
            f"{BASE_URL}/api/v2/sessions/{session_id}/results"
        )
        if results_response.status_code == 200:
            results = results_response.json()
            print(f"   Flags found: {len(results.get('flags_found', []))}")
            print(f"   Vulnerabilities: {len(results.get('vulnerabilities', []))}")
            print(f"   Agent outputs: {len(results.get('outputs', {}))}")


def test_health():
    """Test the health endpoint."""
    print("🏥 Testing Health Endpoint...")

    response = requests.get(f"{BASE_URL}/api/health")
    if response.status_code == 200:
        print("✅ Health check passed")
        return True
    else:
        print(f"❌ Health check failed: {response.text}")
        return False


def get_session_logs(session_id: str):
    """Get and display session logs for debugging."""
    print(f"\n📜 Getting logs for session: {session_id}")

    try:
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}/logs")
        if response.status_code == 200:
            data = response.json()
            print("Logs:")
            print("=" * 50)
            print(data.get("logs", "No logs available"))
            print("=" * 50)
        else:
            print(f"Failed to get logs: {response.text}")
    except Exception as e:
        print(f"Error getting logs: {e}")


def list_sessions():
    """List all sessions."""
    print("\n📋 Listing all sessions...")

    # List basic sessions
    response = requests.get(f"{BASE_URL}/api/sessions")
    if response.status_code == 200:
        sessions = response.json()
        print(f"Basic sessions: {len(sessions)}")
        for session in sessions[-3:]:  # Show last 3
            print(f"  - {session['name']} ({session['status']})")

    # List advanced sessions
    response = requests.get(f"{BASE_URL}/api/v2/sessions")
    if response.status_code == 200:
        sessions = response.json()
        print(f"Advanced sessions: {len(sessions)}")
        for session in sessions[-3:]:  # Show last 3
            print(
                f"  - {session['name']} ({session['status']}) - Mode: {session.get('mode', 'N/A')}"
            )


def main():
    """Run all tests."""
    print("🚀 CAI Kubernetes Job Manager - Test Suite")
    print("=" * 50)

    # Test health first
    if not test_health():
        print("❌ Service not healthy, stopping tests")
        return

    # List existing sessions
    list_sessions()

    # Test basic functionality
    basic_session_id = test_basic_session()
    if basic_session_id:
        time.sleep(3)  # Wait a bit for job to start
        get_session_logs(basic_session_id)
        monitor_session(basic_session_id, "basic")

    # Test advanced features
    # advanced_session_id = test_advanced_session()
    # if advanced_session_id:
    #     monitor_session(advanced_session_id, "advanced")

    # ctf_session_id = test_ctf_session()
    # if ctf_session_id:
    #     monitor_session(ctf_session_id, "ctf")

    # queue_session_id = test_queue_session()
    # if queue_session_id:
    #     monitor_session(queue_session_id, "queue")

    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main()
