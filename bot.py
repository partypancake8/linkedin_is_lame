#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Minimal MVP
Single-run automation for trivial Easy Apply submissions.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration - Update these paths for your system
CHROME_USER_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
CHROME_PROFILE = "Default"  # Change if using a different Chrome profile
RESUME_PATH = os.path.expanduser("~/linkedin_is_lame/resume.pdf")  # Update to your resume location
LOG_FILE = "log.jsonl"

# Timeouts (seconds)
BUTTON_TIMEOUT = 10000  # 10 seconds
MODAL_TIMEOUT = 5000    # 5 seconds
SUBMIT_TIMEOUT = 5000   # 5 seconds


def log_result(job_url: str, status: str, failure_reason: str = None, steps_completed: int = 0):
    """Append structured log entry to JSONL file."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
            # Launch browser with persistent context (Chrome profile)
            context = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA_DIR,
                channel="chrome",
                headless=False,  # Set to True for background operation
                args=[f"--profile-directory={CHROME_PROFILE}"]
            )
            
            page = context.pages[0] if context.pages else context.new_page()
            steps_completed += 1  # Browser launched
            
            # Navigate to job URL
            print(f"Navigating to {job_url}...")
            page.goto(job_url, wait_until="domcontentloaded")
            steps_completed += 1  # Navigation complete
            
            # Step 1: Find Easy Apply button
            print("Looking for Easy Apply button...")
            try:
                easy_apply_button = page.wait_for_selector(
                    "button:has-text('Easy Apply')",
                    timeout=BUTTON_TIMEOUT
                )
            except PlaywrightTimeout:
                log_result(job_url, "SKIPPED", "Easy Apply button not found", steps_completed)
                context.close()
                return
            
            steps_completed += 1  # Button found
            
            # Step 2: Click Easy Apply button
            print("Clicking Easy Apply button...")
            easy_apply_button.click()
            
            # Step 3: Wait for modal to appear
            print("Waiting for modal...")
            try:
                modal = page.wait_for_selector(
                    '[role="dialog"], .jobs-easy-apply-modal',
                    timeout=MODAL_TIMEOUT
                )
            except PlaywrightTimeout:
                log_result(job_url, "SKIPPED", "Modal did not appear", steps_completed)
                context.close()
                return
            
            steps_completed += 1  # Modal appeared
            
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
