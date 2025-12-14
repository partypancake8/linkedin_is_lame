"""Button interactions"""

import time


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
                
                # Check if button is disabled
                is_disabled = btn.is_disabled()
                if is_disabled:
                    print(f"  ⚠️ '{button_text}' button found but DISABLED")
                    print(f"     This usually means required fields are not filled")
                    
                    # Check for any visible error messages or required field indicators
                    error_selectors = [
                        '[role="dialog"] .artdeco-inline-feedback--error',
                        '[role="dialog"] [role="alert"]',
                        '[role="dialog"] .error-message',
                    ]
                    for err_sel in error_selectors:
                        if page.locator(err_sel).count() > 0:
                            error_text = page.locator(err_sel).first.inner_text()
                            print(f"     Error message: {error_text[:100]}")
                    
                    return False
                
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
