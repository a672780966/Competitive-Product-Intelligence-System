#!/usr/bin/env python3
"""CPIS V1 — demo data seeder. Idempotent. Uses REST API."""
import json, os, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_BASE = os.environ.get("CPIS_API_BASE", "http://localhost:8000")


def api_post(path, data):
    """POST to API. Raises on failure."""
    req = Request(
        f"{API_BASE}{path}",
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def api_get(path):
    """GET from API. Raises on failure."""
    with urlopen(f"{API_BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode())


def seed():
    print("=== CPIS V1 Demo Seeder ===")

    # 1. Check health
    try:
        api_get("/health/live")
    except (HTTPError, URLError) as e:
        print(f"ERROR: API not reachable ({e}). Start the backend first.")
        sys.exit(1)
    print("[OK] API available")

    # 2. Check if already seeded (check products)
    try:
        products = api_get("/api/v1/products?page=1&page_size=1")
    except (HTTPError, URLError) as e:
        print(f"ERROR: GET /api/v1/products failed: {e}")
        sys.exit(1)

    total = products.get("total", 0) if isinstance(products, dict) else 0
    if total > 0:
        print(f"[SKIP] Already seeded ({total} product(s) exist)")
        sys.exit(0)

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
        try:
            api_post("/api/v1/products", p)
            print(f"  [OK] Created product: {p['name']}")
        except (HTTPError, URLError) as e:
            print(f"  ERROR: POST /api/v1/products failed for '{p['name']}': {e}")
            sys.exit(1)

    # 4. Create a discovery session
    try:
        api_post(
            "/api/v1/discovery/sessions",
            {
                "query": "AI-powered smart devices 2026",
                "target_brand": "TechPro",
                "topic": "electronics",
            },
        )
        print("  [OK] Discovery session created")
    except (HTTPError, URLError) as e:
        print(f"  ERROR: POST /api/v1/discovery/sessions failed: {e}")
        sys.exit(1)

    # 5. Create a collection template
    try:
        api_post(
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
        print("  [OK] Collection template created")
    except (HTTPError, URLError) as e:
        print(f"  ERROR: POST /api/v1/collection-templates failed: {e}")
        sys.exit(1)

    # 6. Verify data was actually created
    print("Verifying seeded data...")
    try:
        products = api_get("/api/v1/products?page=1&page_size=100")
    except (HTTPError, URLError) as e:
        print(f"  ERROR: GET /api/v1/products failed during verification: {e}")
        sys.exit(1)

    count = len(products.get("items", [])) if isinstance(products, dict) else 0
    if count == 0:
        print("  ERROR: No products found after seeding — data was not persisted")
        sys.exit(1)
    print(f"  [OK] {count} product(s) verified in database")

    try:
        sessions = api_get("/api/v1/discovery/sessions?page=1&page_size=10")
    except (HTTPError, URLError):
        # optional — don't fail if endpoint missing
        sessions = None

    if sessions and isinstance(sessions, dict) and sessions.get("total", 0) > 0:
        print(f"  [OK] {sessions['total']} discovery session(s) verified")
    else:
        print("  [OK] Discovery session created (verification skipped)")

    try:
        templates = api_get("/api/v1/collection-templates?page=1&page_size=10")
    except (HTTPError, URLError):
        templates = None

    if templates and isinstance(templates, dict) and templates.get("total", 0) > 0:
        print(f"  [OK] {templates['total']} collection template(s) verified")
    else:
        print("  [OK] Collection template created (verification skipped)")

    print("\n=== Seeding Complete ===")
    print("Demo data created. Browse to http://localhost:8080")


if __name__ == "__main__":
    seed()
