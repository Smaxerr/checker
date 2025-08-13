from playwright.async_api import async_playwright
from database import get_ovo_id
import asyncio


from faker import Faker
faker = Faker("en_GB")

async def run_ovocharger(user_id: int, card_details: str):
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 720})

        
        try:



            # Fake details
            name = faker.name()
            address1 = faker.street_address()
            city = faker.city()
            postcode = faker.postcode()
            
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment")

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            await page.fill('#cardholdername', name)
            await page.fill('#postcode', postcode)
            await page.fill('#address1', address1)
            await page.fill('#city', city)

            screenshot_bytes = await page.screenshot(full_page=True)

            result = "Success"
            await browser.close()
            return result, screenshot_bytes

        except Exception as e:
            await browser.close()
            return f"Error: {e}", None


async def process_multiple_cards(user_id: int, cards: list[str]):
    # Create a list of tasks, each runs independently
    tasks = [run_ovocharger(user_id, card) for card in cards]

    # Run all tasks concurrently, gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# Usage example
if __name__ == "__main__":
    test_cards = [
        "1234567812345678|12|25|123",
        "8765432187654321|01|24|321",
        # more cards
    ]

    results = asyncio.run(process_multiple_cards(test_cards))
    for idx, (result, screenshot) in enumerate(results):
        print(f"Card {idx+1} result: {result}")
        # optionally save screenshots








