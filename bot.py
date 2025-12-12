#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Minimal MVP
Single-run automation for trivial Easy Apply submissions.
"""

import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration - Update these paths for your system
BROWSER_DATA_DIR = "./browser_data"
RESUME_PATH = os.path.expanduser("/Users/sawyersmith/Documents/resume2025.pdf")
LOG_FILE = "log.jsonl"

# Timeouts (milliseconds)
BUTTON_TIMEOUT = 15000  # 15 seconds
MODAL_TIMEOUT = 15000   # 15 seconds
SUBMIT_TIMEOUT = 10000  # 10 seconds

# User agent to avoid detection
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def log_result(job_url: str, status: str, failure_reason: str = None, steps_completed: int = 0):
    """Append structured log entry to JSONL file."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "job_url": job_url,
        "status": status,
        "steps_completed": steps_completed,
    }
    if failure_reason:
        log_entry["failure_reason"] = failure_reason
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"[{status}] {job_url}")
    if failure_reason:
        print(f"  Reason: {failure_reason}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python bot.py <job_url>")
        sys.exit(1)
    
    job_url = sys.argv[1]
    steps_completed = 0
    
    # Validate resume exists
    if not os.path.exists(RESUME_PATH):
        log_result(job_url, "FAILED", f"Resume not found at {RESUME_PATH}", steps_completed)
        sys.exit(1)
    
    try:
        with sync_playwright() as p:
            # Launch browser with persistent context (separate profile for bot)
            print("Launching browser...")
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
                channel=None,  # Use Playwright's Chromium
                # These help avoid detection
                ignore_default_args=["--enable-automation"],
                chromium_sandbox=False,
            )
            
            # Set extra headers to appear more like a real browser
            page = context.pages[0] if context.pages else context.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            })
            
            steps_completed += 1  # Browser launched
            
            # Navigate to job URL
            print(f"Navigating to {job_url}...")
            page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
            steps_completed += 1  # Navigation complete
            
            # Wait a moment for page to fully render
            print("Waiting for page to fully load...")
            page.wait_for_timeout(5000)  # Wait 5 seconds for dynamic content
            
            # Check if we're actually redirected to auth wall or login page
            current_url = page.url
            if "/authwall" in current_url or "/checkpoint/challenge" in current_url or current_url.startswith("https://www.linkedin.com/login"):
                log_result(job_url, "FAILED", "LinkedIn authentication required - run ./setup_login.sh first", steps_completed)
                print("\n⚠️  LinkedIn is asking you to log in!")
                print("Run: ./setup_login.sh\n")
                context.close()
                return
            
            # Step 1: Find Easy Apply button (actually a link on LinkedIn)
            print("Looking for Easy Apply button...")
            
            # Wait a bit more for the apply button to appear
            page.wait_for_timeout(2000)
            
            # Take a screenshot for debugging before searching
            page.screenshot(path="debug_before_search.png")
            print("  Screenshot saved: debug_before_search.png")
            
            # Try to find Easy Apply - it's actually an <a> tag, not a button!
            easy_apply_element = None
            try:
                # Method 1: Look for link with aria-label containing "Easy Apply"
                easy_apply_element = page.locator('a[aria-label*="Easy Apply"]').first
                easy_apply_element.wait_for(state="visible", timeout=5000)
                print("  ✓ Found Easy Apply link (aria-label method)")
            except PlaywrightTimeout:
                try:
                    # Method 2: Look for link with data-view-name="job-apply-button"
                    easy_apply_element = page.locator('a[data-view-name="job-apply-button"]').first
                    easy_apply_element.wait_for(state="visible", timeout=3000)
                    print("  ✓ Found Easy Apply link (data-view-name method)")
                except PlaywrightTimeout:
                    try:
                        # Method 3: Look for any link containing "Easy Apply" text
                        easy_apply_element = page.locator('a:has-text("Easy Apply")').first
                        easy_apply_element.wait_for(state="visible", timeout=3000)
                        print("  ✓ Found Easy Apply link (text method)")
                    except PlaywrightTimeout:
                        # Debug output
                        page.screenshot(path="debug_no_button.png")
                        all_links = page.locator('a').all()
                        print(f"  ✗ Could not find Easy Apply (searched {len(all_links)} links)")
                        log_result(job_url, "SKIPPED", f"Easy Apply link not found (screenshot: debug_no_button.png)", steps_completed)
                        context.close()
                        return
            
            if not easy_apply_element:
                page.screenshot(path="debug_no_button.png")
                log_result(job_url, "SKIPPED", "Easy Apply element not found", steps_completed)
                context.close()
                return
            
            steps_completed += 1  # Easy Apply found
            
            # Step 2: Navigate to Easy Apply page
            print("Opening Easy Apply...")
            
            # Scroll element into view first
            easy_apply_element.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            
            # Get the href - we'll navigate directly instead of clicking
            href = easy_apply_element.get_attribute("href") or ""
            print(f"  Easy Apply URL: {href}")
            
            # Check if it's an external (non-LinkedIn) page
            if href and href != "#" and not href.startswith("javascript:") and not "linkedin.com" in href:
                print(f"  ⚠️  Easy Apply redirects to external site")
                log_result(job_url, "SKIPPED", f"Easy Apply redirects to external site: {href}", steps_completed)
                context.close()
                return
            
            # Based on research: LinkedIn blocks automated clicks on Easy Apply
            # Solution: Use JavaScript click or wait for manual interaction
            
            print(f"  Attempting to open Easy Apply form...")
            
            # Try Method 1: JavaScript click (bypasses Playwright detection)
            try:
                print(f"    Method 1: JavaScript click...")
                easy_apply_element.evaluate("el => el.click()")
                page.wait_for_timeout(3000)  # Wait for modal/page to load
                print(f"    ✓ JavaScript click executed")
            except Exception as e:
                print(f"    ✗ JavaScript click failed: {e}")
                
                # Try Method 2: Navigate to href
                if href and "linkedin.com" in href:
                    print(f"    Method 2: Direct navigation to {href}")
                    page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    print(f"    ✓ Navigation complete")
                else:
                    print(f"    ✗ No valid navigation options")
                    log_result(job_url, "FAILED", "Could not open Easy Apply", steps_completed)
                    context.close()
                    return
            
            # Additional wait for apply flow to fully load
            print("Waiting for apply flow to stabilize...")
            page.wait_for_timeout(2000)
            
            # Step 3: Detect if we're in the apply flow (modal or dedicated page)
            print("Looking for Easy Apply form...")
            
            current_url = page.url
            print(f"  Current URL: {current_url}")
            
            # Take screenshot to see what we got
            page.screenshot(path="debug_after_click.png")
            print("  Screenshot: debug_after_click.png")
            
            # Look for the apply form with comprehensive selectors from research
            form_found = False
            form_selector = None
            
            # Try multiple selectors based on successful implementations
            selectors_to_try = [
                ('[role="dialog"]', 'aria-role dialog'),
                ('.jobs-easy-apply-modal', 'easy-apply modal class'),
                ('.artdeco-modal', 'artdeco modal class'),
                ('div.jobs-easy-apply-modal__content', 'modal content'),
                ('.artdeco-modal__content', 'artdeco content'),
                ('form[data-job-id]', 'form with job-id'),
                ('h2:has-text("Easy Apply")', 'Easy Apply header'),
                ('.jobs-easy-apply-content', 'easy apply content'),
            ]
            
            for selector, description in selectors_to_try:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        print(f"  ✓ Found form via {description} ({count} elements)")
                        form_found = True
                        form_selector = selector
                        steps_completed += 1
                        break
                except Exception as e:
                    print(f"    Selector '{selector}' check failed: {e}")
            
            if not form_found:
                # Final fallback: Check for form input elements
                print("  Checking for form input elements...")
                form_element_selectors = [
                    'input[type="file"]',
                    'button:has-text("Next")',
                    'button:has-text("Submit")',
                    'button:has-text("Review")',
                    'input[type="text"]',
                    'input[type="number"]',
                    'select',
                ]
                
                total_elements = 0
                for sel in form_element_selectors:
                    try:
                        count = page.locator(sel).count()
                        total_elements += count
                    except:
                        pass
                
                if total_elements > 0:
                    form_found = True
                    print(f"  ✓ Found {total_elements} form input elements")
                    steps_completed += 1
            
            if not form_found:
                print("  ✗ No apply form found")
                log_result(job_url, "SKIPPED", "Easy Apply form did not appear", steps_completed)
                context.close()
                return
            
            # Wait a bit for modal content to fully load
            page.wait_for_timeout(2000)
            
            # Take screenshot of modal for debugging
            page.screenshot(path="debug_modal_opened.png")
            print("  Screenshot of modal: debug_modal_opened.png")
            
            # Step 4: Check for multi-step flow (presence of Next/Continue buttons)
            print("Checking for multi-step flow...")
            next_buttons = page.locator("button:has-text('Next'), button:has-text('Continue')").count()
            if next_buttons > 0:
                log_result(job_url, "SKIPPED", "Multi-step application detected", steps_completed)
                context.close()
                return
            
            steps_completed += 1  # Single-step confirmed
            
            # Step 5: Check for required text inputs (questions)
            print("Checking for required questions...")
            required_inputs = page.locator("input[required]:not([type='file']), textarea[required]").count()
            if required_inputs > 0:
                log_result(job_url, "SKIPPED", "Required text inputs detected", steps_completed)
                context.close()
                return
            
            steps_completed += 1  # No questions required
            
            # Step 6: Upload resume if file input exists
            print("Looking for file upload...")
            file_input = page.locator("input[type='file']").first
            if file_input.count() > 0:
                print(f"Uploading resume from {RESUME_PATH}...")
                file_input.set_input_files(RESUME_PATH)
                steps_completed += 1  # Resume uploaded
            
            # Step 7: Find and click Submit button
            print("Looking for Submit button...")
            try:
                submit_button = page.wait_for_selector(
                    "button:has-text('Submit application'), button:has-text('Submit')",
                    timeout=SUBMIT_TIMEOUT
                )
            except PlaywrightTimeout:
                log_result(job_url, "SKIPPED", "Submit button not found", steps_completed)
                context.close()
                return
            
            print("Clicking Submit...")
            submit_button.click()
            steps_completed += 1  # Submit clicked
            
            # Step 8: Wait for confirmation
            print("Waiting for confirmation...")
            try:
                # Wait for modal to close or success message
                page.wait_for_selector(
                    "text=/application.*submitted|application.*sent/i",
                    timeout=SUBMIT_TIMEOUT
                )
                log_result(job_url, "SUCCESS", None, steps_completed)
            except PlaywrightTimeout:
                # Check if modal closed (could still be success)
                modal_visible = page.locator('[role="dialog"]').count() > 0
                if not modal_visible:
                    log_result(job_url, "SUCCESS", "Modal closed (assumed success)", steps_completed)
                else:
                    log_result(job_url, "FAILED", "Confirmation not detected", steps_completed)
            
            # Clean exit
            context.close()
    
    except Exception as e:
        log_result(job_url, "FAILED", str(e), steps_completed)
        sys.exit(1)


if __name__ == "__main__":
    main()
