#!/usr/bin/env python3
"""CPIS V1 — demo data seeder. Idempotent. Uses REST API."""
import json, os, sys, time
from urllib.request import Request, urlopen
from urllib.error import URLError

API_BASE = os.environ.get("CPIS_API_BASE", "http://localhost:8000")


def api_post(path, data):
    req = Request(
        f"{API_BASE}{path}",
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        print(f"  [WARN] POST {path} failed: {e}")
        return None


def api_get(path):
    try:
        with urlopen(f"{API_BASE}{path}", timeout=10) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        print(f"  [WARN] GET {path} failed: {e}")
        return None


def seed():
    print("=== CPIS V1 Demo Seeder ===")

    # 1. Check health
    health = api_get("/health/live")
    if not health:
        print("ERROR: API not available. Start the backend first.")
        sys.exit(1)
    print("[OK] API available")

    # 2. Check if already seeded (check products)
    products = api_get("/api/v1/products?page=1&page_size=1")
    if products and products.get("total", 0) > 0:
        print(f"[SKIP] Already seeded ({products['total']} products exist)")
        return

    # 3. Create products via API
    demo_products = [
        {
            "name": "TechPro X100",
            "brand": "TechPro",
            "category": "electronics",
            "description": "Premium smart device with AI-powered features.",
        },
        {
            "name": "NovaBook Pro 14",
            "brand": "NovaTech",
            "category": "laptop",
            "description": "Lightweight laptop with 14-inch OLED display.",
        },
        {
            "name": "SoundWave Buds Pro",
            "brand": "SoundWave",
            "category": "audio",
            "description": "Wireless earbuds with active noise cancellation.",
        },
    ]

    for p in demo_products:
        result = api_post("/api/v1/products", p)
        if result:
            print(f"  [OK] Created product: {p['name']}")

    # 4. Create a discovery session
    session = api_post(
        "/api/v1/discovery/sessions",
        {
            "query": "AI-powered smart devices 2026",
            "target_brand": "TechPro",
            "topic": "electronics",
        },
    )
    if session:
        print(f"  [OK] Discovery session: {session.get('id', 'created')}")

    # 5. Create a collection template
    template = api_post(
        "/api/v1/collection-templates",
        {
            "name": "TechPro Product Monitor",
            "description": "Monitor TechPro product pages",
            "sources": [
                {
                    "url": "https://example.com/techpro-x100",
                    "category_hint": "smartphone",
                }
            ],
            "feishu_sync_enabled": False,
        },
    )
    if template:
        print(f"  [OK] Collection template: {template.get('id', 'created')}")

    print("\n=== Seeding Complete ===")
    print("Demo data created. Browse to http://localhost:8080")


if __name__ == "__main__":
    seed()
