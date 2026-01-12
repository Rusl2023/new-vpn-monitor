import subprocess
import time
import json
import os
import tempfile
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"

XRAY_BIN = "./xray"
TIMEOUT = 5
TOP_LIMIT = 50


def parse_vless(link: str):
    try:
        u = urlparse(link)

        host = u.hostname
        if not host:
            return None

        # порт может быть "80/" → чистим
        port_raw = u.netloc.split(":")[-1]
        port = int(port_raw.split("/")[0])

        uuid = u.username
        if not uuid:
            return None

        params = parse_qs(u.query)

        return {
            "uuid": uuid,
            "host": host,
            "port": port,
            "params": params,
        }
    except Exception:
        return None


def build_config(v):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": 1080,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": v["host"],
                    "port": v["port"],
                    "users": [{
                        "id": v["uuid"],
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": {
                "network": v["params"].get("type", ["tcp"])[0],
                "security": v["params"].get("security", ["none"])[0],
                "tlsSettings": {
                    "serverName": v["params"].get("sni", [""])[0]
                }
            }
        }]
    }


def check(link: str):
    v = parse_vless(link)
    if not v:
        return None

    cfg = build_config(v)

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        json.dump(cfg, f)
        cfg_path = f.name

    start = time.time()

    try:
        p = subprocess.run(
            [XRAY_BIN, "run", "-c", cfg_path],
            timeout=TIMEOUT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired:
        return round((time.time() - start) * 1000)

    return None


def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found")
        return

    with open(INPUT_FILE) as f:
        links = [l.strip() for l in f if l.strip().startswith("vless://")]

    results = []

    for link in links:
        latency = check(link)
        if latency:
            results.append((latency, link))
            print(f"OK {latency} ms")

    results.sort(key=lambda x: x[0])
    results = results[:TOP_LIMIT]

    os.makedirs("githubmirror", exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        for latency, link in results:
            f.write(link + "\n")

    print(f"Saved {len(results)} servers → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
