import os
import sys
import time

# Add source directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sources.tools.searxSearch import searxSearch
from sources.browser import Browser, create_driver

def test_searx():
    print("Testing SearxNG connection...")
    searx_url = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
    print(f"Using SearxNG URL: {searx_url}")
    
    tool = searxSearch(base_url=searx_url)
    try:
        result = tool.execute(["test search query"])
        if "Error" in result or "No search results" in result:
            print(f"❌ SearxNG search failed: {result}")
        else:
            print(f"✅ SearxNG search successful! Found {len(result.splitlines())} lines of results.")
            print("First few lines:")
            print("\n".join(result.splitlines()[:5]))
    except Exception as e:
        print(f"❌ SearxNG Exception: {e}")

def test_browser():
    print("\nTesting Browser initialization...")
    try:
        # Force headless for this test to match backend environment if needed, 
        # but locally we might want to see it. 
        # However, the user said "browser view shows static browser", implying they are watching the backend's browser via the UI.
        
        driver = create_driver(headless=True, stealth_mode=False)
        browser = Browser(driver)
        print("✅ Browser initialized successfully.")
        
        print("Testing Navigation...")
        browser.go_to("https://www.google.com")
        print(f"✅ Navigated to {browser.driver.current_url}")
        
        text = browser.get_text()
        print(f"Page text length: {len(text)}")
        if len(text) > 50: # Google should have more than 50 chars even with stripping
            print("✅ Content verification passed.")
        else:
            print("❌ Content verification failed.")
            print(f"Text content: {text}")
            
        browser.close()
        print("✅ Browser closed.")
        
    except Exception as e:
        print(f"❌ Browser Exception: {e}")

if __name__ == "__main__":
    test_searx()
    test_browser()
