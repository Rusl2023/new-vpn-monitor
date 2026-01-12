import socket
import ssl
import time
import re
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "githubmirror/26_alive_filtered.txt"
OUTPUT_FILE = "githubmirror/26_alive_final.txt"
MAX_LATENCY = 600  # ms

def parse_vless(link: str):
    """
    Разбирает ссылку vless://
    """
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

def tcp_ping(host, port, timeout=5):
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return int((time.time() - start) * 1000)
    except Exception:
        return None

def tls_handshake(host, port, timeout=5):
    start = time.time()
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                pass
        return int((time.time() - start) * 1000)
    except Exception:
        return None

def ws_head(host, port, path="/", use_tls=False, timeout=5):
    import http.client
    try:
        if use_tls:
            conn = http.client.HTTPSConnection(host, port=port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port=port, timeout=timeout)
        conn.request("HEAD", path)
        res = conn.getresponse()
        conn.close()
        return res.status < 400
    except Exception:
        return False

def check_server(server):
    host = server["host"]
    port = server["port"]
    params = server["params"]

    # Определяем, нужен ли TLS
    use_tls = False
    if "security" in params:
        sec = params.get("security", ["none"])[0].lower()
        if sec in ["tls", "reality"]:
            use_tls = True

    # Определяем путь для WS
    path = "/"
    if "path" in params:
        path = params["path"][0]

    tcp_latency = tcp_ping(host, port)
    if tcp_latency is None:
        return None

    tls_latency = None
    if use_tls:
        tls_latency = tls_handshake(host, port)
        if tls_latency is None:
            return None

    ws_ok = True
    if "type" in params and params["type"][0].lower() == "ws":
        ws_ok = ws_head(host, port, path=path, use_tls=use_tls)
        if not ws_ok:
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

    results = []
    for line in lines:
        parsed = parse_vless(line.strip())
        if not parsed:
            continue
        checked = check_server(parsed)
        if checked:
            results.append(checked)

    # сортируем по latency
    results.sort(key=lambda x: x["latency"])

    # сохраняем
    with open(OUTPUT_FILE, "w") as f:
        for s in results:
            f.write(s["raw"] + "\n")

    print(f"Saved {len(results)} servers → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
