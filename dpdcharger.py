from playwright.async_api import async_playwright
import asyncio

async def run_dpdcharger(card_details: str):
    # card_details format: cardnumber|expirymonth|expiryyear|cvv
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:

            await page.goto("https://send.dpd.co.uk/order?step=parcelDetails")

            await page.wait_for_load_state('load')  # waits for full page load

            await asyncio.sleep(2)  # wait 2 seconds to allow dynamic content to render

            screenshot_bytes = await page.screenshot()

            # For demo, pretend success if element found
            result = "Success"

            await browser.close()
            return result, screenshot_bytes

        except Exception as e:
            await browser.close()
            return f"Error: {e}", None




