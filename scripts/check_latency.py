import socket
import ssl
import time
import re
from urllib.parse import parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 600  # ms
TIMEOUT = 3  # сек на каждое соединение
MAX_THREADS = 20  # параллельные проверки

def parse_vless(link: str):
    pattern = r"vless://([^@]+)@([^:]+):(\d+)\?(.+)"
    match = re.match(pattern, link)
    if not match:
        return None
    uuid, host, port, query = match.groups()
    params = parse_qs(query)
    return {
        "uuid": uuid,
        "host": host,
        "port": int(port),
        "params": params,
        "raw": link
    }

def tcp_ping(host, port):
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        sock.close()
        return int((time.time() - start) * 1000)
    except:
        return None

def tls_handshake(host, port):
    start = time.time()
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                pass
        return int((time.time() - start) * 1000)
    except:
        return None

def ws_head(host, port, path="/", use_tls=False):
    import http.client
    try:
        if use_tls:
            conn = http.client.HTTPSConnection(host, port=port, timeout=TIMEOUT)
        else:
            conn = http.client.HTTPConnection(host, port=port, timeout=TIMEOUT)
        conn.request("HEAD", path)
        res = conn.getresponse()
        conn.close()
        return res.status < 400
    except:
        return False

def check_server(server):
    host = server["host"]
    port = server["port"]
    params = server["params"]

    use_tls = params.get("security", ["none"])[0].lower() in ["tls", "reality"]
    path = params.get("path", ["/"])[0]

    tcp_latency = tcp_ping(host, port)
    if tcp_latency is None:
        return None

    tls_latency = None
    if use_tls:
        tls_latency = tls_handshake(host, port)
        if tls_latency is None:
            return None

    if params.get("type", ["tcp"])[0].lower() == "ws":
        if not ws_head(host, port, path, use_tls):
            return None

    latency = tls_latency if tls_latency else tcp_latency
    if latency > MAX_LATENCY:
        return None

    server["latency"] = latency
    server["tls_latency"] = tls_latency or 0
    return server

def main():
    with open(INPUT_FILE) as f:
        lines = f.read().splitlines()

    parsed_servers = [parse_vless(line) for line in lines]
    parsed_servers = [s for s in parsed_servers if s]

    results = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_server = {executor.submit(check_server, s): s for s in parsed_servers}
        for future in as_completed(future_to_server):
            server = future.result()
            if server:
                results.append(server)

    # сортируем по latency
    results.sort(key=lambda x: x["latency"])

    # сохраняем
    with open(OUTPUT_FILE, "w") as f:
        for s in results:
            f.write(s["raw"] + "\n")

    print(f"Saved {len(results)} servers → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
