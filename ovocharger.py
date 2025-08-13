from playwright.async_api import async_playwright
import asyncio

async def run_ovocharger(card_details: str):
    cardnumber, expirymonth, expiryyear, cvv = card_details.split('|')

    async with async_playwright() as p:
            user_data_dir = "/tmp/playwright-profile"
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=["--no-sandbox"]
            )
            page = await browser.new_page()

            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            await page.goto("https://ovoenergypayments.paypoint.com/GuestPayment", timeout=60000)

            # Fake details
            name = faker.name()
            address1 = faker.street_address()
            city = faker.city()
            postcode = faker.postcode()

            ovo_id = await get_ovo_id(user_id)
            if not ovo_id:
                return None, "NO_OVO_ID"

            await page.fill('#customerid', ovo_id)
            await page.fill('#amount', '1')
            await page.fill('#cardholdername', name)

            frame_element = await page.wait_for_selector('iframe[src*="hostedfields.paypoint.services"]', timeout=10000)
            frame = await frame_element.content_frame()
            await frame.fill('input[name="card_number"]', card_number)

            await page.select_option('select[name="PaymentCard.ExpiryMonth"]', exp_month)
            await page.select_option('select[name="PaymentCard.ExpiryYear"]', exp_year)
            await page.fill('input[name="PaymentCard.CVV"]', cvv)

            await page.fill('#postcode', postcode)
            await page.fill('#address1', address1)
            await page.fill('#city', city)
            await page.fill('#emailForConfirmation', 'maxxxier@yahoo.com')
            await page.fill('#mobileNumberForSmsConfirmation', '07454805800')
            await page.check('input[name="AcceptedTermsAndConditions"]')

            
            # Click the Make Payment button
            button_locator = page.locator('input#makePayment')
            # Try clicking once
            await button_locator.click(force=True, timeout=10000)
            await page.wait_for_timeout(2000)  # brief pause after click
            # Check if button still visible — retry if needed
            for attempt in range(2):  # retry up to 2 times
                if await button_locator.is_visible():
                    print(f"[Retry] Button still visible. Retrying click... (Attempt {attempt + 1})")
                    await button_locator.click(force=True)
                    await page.wait_for_timeout(2000)
                else:
                    break
            else:
                print("[Warning] Button still visible after 2 retries.")

            await page.wait_for_timeout(15000)  # brief pause after click
            
            status = "UNKNOWN"
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

            await page.screenshot(path=filename, full_page=True)
            await browser.close()
            return filename, status

    except Exception as e:
        print(f"[Screenshot Error for card {card}]: {e}")
        return None, "ERROR"


async def process_multiple_cards(cards: list[str]):
    # Create a list of tasks, each runs independently
    tasks = [run_ovocharger(card) for card in cards]

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

