"""Browser session management"""

from playwright.sync_api import sync_playwright


def launch_browser():
    """
    Launch persistent browser context and return (context, page).
    Reuses login session across runs.
    """
    print("Launching browser...")
    
    p = sync_playwright().start()
    
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
    
    return context, page
