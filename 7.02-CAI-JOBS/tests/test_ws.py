import asyncio
import websockets
import json
import sys

async def test_loki_ws(session_id):
    uri = f"ws://172.18.254.202:8000/api/sessions/{session_id}/logs/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            while True:
                msg = await websocket.recv()
                print(f"Raw data: {msg}")
                try:
                    data = json.loads(msg)
                    if data.get("heartbeat"):
                        print(f"Heartbeat: {data.get('status')} at {data.get('timestamp')}")
                        continue
                    if data.get("line"):
                        print(f"Log: [{data.get('timestamp')}] {data.get('line')}")
                    else:
                        print(f"Info/Status: {data}")
                    
                    if data.get("status") == "Completed" and not data.get("heartbeat") and not data.get("info"):
                        print("Job completed, closing connection.")
                        # break # Optional: stay connected to see if more logs come
                except Exception as e:
                    print(f"Non-JSON or error: {msg} ({e})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_ws.py <session_id>")
        sys.exit(1)
    asyncio.run(test_loki_ws(sys.argv[1]))
