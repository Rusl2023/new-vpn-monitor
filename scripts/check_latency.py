import socket
import ssl
import time
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 0.6  # 600ms

def parse_vless(link):
    """Разбирает ссылку VLESS и возвращает host, port, path, tls"""
    try:
        url = urlparse(link)
        host = url.hostname
        port = url.port
        query = parse_qs(url.query)
        path = query.get("path", ["/"])[0]
        tls = "tls" in query or query.get("security", ["none"])[0].lower() == "tls"
        return host, port, path, tls
    except Exception as e:
        print(f"Parse error: {link} -> {e}")
        return None, None, None, None

def check_latency(host, port, use_tls):
    """Измеряет TCP latency и TLS handshake latency"""
    tcp_latency = None
    tls_latency = 0
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=3)
        tcp_latency = time.time() - start
        if use_tls:
            context = ssl.create_default_context()
            start_tls = time.time()
            wrapped = context.wrap_socket(sock, server_hostname=host)
            tls_latency = time.time() - start_tls
            wrapped.close()
        else:
            sock.close()
    except Exception as e:
        return None, None
    return tcp_latency, tls_latency

def main():
    alive = []
    with open(INPUT_FILE) as f:
        lines = f.read().splitlines()

    for line in lines:
        host, port, path, tls = parse_vless(line.strip())
        if not host or not port:
            continue
        tcp, tlat = check_latency(host, port, tls)
        if tcp is None:
            continue
        total_latency = tcp + (tlat if tlat else 0)
        if total_latency <= MAX_LATENCY:
            alive.append((line.strip(), total_latency))

    alive.sort(key=lambda x: x[1])
    print(f"Saved {len(alive)} servers → {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w") as f:
        for line, lat in alive:
            f.write(line + "\n")

if __name__ == "__main__":
    main()
