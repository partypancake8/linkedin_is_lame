"""State detection logic"""

from linkedin_easy_apply.perception.text_fields import detect_text_fields_in_modal


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
