import time
from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==== CONFIG ====
SHEET_NAME = "Copy of cert scan"        
CREDENTIAL_FILE = "n8n-workflow-project-464813-4e1032a0108d.json"
URL_COLUMN = 5   # Column E
NAME_COLUMN = 1  # Column A
GRADE_COLUMN = 8 # Column H
# ===============

def get_card_info(page):
    # Selectors based on your outerHTML
    card_name_el = page.query_selector("p.text-center.text-display5.uppercase")
    grade_el = page.query_selector("p.mt-1.text-center.text-body1.font-semibold.uppercase.text-primary")

    card_name = card_name_el.inner_text().strip() if card_name_el else "N/A"
    grade = grade_el.inner_text().strip() if grade_el else "N/A"

    return card_name, grade


def main():
    # === Google Sheets Auth ===
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    all_values = sheet.get_all_values()
    num_rows = len(all_values)

    # === Playwright Start ===
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = context.new_page()

        for row in range(2, num_rows + 1):  # skip header row
            url = sheet.cell(row, URL_COLUMN).value
            if not url:
                continue

            try:
                page.goto(url, timeout=60000)
                time.sleep(2 + (row % 3))  # small natural delay

                card_name, grade = get_card_info(page)

                sheet.update_cell(row, NAME_COLUMN, card_name)
                sheet.update_cell(row, GRADE_COLUMN, grade)

                print(f"✅ Row {row} updated: {card_name} - {grade}")

            except Exception as e:
                print(f"❌ Error at row {row}: {e}")
                continue

        browser.close()


if __name__ == "__main__":
    main()
