"""Keyboard interactions"""

import time
import random
from linkedin_easy_apply.utils.timing import human_delay


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
        page.evaluate("document.body.focus()")
        time.sleep(0.3)

        # Tab through elements to find our target
        for i in range(max_tabs):
            page.keyboard.press("Tab")
            time.sleep(0.1)  # Small delay to let focus update

            # Get focused element info (exactly like test script)
            focused_info = page.evaluate(
                """() => {
                const el = document.activeElement;
                if (!el) return null;
                return {
                    tag: el.tagName,
                    text: el.textContent?.trim().substring(0, 100),
                    type: el.type,
                    ariaLabel: el.getAttribute('aria-label'),
                    classes: el.className
                };
            }"""
            )

            # Check if we found it (must check focused_info exists first)
            if focused_info and focused_info.get("text"):
                text_lower = focused_info.get("text", "").lower()
                aria_lower = (focused_info.get("ariaLabel") or "").lower()
                target_lower = button_text.lower()

                # Match if target text is in either the text content or aria-label
                if target_lower in text_lower or target_lower in aria_lower:
                    tag = focused_info.get("tag", "")
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
