"""
Sign up a regular Hub account for the wiki screenshots (Playwright, headless).

The dashboard hard-wires demo@edamame.tech to a client-side mock workspace, so
the acme.com capture needs an ordinary email + password account. Every
confirmed Hub account is added to acme.com as a viewer by the PostConfirmation
trigger, which is all the capture needs.

Usage:
    python src/create_screenshot_account.py --email you+hubshots@example.com \
        --password '<strong password>'

The script submits the signup form, then waits for the 6-digit confirmation
code on stdin (read it in the mailbox) and confirms the account. Store the
credentials as the HUB_SCREENSHOT_ACME_EMAIL / HUB_SCREENSHOT_ACME_PASSWORD
repository secrets (gh secret set ...) -- never in git. Keep MFA off.
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

DEFAULT_BASE_URL = "https://hub.edamame.tech"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Hub screenshot account")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--code", help="Confirmation code (otherwise read from stdin)")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{base}/auth/signup", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        page.fill("input[type=email]", args.email)
        pw = page.query_selector_all("input[type=password]")
        if len(pw) < 2:
            print("ERROR: signup form not found (expected password + confirm fields)")
            return 1
        pw[0].fill(args.password)
        pw[1].fill(args.password)
        page.click("button[type=submit]")
        page.wait_for_timeout(4000)

        if not page.query_selector("[data-cy=inputPinCode]"):
            print("ERROR: confirmation step did not appear. Page text:")
            print(page.inner_text("body")[:800])
            return 1

        code = args.code or input("Confirmation code from the mailbox: ").strip()
        if len(code) != 6 or not code.isdigit():
            print("ERROR: expected a 6-digit code")
            return 1
        pins = page.query_selector_all("[data-cy=inputPinCode]")
        pins[0].click()
        page.keyboard.type(code)
        page.wait_for_timeout(1000)
        btn = page.query_selector("button[type=submit]") or page.query_selector("button:has-text('Confirm')")
        if btn:
            btn.click()
        page.wait_for_timeout(6000)
        print(f"Landed on: {page.url}")
        ok = "/dashboard" in page.url or "/auth/login" in page.url
        browser.close()
        if ok:
            print("Account confirmed. Now: gh secret set HUB_SCREENSHOT_ACME_EMAIL / HUB_SCREENSHOT_ACME_PASSWORD")
            return 0
        print("WARN: could not confirm the landing page; check the account manually.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
