"""
Meeting Copilot — Live Interactive CLI Demo
Demonstrates real-time STT streaming, action items, proactive nudges,
and Copilot Q&A over WebSocket with ANSI terminal colors.
"""
import asyncio
import json
import sys
import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

WS_URL = "ws://localhost:8000/ws/meetings/default_sync"

async def run_live_demo():
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}  🎙️  MEETING COPILOT — LIVE SIMULATION DEMO        {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}\n")
    print(f"{BLUE}[*] Connecting to WebSocket: {WS_URL} ...{RESET}")

    try:
        async with websockets.connect(WS_URL) as ws:
            print(f"{GREEN}[+] Connected to Meeting Stream!{RESET}\n")

            # 1. Sync History
            init_res = await asyncio.wait_for(ws.recv(), timeout=5.0)
            init_data = json.loads(init_res)
            print(f"{BLUE}[SYNC] Received history: {len(init_data.get('segments', []))} past segments, {len(init_data.get('action_items', []))} action items.{RESET}\n")

            # 2. Simulate dialogue chunks
            dialogue_samples = [
                ("Sarah K.", "Welcome everyone to our weekly sync. Let's start with Q4 roadmap updates."),
                ("Dave R.", "The API integration for Project Gamma is underway, but we need to address supply chain bottlenecks."),
                ("Emily W.", "Logistics is facing delays on the international shipments. We may need a fallback vendor."),
                ("Sarah K.", "I agree. Let's schedule a dedicated deep dive tomorrow at 2 PM to finalize the vendor choice."),
                ("Alex M.", "I will prepare the supplier comparative report and share it before tomorrow noon."),
            ]

            print(f"{BOLD}{YELLOW}--- STREAMING LIVE MEETING DIALOGUE ---{RESET}\n")

            for idx, (speaker, speech) in enumerate(dialogue_samples, start=1):
                timestamp = f"00:{idx * 15:02d}"
                payload = {
                    "type": "audio_chunk",
                    "data": f"base64_demo_audio_{idx}",
                    "format": "webm_opus",
                    "timestamp": timestamp
                }
                await ws.send(json.dumps(payload))

                # Receive transcript
                res = await asyncio.wait_for(ws.recv(), timeout=5.0)
                parsed = json.loads(res)
                if parsed.get("type") == "transcript_segment":
                    print(f"{CYAN}[{parsed.get('timestamp')}] {BOLD}{parsed.get('speaker')}:{RESET} {parsed.get('text')}")

                # Check for action item or nudge broadcast
                try:
                    while True:
                        extra_res = await asyncio.wait_for(ws.recv(), timeout=0.3)
                        extra_data = json.loads(extra_res)
                        if extra_data.get("type") == "action_item_detected":
                            print(f"  {BOLD}{GREEN}⚡ [ACTION ITEM DETECTED]:{RESET} {extra_data.get('title')} -> Assigned to: {extra_data.get('assignee')} (Due: {extra_data.get('due_date')})")
                        elif extra_data.get("type") == "proactive_nudge":
                            print(f"  {BOLD}{MAGENTA}💡 [COPILOT NUDGE]:{RESET} {extra_data.get('nudge')}")
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(1.2)

            # 3. Ask Copilot Query
            print(f"\n{BOLD}{YELLOW}--- REAL-TIME COPILOT QUERY ---{RESET}")
            user_question = "What was the decision regarding the logistics delay?"
            print(f"{BLUE}❓ User Asks:{RESET} {user_question}")

            await ws.send(json.dumps({
                "type": "copilot_query",
                "query": user_question
            }))

            copilot_res = await asyncio.wait_for(ws.recv(), timeout=5.0)
            copilot_data = json.loads(copilot_res)
            print(f"{BOLD}{GREEN}🤖 Copilot Answer:{RESET} {copilot_data.get('answer')}")
            print(f"{CYAN}   Citations: {copilot_data.get('references')}{RESET}\n")

            print(f"{BOLD}{GREEN}✅ Live simulation completed successfully!{RESET}\n")

    except ConnectionRefusedError:
        print(f"\n{YELLOW}[!] Could not connect to {WS_URL}.")
        print(f"    Please ensure the backend server is running via:")
        print(f"    uvicorn app.main:app --reload{RESET}\n")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_demo())

