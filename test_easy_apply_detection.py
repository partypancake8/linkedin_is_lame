#!/usr/bin/env python3
"""
Test script to locate and activate the Easy Apply button using different methods.
This helps us understand the page structure and find the most reliable approach.
"""

import asyncio
import sys
from playwright.async_api import async_playwright
from pathlib import Path

async def test_easy_apply_detection(job_url: str):
    """Test various methods to locate and activate the Easy Apply button."""
    
    browser_data = Path("./browser_data")
    
    async with async_playwright() as p:
        print("🌐 Launching browser with saved session...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(browser_data),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        print(f"\n📄 Navigating to: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)  # Give page time to render
        
        print("\n" + "="*80)
        print("METHOD 1: Direct selector search")
        print("="*80)
        
        # Method 1: Try common selectors
        selectors = [
            'button:has-text("Easy Apply")',
            'button.jobs-apply-button',
            '[aria-label*="Easy Apply"]',
            'button[data-job-id]',
            '.jobs-apply-button--top-card button',
            'button.artdeco-button--primary:has-text("Easy Apply")',
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    is_visible = await element.is_visible()
                    print(f"✅ Found with '{selector}'")
                    print(f"   Text: '{text}' | Visible: {is_visible}")
                else:
                    print(f"❌ Not found: '{selector}'")
            except Exception as e:
                print(f"❌ Error with '{selector}': {str(e)[:50]}")
        
        print("\n" + "="*80)
        print("METHOD 2: Search all buttons on page")
        print("="*80)
        
        # Method 2: Find all buttons and filter by text
        all_buttons = await page.query_selector_all('button')
        print(f"Found {len(all_buttons)} total buttons on page")
        
        easy_apply_buttons = []
        for i, btn in enumerate(all_buttons):
            try:
                text = await btn.text_content()
                if text and 'easy apply' in text.lower():
                    is_visible = await btn.is_visible()
                    classes = await btn.get_attribute('class')
                    aria_label = await btn.get_attribute('aria-label')
                    easy_apply_buttons.append({
                        'index': i,
                        'text': text.strip(),
                        'visible': is_visible,
                        'classes': classes,
                        'aria_label': aria_label
                    })
            except:
                continue
        
        print(f"\nFound {len(easy_apply_buttons)} buttons with 'Easy Apply' text:")
        for btn_info in easy_apply_buttons:
            print(f"\n  Button {btn_info['index']}:")
            print(f"    Text: '{btn_info['text']}'")
            print(f"    Visible: {btn_info['visible']}")
            print(f"    Classes: {btn_info['classes']}")
            print(f"    Aria-label: {btn_info['aria_label']}")
        
        print("\n" + "="*80)
        print("METHOD 3: Keyboard navigation (Tab search)")
        print("="*80)
        
        # Method 3: Tab through elements to find Easy Apply
        print("Starting Tab navigation search (max 50 tabs)...")
        
        # Reset focus to body
        await page.keyboard.press('Escape')
        await asyncio.sleep(0.5)
        await page.evaluate('document.body.focus()')
        
        found_via_keyboard = False
        for tab_count in range(50):
            await page.keyboard.press('Tab')
            await asyncio.sleep(0.1)  # Small delay to let focus update
            
            # Get focused element
            focused_text = await page.evaluate('''() => {
                const el = document.activeElement;
                if (!el) return null;
                return {
                    tag: el.tagName,
                    text: el.textContent?.trim().substring(0, 100),
                    type: el.type,
                    ariaLabel: el.getAttribute('aria-label'),
                    classes: el.className
                };
            }''')
            
            if focused_text and focused_text.get('text'):
                text = focused_text.get('text', '').lower()
                if 'easy apply' in text:
                    print(f"\n✅ FOUND via Tab (after {tab_count + 1} tabs)!")
                    print(f"   Tag: {focused_text.get('tag')}")
                    print(f"   Text: '{focused_text.get('text')}'")
                    print(f"   Type: {focused_text.get('type')}")
                    print(f"   Aria-label: {focused_text.get('ariaLabel')}")
                    print(f"   Classes: {focused_text.get('classes')}")
                    found_via_keyboard = True
                    
                    # Try to activate it
                    print("\n   Attempting to activate with Enter key...")
                    await asyncio.sleep(0.5)
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(2)
                    
                    # Check if modal opened
                    modal_visible = await page.is_visible('[role="dialog"]', timeout=2000)
                    print(f"   Modal opened: {modal_visible}")
                    
                    break
        
        if not found_via_keyboard:
            print(f"❌ Did not find Easy Apply after {tab_count + 1} tabs")
        
        print("\n" + "="*80)
        print("METHOD 4: Page structure analysis")
        print("="*80)
        
        # Method 4: Analyze the page structure
        structure = await page.evaluate('''() => {
            const info = {
                hasJobCard: !!document.querySelector('.jobs-details'),
                hasTopCard: !!document.querySelector('.jobs-details-top-card'),
                hasApplyButton: !!document.querySelector('.jobs-apply-button'),
                allButtonTexts: Array.from(document.querySelectorAll('button'))
                    .map(b => b.textContent?.trim())
                    .filter(t => t && t.length < 50)
                    .slice(0, 20),  // First 20 button texts
                modalPresent: !!document.querySelector('[role="dialog"]')
            };
            return info;
        }''')
        
        print(f"Job card present: {structure.get('hasJobCard')}")
        print(f"Top card present: {structure.get('hasTopCard')}")
        print(f"Apply button class present: {structure.get('hasApplyButton')}")
        print(f"Modal currently open: {structure.get('modalPresent')}")
        print(f"\nFirst 20 button texts found:")
        for idx, text in enumerate(structure.get('allButtonTexts', []), 1):
            print(f"  {idx}. '{text}'")
        
        print("\n" + "="*80)
        print("RECOMMENDATION:")
        print("="*80)
        
        if len(easy_apply_buttons) > 0:
            visible_count = sum(1 for b in easy_apply_buttons if b['visible'])
            print(f"✅ Found {len(easy_apply_buttons)} Easy Apply buttons ({visible_count} visible)")
            print(f"   Best approach: Use selector 'button:has-text(\"Easy Apply\")' and filter for visible")
        elif found_via_keyboard:
            print(f"✅ Keyboard navigation works")
            print(f"   Best approach: Tab through elements until 'Easy Apply' text is found")
        else:
            print(f"❌ Easy Apply button not detected")
            print(f"   The page may require scrolling or the job doesn't have Easy Apply")
        
        print("\n📸 Taking screenshot for manual inspection...")
        await page.screenshot(path="easy_apply_detection.png")
        print("   Saved to: easy_apply_detection.png")
        
        print("\n⏸️  Pausing for 10 seconds so you can inspect the page...")
        await asyncio.sleep(10)
        
        await context.close()
        print("\n✅ Test complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_easy_apply_detection.py <job_url>")
        sys.exit(1)
    
    job_url = sys.argv[1]
    asyncio.run(test_easy_apply_detection(job_url))
