#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Main Orchestration
Modular refactor - behavior unchanged
"""

import sys
import json
import time
import random
import argparse
from datetime import datetime, timezone

# Local imports
from linkedin_easy_apply.browser.session import launch_browser
from linkedin_easy_apply.state.detector import detect_state
from linkedin_easy_apply.perception.text_fields import detect_text_fields_in_modal, detect_inline_validation_error
from linkedin_easy_apply.perception.radios import detect_radio_groups
from linkedin_easy_apply.perception.selects import detect_select_fields
from linkedin_easy_apply.reasoning.classify import classify_field_type
from linkedin_easy_apply.reasoning.resolve_text import resolve_field_answer
from linkedin_easy_apply.reasoning.resolve_radio import resolve_radio_question
from linkedin_easy_apply.reasoning.resolve_select import resolve_select_answer
from linkedin_easy_apply.interaction.keyboard import keyboard_navigate_and_click_button
from linkedin_easy_apply.interaction.buttons import activate_button_in_modal, wait_for_easy_apply_modal
from linkedin_easy_apply.utils.logging import log_result
from linkedin_easy_apply.utils.timing import human_delay
import linkedin_easy_apply.config as config


def format_elapsed_time(seconds):
    """Format elapsed time in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def log_with_time(start_time, *args, **kwargs):
    """Log result with elapsed time display"""
    elapsed = time.time() - start_time
    print(f"⏱️  Total time: {format_elapsed_time(elapsed)}")
    log_result(*args, **kwargs)


def finalize_job(is_batch_mode, context, status):
    """
    Helper to finalize a job in single or batch mode.
    In single-job mode: closes context and returns None
    In batch mode: keeps context open and returns status for summary
    """
    if is_batch_mode:
        return status
    else:
        context.close()
        return None


def load_job_links(file_path):
    """Load job URLs from file, one per line. Strips comments and deduplicates."""
    with open(file_path, 'r') as f:
        urls = []
        seen = set()
        for line in f:
            # Strip whitespace and ignore comments
            line = line.strip()
            if line and not line.startswith('#'):
                if line not in seen:
                    urls.append(line)
                    seen.add(line)
        return urls


def is_already_applied(page):
    """
    Pre-flight check: detect if job has already been applied to.
    
    This is a terminal state check that must run BEFORE:
    - Clicking Easy Apply
    - Modal detection
    - State machine entry
    
    Why early: Text fields persist in DOM, state detection assumes new application,
    and "already applied" is a terminal state, not a form state.
    
    Returns: (bool, str) - (is_applied, reason)
    """
    
    # 1️⃣ Check Easy Apply button state FIRST (most reliable)
    try:
        # Look for primary action button
        primary_button = page.locator('button.jobs-apply-button, button[aria-label*="Easy Apply"], button:has-text("Easy Apply")').first
        
        if primary_button.count() > 0:
            button_text = primary_button.inner_text().strip()
            
            # Exact match: button says "Applied" (not "Easy Apply")
            if button_text == "Applied":
                return (True, "button_exact_text: Applied")
            
            # Button says "View application"
            if "View application" in button_text:
                return (True, "button_text: View application")
            
            # Button is disabled AND contains "Applied"
            try:
                if primary_button.is_disabled() and "Applied" in button_text:
                    return (True, "button_disabled_applied")
            except:
                pass
    except:
        pass
    
    # 2️⃣ Check for explicit application status badges/chips
    # These are highly specific UI elements that indicate applied status
    try:
        # Look for status badges in the job card header area
        status_indicators = [
            '.jobs-unified-top-card__applicant-count:has-text("Applied")',
            '.artdeco-inline-feedback:has-text("Applied")',
            '[data-test-job-apply-state="APPLIED"]',
            '.job-card-container__footer-item:has-text("Applied")',
        ]
        
        for indicator in status_indicators:
            if page.locator(indicator).count() > 0:
                return (True, f"status_badge: {indicator}")
    except:
        pass
    
    # 3️⃣ Check for application confirmation screen
    # Only if we're on a confirmation page with NO Easy Apply button
    try:
        confirmation_texts = [
            'text="Application sent"',
            'text="Your application was sent"',
            'text="Application submitted"',
        ]
        
        for text in confirmation_texts:
            if page.locator(text).count() > 0:
                # Verify no Easy Apply button exists
                easy_apply_exists = page.locator('button:has-text("Easy Apply")').count() > 0
                if not easy_apply_exists:
                    return (True, "confirmation_screen")
        
    except:
        pass
    
    # If uncertain, proceed normally (conservative approach - never block valid applications)
    return (False, "")


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='LinkedIn Easy Apply Bot - Automated application submission',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Speed Modes:
  --speed dev       40-50%% faster (1.5x-2x speed) - balanced testing
  --speed super     70-80%% faster (3x-5x speed) - maximum safe speed
  (default)         Production speed - safest, most human-like

Batch Mode:
  --links-file FILE Process multiple job URLs from file (one per line)

Examples:
  python -m linkedin_easy_apply.main "https://linkedin.com/jobs/view/123456789/"
  python -m linkedin_easy_apply.main --speed dev "https://linkedin.com/jobs/view/123456789/"
  python -m linkedin_easy_apply.main --speed super "https://linkedin.com/jobs/view/123456789/"
  python -m linkedin_easy_apply.main --links-file jobs.txt
        """
    )
    parser.add_argument('job_url', nargs='?', help='LinkedIn job URL to apply to')
    parser.add_argument(
        '--speed',
        choices=['dev', 'super'],
        help='Speed mode: dev (1.5x-2x) or super (3x-5x)'
    )
    parser.add_argument(
        '--links-file',
        help='File containing job URLs (one per line) for batch processing'
    )
    
    args = parser.parse_args()
    
    # Validate: either job_url or --links-file must be provided
    if not args.job_url and not args.links_file:
        parser.error("Either job_url or --links-file must be provided")
    if args.job_url and args.links_file:
        parser.error("Cannot use both job_url and --links-file")
    
    # Determine batch mode and load job URLs
    is_batch_mode = args.links_file is not None
    if is_batch_mode:
        job_urls = load_job_links(args.links_file)
        print(f"📋 Batch mode: {len(job_urls)} jobs loaded from {args.links_file}\n")
    else:
        job_urls = [args.job_url]
    
    # Configure speed mode based on command-line flag
    if args.speed == 'dev':
        config.DEV_TEST_SPEED = True
        config.SUPER_DEV_SPEED = False
        print("⚡ DEV_TEST_SPEED enabled (1.5x-2x speed)\n")
    elif args.speed == 'super':
        config.DEV_TEST_SPEED = False
        config.SUPER_DEV_SPEED = True
        print("⚡⚡ SUPER_DEV_SPEED enabled (3x-5x speed)\n")
    else:
        config.DEV_TEST_SPEED = False
        config.SUPER_DEV_SPEED = False
    
    # Rebuild TIMING dict after config changes
    config.TIMING = config.get_active_timing()
    
    # Batch mode tracking
    batch_results = []
    
    # Launch browser once for all jobs
    context, page = launch_browser()
    
    # Process each job URL
    for job_index, job_url in enumerate(job_urls, 1):
        # Print batch progress header
        if is_batch_mode:
            print("\n" + "="*60)
            print(f"JOB {job_index}/{len(job_urls)}")
            print("="*60)
        
        # Start timer for this job
        start_time = time.time()
        steps_completed = 0
        
        print("="*60)
        print("LinkedIn Easy Apply Bot - Manual Trigger Mode")
        print("="*60)
        print()
        
        # Navigate to job page
        print(f"Navigating to {job_url}...")
        page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        steps_completed += 1
        
        # PRE-FLIGHT CHECK: Detect if already applied
        # This must happen BEFORE clicking Easy Apply or entering the state machine
        # because "already applied" is a terminal state, not a form state.
        already_applied, reason = is_already_applied(page)
        if already_applied:
            print(f"\n🔁 Job already applied — skipping ({reason})")
            print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
            log_result(job_url, "SKIPPED_ALREADY_APPLIED", reason, steps_completed)
            status = finalize_job(is_batch_mode, context, "SKIPPED_ALREADY_APPLIED")
            if status:
                batch_results.append(status)
                continue
            return
    
        print()
        print("="*60)
        print("EASY APPLY ACTIVATION - AUTO MODE")
        print("="*60)
        print()
        print("🤖 Bot will attempt keyboard navigation to Easy Apply...")
        print("Looking for Easy Apply button...")
        
        # Try to navigate to Easy Apply using keyboard
        success = keyboard_navigate_and_click_button(page, "Easy Apply", max_tabs=30)
        
        if success:
            print("✅ Bot successfully activated Easy Apply!")
            page.wait_for_timeout(2000)
        else:
            print("⚠️ Bot couldn't find Easy Apply via keyboard")
            print("\nPlease manually:")
            print("  1. Press Tab until Easy Apply is highlighted")
            print("  2. Press Enter")
            print()
            input("Press Enter here when modal opens...")
        
        print()
        # Wait for modal to appear
        if not wait_for_easy_apply_modal(page):
            print("❌ Easy Apply modal not detected")
            print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
            log_result(job_url, "FAILED", "Modal not detected after manual click", steps_completed)
            status = finalize_job(is_batch_mode, context, "FAILED")
            if status:
                batch_results.append(status)
                continue
            return
    
        steps_completed += 1
        page.wait_for_timeout(1000)
    
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
            print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
            log_result(job_url, "FAILED", "No form elements found in modal", steps_completed)
            status = finalize_job(is_batch_mode, context, "FAILED")
            if status:
                batch_results.append(status)
                continue
            return
    
        print("\n✅ Form detected! Starting application process...")
    
        # Process multi-step form with state machine
        max_steps = 10
        current_step = 0
        resume_path = "/Users/sawyersmith/Documents/resume2025.pdf"
        text_fields_processed = False  # Track if text fields were already processed this step
    
        while current_step < max_steps:
            current_step += 1
        
            # Wait for page to stabilize
            page.wait_for_timeout(1000)
        
            # STATE DETECTION FIRST - before any actions
            state = detect_state(page, current_step)
            print(f"\n--- Step {current_step}/{max_steps} | State: {state} ---")
        
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
        
            # Handle radio buttons with semantic resolution
            radio_groups_data = detect_radio_groups(page)
            print(f"  Found {len(radio_groups_data)} radio group(s)")
        
            radio_needs_pause = False
            for group_data in radio_groups_data:
                try:
                    group_name = group_data['name']
                    question_text = group_data['question_text']
                    option_count = group_data['option_count']
                    option_labels = group_data['option_labels']
                    group_radios = group_data['radios']
                
                    print(f"\n  Radio Group: {group_name}")
                    print(f"    Question: {question_text}")
                    print(f"    Options ({option_count}): {', '.join(option_labels)}")
                
                    # Resolve question
                    answer, confidence, matched_key = resolve_radio_question(page, group_name, question_text, option_count, option_labels)
                
                    print(f"    Matched Key: {matched_key}")
                    print(f"    Confidence: {confidence}")
                
                    if answer is not None and confidence == 'high':
                        # Determine target index based on answer type
                        if isinstance(answer, bool):
                            # Binary question: True=0 (Yes), False=1 (No)
                            target_index = 0 if answer else 1
                            print(f"    Resolved Answer: {'Yes' if answer else 'No'} (selecting option {target_index + 1})")
                        elif isinstance(answer, int):
                            # Multi-option question: answer is the index
                            target_index = answer
                            print(f"    Resolved Answer: Option {target_index + 1} (index {target_index})")
                        else:
                            # Unexpected answer type
                            print(f"    ⚠️ Unexpected answer type: {type(answer)}")
                            radio_needs_pause = True
                            continue
                    
                        # Validate index is within bounds
                        if target_index >= option_count:
                            print(f"    ⚠️ Target index {target_index} out of bounds (only {option_count} options)")
                            radio_needs_pause = True
                            continue
                    
                        target_radio = group_radios.nth(target_index)
                    
                        # Ensure radio is visible before attempting selection
                        if not target_radio.is_visible():
                            print(f"    ⚠️ Radio option {target_index + 1} is not visible")
                            radio_needs_pause = True
                            continue
                    
                        # Check if already selected
                        is_checked = target_radio.is_checked()
                        if is_checked:
                            print(f"    ℹ️ Option {target_index + 1} already selected")
                        else:
                            # Focus and select using Space
                            target_radio.focus()
                            human_delay(config.TIMING["focus_delay_min"], config.TIMING["focus_delay_max"])
                            page.keyboard.press("Space")
                            human_delay(config.TIMING["key_delay_min"], config.TIMING["key_delay_max"])
                        
                            # Verify selection worked
                            if target_radio.is_checked():
                                print(f"    ✓ Selected option {target_index + 1}")
                            else:
                                # Try fallback click on label
                                print(f"    ⚠️ Space key didn't work, trying label click")
                                try:
                                    # Find associated label and click it
                                    radio_id = target_radio.get_attribute('id')
                                    if radio_id:
                                        label = page.locator(f'[role="dialog"] label[for="{radio_id}"]')
                                        if label.count() > 0:
                                            label.first.click()
                                            human_delay(config.TIMING["key_delay_min"], config.TIMING["key_delay_max"])
                                            if target_radio.is_checked():
                                                print(f"    ✓ Label click succeeded")
                                            else:
                                                print(f"    ⚠️ Label click failed")
                                                radio_needs_pause = True
                                        else:
                                            print(f"    ⚠️ No label found for radio")
                                            radio_needs_pause = True
                                    else:
                                        print(f"    ⚠️ Radio has no id attribute")
                                        radio_needs_pause = True
                                except Exception as click_error:
                                    print(f"    ⚠️ Label click error: {click_error}")
                                    radio_needs_pause = True
                    
                        # Log to file
                        log_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "job_url": job_url,
                            "state": "RADIO_RESOLUTION",
                            "group_name": group_name,
                            "question": question_text,
                            "matched_key": matched_key,
                            "answer": answer,
                            "selected_option": option_labels[target_index] if target_index < len(option_labels) else f"Option {target_index + 1}",
                            "confidence": confidence,
                        }
                        with open("log.jsonl", "a") as f:
                            f.write(json.dumps(log_entry) + "\n")
                    else:
                        # Low confidence - pause
                        print(f"    ⚠️ Low confidence - cannot resolve question")
                        radio_needs_pause = True
                    
                        # Log unresolved radio
                        log_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "job_url": job_url,
                            "state": "RADIO_UNRESOLVED",
                            "group_name": group_name,
                            "question": question_text,
                            "option_count": option_count,
                            "confidence": confidence,
                            "reason": matched_key,
                        }
                        with open("log.jsonl", "a") as f:
                            f.write(json.dumps(log_entry) + "\n")
                        
                except Exception as e:
                    print(f"  ⚠️ Error with radio group: {e}")
                    radio_needs_pause = True
        
            if radio_needs_pause:
                elapsed = time.time() - start_time
                print("\n⏸️  PAUSED - Unresolved radio button questions")
                print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                print("   Press Enter to SKIP this application")
                input()
            
                print("\n⚠️ Skipping application")
                print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                log_result(job_url, "SKIPPED", "Radio questions with low confidence", steps_completed)
                status = finalize_job(is_batch_mode, context, "SKIPPED")
                if status:
                    batch_results.append(status)
                    continue
                return
        
            # Handle checkboxes (simple consent boxes only)
            checkboxes = page.locator('[role="dialog"] input[type="checkbox"]')
            checkbox_count = checkboxes.count()
        
            if checkbox_count > 0:
                print(f"  Found {checkbox_count} checkbox(es)")
                for i in range(checkbox_count):
                    checkbox = checkboxes.nth(i)
                    try:
                        is_already_checked = checkbox.is_checked()
                    
                        # Try to get label
                        checkbox_id = checkbox.get_attribute('id')
                        label_text = ''
                        if checkbox_id:
                            label = page.locator(f'label[for="{checkbox_id}"]')
                            if label.count() > 0:
                                label_text = label.first.inner_text().strip()
                    
                        print(f"    Checkbox {i+1}: {'[✓]' if is_already_checked else '[ ]'} {label_text[:60] if label_text else 'no label'}")
                    
                        if not is_already_checked:
                            label_lower = label_text.lower()
                        
                            # Categorize checkbox
                            is_consent = any(word in label_lower for word in ["agree", "consent", "terms", "acknowledge", "confirm"])
                            is_communication = any(word in label_lower for word in ["email", "communication", "updates", "marketing", "newsletter", "inform", "receive"])
                        
                            # Check if it's marked as required
                            is_required = False
                            if checkbox_id:
                                # Check if the fieldset or label has "required" indicator
                                required_marker = page.locator(f'label[for="{checkbox_id}"] :has-text("*")').count() > 0
                                aria_required = checkbox.get_attribute('aria-required') == 'true'
                                is_required = required_marker or "required" in label_lower or aria_required
                        
                            if is_consent or is_required:
                                # Always check consent and required checkboxes
                                checkbox.focus()
                                human_delay(config.TIMING["focus_delay_min"], config.TIMING["focus_delay_max"])
                                page.keyboard.press("Space")
                                human_delay(config.TIMING["key_delay_min"], config.TIMING["key_delay_max"])
                                print(f"      → Checked (consent/required)")
                            elif is_communication:
                                # Leave marketing/communication checkboxes UNCHECKED (opt-out by default)
                                print(f"      → Skipped (marketing/communication)")
                            else:
                                # Unknown checkbox - CHECK IT to avoid blocking submission
                                # Most unknown checkboxes are required for form submission
                                print(f"      → Checking (unknown - assuming required to avoid blocking)")
                                checkbox.focus()
                                human_delay(config.TIMING["focus_delay_min"], config.TIMING["focus_delay_max"])
                                page.keyboard.press("Space")
                                human_delay(config.TIMING["key_delay_min"], config.TIMING["key_delay_max"])
                    except Exception as e:
                        print(f"  ⚠️ Error with checkbox: {e}")
        
            # Handle select dropdowns with semantic resolution
            select_fields = detect_select_fields(page)
            print(f"  Found {len(select_fields)} select dropdown(s)")
        
            select_needs_pause = False
            for idx, select_data in enumerate(select_fields, 1):
                try:
                    label = select_data['label']
                    option_count = select_data['option_count']
                    option_texts = select_data['option_texts']
                    option_values = select_data['option_values']
                    current_value = select_data['current_value']
                    element = select_data['element']
                
                    print(f"\n  Select Field {idx}: {label}")
                    print(f"    Options ({option_count}): {', '.join(option_texts[:5])}{'...' if option_count > 5 else ''}")
                    print(f"    Current Value: {current_value}")
                
                    # Resolve answer (returns index, not value)
                    answer_index, confidence, matched_key = resolve_select_answer(select_data)
                
                    print(f"    Matched Key: {matched_key}")
                    print(f"    Confidence: {confidence}")
                
                    # Confidence requirements:
                    # - Self-ID fields: Allow medium OR high (safe "Decline" fallback)
                    # - Start date/notice period: Require high only (discrete time matching)
                    # - All others: Must be high
                    allow_medium_confidence = {'gender', 'race', 'veteran_status', 'disability_status'}
                    can_proceed = (
                        answer_index is not None and
                        (confidence == 'high' or (confidence == 'medium' and matched_key in allow_medium_confidence))
                    )
                
                    if can_proceed:
                        print(f"    Resolved Answer: Index {answer_index}")
                    
                        # Capture value before selection
                        previous_value = element.input_value()
                        target_option_text = option_texts[answer_index] if answer_index < len(option_texts) else None
                        target_option_value = option_values[answer_index] if answer_index < len(option_values) else None
                    
                        print(f"    Target: '{target_option_text}' (value: {target_option_value})")
                    
                        # Multi-strategy interaction ladder (stop on first success)
                        selection_succeeded = False
                        strategy_used = None
                    
                        # STRATEGY 1: Native <select> element - direct value assignment
                        if not selection_succeeded:
                            try:
                                print(f"    Attempting Strategy 1: Native select.value assignment")
                                # For native <select>, set the value directly
                                if target_option_value:
                                    element.evaluate(f"""(el) => {{
                                        el.value = '{target_option_value}';
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    }}""")
                                    human_delay(config.TIMING["dropdown_open_min"], config.TIMING["dropdown_open_max"])
                                
                                    # Verify selection - check if current value matches target
                                    new_value = element.input_value()
                                    if new_value == target_option_value:
                                        selection_succeeded = True
                                        strategy_used = "native_value_assignment"
                                        print(f"    ✓ Strategy 1 succeeded (value: {new_value})")
                                    else:
                                        print(f"    ✗ Strategy 1 failed (expected: {target_option_value}, got: {new_value})")
                            except Exception as e:
                                print(f"    ✗ Strategy 1 error: {e}")
                    
                        # STRATEGY 2: Playwright's select_option method
                        if not selection_succeeded:
                            try:
                                print(f"    Attempting Strategy 2: Playwright select_option by index")
                                element.select_option(index=answer_index)
                                human_delay(config.TIMING["dropdown_open_min"], config.TIMING["dropdown_open_max"])
                            
                                # Verify selection - check if value changed from previous
                                new_value = element.input_value()
                                # Success if either: value matches target OR value changed from empty/previous
                                if new_value == target_option_value or (new_value != previous_value and new_value):
                                    selection_succeeded = True
                                    strategy_used = "playwright_select_option"
                                    print(f"    ✓ Strategy 2 succeeded (value: {new_value})")
                                else:
                                    print(f"    ✗ Strategy 2 failed (value unchanged: {new_value})")
                            except Exception as e:
                                print(f"    ✗ Strategy 2 error: {e}")
                    
                        # STRATEGY 3: Keyboard navigation (existing approach)
                        if not selection_succeeded:
                            try:
                                print(f"    Attempting Strategy 3: Keyboard navigation")
                                element.focus()
                                human_delay(config.TIMING["dropdown_verify_min"], config.TIMING["dropdown_verify_max"])
                            
                                # Attempt to open dropdown using Space
                                page.keyboard.press("Space")
                                human_delay(config.TIMING["dropdown_open_min"], config.TIMING["dropdown_open_max"])
                            
                                # Fallback: some dropdowns require ArrowUp to open
                                page.keyboard.press("ArrowUp")
                                human_delay(config.TIMING["dropdown_open_min"], config.TIMING["dropdown_open_max"])
                            
                                # Reset to top by pressing ArrowUp multiple times
                                for _ in range(option_count + 2):
                                    page.keyboard.press("ArrowUp")
                                    human_delay(config.TIMING["dropdown_nav_min"], config.TIMING["dropdown_nav_max"])
                            
                                # Navigate down to target index
                                for _ in range(answer_index):
                                    page.keyboard.press("ArrowDown")
                                    human_delay(config.TIMING["dropdown_verify_min"], config.TIMING["dropdown_verify_max"])
                            
                                # Press Enter to select
                                page.keyboard.press("Enter")
                                human_delay(config.TIMING["dropdown_close_min"], config.TIMING["dropdown_close_max"])
                            
                                # Verify selection - check if value changed from previous
                                new_value = element.input_value()
                                # Success if either: value matches target OR value changed from empty/previous
                                if new_value == target_option_value or (new_value != previous_value and new_value):
                                    selection_succeeded = True
                                    strategy_used = "keyboard_navigation"
                                    print(f"    ✓ Strategy 3 succeeded (value: {new_value})")
                                else:
                                    print(f"    ✗ Strategy 3 failed (value unchanged: {new_value})")
                            except Exception as e:
                                print(f"    ✗ Strategy 3 error: {e}")
                    
                        # STRATEGY 4: Custom/ARIA dropdown - click-based interaction
                        if not selection_succeeded and target_option_text:
                            try:
                                print(f"    Attempting Strategy 4: Click-based ARIA dropdown")
                                # Click the select element to open dropdown
                                element.click()
                                human_delay(config.TIMING["dropdown_open_min"], config.TIMING["dropdown_open_max"])
                            
                                # Try to find and click the option by visible text
                                # Look for option within modal dialog
                                option_selector = f'[role="dialog"] [role="option"]:has-text("{target_option_text}")'
                                option_locator = page.locator(option_selector).first
                            
                                if option_locator.count() > 0:
                                    option_locator.click()
                                    human_delay(config.TIMING["dropdown_close_min"], config.TIMING["dropdown_close_max"])
                                
                                    # Verify selection - check if value changed from previous
                                    new_value = element.input_value()
                                    # Success if either: value matches target OR value changed from empty/previous
                                    if new_value == target_option_value or (new_value != previous_value and new_value):
                                        selection_succeeded = True
                                        strategy_used = "aria_click_option"
                                        print(f"    ✓ Strategy 4 succeeded (value: {new_value})")
                                    else:
                                        print(f"    ✗ Strategy 4 failed (value unchanged: {new_value})")
                                else:
                                    print(f"    ✗ Strategy 4 failed (option not found)")
                            except Exception as e:
                                print(f"    ✗ Strategy 4 error: {e}")
                    
                        # Evaluate final result
                        if selection_succeeded:
                            print(f"    ✓ Selection succeeded using: {strategy_used}")
                        else:
                            print(f"    ⚠️ All selection strategies failed - pausing")
                            select_needs_pause = True
                    
                        # Log to file
                        log_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "job_url": job_url,
                            "state": "SELECT_RESOLUTION",
                            "label": label,
                            "matched_key": matched_key,
                            "selected_index": answer_index,
                            "confidence": confidence,
                            "selection_succeeded": selection_succeeded,
                            "strategy_used": strategy_used if selection_succeeded else "all_failed",
                        }
                        with open("log.jsonl", "a") as f:
                            f.write(json.dumps(log_entry) + "\n")
                    else:
                        # Low/medium confidence - pause with specific reason
                        if confidence == 'medium' and matched_key not in allow_medium_confidence:
                            print(f"    ⚠️ Medium confidence requires manual verification")
                        elif matched_key == 'unsupported_dropdown_type':
                            print(f"    ⚠️ Dropdown type not eligible for auto-selection (only EEO/self-ID fields allowed)")
                        else:
                            print(f"    ⚠️ Low confidence - cannot resolve dropdown")
                        select_needs_pause = True
                    
                        # Log unresolved select
                        log_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "job_url": job_url,
                            "state": "SELECT_UNRESOLVED",
                            "label": label,
                            "option_count": option_count,
                            "confidence": confidence,
                            "reason": matched_key,
                        }
                        with open("log.jsonl", "a") as f:
                            f.write(json.dumps(log_entry) + "\n")
                        
                except Exception as e:
                    print(f"  ⚠️ Error with select field: {e}")
                    select_needs_pause = True
        
            if select_needs_pause:
                elapsed = time.time() - start_time
                print("\n⏸️  PAUSED - Unresolved select dropdown fields")
                print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                print("   Press Enter to SKIP this application")
                input()
            
                print("\n⚠️ Skipping application")
                print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                log_result(job_url, "SKIPPED", "Select fields with low confidence", steps_completed)
                status = finalize_job(is_batch_mode, context, "SKIPPED")
                if status:
                    batch_results.append(status)
                    continue
                return
        
            # STATE HANDLERS
            if state == "MODAL_TEXT_FIELD_DETECTED":
                # Only process text fields once per step
                if text_fields_processed:
                    print("\n⏭️  Text fields already processed this step, checking for navigation buttons...")
                    # Skip to button detection by continuing loop
                    continue
            
                print("\n📝 Text field(s) detected in modal")
            
                # Detect fields again to get metadata
                text_fields = detect_text_fields_in_modal(page)
                field_count = len(text_fields)
            
                print(f"   Found {field_count} text input field(s) requiring input")
            
                # Process ALL text fields with semantic resolution
                for idx, field in enumerate(text_fields, 1):
                    field_info = {
                        'tag': field.get('tag', 'input'),
                        'input_type': field.get('input_type', 'text'),
                        'label': field['label'],
                        'aria_label': field['aria_label'],
                        'placeholder': field['placeholder'],
                        'name': field['name'],
                    }
                
                    print(f"\n   Field {idx}/{field_count}:")
                    print(f"     Tag: {field_info['tag']}")
                    print(f"     Input Type: {field_info['input_type']}")
                    print(f"     Label: {field_info['label']}")
                    print(f"     Placeholder: {field_info['placeholder']}")
                
                    # CLASSIFY FIELD
                    classification = classify_field_type(field_info)
                    print(f"     Classification: {classification}")
                
                    # RESOLVE ANSWER
                    resolved_value = resolve_field_answer(field_info, classification)
                
                    if resolved_value:
                        print(f"     Resolved Answer: '{resolved_value}'")
                        value_to_type = resolved_value
                        needs_pause = False
                    else:
                        # No answer found - PAUSE/SKIP behavior (NO "TEST" fallback)
                        # Tier-1/Tier-2 fields should never reach here (always resolve or fail)
                        # Generic TEXT_FIELD, NUMERIC_FIELD without matches will pause
                        print(f"     ⚠️ No answer found - will PAUSE")
                        value_to_type = None
                        needs_pause = True
                
                    # TYPE VALUE if we have one
                    if value_to_type:
                        print(f"     Typing '{value_to_type}'...")
                        try:
                            field['element'].focus()
                            time.sleep(0.3)
                            page.keyboard.press("Control+a")
                            time.sleep(0.1)
                            page.keyboard.type(value_to_type, delay=random.randint(50, 150))
                            time.sleep(0.3)
                            print(f"     ✓ Typed '{value_to_type}'")
                        
                            # Check for inline validation errors after typing
                            time.sleep(0.5)  # Give validation time to trigger
                            has_error, error_text = detect_inline_validation_error(page, field['element'])
                        
                            if has_error:
                                print(f"     ❌ Validation error detected: {error_text}")
                                needs_pause = True
                            
                                # Log validation error
                                validation_log = {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "job_url": job_url,
                                    "state": "VALIDATION_ERROR",
                                    "field_label": field_info['label'],
                                    "field_type": field_info['input_type'],
                                    "typed_value": value_to_type,
                                    "error_text": error_text,
                                }
                                with open("log.jsonl", "a") as f:
                                    f.write(json.dumps(validation_log) + "\n")
                        
                        except Exception as e:
                            print(f"     ⚠️ Error typing: {e}")
                            needs_pause = True
                
                    # Track for logging
                    field['classification'] = classification
                    field['resolved_value'] = resolved_value
                    field['typed_value'] = value_to_type
                    field['needs_pause'] = needs_pause
            
                # Check if ANY field needs pause
                any_unresolved = any(f.get('needs_pause', False) for f in text_fields)
            
                # Log to file with enhanced metadata
                log_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "job_url": job_url,
                    "state": "MODAL_TEXT_FIELD_DETECTED",
                    "action": "FIELD_RESOLUTION_ATTEMPTED",
                    "field_count": field_count,
                    "fields": [
                        {
                            "label": f['label'],
                            "placeholder": f['placeholder'],
                            "type": f.get('input_type', 'unknown'),
                            "classification": f.get('classification', 'UNKNOWN'),
                            "resolved_answer": f.get('resolved_value'),
                            "typed_value": f.get('typed_value'),
                            "needs_pause": f.get('needs_pause', False),
                        }
                        for f in text_fields
                    ]
                }
                with open("log.jsonl", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            
                if any_unresolved:
                    # PAUSE FOR HUMAN INSPECTION
                    elapsed = time.time() - start_time
                    print(f"\n⏸️  PAUSED - {field_count} field(s) detected, some unresolved")
                    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                    print("   Some fields could not be auto-filled")
                    print("   Options:")
                    print("     1. Press Enter to SKIP this application (recommended)")
                    print("     2. Manually correct the fields and continue")
                    print()
                
                    choice = input("Press Enter to skip application: ").strip()
                
                    print("\n⚠️ Skipping application - unresolved fields present")
                    print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                    log_result(job_url, "SKIPPED", "Text fields with unresolved answers", steps_completed)
                    status = finalize_job(is_batch_mode, context, "SKIPPED")
                    if status:
                        batch_results.append(status)
                        continue
                    return
                else:
                    # ALL FIELDS RESOLVED - continue to next step
                    print(f"\n✅ All {field_count} field(s) resolved automatically")
                    print("   Continuing to next step...")
                    text_fields_processed = True  # Mark as processed
                    # Don't return - let the loop continue to detect Submit/Next buttons
        
            elif state == "MODAL_SINGLE_STEP":
                print("\n🎯 Single-step application detected!")
                print("✅ This is our target - ready to submit via keyboard!")
            
                # MANUAL CONFIRMATION REQUIRED
                elapsed = time.time() - start_time
                print("\n⚠️  FINAL SUBMISSION CONFIRMATION")
                print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                print("   The application is ready to be submitted.")
                print("   Type YES to submit, or NO to exit without submitting.")
                print()
            
                confirmation = input("Submit application? (Y/N): ").strip().upper()
            
                if confirmation not in ["Y", "YES"]:
                    print("\n❌ Submission cancelled by user")
                    print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                    log_result(job_url, "CANCELLED", "User declined final submission", steps_completed)
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "CANCELLED")
                    if status:
                        batch_results.append(status)
                        continue
                    return
            
                print("\n✅ User confirmed - proceeding with submission...")
            
                # Activate submit button using modal-scoped method
                if activate_button_in_modal(page, "Submit"):
                    page.wait_for_timeout(3000)
                
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
                        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                        log_result(job_url, "SUCCESS", "Application submitted (keyboard)", steps_completed + 1)
                    else:
                        print("\n⚠️ Submit pressed but success not confirmed")
                        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                        log_result(job_url, "SUCCESS", "Submit pressed (unconfirmed)", steps_completed + 1)
                
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "SUCCESS")
                    if status:
                        batch_results.append(status)
                        continue
                    return
                else:
                    elapsed = time.time() - start_time
                    print("\n⏸️  PAUSED - Submit button not accessible")
                    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                    print("   The Submit button may be disabled or not found")
                    print("   Press Enter to skip or manually investigate")
                    print()
                
                    input("Press Enter to skip application: ")
                
                    print("\n⚠️ Skipping application - Submit button not accessible")
                    print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                    log_result(job_url, "SKIPPED", "Submit button not accessible", steps_completed)
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "SKIPPED")
                    if status:
                        batch_results.append(status)
                        continue
                    return
        
            elif state == "MODAL_FORM_STEP":
                print("\n📝 Multi-step form detected - intermediate step with Next button")
                print("   Proceeding to next step...")
            
                # Activate Next button using modal-scoped method
                if activate_button_in_modal(page, "Next"):
                    page.wait_for_timeout(2000)
                    text_fields_processed = False  # Reset for next step
                    # Continue to next iteration
                    continue
                else:
                    # Next button not clickable (likely disabled due to validation)
                    elapsed = time.time() - start_time
                    print("\n⏸️  PAUSED - Next button not accessible")
                    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                    print("   The Next button may be disabled due to:")
                    print("     - Required field not filled")
                    print("     - Required checkbox not checked")
                    print("     - Validation error")
                    print()
                    print("   Options:")
                    print("     1. Press Enter to SKIP this application")
                    print("     2. Manually fix the issue and continue")
                    print()
                
                    input("Press Enter to skip application: ")
                
                    print("\n⚠️ Skipping application - Next button not accessible")
                    print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                    log_result(job_url, "SKIPPED", "Next button not accessible", steps_completed)
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "SKIPPED")
                    if status:
                        batch_results.append(status)
                        continue
                    return
        
            elif state == "MODAL_REVIEW_STEP":
                print("\n📋 Review step detected - final review before submission")
                print("   Moving to review...")
            
                # Try Review button first, then Submit
                if activate_button_in_modal(page, "Review"):
                    page.wait_for_timeout(2000)
                    continue
                elif page.locator('[role="dialog"] button:has-text("Submit")').count() > 0:
                    # MANUAL CONFIRMATION REQUIRED before final submit
                    elapsed = time.time() - start_time
                    print("\n⚠️  FINAL SUBMISSION CONFIRMATION")
                    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                    print("   The application is ready to be submitted.")
                    print("   Type YES to submit, or NO to exit without submitting.")
                    print()
                
                    confirmation = input("Submit application? (Y/N): ").strip().upper()
                
                    if confirmation not in ["Y", "YES"]:
                        print("\n❌ Submission cancelled by user")
                        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                        log_result(job_url, "CANCELLED", "User declined final submission", steps_completed)
                        print("\nKeeping browser open for inspection...")
                        input("Press Enter to close browser...")
                        status = finalize_job(is_batch_mode, context, "CANCELLED")
                        if status:
                            batch_results.append(status)
                            continue
                        return
                
                    print("\n✅ User confirmed - proceeding with submission...")
                
                    if activate_button_in_modal(page, "Submit"):
                        page.wait_for_timeout(3000)
                
                    # Check for success
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
                        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                        log_result(job_url, "SUCCESS", "Application submitted (multi-step)", steps_completed + 1)
                    else:
                        print("\n⚠️ Submit pressed but success not confirmed")
                        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                        log_result(job_url, "SUCCESS", "Submit pressed (unconfirmed)", steps_completed + 1)
                
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "SUCCESS")
                    if status:
                        batch_results.append(status)
                        continue
                    return
                else:
                    elapsed = time.time() - start_time
                    print("\n⏸️  PAUSED - Review/Submit button not accessible")
                    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
                    print("   Could not find or activate Review or Submit button")
                    print("   Press Enter to skip or manually investigate")
                    print()
                
                    input("Press Enter to skip application: ")
                
                    print("\n⚠️ Skipping application - Review/Submit button not accessible")
                    print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                    log_result(job_url, "SKIPPED", "Review/Submit button not accessible", steps_completed)
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    status = finalize_job(is_batch_mode, context, "SKIPPED")
                    if status:
                        batch_results.append(status)
                        continue
                    return
        
            elif state == "SUBMITTED":
                print("\n✅ Application already submitted!")
                print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                log_result(job_url, "SUCCESS", "Application confirmed submitted", steps_completed)
                status = finalize_job(is_batch_mode, context, "SUCCESS")
                if status:
                    batch_results.append(status)
                    continue
                return
        
            elif state == "ERROR":
                print("\n❌ Unexpected state - cannot determine next action")
                print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                log_result(job_url, "FAILED", "Unknown state detected", steps_completed)
                print("\nKeeping browser open for inspection...")
                input("Press Enter to close browser...")
                status = finalize_job(is_batch_mode, context, "FAILED")
                if status:
                    batch_results.append(status)
                    continue
                return
        
            elif state == "MODAL_OPEN":
                print("  Modal open but no clear navigation buttons yet")
                # Continue to next iteration
                continue
        
            else:
                print(f"\n⚠️ Unhandled state: {state}")
                print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
                log_result(job_url, "FAILED", f"Unhandled state: {state}", steps_completed)
                status = finalize_job(is_batch_mode, context, "FAILED")
                if status:
                    batch_results.append(status)
                    continue
                return
    
        print("\n⚠️ Max steps reached without completion")
        print(f"⏱️  Total time: {format_elapsed_time(time.time() - start_time)}")
        log_result(job_url, "FAILED", "Max steps reached", steps_completed)
        status = finalize_job(is_batch_mode, context, "FAILED")
        if status:
            batch_results.append(status)
    
    # Batch mode summary
    if is_batch_mode:
        print("\n" + "="*60)
        print("BATCH COMPLETE")
        print("="*60)
        
        # Count results
        from collections import Counter
        counts = Counter(batch_results)
        
        print(f"\nProcessed {len(job_urls)} jobs:")
        for status in ["SUCCESS", "SKIPPED", "SKIPPED_ALREADY_APPLIED", "CANCELLED", "FAILED"]:
            if counts[status] > 0:
                print(f"  {status}: {counts[status]}")
        
        print("\nClosing browser...")
        context.close()


if __name__ == "__main__":
    main()
