import os
import json
import re
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.async_api import async_playwright

# ------------------- CONFIG -------------------
JSON_KEYFILE = "n8n-workflow-project-464813-4e1032a0108d.json"
SHEET_NAME = "CGC-BGS"
START_ROW = 1
# ------------------------------------------------

EMAIL = "likepeas@gmail.com"
PASSWORD = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

async def click_grader_grade(page, grader: str, grade: str) -> bool:
    """Click the '<grader> population' button matching `grade` exactly."""
    try:
        print(f"🎯 Selecting: {grader} {grade}")
        popup = page.locator("div[data-testid='card-pops']").first
        await popup.scroll_into_view_if_needed()
        await page.wait_for_timeout(900)

        header = page.get_by_text(f"{grader} population", exact=True)
        if not await header.count():
            print(f"❌ Header '{grader} population' not found")
            return False

        wrapper = header.locator("xpath=..")
        buttons = wrapper.locator("button")

        button_count = await buttons.count()
        for i in range(button_count):
            btn = buttons.nth(i)
            grade_span = btn.locator("span").first
            text = await grade_span.text_content()
            text = text.strip() if text else ""

            if text == grade:
                await btn.scroll_into_view_if_needed()
                await btn.click(timeout=2000)
                print(f"✅ Clicked: {grader} {grade}")
                await page.wait_for_timeout(500)
                return True

        print(f"❌ Exact grade '{grade}' not found under '{grader}'.")
    except Exception as e:
        print(f"❌ Error selecting {grader} {grade}: {e}")

    return False


async def fetch_prices(page, num_sales=4):
    print("💵 Waiting for recent sales to load...")
    await page.wait_for_timeout(3000)

    prices = []
    blocks = page.locator("div.MuiTypography-body1.css-vxna0y")

    block_count = await blocks.count()
    for i in range(block_count):
        try:
            price_span = blocks.nth(i).locator("span[class*='css-16tlq5a']")
            price_text = await price_span.inner_text()
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


async def try_click_card_button(page) -> bool:
    """Try to click the card button (first match). Return True if clicked."""
    try:
        # Use a class-based selector for the button you provided
        button = page.locator("button.MuiButtonBase-root.css-1ege7gw").first
        await button.wait_for(state="visible", timeout=5000)
        await button.click()
        print("✅ Clicked card button")
        await page.wait_for_timeout(1500)
        return True
    except Exception as e:
        print(f"⚠️ Could not click card button: {e}")
        return False


async def perform_login_if_needed(page) -> bool:
    """If login flow is detected, perform login. Return True if login performed (or already logged in)."""
    try:
        # detect a log-in button
        login_btn = page.locator("button:has-text('Log in')").first
        if await login_btn.count():
            print("🔐 Login button detected — clicking it")
            await login_btn.click()
            await page.wait_for_timeout(1000)

            # find email input
            email_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input#email",
                "input[name='username']",
                "input[type='text']"
            ]
            email_input = None
            for sel in email_selectors:
                el = page.locator(sel).first
                if await el.count():
                    email_input = el
                    break

            if email_input is None:
                # fallback: any input with placeholder or name including email
                possible = page.locator("input")
                for i in range(await possible.count()):
                    inp = possible.nth(i)
                    try:
                        placeholder = (await inp.get_attribute("placeholder")) or ""
                        aria = (await inp.get_attribute("aria-label")) or ""
                        name = (await inp.get_attribute("name")) or ""
                        if "@" in placeholder or "email" in placeholder.lower() or "email" in aria.lower() or "email" in name.lower():
                            email_input = inp
                            break
                    except:
                        continue

            if email_input:
                await email_input.fill(EMAIL)
                await page.wait_for_timeout(300)
                print("✅ Filled email")
            else:
                print("❌ Could not locate email input — aborting login attempt.")
                return False

            # find password input
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input#password"
            ]
            password_input = None
            for sel in password_selectors:
                el = page.locator(sel).first
                if await el.count():
                    password_input = el
                    break

            if password_input is None:
                possible = page.locator("input")
                for i in range(await possible.count()):
                    inp = possible.nth(i)
                    try:
                        itype = (await inp.get_attribute("type")) or ""
                        name = (await inp.get_attribute("name")) or ""
                        aria = (await inp.get_attribute("aria-label")) or ""
                        if "password" in itype.lower() or "pass" in name.lower() or "password" in aria.lower():
                            password_input = inp
                            break
                    except:
                        continue

            if password_input:
                await password_input.fill(PASSWORD)
                await page.wait_for_timeout(300)
                print("✅ Filled password")
            else:
                print("❌ Could not locate password input — aborting login attempt.")
                return False

            # submit
            submitted = False
            submit_btn = page.locator(
                "button:has-text('Log in'), button:has-text('Log In'), button:has-text('Sign in'), button:has-text('Sign In'), button[type='submit']"
            ).last
            if await submit_btn.count():
                try:
                    await submit_btn.click()
                    submitted = True
                    print("➡️ Clicked submit button")
                except:
                    submitted = False

            if not submitted and password_input:
                try:
                    await password_input.press("Enter")
                    submitted = True
                    print("➡️ Pressed Enter in password field to submit")
                except:
                    submitted = False

            if submitted:
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
                await page.wait_for_timeout(2000)
                print("🔓 Login attempt completed")
                return True
            else:
                print("⚠️ Login not submitted (no submit button found).")
                return False
        else:
            # No login button found — assume either already logged in or no login needed.
            return True
    except Exception as e:
        print(f"⚠️ Error during login detection/flow: {e}")
        return False


async def process_rows_async(all_values, start_row, sheet):
    """
    all_values: result of sheet.get_all_values()
    start_row: 1-based row index where to start
    sheet: gspread sheet object to update cells
    """
    EMAIL = "likepeas@gmail.com"
    PASSWORD = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    num_rows = len(all_values)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--start-maximized"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        print(f"🚀 Processing rows {start_row}..{num_rows}")

        for row in range(start_row - 1, num_rows):  # all_values is 0-indexed
            rnum = row + 1
            try:
                row_vals = all_values[row]
                url = row_vals[5] if len(row_vals) > 5 else ""
                grader = row_vals[6] if len(row_vals) > 6 else ""
                fake_grade = row_vals[7] if len(row_vals) > 7 else ""

                if not url or not grader or not fake_grade:
                    print(f"⚠️ Skipping row {rnum}: Missing required data")
                    continue

                grade = fake_grade[:2] if len(fake_grade) > 3 else fake_grade
                print(f"\n🔁 Processing row {rnum}: {grader} {grade}")

                # Navigate to the card page
                try:
                    await page.goto(url, timeout=30000)
                except Exception as e:
                    print(f"⚠️ Navigation error for row {rnum}: {e}")
                    continue
                await page.wait_for_timeout(2000)

                # 1) Click the card button
                button = page.locator("button.MuiButtonBase-root.css-1ege7gw").first
                await button.wait_for(state="visible", timeout=5000)
                await button.click()
                print("✅ Clicked card button")
                await page.wait_for_timeout(2000)

                # 2) Click the "Log in" button
                
                await perform_login_if_needed(page)

                    # 4) Submit form
                    

                # 5) Continue with grader/grade selection
                success = await click_grader_grade(page, grader, grade)
                await page.wait_for_timeout(1000)

                if success:
                    prices = await fetch_prices(page, 4)
                    if prices:
                        avg = sum(prices) / len(prices)
                        # Write results to sheet
                        for i, price in enumerate(prices[:4]):
                            try:
                                sheet.update_cell(rnum, 12 + i, price)
                            except Exception as e:
                                print(f"⚠️ Failed to update cell for row {rnum}, col {12+i}: {e}")
                        try:
                            sheet.update_cell(rnum, 16, avg)
                            
                        except Exception as e:
                            print(f"⚠️ Failed to update avg cell for row {rnum}: {e}")
                        print(f"✅ Updated row {rnum} with prices and average.")
                    else:
                        print(f"❌ No prices found for row {rnum}.")
                else:
                    print(f"❌ Could not select grader/grade for row {rnum}.")

                await page.wait_for_timeout(1200)

            except Exception as e:
                print(f"❌ Error processing row {rnum}: {e}")
                continue

        # Close browser when done
        try:
            await browser.close()
        except:
            pass
        print("🎉 All rows processed. Browser closed.")



def run_automation():
    # Setup Google Sheets
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    all_values = sheet.get_all_values()
    num_rows = len(all_values)
    print(f"Read {num_rows} rows from sheet '{SHEET_NAME}'")

    # Run the async processing that reuses one browser and login
    asyncio.run(process_rows_async(all_values, START_ROW, sheet))


if __name__ == "__main__":
    run_automation()
