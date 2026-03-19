"""
Generate screenshots for EDAMAME Hub dashboard pages using Playwright.

Uses a persistent browser profile so that Cognito/Amplify auth tokens
(stored in localStorage/IndexedDB) survive across runs.

Usage:
    # First run: log in interactively and capture screenshots
    python src/generate_screenshots.py --login --domain-id YOUR_DOMAIN_ID

    # Subsequent runs: reuse saved session (headed, same profile)
    python src/generate_screenshots.py --domain-id YOUR_DOMAIN_ID

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

FEATURES_PATH = Path(__file__).parent.with_name("features.json")
PROFILE_DIR = Path(__file__).parent.with_name(".browser_profile")
DEFAULT_BASE_URL = "https://hub.edamame.tech"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.with_name("screenshots")
VIEWPORT = {"width": 1440, "height": 900}
NAV_WAIT_MS = 5000
TAB_WAIT_MS = 2000


def load_features() -> dict:
    with FEATURES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def wait_for_page_ready(page: Page, extra_ms: int = NAV_WAIT_MS):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(extra_ms)


def is_on_login_page(page: Page) -> bool:
    return "/auth/" in page.url or "login" in page.url


def is_logged_in(page: Page, base_url: str) -> bool:
    """True only when we're on the hub dashboard, not auth or OAuth redirect."""
    url = page.url
    return base_url in url and "/dashboard/" in url and "/auth/" not in url


def dismiss_overlays(page: Page):
    for selector in [
        "[aria-label='Close']",
        "button:has-text('Close')",
        "button:has-text('Dismiss')",
        ".chakra-modal__close-btn",
    ]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(500)
        except Exception:
            pass


def capture(page: Page, output_path: Path):
    dismiss_overlays(page)
    page.screenshot(path=str(output_path), full_page=True)
    print(f"    -> {output_path.name}")


def click_tab_by_text(page: Page, text: str) -> bool:
    """Click a pill-tab or button containing the given text."""
    for sel in [
        f"button:has-text('{text}')",
        f"[role='tab']:has-text('{text}')",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(TAB_WAIT_MS)
                return True
        except Exception:
            pass
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate EDAMAME Hub dashboard screenshots"
    )
    parser.add_argument("--login", action="store_true", help="Pause for manual login")
    parser.add_argument("--domain-id", required=True, help="Domain ID")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--profile-dir", type=Path, default=PROFILE_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = load_features()
    features = data.get("features", [])
    mappings = data.get("screenshot_metadata", {}).get("sub_feature_mappings", {})

    base = args.base_url.rstrip("/")
    domain_base = f"{base}/dashboard/{args.domain_id}"

    print(f"Profile: {args.profile_dir}")
    print(f"Domain:  {domain_base}")
    print(f"Output:  {args.output_dir}")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(args.profile_dir),
            headless=False,
            viewport=VIEWPORT,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Navigate to dashboard to check auth
        page.goto(f"{domain_base}/home", wait_until="domcontentloaded")
        wait_for_page_ready(page)

        if not is_logged_in(page, base) or args.login:
            print("=" * 60)
            print("Please log in to the dashboard in the browser window.")
            print("Complete the full login flow (including Google/GitHub OAuth).")
            print("Wait until you see the dashboard home page, then the script")
            print("will auto-detect and start capturing.")
            print("=" * 60)
            while not is_logged_in(page, base):
                page.wait_for_timeout(2000)
            print("Logged in! Starting capture...")
            page.goto(f"{domain_base}/home", wait_until="domcontentloaded")
            wait_for_page_ready(page)

        if not is_logged_in(page, base):
            print("ERROR: Still on login page. Auth failed.")
            context.close()
            return

        print(f"Authenticated. Current URL: {page.url}")
        print(f"Capturing {len(features)} features...\n")

        for feature in features:
            fname = feature["title"]["en"]
            print(f"[{feature['name']}] {fname}")

            for sf in feature.get("sub_features", []):
                name = sf["name"]
                path = sf.get("path", "")
                mapping = mappings.get(name, {})
                prefix = mapping.get("prefix", "00")
                filename = f"{prefix}_{name}.png"
                out = args.output_dir / filename

                if "{" in path:
                    print(f"  {name}: skipped (dynamic param: {path})")
                    continue

                if "?" in path:
                    parts = path.split("?", 1)
                    url = f"{domain_base}/{parts[0]}?{parts[1]}"
                else:
                    url = f"{domain_base}/{path}"

                print(f"  {name}: {url}")
                page.goto(url, wait_until="domcontentloaded")
                wait_for_page_ready(page)

                if is_on_login_page(page):
                    print("    WARN: Redirected to login. Session may have expired.")
                    continue

                capture(page, out)

        context.close()

    captured = list(args.output_dir.glob("*.png"))
    print(f"\nDone! {len(captured)} screenshots in {args.output_dir}")


if __name__ == "__main__":
    main()
