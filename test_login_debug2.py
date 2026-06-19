import json
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.on("pageerror", lambda exc: print("pageerror", exc))
    page.on("console", lambda msg: print("console", msg.type, msg.text))
    page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=20000)
    page.screenshot(path="D:/obd/test-output/login_initial.png", full_page=True)
    page.fill('input[type="text"]', 'admin@test.com')
    page.fill('input[type="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_timeout(4000)
    page.screenshot(path="D:/obd/test-output/login_after_click.png", full_page=True)
    print("current_url", page.url)
    browser.close()
