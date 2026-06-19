import json
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
PAGES = [
    "/login",
    "/dashboard",
    "/dashboard/alerts",
    "/dashboard/analytics",
    "/dashboard/map",
    "/dashboard/fleet",
    "/dashboard/drivers",
    "/dashboard/maintenance",
]

os.makedirs("D:/obd/test-output", exist_ok=True)

def login(page):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    page.fill('input[type="text"]', 'admin@test.com')
    page.fill('input[type="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=15000)

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    for path in PAGES:
        res = {"url": BASE + path, "status": "ok"}
        try:
            if path != "/login":
                login(page)
            r = page.goto(BASE + path, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(500)
            res["status_code"] = r.status if r else None
            res["final_url"] = page.url
            res["title"] = page.title()
            page.screenshot(path=f"D:/obd/test-output/page_{path.replace('/', '_').strip('_') or 'home'}.png", full_page=False)
        except Exception as e:
            res["status"] = "error"
            res["error"] = str(e)
        results.append(res)
    browser.close()

print(json.dumps(results, indent=2))
