import json
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    responses = []
    page.on("response", lambda r: responses.append({"url": r.url, "status": r.status}))
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    page.fill('input[type="text"]', 'admin@test.com')
    page.fill('input[type="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_timeout(4000)
    print(json.dumps({"url": page.url, "title": page.title(), "responses": [r for r in responses if 'auth' in r['url']]}, indent=2))
    os.makedirs("D:/obd/test-output", exist_ok=True)
    page.screenshot(path="D:/obd/test-output/login_after_fix2.png", full_page=True)
    browser.close()
