import json
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.on("console", lambda msg: print("console", msg.type, msg.text))
    page.on("pageerror", lambda exc: print("pageerror", exc))
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    page.fill('input[type="text"]', 'admin@test.com')
    page.fill('input[type="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_timeout(4000)
    print(json.dumps({"url": page.url, "title": page.title()}, indent=2))
    os.makedirs("D:/obd/test-output", exist_ok=True)
    page.screenshot(path="D:/obd/test-output/login_after_fix.png", full_page=True)
    browser.close()
