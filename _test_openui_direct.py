"""Test OpenUI directly from worker container."""
import requests, json, time, os

url = os.environ.get("OPENUI_SERVICE_URL", "http://host.docker.internal:7878") + "/generate"

payload = {
    "designerPRD": {
        "business_name": "Arena Gym Fitness",
        "sections": [
            {"name": "hero", "title": "Academia de Elite", "content": "Academia em Campina Grande do Sul"}
        ],
        "color_palette": {
            "primary": "#1a1a2e",
            "secondary": "#e94560",
            "accent": "#f5a623",
            "background": "#ffffff",
            "text": "#333333"
        },
        "typography": {}
    }
}

print(f"POST {url}")
t0 = time.monotonic()
try:
    r = requests.post(url, json=payload, timeout=120)
    elapsed = time.monotonic() - t0
    print(f"Status: {r.status_code} in {elapsed:.1f}s")
    data = r.json()
    html = data.get("html", data.get("code", ""))
    print(f"HTML length: {len(html)} chars")
    print(f"Model: {data.get('model', 'unknown')}")
    print(f"HTML preview (first 300): {html[:300]}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
