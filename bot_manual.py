#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot - Manual Trigger Version with Keyboard Navigation

Uses keyboard controls (Tab + Enter) instead of clicks to avoid detection.
More human-like and reliable than automated clicking.
"""

import sys
import json
import time
import random
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# Static answer bank - known facts only, no job-specific data
ANSWER_BANK = {
    # Numeric answers
    'years_experience': '1',
    'years_of_experience': '1',
    'total_experience': '1',
    'work_experience': '1',
    'notice_period': '2',
    'notice_period_weeks': '2',
    'gpa': '3.5',
    
    # Text answers
    'linkedin_url': 'https://linkedin.com/in/yourprofile',
    'portfolio_url': 'https://yourportfolio.com',
    'github_url': 'https://github.com/yourusername',
    'website': 'https://yourwebsite.com',
    
    # Short text responses (safe, generic)
    'skills_summary': 'Strong background in software development with focus on automation and testing.',
    'why_interested': 'Interested in contributing to innovative projects and growing technical skills.',
}

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

def human_delay(min_ms=300, max_ms=800):
    """Random human-like delay"""
    import random
    delay = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay)

def keyboard_fill_input(page, selector, value, label="field"):
    """Fill input using keyboard (more human-like)"""
    try:
        element = page.locator(selector).first
        if element.count() > 0:
            # Focus element
            element.focus()
            human_delay(200, 400)
            
            # Clear existing value
            page.keyboard.press("Control+a")
            human_delay(100, 200)
            
            # Type new value with realistic delays
            page.keyboard.type(value, delay=random.randint(50, 150))
            human_delay(200, 400)
            print(f"  ✓ Filled {label}: {value}")
            return True
    except Exception as e:
        print(f"  ⚠️ Error filling {label}: {e}")
    return False

def keyboard_select_radio(page, group_name, label="radio group"):
    """Select radio button using keyboard navigation"""
    try:
        # Find all radios in the group
        radios = page.locator(f'input[type="radio"][name="{group_name}"]')
        count = radios.count()
        
        if count > 0:
            # Focus first radio
            first_radio = radios.first
            first_radio.focus()
            human_delay(300, 500)
            
            # Press Space to select (more reliable than Enter for radios)
            page.keyboard.press("Space")
            human_delay(200, 400)
            
            print(f"  ✓ Selected {label}")
            return True
    except Exception as e:
        print(f"  ⚠️ Error selecting {label}: {e}")
    return False

def keyboard_navigate_and_click_button(page, button_text, max_tabs=30):
    """Navigate to button/link using Tab and activate with Enter"""
    try:
        print(f"  Navigating to '{button_text}' using keyboard Tab navigation...")
        
        # Reset focus to body (exactly like test script)
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.evaluate('document.body.focus()')
        time.sleep(0.3)
        
        # Tab through elements to find our target
        for i in range(max_tabs):
            page.keyboard.press("Tab")
            time.sleep(0.1)  # Small delay to let focus update
            
            # Get focused element info (exactly like test script)
            focused_info = page.evaluate("""() => {
                const el = document.activeElement;
                if (!el) return null;
                return {
                    tag: el.tagName,
                    text: el.textContent?.trim().substring(0, 100),
                    type: el.type,
                    ariaLabel: el.getAttribute('aria-label'),
                    classes: el.className
                };
            }""")
            
            # Check if we found it (must check focused_info exists first)
            if focused_info and focused_info.get('text'):
                text_lower = focused_info.get('text', '').lower()
                aria_lower = (focused_info.get('ariaLabel') or '').lower()
                target_lower = button_text.lower()
                
                # Match if target text is in either the text content or aria-label
                if target_lower in text_lower or target_lower in aria_lower:
                    tag = focused_info.get('tag', '')
                    print(f"  ✓ Found '{button_text}' via Tab #{i+1}")
                    print(f"    Tag: {tag}, Text: '{focused_info.get('text')}'")
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(2)
                    return True
        
        print(f"  ⚠️ Could not find '{button_text}' after {max_tabs} tabs")
        return False
        
    except Exception as e:
        print(f"  ⚠️ Error navigating to button: {e}")
        return False

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

def detect_state(page, step_number):
    """Detect current UI state based on DOM signals - NO ACTIONS, only detection"""
    try:
        # Check for modal first (most specific)
        modal_visible = page.locator('[role="dialog"]').is_visible()
        
        if modal_visible:
            # CHECK FOR TEXT FIELDS FIRST - before button detection
            text_fields = detect_text_fields_in_modal(page)
            if len(text_fields) > 0:
                return "MODAL_TEXT_FIELD_DETECTED"
            
            # We're in the modal - check what buttons are present
            submit_selectors = [
                'button:has-text("Submit application")',
                'button[aria-label*="Submit"]',
                'button:has-text("Submit")',
            ]
            next_selectors = [
                'button:has-text("Next")',
                'button[aria-label*="Next"]',
                'button:has-text("Continue")',
            ]
            review_selectors = [
                'button:has-text("Review")',
                'button[aria-label*="Review"]',
            ]
            
            has_submit = any(page.locator(sel).count() > 0 for sel in submit_selectors)
            has_next = any(page.locator(sel).count() > 0 for sel in next_selectors)
            has_review = any(page.locator(sel).count() > 0 for sel in review_selectors)
            has_success = page.locator(':has-text("Application sent")').count() > 0
            
            if has_success:
                return "SUBMITTED"
            elif has_submit and not has_next and not has_review:
                # Submit button present, no Next/Review = single step
                return "MODAL_SINGLE_STEP"
            elif has_review:
                # Review step - typically the final review before submit
                return "MODAL_REVIEW_STEP"
            elif has_next:
                # Next button = intermediate form step
                return "MODAL_FORM_STEP"
            elif has_submit and (has_next or has_review):
                # Has submit AND navigation = multi-step final page
                return "MODAL_REVIEW_STEP"
            else:
                return "MODAL_OPEN"
        
        # Check for Easy Apply button on job page
        easy_apply_exists = page.locator('[aria-label*="Easy Apply"]').count() > 0
        if easy_apply_exists:
            return "JOB_PAGE"
        
        return "ERROR"
    except Exception as e:
        print(f"  ⚠️ State detection error: {e}")
        return "ERROR"

def activate_button_in_modal(page, button_text):
    """Focus and activate button INSIDE modal only - NO page-wide tabbing"""
    try:
        # Modal-scoped selectors only - will NEVER escape modal context
        selectors = [
            f'[role="dialog"] button:has-text("{button_text}")',
            f'[role="dialog"] button[aria-label*="{button_text}"]',
        ]
        
        for selector in selectors:
            if page.locator(selector).count() > 0:
                btn = page.locator(selector).first
                btn.focus()
                time.sleep(0.5)
                page.keyboard.press("Enter")
                time.sleep(1)
                print(f"  ✓ Activated '{button_text}' button in modal")
                return True
        
        print(f"  ⚠️ '{button_text}' button not found in modal")
        return False
    except Exception as e:
        print(f"  ⚠️ Error activating '{button_text}': {e}")
        return False

def detect_text_fields_in_modal(page):
    """Detect visible text input fields inside Easy Apply modal only"""
    try:
        # Scope detection to modal container only
        modal_selector = '[role="dialog"]'
        
        # Find all text-like inputs within the modal
        field_selectors = [
            f'{modal_selector} input[type="text"]',
            f'{modal_selector} input[type="number"]',
            f'{modal_selector} textarea',
        ]
        
        # Fields to SKIP - these are auto-fillable or optional
        skip_patterns = [
            'phone', 'mobile', 'telephone', 'cell',  # Phone fields
            'email', 'e-mail',  # Email fields
            'address', 'street', 'city', 'zip', 'postal',  # Address fields
            'linkedin', 'website', 'url', 'portfolio',  # Social/web links
        ]
        
        detected_fields = []
        
        for selector in field_selectors:
            fields = page.locator(selector)
            count = fields.count()
            
            for i in range(count):
                field = fields.nth(i)
                
                # Skip if disabled or hidden
                if not field.is_visible() or field.is_disabled():
                    continue
                
                # Skip if field already has a value (already filled)
                current_value = field.input_value()
                if current_value and current_value.strip():
                    continue
                
                # Extract metadata
                field_id = field.get_attribute('id') or ''
                field_name = field.get_attribute('name') or ''
                placeholder = field.get_attribute('placeholder') or ''
                aria_label = field.get_attribute('aria-label') or ''
                
                # Try to find associated label
                label_text = ''
                if field_id:
                    label = page.locator(f'label[for="{field_id}"]')
                    if label.count() > 0:
                        label_text = label.first.inner_text().strip()
                
                # Determine field type
                tag_name = field.evaluate('el => el.tagName').lower()
                input_type = field.get_attribute('type') if tag_name == 'input' else 'textarea'
                
                # Check if this field should be skipped
                should_skip = False
                text_to_check = f"{field_id} {field_name} {label_text} {placeholder} {aria_label}".lower()
                
                for pattern in skip_patterns:
                    if pattern in text_to_check:
                        should_skip = True
                        print(f"  ⏭️  Skipping auto-fillable field: {label_text or placeholder or field_name} (matched: {pattern})")
                        break
                
                if should_skip:
                    continue
                
                detected_fields.append({
                    'element': field,
                    'tag': tag_name,
                    'input_type': input_type,
                    'label': label_text,
                    'aria_label': aria_label,
                    'placeholder': placeholder,
                    'name': field_name,
                })
        
        return detected_fields
    
    except Exception as e:
        print(f"  ⚠️ Error detecting text fields: {e}")
        return []

def classify_field_type(field_metadata):
    """
    Classify field as NUMERIC, TEXT, or UNKNOWN based on hard rules.
    No AI, no guessing - deterministic only.
    """
    input_type = field_metadata.get('input_type', '').lower()
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine all text for keyword matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
    # RULE 1: HTML5 input type
    if input_type == 'number':
        return 'NUMERIC_FIELD'
    
    # RULE 2: Keyword patterns for numeric fields
    numeric_keywords = [
        'year', 'years', 'yrs',
        'experience',
        'month', 'months',
        'salary', 'compensation',
        'notice period', 'notice',
        'gpa',
    ]
    
    for keyword in numeric_keywords:
        if keyword in combined_text:
            return 'NUMERIC_FIELD'
    
    # RULE 3: Textarea is always text
    if field_metadata.get('tag') == 'textarea':
        return 'TEXT_FIELD'
    
    # RULE 4: If it's a text input type
    if input_type in ['text', 'tel', 'url', '']:
        return 'TEXT_FIELD'
    
    # RULE 5: Unknown
    return 'UNKNOWN_FIELD'

def resolve_field_answer(field_metadata, field_classification):
    """
    Pure function: given field metadata and classification, return answer or None.
    
    Returns:
        str: value to type into field
        None: if no confident match found
    """
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine for matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
    # Keyword → answer bank key mappings
    keyword_mappings = {
        # Numeric mappings
        ('year', 'experience'): 'years_experience',
        ('years', 'experience'): 'years_experience',
        ('work experience',): 'work_experience',
        ('total experience',): 'total_experience',
        ('notice period', 'week'): 'notice_period_weeks',
        ('notice',): 'notice_period',
        ('gpa',): 'gpa',
        
        # Text mappings
        ('linkedin', 'url'): 'linkedin_url',
        ('linkedin', 'profile'): 'linkedin_url',
        ('portfolio', 'url'): 'portfolio_url',
        ('portfolio', 'website'): 'portfolio_url',
        ('github',): 'github_url',
        ('website',): 'website',
        ('skills',): 'skills_summary',
        ('why', 'interested'): 'why_interested',
        ('why', 'want', 'work'): 'why_interested',
    }
    
    # Try to match keywords
    matched_key = None
    for keywords, bank_key in keyword_mappings.items():
        if all(kw in combined_text for kw in keywords):
            matched_key = bank_key
            break
    
    if matched_key and matched_key in ANSWER_BANK:
        answer = ANSWER_BANK[matched_key]
        
        # TYPE SAFETY CHECK
        if field_classification == 'NUMERIC_FIELD':
            # Ensure answer is numeric
            if not answer.replace('.', '').isdigit():
                print(f"  ⚠️ Warning: Numeric field matched to non-numeric answer '{matched_key}'")
                return None
        
        return answer
    
    # No confident match
    return None

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
            
            # Handle radio buttons using keyboard
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
                            # Use keyboard to select
                            keyboard_select_radio(page, name, f"radio group '{name}'")
                            
                except Exception as e:
                    print(f"  ⚠️ Error with radio button {i}: {e}")
            
            # Handle checkboxes using keyboard (only consent/agreement)
            checkboxes = page.locator('input[type="checkbox"]')
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
                                checkbox.focus()
                                human_delay(200, 400)
                                page.keyboard.press("Space")
                                human_delay(200, 400)
                                print(f"  ✓ Checked consent checkbox (keyboard)")
                except Exception as e:
                    print(f"  ⚠️ Error with checkbox: {e}")
            
            page.wait_for_timeout(500)
            
            # STATE-DRIVEN ACTIONS - no more blind button checking
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
