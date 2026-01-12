import socket
import ssl
import time
import concurrent.futures
import os

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY_MS = 600  # отсекаем >600ms
MAX_WORKERS = 50      # количество потоков
TIMEOUT = 1           # тайм-аут на соединение в секундах

os.makedirs("githubmirror", exist_ok=True)

def parse_vless(link):
    """
    Простой парсер VLESS-ссылки.
    """
    try:
        main = link.split("@")[1]
        host_port = main.split("?")[0]
        host, port = host_port.split(":")
        return host, int(port)
    except Exception:
        return None, None

def check_latency(link):
    host, port = parse_vless(link)
    if not host or not port:
        return None

    start = time.time()
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                tls_start = time.time()
                # simple handshake test
                ssock.do_handshake()
                tls_end = time.time()
    except Exception:
        return None

    total_latency = (time.time() - start) * 1000  # ms
    tls_latency = (tls_end - tls_start) * 1000 if 'tls_end' in locals() else None

    if total_latency > MAX_LATENCY_MS:
        return None

    return f"{link}  # latency={total_latency:.0f}ms tls={tls_latency:.0f}ms"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} не найден")
        return

    with open(INPUT_FILE, "r") as f:
        links = [l.strip() for l in f if l.strip().startswith("vless://")]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_latency, link) for link in links]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    results.sort(key=lambda x: float(x.split("latency=")[1].split("ms")[0]))  # сортировка по latency

    with open(OUTPUT_FILE, "w") as f:
        for line in results:
            f.write(line + "\n")

    print(f"Saved {len(results)} servers → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
