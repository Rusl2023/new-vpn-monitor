#!/usr/bin/env python3
import asyncio
import ssl
import socket
from urllib.parse import urlparse, parse_qs
import aiohttp
import time

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 0.6  # 600ms
TIMEOUT = 5

# Парсинг VLESS URL
def parse_vless(url):
    url = url.strip()
    if not url.startswith("vless://"):
        return None
    url = url[7:]
    user_host, *rest = url.split("@")
    host_port, *params = rest[0].split("?")
    host, port = host_port.split(":")
    query = {}
    if params:
        query = parse_qs(params[0])
    return {
        "url": url,
        "host": host,
        "port": int(port),
        "params": query,
    }

# Проверка TCP + TLS
async def check_server(server):
    host = server["host"]
    port = server["port"]
    params = server["params"]
    start = time.time()
    tls_latency = 0
    try:
        # TCP connect
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), TIMEOUT)
        # TLS handshake (если нужно)
        if params.get("security", ["none"])[0] in ["tls", "reality"]:
            ctx = ssl.create_default_context()
            ssl_start = time.time()
            reader_ssl, writer_ssl = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx), TIMEOUT
            )
            tls_latency = time.time() - ssl_start
            writer_ssl.close()
            await writer_ssl.wait_closed()
        writer.close()
        await writer.wait_closed()
        latency = time.time() - start
    except Exception:
        return None

    # Минимальный WS HEAD проверка
    ws_path = params.get("path", ["/"])[0]
    scheme = "https" if params.get("security", ["none"])[0] in ["tls", "reality"] else "http"
    url = f"{scheme}://{host}:{port}{ws_path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=TIMEOUT):
                pass
    except Exception:
        pass  # не критично

    if latency > MAX_LATENCY:
        return None
    return {"url": server["url"], "latency": latency, "tls_latency": tls_latency}

async def main():
    servers = []
    with open(INPUT_FILE) as f:
        for line in f:
            parsed = parse_vless(line)
            if parsed:
                servers.append(parsed)
    results = await asyncio.gather(*[check_server(s) for s in servers])
    alive = [r for r in results if r]
    alive.sort(key=lambda x: x["latency"])
    with open(OUTPUT_FILE, "w") as f:
        for s in alive:
            f.write(f"{s['url']} # latency={int(s['latency']*1000)}ms tls={int(s['tls_latency']*1000)}ms\n")

if __name__ == "__main__":
    asyncio.run(main())
