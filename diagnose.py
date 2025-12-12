#!/usr/bin/env python3
"""Diagnostic script to see what happens when we click Easy Apply"""

from playwright.sync_api import sync_playwright
import sys

BROWSER_DATA_DIR = "./browser_data"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

job_url = "https://www.linkedin.com/jobs/view/4339460943/"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=BROWSER_DATA_DIR,
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        viewport={"width": 1280, "height": 720},
        user_agent=USER_AGENT,
        locale="en-US",
        timezone_id="America/New_York",
        channel=None,
        ignore_default_args=["--enable-automation"],
        chromium_sandbox=False,
    )
    
    page = context.pages[0] if context.pages else context.new_page()
    page.set_extra_http_headers({
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    
    print(f"Navigating to {job_url}")
    page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    
    print("\nLooking for Easy Apply...")
    easy_apply = page.locator('a[aria-label*="Easy Apply"]').first
    easy_apply.wait_for(state="visible", timeout=10000)
    
    href = easy_apply.get_attribute("href")
    print(f"Easy Apply href: {href}")
    
    print("\nClicking Easy Apply...")
    easy_apply.click()
    
    print("Waiting 10 seconds...")
    page.wait_for_timeout(10000)
    
    print(f"\nCurrent URL: {page.url}")
    print(f"Page title: {page.title()}")
    
    print("\nLooking for dialogs/modals...")
    dialogs = page.locator('[role="dialog"]').all()
    print(f"Found {len(dialogs)} dialogs")
    
    print("\nLooking for forms...")
    forms = page.locator('form').all()
    print(f"Found {len(forms)} forms")
    
    print("\nLooking for file inputs...")
    file_inputs = page.locator('input[type="file"]').all()
    print(f"Found {len(file_inputs)} file inputs")
    
    print("\nLooking for Next/Submit buttons...")
    next_btns = page.locator('button:has-text("Next"), button:has-text("Submit"), button:has-text("Review")').all()
    print(f"Found {len(next_btns)} action buttons")
    for i, btn in enumerate(next_btns[:5]):
        print(f"  Button {i+1}: {btn.text_content()}")
    
    print("\nTaking screenshot...")
    page.screenshot(path="diagnostic.png")
    print("Saved to: diagnostic.png")
    
    print("\n✓ Browser staying open. Press Ctrl+C to exit...")
    try:
        page.wait_for_timeout(300000)
    except KeyboardInterrupt:
        print("\nExiting...")
    
    context.close()
