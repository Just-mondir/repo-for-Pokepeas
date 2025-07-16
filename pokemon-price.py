from playwright.sync_api import sync_playwright
import re

# Click the correct grade under a specific grader (e.g., PSA 10)
def click_grader_grade(page, grader: str, grade: str):
    print(f"🎯 Selecting: {grader} {grade}")
    try:
        # Find the section header like "PSA population"
        grader_title = page.locator(f"text={grader} population").first
        wrapper = grader_title.locator("xpath=..").locator("xpath=..")
        button = wrapper.locator(f"button:has(span:text('{grade}'))").first
        button.click()
        page.wait_for_timeout(1000)
        
        
    except:
        print(f"❌ Couldn't click {grader} {grade}")

# Extract recent sale prices from the transaction section
def fetch_prices(page, num_sales=4):
    print("💵 Waiting for recent sales to load...")
      # wait to ensure filtered data appears

    print("🔍 Extracting recent eBay sale prices...")
    blocks = page.locator("div.MuiTypography-body1.css-vxna0y")
    prices = []

    for i in range(blocks.count()):
        try:
            price_span = blocks.nth(i).locator("span[class*='css-16tlq5a']")
            price_text = price_span.inner_text()
            match = re.search(r"\$([0-9\s,\.]+)", price_text)



            if match:
                price_str = match.group(1).replace(" ", "").replace("\u202f", "").replace(",", "")

                price = float(price_str)
                prices.append(price)
            if len(prices) >= num_sales:
                break
        except Exception as e:
            print(f"⚠️ Skipping sale {i+1}: {e}")

    return prices



# Full scraping pipeline
def fetch_avg_price(url, grader, grade, num_sales=4):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"🌐 Navigating to {url}")
        page.goto(url)
        page.wait_for_timeout(2000)  # wait for cards to load

        try:
            print("🖱️ Clicking on the first card image...")
            page.locator("img[data-testid^='gallery-image']").first.click()
            page.wait_for_timeout(3000)
              # give time to observe result
        except Exception as e:
            print(f"❌ Failed to click first image: {e}")
        
        # Instead of waiting for "networkidle", wait for a visible section
        

        # Click the specific grade under the selected grader
        click_grader_grade(page, grader, grade)
        page.wait_for_timeout(1000)

        # Scrape prices
        prices = fetch_prices(page, num_sales)

        if not prices:
            print("❌ No matching prices found.")
            return

        print("\n✅ Recent Prices:")
        for i, p in enumerate(prices, 1):
            print(f"• Sale {i}: ${p:.2f}")

        avg = sum(prices) / len(prices)
        print(f"\n📊 Average of {len(prices)} sales: ${avg:.2f}")

        browser.close()
        return avg

# 🔎 Run the script here
url = "https://app.alt.xyz/browse?query=Charizard%20%7C%20Base%20Set%202%20Unlimited&sortBy=newest_first"
grader = "PSA"
grade ="9"
fetch_avg_price(url, grader, grade)
