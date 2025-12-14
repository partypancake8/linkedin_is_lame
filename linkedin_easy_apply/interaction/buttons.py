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
