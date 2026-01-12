#!/usr/bin/env python3
import subprocess
import tempfile
import time
import json
import base64
import urllib.parse
from pathlib import Path

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
XRAY_BIN = "./xray"

TIMEOUT = 8


def parse_vless(link: str):
    assert link.startswith("vless://")
    link = link[len("vless://"):]

    user, rest = link.split("@", 1)
    hostport, _, params = rest.partition("?")
    host, port = hostport.split(":")

    query = urllib.parse.parse_qs(params)

    def q(name, default=None):
        return query.get(name, [default])[0]

    return {
        "id": user,
        "host": host,
        "port": int(port),
        "type": q("type", "tcp"),
        "security": q("security"),
        "sni": q("sni"),
        "fp": q("fp"),
        "flow": q("flow"),
        "pbk": q("pbk"),
        "sid": q("sid"),
        "spx": q("spx"),
        "alpn": q("alpn"),
        "mux": q("mux"),
    }


def make_config(v):
    stream = {
        "network": v["type"] or "tcp",
    }

    if v["security"] == "reality":
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "serverName": v["sni"],
            "publicKey": v["pbk"],
            "shortId": v["sid"],
            "fingerprint": v["fp"] or "chrome",
            "spiderX": v["spx"] or "/",
        }
    elif v["security"] == "tls":
        stream["security"] = "tls"
        stream["tlsSettings"] = {
            "serverName": v["sni"],
            "allowInsecure": True,
            "fingerprint": v["fp"] or "chrome",
            "alpn": v["alpn"].split(",") if v["alpn"] else None,
        }

    outbound = {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": v["host"],
                "port": v["port"],
                "users": [{
                    "id": v["id"],
                    "encryption": "none",
                    "flow": v["flow"],
                }]
            }]
        },
        "streamSettings": stream,
    }

    if v["mux"] == "1":
        outbound["mux"] = {"enabled": True}

    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": 10808,
            "listen": "127.0.0.1",
            "protocol": "socks",
        }],
        "outbounds": [
            outbound,
            {"protocol": "freedom", "tag": "direct"}
        ]
    }


def check(link):
    v = parse_vless(link)
    cfg = make_config(v)

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        json.dump(cfg, f)
        cfg_path = f.name

    start = time.time()
    try:
        subprocess.run(
            [XRAY_BIN, "run", "-test", "-config", cfg_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=True
        )
        return round((time.time() - start) * 1000)
    except Exception:
        return None
    finally:
        Path(cfg_path).unlink(missing_ok=True)


def main():
    out = []
    for line in Path(INPUT_FILE).read_text().splitlines():
        latency = check(line.strip())
        if latency is not None:
            out.append((latency, line))

    out.sort(key=lambda x: x[0])

    with open(OUTPUT_FILE, "w") as f:
        for lat, link in out:
            f.write(f"# {lat} ms\n{link}\n")


if __name__ == "__main__":
    main()
