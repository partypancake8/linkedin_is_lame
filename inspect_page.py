#!/usr/bin/env python3
"""Quick script to inspect the Easy Apply button on a LinkedIn job page."""

from playwright.sync_api import sync_playwright
import sys

BROWSER_DATA_DIR = "./browser_data"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_page.py <job_url>")
        sys.exit(1)
    
    job_url = sys.argv[1]
    
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
        
        print(f"Navigating to {job_url}...")
        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        
        print("\nWaiting 5 seconds for page to load...")
        page.wait_for_timeout(5000)
        
        print("\n" + "="*80)
        print("INSPECTING ALL BUTTONS ON PAGE")
        print("="*80)
        
        all_buttons = page.locator("button").all()
        print(f"\nFound {len(all_buttons)} buttons total\n")
        
        for i, btn in enumerate(all_buttons[:30]):  # First 30 buttons
            try:
                text = btn.text_content() or ""
                aria_label = btn.get_attribute("aria-label") or ""
                class_name = btn.get_attribute("class") or ""
                data_control = btn.get_attribute("data-control-name") or ""
                
                # Check if it might be the Easy Apply button
                is_easy_apply = (
                    "easy apply" in text.lower() or
                    "easy apply" in aria_label.lower() or
                    "easy-apply" in class_name.lower() or
                    "easy" in data_control.lower()
                )
                
                marker = "🎯 " if is_easy_apply else "   "
                
                print(f"{marker}Button {i+1}:")
                print(f"  Text: '{text.strip()[:80]}'")
                if aria_label:
                    print(f"  Aria-label: '{aria_label[:80]}'")
                if data_control:
                    print(f"  Data-control-name: '{data_control[:80]}'")
                print(f"  Classes: '{class_name[:100]}'")
                print()
                
            except Exception as e:
                print(f"  Button {i+1}: Error - {e}\n")
        
        print("\n" + "="*80)
        print("Press Ctrl+C to exit...")
        print("="*80)
        
        try:
            page.wait_for_timeout(300000)  # Wait 5 minutes
        except KeyboardInterrupt:
            print("\nExiting...")
        
        context.close()

if __name__ == "__main__":
    main()
