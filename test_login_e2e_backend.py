import json
import os
from playwright.sync_api import sync_playwright

def run_login_test():
    result = {"login": "pending"}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()
            page.on("console", lambda msg: print("console", msg.type, msg.text))
            page.on("pageerror", lambda exc: print("pageerror", exc))
            page.goto("http://localhost:3000/login", wait_until="networkidle", timeout=30000)
            page.fill('input[type="text"]', 'admin@test.com')
            page.fill('input[type="password"]', 'admin123')
            page.click('button[type="submit"]')
            page.wait_for_timeout(3000)
            result["login"] = "completed"
            result["final_url"] = page.url
            os.makedirs("D:/obd/test-output", exist_ok=True)
            page.screenshot(path="D:/obd/test-output/login_result.png", full_page=True)
            browser.close()
    except Exception as e:
        result["login"] = "failed"
        result["error"] = str(e)
    print(json.dumps(result, indent=2))

run_login_test()
