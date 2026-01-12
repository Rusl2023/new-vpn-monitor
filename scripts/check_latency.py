# scripts/check_latency.py
import asyncio
import ssl
import time

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 0.6  # 600ms
TIMEOUT = 5  # сек

def parse_vless(url: str):
    """Парсинг VLESS URL"""
    if not url.startswith("vless://"):
        return None
    try:
        parts = url[8:].split("@")
        user_id, rest = parts
        host_port, *_ = rest.split("?")
        host, port = host_port.split(":")
        return {"url": url, "host": host, "port": int(port)}
    except Exception:
        return None

async def check_tcp_tls(server):
    host = server["host"]
    port = server["port"]

    start = time.time()
    try:
        ssl_context = ssl.create_default_context()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ssl_context), TIMEOUT
        )
        latency = time.time() - start
        writer.close()
        await writer.wait_closed()
    except Exception:
        return None

    if latency > MAX_LATENCY:
        return None

    return {"url": server["url"], "latency": round(latency*1000)}

async def main():
    servers = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            srv = parse_vless(line.strip())
            if srv:
                servers.append(srv)

    tasks = [check_tcp_tls(s) for s in servers]
    results = await asyncio.gather(*tasks)

    alive = [r for r in results if r]
    alive.sort(key=lambda x: x["latency"])

    with open(OUTPUT_FILE, "w") as f:
        for s in alive:
            f.write(f"{s['url']}  # latency={s['latency']}ms\n")

    print(f"Saved {len(alive)} servers → {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
