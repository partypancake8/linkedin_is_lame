#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Manual Trigger Version

Based on research from successful implementations, LinkedIn blocks automated
clicks on Easy Apply buttons. This version navigates to the job, pauses for
you to manually click Easy Apply, then automates the form filling.

This approach works around LinkedIn's bot detection while still saving you
time on form completion.
"""

import sys
import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

def log_result(job_url, status, reason="", steps_completed=0):
    """Log application result to JSONL file"""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_url": job_url,
        "status": status,
        "steps_completed": steps_completed,
    }
    if reason:
        result["failure_reason"] = reason
    
    with open("log.jsonl", "a") as f:
        f.write(json.dumps(result) + "\n")
    
    print(f"[{status}] {job_url}")
    if reason:
        print(f"  Reason: {reason}")

def wait_for_easy_apply_modal(page, timeout=30000):
    """Wait for Easy Apply modal to appear with comprehensive selectors"""
    print("Waiting for Easy Apply modal...")
    
    selectors = [
        'div[role="dialog"]',
        '.jobs-easy-apply-modal',
        '.artdeco-modal',
        'div.jobs-easy-apply-modal__content',
        '.artdeco-modal__content',
    ]
    
    for selector in selectors:
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout)
            print(f"  ✓ Modal detected via: {selector}")
            return True
        except:
            continue
    
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python bot_manual.py <job_url>")
        sys.exit(1)
    
    job_url = sys.argv[1]
    steps_completed = 0
    
    print("="*60)
    print("LinkedIn Easy Apply Bot - Manual Trigger Mode")
    print("="*60)
    print()
    
    with sync_playwright() as p:
        # Launch persistent browser context (reuses login session)
        print("Launching browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=site-per-process"
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        steps_completed += 1
        
        # Navigate to job page
        print(f"Navigating to {job_url}...")
        page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        steps_completed += 1
        
        print()
        print("="*60)
        print("MANUAL ACTION REQUIRED")
        print("="*60)
        print()
        print("The bot has navigated to the job page.")
        print()
        print("👆 Please click the 'Easy Apply' button manually")
        print()
        print("The bot will detect when the modal opens and continue")
        print("automatically from there.")
        print()
        print("Press Enter when you've clicked Easy Apply...")
        input()
        
        # Wait for modal to appear
        if not wait_for_easy_apply_modal(page):
            print("❌ Easy Apply modal not detected")
            log_result(job_url, "FAILED", "Modal not detected after manual click", steps_completed)
            context.close()
            return
        
        steps_completed += 1
        page.wait_for_timeout(1000)
        
        # Take screenshot of modal
        page.screenshot(path="debug_modal.png")
        print("  Screenshot saved: debug_modal.png")
        
        # Look for form elements
        print("\nAnalyzing form...")
        
        # Check for resume upload
        resume_upload = page.locator('input[type="file"]').count()
        print(f"  Resume uploads: {resume_upload}")
        
        # Check for next/submit buttons
        next_btn = page.locator('button:has-text("Next")').count()
        review_btn = page.locator('button:has-text("Review")').count()
        submit_btn = page.locator('button:has-text("Submit")').count()
        print(f"  Next buttons: {next_btn}")
        print(f"  Review buttons: {review_btn}")
        print(f"  Submit buttons: {submit_btn}")
        
        # Check for text inputs
        text_inputs = page.locator('input[type="text"], input[type="number"], textarea').count()
        print(f"  Text inputs: {text_inputs}")
        
        # Check for selects/dropdowns
        selects = page.locator('select').count()
        print(f"  Dropdowns: {selects}")
        
        # Check for radio buttons
        radios = page.locator('input[type="radio"]').count()
        print(f"  Radio buttons: {radios}")
        
        if resume_upload == 0 and next_btn == 0 and submit_btn == 0 and review_btn == 0:
            print("\n❌ No form elements detected")
            log_result(job_url, "FAILED", "No form elements found in modal", steps_completed)
            context.close()
            return
        
        print("\n✅ Form detected! Starting application process...")
        
        # Process multi-step form
        max_steps = 10
        current_step = 0
        resume_path = "/Users/sawyersmith/Documents/resume2025.pdf"
        
        while current_step < max_steps:
            current_step += 1
            print(f"\n--- Step {current_step}/{max_steps} ---")
            
            # Wait for page to stabilize
            page.wait_for_timeout(1000)
            
            # Handle resume upload if present
            resume_inputs = page.locator('input[type="file"]')
            if resume_inputs.count() > 0:
                print("  Uploading resume...")
                try:
                    resume_inputs.first.set_input_files(resume_path)
                    print("  ✓ Resume uploaded")
                    page.wait_for_timeout(500)
                except Exception as e:
                    print(f"  ⚠️ Resume upload failed: {e}")
            
            # Fill text inputs (phone, email, etc.)
            text_inputs = page.locator('input[type="text"]:visible, input[type="tel"]:visible, input[type="email"]:visible')
            for i in range(text_inputs.count()):
                try:
                    input_el = text_inputs.nth(i)
                    # Check if already filled
                    current_value = input_el.input_value()
                    if current_value and len(current_value.strip()) > 0:
                        continue
                    
                    # Try to determine what field this is
                    placeholder = input_el.get_attribute("placeholder") or ""
                    aria_label = input_el.get_attribute("aria-label") or ""
                    field_text = (placeholder + " " + aria_label).lower()
                    
                    # Skip if it looks like a custom question we can't answer
                    if any(word in field_text for word in ["year", "experience", "salary", "why", "describe"]):
                        print(f"  ⚠️ Skipping custom question field")
                        continue
                        
                except Exception as e:
                    print(f"  ⚠️ Error processing text input: {e}")
            
            # Fill number inputs with 0 (safe default for years of experience, etc.)
            number_inputs = page.locator('input[type="number"]:visible')
            for i in range(number_inputs.count()):
                try:
                    input_el = number_inputs.nth(i)
                    current_value = input_el.input_value()
                    if not current_value or current_value.strip() == "":
                        input_el.fill("0")
                        print(f"  Filled number input with: 0")
                except Exception as e:
                    print(f"  ⚠️ Error filling number input: {e}")
            
            # Handle radio buttons - select first option for each group
            radio_groups = {}
            radios = page.locator('input[type="radio"]')
            radio_count = radios.count()
            print(f"  Found {radio_count} radio buttons")
            
            for i in range(radio_count):
                try:
                    radio = radios.nth(i)
                    name = radio.get_attribute("name") or f"radio_{i}"
                    
                    if name not in radio_groups:
                        radio_groups[name] = True
                        
                        # Check if any radio in this group is already selected
                        group_radios = page.locator(f'input[type="radio"][name="{name}"]')
                        is_checked = False
                        for j in range(group_radios.count()):
                            if group_radios.nth(j).is_checked():
                                is_checked = True
                                break
                        
                        if not is_checked:
                            # Try to select first radio in group (usually "Yes")
                            first_radio = group_radios.first
                            try:
                                # Try regular click first
                                first_radio.click(timeout=1000)
                                print(f"  ✓ Selected radio in group '{name}'")
                            except:
                                # Force click if regular click fails
                                try:
                                    first_radio.click(force=True, timeout=1000)
                                    print(f"  ✓ Force-selected radio in group '{name}'")
                                except:
                                    # Try clicking the label instead
                                    radio_id = first_radio.get_attribute("id")
                                    if radio_id:
                                        label = page.locator(f'label[for="{radio_id}"]')
                                        if label.count() > 0:
                                            label.first.click()
                                            print(f"  ✓ Selected radio via label in group '{name}'")
                except Exception as e:
                    print(f"  ⚠️ Error with radio button {i}: {e}")
            
            # Handle checkboxes (be conservative - only check if label suggests agreement/consent)
            checkboxes = page.locator('input[type="checkbox"]:visible')
            for i in range(checkboxes.count()):
                try:
                    checkbox = checkboxes.nth(i)
                    if checkbox.is_checked():
                        continue
                    
                    # Look for associated label
                    checkbox_id = checkbox.get_attribute("id")
                    if checkbox_id:
                        label = page.locator(f'label[for="{checkbox_id}"]')
                        if label.count() > 0:
                            label_text = label.inner_text().lower()
                            # Only check boxes that look like consent/agreement
                            if any(word in label_text for word in ["agree", "consent", "terms", "acknowledge", "confirm"]):
                                checkbox.click()
                                print(f"  Checked consent checkbox")
                except Exception as e:
                    print(f"  ⚠️ Error with checkbox: {e}")
            
            page.wait_for_timeout(500)
            
            # Check for navigation buttons
            submit_found = page.locator('button:has-text("Submit application"):visible').count() > 0
            review_found = page.locator('button:has-text("Review"):visible').count() > 0
            next_found = page.locator('button:has-text("Next"):visible').count() > 0
            
            if submit_found:
                print("\n🎯 Found Submit button!")
                
                # Check if this is a single-step application (our target)
                if current_step == 1:
                    print("✅ Single-step application - submitting!")
                    submit_btn = page.locator('button:has-text("Submit application"):visible').first
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    
                    # Check for success indicators
                    success_indicators = [
                        'h3:has-text("Application sent")',
                        'h2:has-text("Application sent")',
                        ':has-text("Your application was sent")',
                    ]
                    
                    success = False
                    for indicator in success_indicators:
                        if page.locator(indicator).count() > 0:
                            success = True
                            break
                    
                    if success:
                        print("\n✅ APPLICATION SUBMITTED SUCCESSFULLY!")
                        log_result(job_url, "SUCCESS", "Application submitted", steps_completed + 1)
                    else:
                        print("\n⚠️ Submit clicked but success not confirmed")
                        log_result(job_url, "SUCCESS", "Submit clicked (unconfirmed)", steps_completed + 1)
                    
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    context.close()
                    return
                else:
                    print("⚠️ Multi-step application detected - skipping")
                    log_result(job_url, "SKIPPED", "Multi-step application (not single-step)", steps_completed)
                    context.close()
                    return
                    
            elif review_found:
                print("  Found Review button - clicking...")
                review_btn = page.locator('button:has-text("Review"):visible').first
                review_btn.click()
                page.wait_for_timeout(1500)
                
            elif next_found:
                print("  Found Next button - clicking...")
                next_btn = page.locator('button:has-text("Next"):visible').first
                next_btn.click()
                page.wait_for_timeout(1500)
                
            else:
                print("\n⚠️ No navigation buttons found")
                log_result(job_url, "FAILED", "No navigation buttons found", steps_completed)
                print("\nKeeping browser open for inspection...")
                input("Press Enter to close browser...")
                context.close()
                return
        
        print("\n⚠️ Max steps reached without completion")
        log_result(job_url, "FAILED", "Max steps reached", steps_completed)
        context.close()

if __name__ == "__main__":
    main()
