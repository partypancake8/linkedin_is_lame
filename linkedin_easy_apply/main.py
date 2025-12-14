#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Main Orchestration
Modular refactor - behavior unchanged
"""

import sys
import json
import time
import random
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <job_url>")
        sys.exit(1)
    
    job_url = sys.argv[1]
    steps_completed = 0
    
    print("="*60)
    print("LinkedIn Easy Apply Bot - Manual Trigger Mode")
    print("="*60)
    print()
    
    # Launch browser
    context, page = launch_browser()
    steps_completed += 1
    
    # Navigate to job page
    print(f"Navigating to {job_url}...")
    page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    steps_completed += 1
    
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
        log_result(job_url, "FAILED", "Modal not detected after manual click", steps_completed)
        context.close()
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
        log_result(job_url, "FAILED", "No form elements found in modal", steps_completed)
        context.close()
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
                answer, confidence, matched_key = resolve_radio_question(page, group_name, question_text, option_count)
                
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
                        human_delay(300, 500)
                        page.keyboard.press("Space")
                        human_delay(200, 400)
                        
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
                                        human_delay(200, 400)
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
            print("\n⏸️  PAUSED - Unresolved radio button questions")
            print("   Press Enter to SKIP this application")
            input()
            print("\n⚠️ Skipping application")
            log_result(job_url, "SKIPPED", "Radio questions with low confidence", steps_completed)
            context.close()
            return
        
        # Handle checkboxes (simple consent boxes only)
        checkboxes = page.locator('[role="dialog"] input[type="checkbox"]')
        checkbox_count = checkboxes.count()
        
        if checkbox_count > 0:
            print(f"  Found {checkbox_count} checkbox(es)")
            for i in range(checkbox_count):
                checkbox = checkboxes.nth(i)
                try:
                    if not checkbox.is_checked():
                        # Try to get label
                        checkbox_id = checkbox.get_attribute('id')
                        label_text = ''
                        if checkbox_id:
                            label = page.locator(f'label[for="{checkbox_id}"]')
                            if label.count() > 0:
                                label_text = label.first.inner_text().strip().lower()
                        
                        # Only check boxes that look like consent/agreement
                        if any(word in label_text for word in ["agree", "consent", "terms", "acknowledge", "confirm"]):
                            checkbox.focus()
                            human_delay(200, 400)
                            page.keyboard.press("Space")
                            human_delay(200, 400)
                            print(f"  ✓ Checked consent checkbox (keyboard)")
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
                    
                    # Select option using keyboard-only approach
                    try:
                        element.focus()
                        human_delay(200, 300)
                        
                        # Attempt to open dropdown using Space (preferred)
                        page.keyboard.press("Space")
                        human_delay(300, 500)
                        
                        # Fallback: some LinkedIn dropdowns require ArrowUp to open
                        page.keyboard.press("ArrowUp")
                        human_delay(300, 500)
                        
                        # Reset to top of dropdown by pressing ArrowUp multiple times
                        # Use ArrowUp to ensure we're at the first option
                        for _ in range(option_count + 2):  # Extra presses to ensure we're at top
                            page.keyboard.press("ArrowUp")
                            human_delay(50, 100)
                        
                        # Now navigate down to target index
                        for _ in range(answer_index):
                            page.keyboard.press("ArrowDown")
                            human_delay(100, 150)
                        
                        # Press Enter to select the highlighted option
                        page.keyboard.press("Enter")
                        human_delay(400, 600)
                        
                        # Verify selection succeeded
                        new_value = element.input_value()
                        if new_value == previous_value:
                            # Keyboard selection failed - try fallback
                            print(f"    ⚠️ Keyboard selection failed, attempting fallback")
                            try:
                                element.select_option(index=answer_index)
                                human_delay(300, 500)
                                
                                # Verify fallback
                                final_value = element.input_value()
                                if final_value == previous_value:
                                    print(f"    ⚠️ Fallback also failed - pausing")
                                    select_needs_pause = True
                                else:
                                    print(f"    ✓ Fallback selection succeeded")
                            except Exception as fallback_error:
                                print(f"    ⚠️ Fallback error: {fallback_error} - pausing")
                                select_needs_pause = True
                        else:
                            print(f"    ✓ Keyboard selection succeeded")
                    except Exception as selection_error:
                        print(f"    ⚠️ Selection error: {selection_error}")
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
            print("\n⏸️  PAUSED - Unresolved select dropdown fields")
            print("   Press Enter to SKIP this application")
            input()
            print("\n⚠️ Skipping application")
            log_result(job_url, "SKIPPED", "Select fields with low confidence", steps_completed)
            context.close()
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
                    print(f"     ⚠️ No answer found - using TEST")
                    # Do NOT type TEST into numeric fields
                    if classification == 'NUMERIC_FIELD':
                        print(f"     ⚠️ Numeric field with no answer - will PAUSE")
                        value_to_type = None
                        needs_pause = True
                    else:
                        value_to_type = "TEST"
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
                print(f"\n⏸️  PAUSED - {field_count} field(s) detected, some unresolved")
                print("   Some fields could not be auto-filled")
                print("   Options:")
                print("     1. Press Enter to SKIP this application (recommended)")
                print("     2. Manually correct the fields and continue")
                print()
                
                choice = input("Press Enter to skip application: ").strip()
                
                print("\n⚠️ Skipping application - unresolved fields present")
                log_result(job_url, "SKIPPED", "Text fields with unresolved answers", steps_completed)
                context.close()
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
            print("\n⚠️  FINAL SUBMISSION CONFIRMATION")
            print("   The application is ready to be submitted.")
            print("   Type YES to submit, or NO to exit without submitting.")
            print()
            
            confirmation = input("Submit application? (YES/NO): ").strip().upper()
            
            if confirmation != "YES":
                print("\n❌ Submission cancelled by user")
                log_result(job_url, "CANCELLED", "User declined final submission", steps_completed)
                print("\nKeeping browser open for inspection...")
                input("Press Enter to close browser...")
                context.close()
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
                    log_result(job_url, "SUCCESS", "Application submitted (keyboard)", steps_completed + 1)
                else:
                    print("\n⚠️ Submit pressed but success not confirmed")
                    log_result(job_url, "SUCCESS", "Submit pressed (unconfirmed)", steps_completed + 1)
                
                print("\nKeeping browser open for inspection...")
                input("Press Enter to close browser...")
                context.close()
                return
            else:
                print("⚠️ Could not activate Submit button")
                log_result(job_url, "FAILED", "Submit button not accessible", steps_completed)
                context.close()
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
                print("⚠️ Could not activate Next button")
                log_result(job_url, "FAILED", "Next button not accessible", steps_completed)
                context.close()
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
                print("\n⚠️  FINAL SUBMISSION CONFIRMATION")
                print("   The application is ready to be submitted.")
                print("   Type YES to submit, or NO to exit without submitting.")
                print()
                
                confirmation = input("Submit application? (YES/NO): ").strip().upper()
                
                if confirmation != "YES":
                    print("\n❌ Submission cancelled by user")
                    log_result(job_url, "CANCELLED", "User declined final submission", steps_completed)
                    print("\nKeeping browser open for inspection...")
                    input("Press Enter to close browser...")
                    context.close()
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
                    log_result(job_url, "SUCCESS", "Application submitted (multi-step)", steps_completed + 1)
                else:
                    print("\n⚠️ Submit pressed but success not confirmed")
                    log_result(job_url, "SUCCESS", "Submit pressed (unconfirmed)", steps_completed + 1)
                
                print("\nKeeping browser open for inspection...")
                input("Press Enter to close browser...")
                context.close()
                return
            else:
                print("⚠️ Could not activate Review or Submit button")
                log_result(job_url, "FAILED", "Review/Submit button not accessible", steps_completed)
                context.close()
                return
        
        elif state == "SUBMITTED":
            print("\n✅ Application already submitted!")
            log_result(job_url, "SUCCESS", "Application confirmed submitted", steps_completed)
            context.close()
            return
        
        elif state == "ERROR":
            print("\n❌ Unexpected state - cannot determine next action")
            log_result(job_url, "FAILED", "Unknown state detected", steps_completed)
            print("\nKeeping browser open for inspection...")
            input("Press Enter to close browser...")
            context.close()
            return
        
        elif state == "MODAL_OPEN":
            print("  Modal open but no clear navigation buttons yet")
            # Continue to next iteration
            continue
        
        else:
            print(f"\n⚠️ Unhandled state: {state}")
            log_result(job_url, "FAILED", f"Unhandled state: {state}", steps_completed)
            context.close()
            return
    
    print("\n⚠️ Max steps reached without completion")
    log_result(job_url, "FAILED", "Max steps reached", steps_completed)
    context.close()


if __name__ == "__main__":
    main()
