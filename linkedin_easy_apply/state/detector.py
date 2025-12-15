"""State detection logic"""

from linkedin_easy_apply.perception.text_fields import detect_text_fields_in_modal


def detect_state(page, step_number):
    """Detect current UI state based on DOM signals - NO ACTIONS, only detection

    State detection priority:
    1. Success message (application sent)
    2. Navigation buttons (Submit/Review/Next) - indicates page is ready to advance
    3. Text fields - only if no navigation buttons present (indicates incomplete page)

    This ordering prevents infinite loops where filled text fields remain in DOM
    but navigation buttons indicate the page is ready to proceed.
    """
    try:
        # Check for modal first (most specific)
        modal_visible = page.locator('[role="dialog"]').is_visible()

        if modal_visible:
            # PRIORITY 1: Check for navigation buttons FIRST
            # Navigation buttons indicate actionable state transitions
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

            has_submit = any(
                page.locator(f'[role="dialog"] {sel}').count() > 0
                for sel in submit_selectors
            )
            has_next = any(
                page.locator(f'[role="dialog"] {sel}').count() > 0
                for sel in next_selectors
            )
            has_review = any(
                page.locator(f'[role="dialog"] {sel}').count() > 0
                for sel in review_selectors
            )
            has_success = page.locator(':has-text("Application sent")').count() > 0

            # Debug: Print detected buttons
            if step_number > 1:  # Skip first step to reduce noise
                detected_buttons = []
                if has_submit:
                    detected_buttons.append("Submit")
                if has_next:
                    detected_buttons.append("Next")
                if has_review:
                    detected_buttons.append("Review")
                if detected_buttons:
                    print(
                        f"  [State Detector] Buttons found: {', '.join(detected_buttons)}"
                    )

            # Check for success message (highest priority)
            if has_success:
                return "SUBMITTED"

            # If navigation buttons are present, page is ready to advance
            # Return button-based states BEFORE checking for text fields
            # Check combined states first (Submit + Next/Review = final page)
            if has_submit and (has_next or has_review):
                # Has submit AND navigation = multi-step final page
                return "MODAL_REVIEW_STEP"
            elif has_submit and not has_next and not has_review:
                # Submit button present, no Next/Review = single step
                return "MODAL_SINGLE_STEP"
            elif has_review:
                # Review step - typically the final review before submit
                return "MODAL_REVIEW_STEP"
            elif has_next:
                # Next button only = intermediate form step
                return "MODAL_FORM_STEP"

            # PRIORITY 2: Check for text fields ONLY if no navigation buttons found
            # Text fields indicate incomplete page requiring user input
            # Note: Text fields may persist in DOM after filling, so they're lower priority
            text_fields = detect_text_fields_in_modal(page)
            if len(text_fields) > 0:
                return "MODAL_TEXT_FIELD_DETECTED"

            # No buttons or fields detected - modal is open but state unclear
            return "MODAL_OPEN"

        # Check for Easy Apply button on job page
        easy_apply_exists = page.locator('[aria-label*="Easy Apply"]').count() > 0
        if easy_apply_exists:
            return "JOB_PAGE"

        return "ERROR"
    except Exception as e:
        print(f"  ⚠️ State detection error: {e}")
        return "ERROR"
