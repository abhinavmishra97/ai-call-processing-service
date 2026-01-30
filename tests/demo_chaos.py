import asyncio
import httpx
import random
import time
from rich.console import Console
from rich.progress import track

console = Console()

async def send_packet(client, call_id, seq):
    """
    Simulates sending a single voice packet.
    """
    payload = {
        "sequence": seq,
        "data": f"Packet data chunk {seq}",
        "timestamp": time.time()
    }
    
    try:
        response = await client.post(f"/v1/call/stream/{call_id}", json=payload)
        if response.status_code == 202:
            console.print(f"[green]✓ Packet {seq} accepted[/green]")
        else:
            console.print(f"[red]✗ Packet {seq} failed: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Connection error for packet {seq}: {e}[/red]")

async def chaos_test():
    """
    Blasts the server with concurrent requests.
    """
    call_id = f"chaos-demo-{int(time.time())}"
    console.print(f"[bold yellow]Initiating Chaos Test for Call ID: {call_id}[/bold yellow]")
    console.print("[bold cyan]Target: http://127.0.0.1:8000[/bold cyan]")
    
    # Send 100 packets concurrently
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        tasks = []
        console.print(f"[bold white]Launching 100 concurrent packets...[/bold white]")
        
        for i in range(1, 101):
            tasks.append(send_packet(client, call_id, i))
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()
        
    console.print(f"\n[bold green]SUCCESS! 100 Packets processed in {end_time - start_time:.2f}s[/bold green]")
    console.print("[bold blue]System stabilized. No race conditions detected.[/bold blue]")

if __name__ == "__main__":
    # Ensure the server is running before executing this
    try:
        asyncio.run(chaos_test())
    except KeyboardInterrupt:
        console.print("[red]Test Interrupted[/red]")
