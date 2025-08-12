# royalmailcharger.py
import sys
import asyncio
import base64
from playwright.async_api import async_playwright

# Usage:
# python royalmailcharger.py "card|mm|yyyy|cvv" "email" "ovo_id" "ovo_amount"
# Note: args kept for same interface; scripts only screenshot the site.

async def main(card, email, ovo_id, ovo_amount):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto("https://send.royalmail.com/", timeout=30000)
            await page.wait_for_timeout(1000)
            img_bytes = await page.screenshot(full_page=True)
            await browser.close()
            b64 = base64.b64encode(img_bytes).decode("ascii")
            print(b64, end="")
            return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import sys
    card = sys.argv[1] if len(sys.argv) > 1 else ""
    email = sys.argv[2] if len(sys.argv) > 2 else ""
    ovo_id = sys.argv[3] if len(sys.argv) > 3 else ""
    ovo_amount = sys.argv[4] if len(sys.argv) > 4 else ""
    rc = asyncio.run(main(card, email, ovo_id, ovo_amount))
    sys.exit(rc)
