import asyncio
import httpx
import uuid
import sys

# URL of your local API
API_URL = "http://127.0.0.1:8000"

async def send_packet(msg_id, call_id):
    async with httpx.AsyncClient() as client:
        payload = {
            "sequence": msg_id,
            "data": f"Packet {msg_id}",
            "timestamp": 123456789
        }
        try:
            # We fire this rapidly!
            response = await client.post(f"{API_URL}/v1/call/stream/{call_id}", json=payload)
            return str(response.status_code)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"ERROR: {e}"

async def run_race():
    # 1. Generate a random Call ID that DEFINITELY doesn't exist yet
    call_id = f"race-test-{uuid.uuid4().hex[:8]}"
    print(f"Testing Race Condition for Call ID: {call_id}")
    print("Firing 5 requests simultaneously...")

    # 2. Create 5 concurrent tasks that will hit the server at the exact same millisecond
    tasks = []
    for i in range(5):
        tasks.append(send_packet(i+1, call_id))

    # 3. Fire them all at once!
    results = await asyncio.gather(*tasks)

    print("\nResults (Status Codes):")
    print(results)
    print("\nCheck your SERVER TERMINAL (where uvicorn is running).")
    print("If successful, you might see '>>> RACE CONDITION CAUGHT! <<<' logs,")
    print("but ALL requests should return 202 (Accepted) without 500 Errors.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_race())
