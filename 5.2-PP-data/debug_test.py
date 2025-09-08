"""
Debug test script to identify response issues
"""

import asyncio
import requests
import json
import sys

async def test_direct_client():
    """Test the client directly"""
    print("🧪 Testing direct client...")
    
    try:
        from client import ComputesphereAgent
        
        agent = ComputesphereAgent()
        print("✅ Agent created")
        
        await agent.initialize_agent()
        print("✅ Agent initialized")
        
        print("\n🔍 Testing notification settings query...")
        response = await agent.chat("get notification settings")
        
        print(f"\n📋 Direct Response Details:")
        print(f"   Type: {type(response)}")
        print(f"   Length: {len(str(response)) if response else 0}")
        print(f"   Content: {response}")
        
        await agent.close()
        print("✅ Agent closed")
        
        return response
        
    except Exception as e:
        print(f"❌ Direct client error: {e}")
        return None

def test_api_endpoint():
    """Test the API endpoint"""
    print("\n🌐 Testing API endpoint...")
    
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "get notification settings",
        "session_id": "debug-test-session"
    }
    
    try:
        print(f"📤 Sending request to {url}")
        print(f"📤 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"\n📋 API Response Details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"   Response Data: {json.dumps(response_data, indent=2)}")
            return response_data.get('response')
        else:
            print(f"   Error Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the FastAPI server is running.")
        return None
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def test_health_endpoint():
    """Test the health endpoint"""
    print("\n🏥 Testing health endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {json.dumps(health_data, indent=2)}")
            return health_data.get('agent_ready', False)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_tools_endpoint():
    """Test the tools endpoint"""
    print("\n🔧 Testing tools endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/tools", timeout=30)
        if response.status_code == 200:
            tools_data = response.json()
            tools = tools_data.get('tools', [])
            print(f"✅ Found {len(tools)} tools")
            
            # Show first few tools
            for i, tool in enumerate(tools[:5]):
                name = tool.get('name', 'Unknown')
                desc = tool.get('description', 'No description')[:50]
                print(f"   {i+1}. {name}: {desc}...")
            
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more tools")
                
            return tools
        else:
            print(f"❌ Tools check failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Tools check error: {e}")
        return []

async def main():
    """Run all tests"""
    print("🚀 COMPUTESPHERE AGENT DEBUG TEST")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1️⃣ HEALTH CHECK")
    agent_ready = test_health_endpoint()
    
    if not agent_ready:
        print("❌ Agent not ready. Cannot proceed with tests.")
        return
    
    # Test 2: Tools check
    print("\n2️⃣ TOOLS CHECK")
    tools = test_tools_endpoint()
    
    # Test 3: Direct client test
    print("\n3️⃣ DIRECT CLIENT TEST")
    direct_response = await test_direct_client()
    
    # Test 4: API endpoint test
    print("\n4️⃣ API ENDPOINT TEST")
    api_response = test_api_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    print(f"Health Check: {'✅ Pass' if agent_ready else '❌ Fail'}")
    print(f"Tools Available: {len(tools)} tools")
    print(f"Direct Client: {'✅ Pass' if direct_response else '❌ Fail'}")
    print(f"API Endpoint: {'✅ Pass' if api_response else '❌ Fail'}")
    
    if direct_response and api_response:
        print(f"\n🔍 RESPONSE COMPARISON:")
        print(f"Direct Response Length: {len(str(direct_response))}")
        print(f"API Response Length: {len(str(api_response))}")
        
        if str(direct_response) == str(api_response):
            print("✅ Responses match perfectly!")
        else:
            print("⚠️  Responses differ:")
            print(f"   Direct: {str(direct_response)[:100]}...")
            print(f"   API: {str(api_response)[:100]}...")
    
    print("\n💡 RECOMMENDATIONS:")
    if not agent_ready:
        print("   - Restart the FastAPI server")
    elif not direct_response:
        print("   - Check client.py implementation")
        print("   - Verify MCP server connection")
    elif not api_response:
        print("   - Check FastAPI endpoint implementation")
        print("   - Check server logs for errors")
    else:
        print("   - All tests passed! ✅")

if __name__ == "__main__":
    asyncio.run(main())
