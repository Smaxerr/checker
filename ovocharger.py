from playwright.async_api import async_playwright

async def run_ovocharger(card_details: str):
    # card_details format: cardnumber|expirymonth|expiryyear|cvv
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto("https://ovo.example.com/charger")  # replace with real URL

            # Dummy interaction - adapt as needed
            await page.fill("#cardnumber", cardnumber)
            await page.fill("#expirymonth", expirymonth)
            await page.fill("#expiryyear", expiryyear)
            await page.fill("#cvv", cvv)
            await page.click("#submit")

            # Wait for confirmation or some element
            await page.wait_for_selector("#result", timeout=10000)

            screenshot_bytes = await page.screenshot()

            # For demo, pretend success if element found
            result = "Success"

            await browser.close()
            return result, screenshot_bytes

        except Exception as e:
            await browser.close()
            return f"Error: {e}", None
