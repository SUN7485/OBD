import json
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"

def login(page):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    page.fill('input[type="text"]', 'admin@test.com')
    page.fill('input[type="password"]', 'admin123')
    logs = []
    page.on("console", lambda msg: logs.append({"type": msg.type, "text": msg.text}))
    page.on("pageerror", lambda exc: logs.append({"type": "pageerror", "text": str(exc)}))
    page.click('button[type="submit"]')
    page.wait_for_timeout(4000)
    return logs, page.url

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    logs, final_url = login(page)
    print(json.dumps({"url": final_url, "logs": logs}, indent=2))
    os.makedirs("D:/obd/test-output", exist_ok=True)
    page.screenshot(path="D:/obd/test-output/login_after.png", full_page=True)
    browser.close()
