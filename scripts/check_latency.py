import socket
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"

TIMEOUT = 1.2          # секунды
MAX_WORKERS = 120
TOP_N = 50             # сколько лучших оставить


def parse_vless(link: str):
    try:
        # vless://uuid@host:port?params#tag
        main = link.split("://", 1)[1]
        hostport = main.split("@", 1)[1].split("?", 1)[0]
        host, port = hostport.rsplit(":", 1)
        return host.strip(), int(port.strip())
    except Exception:
        return None


def check_latency(link: str):
    parsed = parse_vless(link)
    if not parsed:
        return None

    host, port = parsed
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        sock.close()
        latency = int((time.time() - start) * 1000)
        return latency, link
    except Exception:
        return None


def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found")
        return

    with open(INPUT_FILE, "r") as f:
        links = [l.strip() for l in f if l.strip().startswith("vless://")]

    print(f"Checking {len(links)} servers...")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_latency, link) for link in links]
        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    results.sort(key=lambda x: x[0])
    best = results[:TOP_N]

    os.makedirs("githubmirror", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for latency, link in best:
            f.write(f"{link}\n")

    print(f"Saved {len(best)} servers → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
