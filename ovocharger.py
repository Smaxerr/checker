from playwright.async_api import async_playwright
import asyncio

from database import get_ovo_id, get_ovo_amount

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
            card_parts = card_details.strip().split("|")
            if len(card_parts) != 4:
                print(f"[Invalid card format]: {card_details}")
                return None, "INVALID"
    
            card_number, exp_month, exp_year, cvv = card_parts
            if len(exp_year) == 2:
                exp_year = "20" + exp_year

            # Fake details
            name = faker.name()
            address1 = faker.street_address()
            city = faker.city()
            postcode = faker.postcode()
            
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment")

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            ovo_id = await get_ovo_id(user_id)
            if not ovo_id:
                return None, "NO_OVO_ID"

            ovo_amount = await get_ovo_amount(user_id)
            if not ovo_amount:
                return None, "NO_OVO_AMOUNT"

            await page.fill('#customerid', ovo_id)
            await page.fill('#amount', ovo_amount)
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
















