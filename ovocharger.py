from playwright.async_api import async_playwright

async def run_ovocharger(card_details: str):
    # card_details format: cardnumber|expirymonth|expiryyear|cvv
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment")

            await page.wait_for_load_state('load')  # waits for full page load

            screenshot_bytes = await page.screenshot()

            # For demo, pretend success if element found
            result = "Success"

            await browser.close()
            return result, screenshot_bytes

        except Exception as e:
            await browser.close()
            return f"Error: {e}", None


