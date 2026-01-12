import requests
import os

URL = "https://github.com/AvenCores/goida-vpn-configs/raw/refs/heads/main/githubmirror/26.txt"
OUTPUT_FILE = "githubmirror/26_alive_filtered.txt"

os.makedirs("githubmirror", exist_ok=True)

print("Downloading 26.txt ...")
r = requests.get(URL, timeout=20)
r.raise_for_status()
lines = r.text.splitlines()

vless_links = [l.strip() for l in lines if l.strip().startswith("vless://")]

print(f"Found {len(vless_links)} VLESS links")

with open(OUTPUT_FILE, "w") as f:
    for link in vless_links:
        f.write(link + "\n")

print(f"Saved to {OUTPUT_FILE}")
