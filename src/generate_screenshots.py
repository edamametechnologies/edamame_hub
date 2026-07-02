"""
Generate screenshots for EDAMAME Hub dashboard pages using Playwright.

Uses a persistent browser profile so that Cognito/Amplify auth tokens
(stored in localStorage/IndexedDB) survive across runs.

The domain UUID is auto-detected from the dashboard redirect after login
(the app lands on /dashboard and redirects to /dashboard/<uuid>/home), so you
normally don't pass it. Use --domain-id only to override the auto-detection.

Usage:
    # First run: log in interactively, then capture (domain auto-detected)
    python src/generate_screenshots.py --login

    # Subsequent runs: reuse saved session (same profile)
    python src/generate_screenshots.py

    # Optional: force a specific domain UUID instead of auto-detecting
    python src/generate_screenshots.py --domain-id <uuid>

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

FEATURES_PATH = Path(__file__).parent.with_name("features.json")
PROFILE_DIR = Path(__file__).parent.with_name(".browser_profile")
ENV_FILE = Path(__file__).parent.with_name(".screenshot.env")
DEFAULT_BASE_URL = "https://hub.edamame.tech"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.with_name("screenshots")
VIEWPORT = {"width": 1440, "height": 900}
NAV_WAIT_MS = 5000
TAB_WAIT_MS = 2000
LOGIN_POLL_MS = 2000
LOGIN_TIMEOUT_MS = 600_000


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


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


def login_with_password(page: Page, base_url: str, email: str, password: str) -> bool:
    """Non-interactive email + password (Cognito) login for CI.

    Uses resilient selectors with fallbacks because the hosted login DOM is not
    part of this repo. Returns True once the app lands on /dashboard/.
    """
    if is_logged_in(page, base_url):
        return True

    print("Attempting non-interactive password login...")
    if "/auth/" not in page.url and "login" not in page.url:
        page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
        wait_for_page_ready(page)

    email_selectors = [
        "[data-cy=inputEmail]",
        "input[type=email]",
        "input[name=email]",
        "input[name=username]",
        "input[id*=email i]",
        "input[autocomplete=username]",
    ]
    password_selectors = [
        "[data-cy=inputPassword]",
        "input[type=password]",
        "input[name=password]",
        "input[autocomplete=current-password]",
    ]
    submit_selectors = [
        "[data-cy=btnLoginLocal]",
        "button[type=submit]",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "button:has-text('Login')",
        "button:has-text('Continue')",
        "input[type=submit]",
    ]

    def fill_first(selectors, value) -> bool:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(value)
                    return True
            except Exception:
                continue
        return False

    def click_first(selectors) -> bool:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    return True
            except Exception:
                continue
        return False

    if not fill_first(email_selectors, email):
        print("ERROR: Could not find the email/username field on the login page.")
        return False

    # Some flows reveal the password field only after submitting the email.
    if not fill_first(password_selectors, password):
        click_first(submit_selectors)
        wait_for_page_ready(page, extra_ms=TAB_WAIT_MS)
        if not fill_first(password_selectors, password):
            print("ERROR: Could not find the password field on the login page.")
            return False

    click_first(submit_selectors)

    deadline = time.time() + (LOGIN_TIMEOUT_MS / 1000)
    while not is_logged_in(page, base_url):
        if time.time() > deadline:
            print("ERROR: Timed out waiting for password login to complete.")
            return False
        page.wait_for_timeout(LOGIN_POLL_MS)

    print("Password login succeeded.")
    return True


# Non-domain segments that can appear right after /dashboard/
RESERVED_DASHBOARD_SEGMENTS = {"profile", "payment_success", "troubleshoting"}


def _domain_id_from_url(url: str) -> str | None:
    match = re.search(r"/dashboard/([^/?#]+)", url)
    if not match:
        return None
    candidate = match.group(1)
    if candidate in RESERVED_DASHBOARD_SEGMENTS:
        return None
    return candidate


def detect_domain_id(page: Page, base_url: str) -> str | None:
    """Resolve the domain UUID the app routes to after login.

    The app lands on /dashboard and redirects to /dashboard/<uuid>/home. We
    first read the current (post-login) URL, then fall back to an explicit
    /dashboard navigation. Returns None if the app could not resolve a single
    domain (e.g. no domain selected and multiple domains available).
    """
    candidate = _domain_id_from_url(page.url)
    if candidate:
        return candidate

    page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
    wait_for_page_ready(page)
    return _domain_id_from_url(page.url)


def ensure_logged_in(page: Page, base_url: str, interactive: bool) -> bool:
    if is_logged_in(page, base_url):
        return True

    email = os.environ.get("HUB_SCREENSHOT_EMAIL")
    password = os.environ.get("HUB_SCREENSHOT_PASSWORD")
    if email and password and login_with_password(page, base_url, email, password):
        return True

    if not interactive:
        print("ERROR: Hub session expired or missing.")
        print("Set HUB_SCREENSHOT_EMAIL / HUB_SCREENSHOT_PASSWORD for non-interactive")
        print("login, or run: python src/generate_screenshots.py --login")
        return False

    print("=" * 60)
    print("Please log in to the dashboard in the browser window.")
    print("Complete the full login flow (including Google/GitHub OAuth).")
    print("Wait until you see the dashboard home page, then the script")
    print("will auto-detect and start capturing.")
    print("=" * 60)

    deadline = time.time() + (LOGIN_TIMEOUT_MS / 1000)
    while not is_logged_in(page, base_url):
        if time.time() > deadline:
            print("ERROR: Timed out waiting for login.")
            return False
        page.wait_for_timeout(LOGIN_POLL_MS)

    print("Logged in! Starting capture...")
    return True


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


def run_action(page: Page, domain_base: str, action: dict):
    """Run a single non-destructive workflow action.

    Supported types: goto, click, fill, wait. There is deliberately no
    'submit' type so captured workflows never trigger destructive operations.
    """
    action_type = action.get("type")
    if action_type == "goto":
        path = action.get("path", "")
        page.goto(f"{domain_base}/{path}", wait_until="domcontentloaded")
        wait_for_page_ready(page)
    elif action_type == "click":
        el = page.query_selector(action["selector"])
        if el and el.is_visible():
            el.click()
            page.wait_for_timeout(500)
    elif action_type == "fill":
        el = page.query_selector(action["selector"])
        if el and el.is_visible():
            el.fill(action.get("value", ""))
    elif action_type == "wait":
        page.wait_for_timeout(int(action.get("ms", 1000)))
    else:
        print(f"    WARN: unknown action type '{action_type}', skipping")


def capture_workflows(page: Page, domain_base: str, workflows: list, output_dir: Path):
    """Capture one screenshot per workflow step, fully driven by features.json.

    Adding/editing/removing a workflow or step needs no code change here.
    Each step is isolated: a broken selector logs a WARN and never aborts the run.
    """
    if not workflows:
        return

    print(f"\nCapturing {len(workflows)} workflows...\n")
    for wf in workflows:
        wf_name = wf.get("name", "workflow")
        print(f"[workflow: {wf_name}] {wf.get('title', {}).get('en', '')}")

        for i, step in enumerate(wf.get("steps", []), 1):
            step_name = step.get("name", f"step{i}")
            path = step.get("path", "") or ""
            filename = f"wf_{wf_name}_{i:02d}_{step_name}.png"
            out = output_dir / filename

            # A dynamic path (contains {...}) can't be resolved statically.
            if path and "{" in path:
                print(f"  {step_name}: skipped (dynamic param: {path})")
                continue

            try:
                # An empty path means "stay on the current page" so multi-click
                # flows (e.g. connect -> start -> view) keep their state.
                if path:
                    if "?" in path:
                        base_path, query = path.split("?", 1)
                        url = f"{domain_base}/{base_path}?{query}"
                    else:
                        url = f"{domain_base}/{path}"

                    print(f"  {step_name}: {url}")
                    page.goto(url, wait_until="domcontentloaded")
                    wait_for_page_ready(page)

                    if is_on_login_page(page):
                        print("    WARN: Redirected to login. Session may have expired.")
                        continue
                else:
                    print(f"  {step_name}: (continue on current page)")

                for action in step.get("actions", []):
                    run_action(page, domain_base, action)

                capture(page, out)
            except Exception as exc:
                print(f"    WARN: step '{step_name}' failed ({exc}); continuing.")


def main():
    load_dotenv(ENV_FILE)

    parser = argparse.ArgumentParser(
        description="Generate EDAMAME Hub dashboard screenshots"
    )
    parser.add_argument("--login", action="store_true", help="Pause for manual login")
    parser.add_argument(
        "--domain-id",
        default=os.environ.get("HUB_SCREENSHOT_DOMAIN_ID"),
        help="Override the auto-detected domain UUID (optional)",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--profile-dir", type=Path, default=PROFILE_DIR)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless (only when saved session is valid)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = load_features()
    features = data.get("features", [])
    mappings = data.get("screenshot_metadata", {}).get("sub_feature_mappings", {})

    base = args.base_url.rstrip("/")

    print(f"Profile: {args.profile_dir}")
    print(f"Output:  {args.output_dir}")
    print(f"Headless: {args.headless}")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(args.profile_dir),
            headless=args.headless,
            viewport=VIEWPORT,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        # If the domain UUID is known up front, navigate straight to its home so
        # the session check passes even for accounts the landing page hides
        # (e.g. the reserved "acme.com" demo domain). Otherwise hit the dashboard
        # landing and let the app redirect so we can auto-detect the UUID.
        if args.domain_id:
            page.goto(
                f"{base}/dashboard/{args.domain_id}/home", wait_until="domcontentloaded"
            )
        else:
            page.goto(f"{base}/dashboard", wait_until="domcontentloaded")
        wait_for_page_ready(page)

        if not ensure_logged_in(page, base, args.login):
            context.close()
            raise SystemExit(1)

        domain_id = args.domain_id or detect_domain_id(page, base)
        if not domain_id:
            print("ERROR: Could not auto-detect a domain UUID.")
            print("The account may have no domain selected or multiple domains.")
            print("Re-run with an explicit --domain-id <uuid> to override.")
            context.close()
            raise SystemExit(1)

        domain_base = f"{base}/dashboard/{domain_id}"
        print(f"Domain:  {domain_base}")

        page.goto(f"{domain_base}/home", wait_until="domcontentloaded")
        wait_for_page_ready(page)

        if not is_logged_in(page, base):
            print("ERROR: Still on login page. Auth failed.")
            context.close()
            raise SystemExit(1)

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

        capture_workflows(page, domain_base, data.get("workflows", []), args.output_dir)

        context.close()

    captured = list(args.output_dir.glob("*.png"))
    print(f"\nDone! {len(captured)} screenshots in {args.output_dir}")


if __name__ == "__main__":
    main()
