"""Regenerate the README screenshots from a running stack (make up first).

    make screenshots
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("UI_URL", "http://localhost:5173")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/screenshots"
SHOTS = {
    "account-6-site-g-outage.png": "/?account=6&as_of=2026-04-20",
    "account-15-latest.png": "/?account=15",
    "account-5-site-d-vs-site-b.png": "/?account=5&as_of=2026-07-20",
    "account-20-empty.png": "/?account=20",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 700}, color_scheme="light")
    for name, path in SHOTS.items():
        page.goto(BASE + path)
        page.wait_for_selector("section h2, [role=alert]")
        bottom = page.locator("main").bounding_box()["height"] + 24
        page.screenshot(path=f"{OUT}/{name}", clip={"x": 0, "y": 0, "width": 900, "height": min(620, bottom)})
        print("saved", name)
    browser.close()
