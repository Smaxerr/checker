from playwright.async_api import async_playwright
import asyncio
import faker as faker_module
import uuid
import os


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




