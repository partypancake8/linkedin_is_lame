#!/usr/bin/env python3
"""
LinkedIn Login Helper
Opens the bot's browser and waits for you to log into LinkedIn.
Press Ctrl+C when done to save the session.
"""

from playwright.sync_api import sync_playwright
import sys

BROWSER_DATA_DIR = "./browser_data"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def main():
    print("Opening browser for LinkedIn login...")
    print("=" * 50)
    print("Instructions:")
    print("1. Log into LinkedIn in the browser that opens")
    print("2. Navigate around LinkedIn to ensure you're logged in")
    print("3. Visit a job posting to verify access")
    print("4. Press Ctrl+C in this terminal when ready")
    print("5. Your session will be saved for future bot runs")
    print("=" * 50)
    
    try:
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
            
            # Navigate to LinkedIn
            print("\nNavigating to LinkedIn...")
            page.goto("https://www.linkedin.com/login")
            
            print("\n✓ Browser is open.")
            print("\nPLEASE DO THE FOLLOWING:")
            print("  1. Log in with your credentials")
            print("  2. After login, visit: https://www.linkedin.com/jobs/")
            print("  3. Make sure you can see job listings")
            print("  4. Then press Ctrl+C here to save the session\n")
            
            # Wait indefinitely until user presses Ctrl+C
            try:
                page.wait_for_timeout(1000000000)  # ~11 days
            except Exception:
                pass
            
    except KeyboardInterrupt:
        print("\n\n✓ Session saved! You can now run the bot.")
        print("Run: ./run.sh \"<job_url>\"\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
