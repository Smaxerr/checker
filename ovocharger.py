# ovocharger.py
import sys
import asyncio
import base64
from playwright.async_api import async_playwright

# Usage:
# python ovocharger.py "card|mm|yyyy|cvv" "email" "ovo_id" "ovo_amount"
# On success: prints base64-encoded PNG to stdout and exits 0.
# On failure: prints error message to stderr and exits 1.

async def main(card, email, ovo_id, ovo_amount):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            # visit OVO paypoint (example)
            await page.goto("https://www.ovoenergy.com/pay-as-you-go/paypoint", timeout=30000)
            # optional: wait for main content
            await page.wait_for_timeout(1000)
            # take screenshot as bytes
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
