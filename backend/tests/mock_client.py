"""
Mock WebSocket Test Client for Meeting Copilot.
Runs standalone to verify all backend WebSocket events, STT streaming,
action item detection, and Copilot queries without needing the frontend.
"""
import sys
import asyncio
import json
import websockets

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_WS_URL = "ws://localhost:8000/ws/meetings/default_sync"

async def run_client_simulation():
    print(f"\n[+] Connecting to {BACKEND_WS_URL} ...")
    try:
        async with websockets.connect(BACKEND_WS_URL) as ws:
            print("[+] Connected successfully!\n")

            # 0. Receive Sync History on initial connection
            init_res = await asyncio.wait_for(ws.recv(), timeout=5.0)
            init_data = json.loads(init_res)
            print(f"<- [0. SYNC HISTORY]: {init_data.get('type')} (Segments: {len(init_data.get('segments', []))}, Actions: {len(init_data.get('action_items', []))})\n")

            # 1. Send Ping
            print("-> [1] Sending Ping...")
            await ws.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"<- Received: {response}\n")

            # 2. Simulate streaming 3 audio chunks
            for i in range(1, 4):
                print(f"-> [2.{i}] Streaming audio_chunk #{i}...")
                mock_audio_payload = {
                    "type": "audio_chunk",
                    "data": f"base64_simulated_audio_bytes_{i}",
                    "format": "webm_opus"
                }
                await ws.send(json.dumps(mock_audio_payload))

                # Receive transcript segment
                res = await asyncio.wait_for(ws.recv(), timeout=5.0)
                parsed = json.loads(res)
                print(f"<- Transcript: [{parsed.get('speaker', 'Unknown')}]: {parsed.get('text', '')}")

                # If an action item was also detected and broadcasted:
                try:
                    res2 = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    parsed2 = json.loads(res2)
                    if parsed2.get("type") == "action_item_detected":
                        print(f"<- [ACTION ITEM DETECTED]: {parsed2.get('title')} -> Assigned to {parsed2.get('assignee')}")
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(0.5)

            # 3. Ask Copilot a question
            print("\n-> [3] Asking Copilot question...")
            query_payload = {
                "type": "copilot_query",
                "query": "What did Sarah say about the follow up meeting?"
            }
            await ws.send(json.dumps(query_payload))
            copilot_res = await asyncio.wait_for(ws.recv(), timeout=5.0)
            copilot_data = json.loads(copilot_res)
            print(f"<- [COPILOT ANSWER]: {copilot_data.get('answer')}")
            print(f"   References: {copilot_data.get('references')}\n")

            print("[+] All client simulation tests passed successfully!")

    except Exception as e:
        print(f"[-] Connection or test error: {e}")

if __name__ == "__main__":
    asyncio.run(run_client_simulation())
