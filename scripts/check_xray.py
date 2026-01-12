import subprocess
import time
import json
import os
import tempfile
import socket
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"

XRAY_BIN = "./xray"
SOCKS_PORT = 1080
TIMEOUT = 6
TOP_LIMIT = 50


def parse_vless(link: str):
    try:
        u = urlparse(link)
        if not u.hostname or not u.username:
            return None

        port = int(u.netloc.split(":")[-1].split("/")[0])

        return {
            "uuid": u.username,
            "host": u.hostname,
            "port": port,
            "params": parse_qs(u.query),
        }
    except Exception:
        return None


def build_config(v):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": SOCKS_PORT,
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


def test_socks_connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    start = time.time()
    try:
        s.connect(("127.0.0.1", SOCKS_PORT))
        s.close()
        return int((time.time() - start) * 1000)
    except Exception:
        return None


def check(link):
    v = parse_vless(link)
    if not v:
        return None

    cfg = build_config(v)

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        json.dump(cfg, f)
        cfg_path = f.name

    try:
        proc = subprocess.Popen(
            [XRAY_BIN, "run", "-c", cfg_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(1.2)  # даём Xray подняться
        latency = test_socks_connect()

        proc.terminate()
        proc.wait(timeout=2)

        return latency
    except Exception:
        return None


def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found")
        return

    with open(INPUT_FILE) as f:
        links = [l.strip() for l in f if l.startswith("vless://")]

    results = []

    for i, link in enumerate(links, 1):
        latency = check(link)
        if latency:
            print(f"[OK] {latency} ms")
            results.append((latency, link))

        if i % 50 == 0:
            print(f"Checked {i}/{len(links)}")

    results.sort(key=lambda x: x[0])
    results = results[:TOP_LIMIT]

    os.makedirs("githubmirror", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for _, link in results:
            f.write(link + "\n")

    print(f"Saved {len(results)} servers → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
