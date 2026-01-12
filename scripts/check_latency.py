import asyncio
import aiohttp
import time
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 600  # ms
TIMEOUT = 5        # секунд на один сервер

results = []

async def check_vless(link):
    try:
        parsed = urlparse(link)
        host = parsed.hostname
        port = parsed.port
        query = parse_qs(parsed.query)
        path = query.get("path", ["/"])[0]
        sni = query.get("sni", [host])[0]

        start = time.time()
        # TLS handshake + TCP ping approximation
        ssl_context = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=ssl_context) as session:
            async with session.head(f"https://{host}:{port}{path}", timeout=TIMEOUT) as resp:
                latency = (time.time() - start) * 1000
                if latency <= MAX_LATENCY:
                    results.append((latency, link))
    except Exception:
        pass

async def main():
    links = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("vless://"):
                links.append(line)

    tasks = [check_vless(link) for link in links]
    await asyncio.gather(*tasks)

    results.sort(key=lambda x: x[0])
    with open(OUTPUT_FILE, "w") as f:
        for latency, link in results:
            f.write(f"{link} # latency={int(latency)}ms\n")

if __name__ == "__main__":
    asyncio.run(main())
