from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

def click_grader_grade(page, grader: str, grade: str):
    try:
        grader_title = page.locator(f"text={grader} population").first
        wrapper = grader_title.locator("xpath=..").locator("xpath=..")
        button = wrapper.locator(f"button:has(span:text('{grade}'))").first
        button.click()
        page.wait_for_timeout(1000)
    except:
        pass

def fetch_prices(page, num_sales=4):
    blocks = page.locator("div.MuiTypography-body1.css-vxna0y")
    prices = []
    for i in range(blocks.count()):
        try:
            price_span = blocks.nth(i).locator("span[class*='css-16tlq5a']")
            price_text = price_span.inner_text()
            match = re.search(r"\$([0-9\s,\.]+)", price_text)
            if match:
                price = float(match.group(1).replace(" ", "").replace("\u202f", "").replace(",", ""))
                prices.append(price)
            if len(prices) >= num_sales:
                break
        except:
            continue
    return prices

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get("url")
    grader = data.get("grader")
    grade = data.get("grade")
    num_sales = int(data.get("num_sales", 4))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(2000)
        try:
            page.locator("img[data-testid^='gallery-image']").first.click()
            page.wait_for_timeout(3000)
        except:
            pass

        click_grader_grade(page, grader, grade)
        prices = fetch_prices(page, num_sales)
        browser.close()

    if not prices:
        return jsonify({"error": "No prices found"}), 404

    avg_price = sum(prices) / len(prices)
    return jsonify({"avg_price": avg_price, "prices": prices})

app.run(host="0.0.0.0", port=8080)
