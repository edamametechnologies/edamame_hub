"""
Uptime check of the Hub and the Portal, with a Slack alert when a site goes
down and when it comes back.

It looks for what took the Portal down in November 2026:
- 2 Nov: a template deploy rewrote the CloudFront distribution without its
  custom domain and certificate. The site presented the *.cloudfront.net
  certificate (hostname mismatch) and CloudFront answered 403 to the name.
- 11 Nov: with the domain back, the page was white. The build loads its
  assets from the distribution's cloudfront.net domain, cross-origin, and the
  distribution had lost its CORS policies, so the browser blocked them.

For each site:
1. TLS: the certificate is valid for the site's name and does not expire
   within CERT_MIN_DAYS.
2. HTTP: / and a deep link answer 200 with the app's HTML (the deep link
   needs CloudFront's 403/404 -> /index.html error responses).
3. Assets: each script and stylesheet of index.html, requested with a
   browser's headers, answers 200 and, when cross-origin, carries
   Access-Control-Allow-Origin.
4. Browser (--browser): headless Chromium renders something in #root.

A failed check is retried before the site is declared down. The state of the
previous run (--state) decides what is posted: one message when a site goes
down, a reminder every REMIND_HOURS while it stays down, one when it is back.
Nothing while it stays up.

Usage:
    python src/uptime_check.py --state .uptime-state.json --browser --dry-run
    python src/uptime_check.py --site test=http://localhost:8000,/x --dry-run
"""

import argparse
import datetime as dt
import html.parser
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SITES = [
    ("Hub", "https://hub.edamame.tech", "/dashboard"),
    ("Portal", "https://portal.edamame.tech", "/auth/welcome"),
]
CERT_MIN_DAYS = 14
REMIND_HOURS = 6
ATTEMPTS = int(os.environ.get("UPTIME_ATTEMPTS", "3"))
RETRY_SECONDS = 20
TIMEOUT = 20
# The SLACK_ALERTS_CHANNEL organization variable (uptime.yml passes it); #qa-alerts until it is set.
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL") or "C072J0U9TH7"
RUN_URL = (
    f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
    f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
)
# What a browser sends for <script type="module" crossorigin>: on 11 Nov a
# plain request still got Access-Control-Allow-Origin, a browser's did not.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Sec-Fetch-Mode": "cors",
}

HINT_CERT = (
    "CloudFront presenting another certificate (*.cloudfront.net) means the distribution lost its "
    "custom domain and certificate, as on 2 Nov 2026: check its Aliases and ViewerCertificate."
)
HINT_CORS = (
    "The browser blocks this file, so the page stays white, as on 11 Nov 2026: check the "
    "distribution's response headers policy (forcecors) and origin request policy (CORS-S3Origin)."
)
HINT_DEEP = "Deep links need CloudFront's error responses (403 and 404 -> /index.html, 200)."
HINT_403 = "CloudFront answers 403 to this name: the domain is probably missing from the distribution's Aliases."


class AssetParser(html.parser.HTMLParser):
    """Collects the scripts and stylesheets of index.html, and whether #root is there."""

    def __init__(self):
        super().__init__()
        self.assets, self.has_root = [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div" and a.get("id") == "root":
            self.has_root = True
        elif tag == "script" and a.get("src"):
            self.assets.append(("script", a["src"], "crossorigin" in a or a.get("type") == "module"))
        elif tag == "link" and "stylesheet" in (a.get("rel") or "") and a.get("href"):
            self.assets.append(("style", a["href"], "crossorigin" in a))


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": BROWSER_HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def cloudfront_domain(host):
    try:
        canonical, _, _ = socket.gethostbyname_ex(host)
        return canonical if canonical != host else ""
    except OSError:
        return ""


def check_tls(host):
    try:
        with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except ssl.SSLCertVerificationError as e:
        return [f"TLS: {str(e.verify_message or e).rstrip('.')}. {HINT_CERT}"]
    except OSError as e:
        return [f"TLS: cannot connect to {host}:443 ({e})."]
    expires = dt.datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), dt.timezone.utc)
    days = (expires - dt.datetime.now(dt.timezone.utc)).days
    if days < CERT_MIN_DAYS:
        return [f"TLS: the certificate expires in {days} days ({expires:%Y-%m-%d}). ACM renews only certificates in use."]
    return []


def check_page(base, path, label):
    url = base + path
    try:
        status, headers, body = fetch(url)
    except Exception as e:  # TLS errors are reported by check_tls
        return [f"{label} {url}: no answer ({e})."], None
    problems = []
    if status != 200:
        hint = HINT_403 if status == 403 and "cloudfront" in headers.get("x-cache", "").lower() else ""
        if path != "/" and status in (403, 404):
            hint = HINT_DEEP
        problems.append(f"{label} {url}: HTTP {status} ({headers.get('x-cache', 'no x-cache')}). {hint}".strip())
        return problems, None
    parser = AssetParser()
    parser.feed(body.decode("utf-8", "replace"))
    if not parser.has_root:
        problems.append(f"{label} {url}: 200 but not the app's page (no #root).")
    return problems, parser


def check_assets(base, parser, extra_hosts=()):
    page_origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(base))
    page_host = urllib.parse.urlsplit(base).hostname
    problems = []
    for kind, src, cors in parser.assets:
        url = urllib.parse.urljoin(base + "/", src)
        host = urllib.parse.urlsplit(url).hostname or ""
        # Only the site's own files: its domain and its CloudFront domain.
        if host != page_host and not host.endswith(".cloudfront.net") and host not in extra_hosts:
            continue
        headers = dict(BROWSER_HEADERS, Referer=base + "/")
        cross = host != page_host
        headers["Sec-Fetch-Dest"] = "script" if kind == "script" else "style"
        headers["Sec-Fetch-Site"] = "cross-site" if cross else "same-origin"
        if cors:
            headers["Origin"] = page_origin
        try:
            status, h, _ = fetch(url, headers)
        except Exception as e:
            problems.append(f"Asset {url}: no answer ({e}).")
            continue
        if status != 200:
            problems.append(f"Asset {url}: HTTP {status} ({h.get('x-cache', 'no x-cache')}).")
            continue
        allow = h.get("access-control-allow-origin", "")
        if cors and cross and allow not in ("*", page_origin):
            problems.append(f"Asset {url}: no Access-Control-Allow-Origin for {page_origin}. {HINT_CORS}")
    return problems


def check_browser(base):
    from playwright.sync_api import sync_playwright

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        try:
            page.goto(base + "/", wait_until="load", timeout=45000)
            page.wait_for_timeout(5000)
            rendered = page.evaluate("() => (document.querySelector('#root')?.childElementCount || 0)")
        finally:
            browser.close()
    if rendered:
        return []
    own = [e for e in errors if "cloudfront.net" in e or urllib.parse.urlsplit(base).hostname in e]
    detail = (own or errors or ["no console error"])[0][:300]
    hint = f" {HINT_CORS}" if "Access-Control-Allow-Origin" in detail else ""
    return [f"Browser: the page renders blank (white page). First error: {detail}{hint}"]


def check_site(base, deep, use_browser, extra_hosts=()):
    problems = []
    host = urllib.parse.urlsplit(base).hostname
    if base.startswith("https://"):
        problems += check_tls(host)
        if problems:
            return problems  # every request would fail the same way
    page_problems, parser = check_page(base, "/", "Page")
    problems += page_problems
    if parser:
        problems += check_assets(base, parser, extra_hosts)
    if deep:
        problems += check_page(base, deep, "Deep link")[0]
    if not problems and use_browser:
        try:
            problems += check_browser(base)
        except Exception as e:
            problems.append(f"Browser: the page did not load ({str(e).splitlines()[0][:200]}).")
    return problems


def check_with_retries(base, deep, use_browser, extra_hosts=()):
    for attempt in range(1, ATTEMPTS + 1):
        problems = check_site(base, deep, use_browser, extra_hosts)
        if not problems or attempt == ATTEMPTS:
            return problems
        print(f"  attempt {attempt} failed, retrying in {RETRY_SECONDS}s: {problems[0][:120]}")
        time.sleep(RETRY_SECONDS)
    return problems


def ago(iso, now):
    minutes = int((now - dt.datetime.fromisoformat(iso)).total_seconds() // 60)
    return f"{minutes // 60} h {minutes % 60:02d} min" if minutes >= 60 else f"{minutes} min"


def decide(name, base, problems, prev, now):
    """The message to post for this site, if any, and its new state."""
    cf = cloudfront_domain(urllib.parse.urlsplit(base).hostname or "")
    where = f" (CloudFront {cf})" if cf.endswith("cloudfront.net") else ""
    up = not problems
    was_up = prev.get("up", True)
    state = dict(prev, up=up, problems=problems)
    if up and was_up:
        return None, {"up": True}
    if up:
        since = prev.get("since", now.isoformat())
        return f":white_check_mark: *{name} is back*: {base} (down for {ago(since, now)}). <{RUN_URL}|Run>", {"up": True}
    details = "\n".join(f"• {p}" for p in problems[:6])
    if was_up:
        state.update(since=now.isoformat(), last_alert=now.isoformat())
        return f":x: *{name} is down*: {base}{where}\n{details}\n<{RUN_URL}|Run>", state
    last = dt.datetime.fromisoformat(prev.get("last_alert", prev.get("since", now.isoformat())))
    if now - last >= dt.timedelta(hours=REMIND_HOURS):
        state["last_alert"] = now.isoformat()
        return f":rotating_light: *{name} is still down* (for {ago(prev.get('since', now.isoformat()), now)}): {base}{where}\n{details}\n<{RUN_URL}|Run>", state
    return None, state


def post_slack(text, dry_run):
    if dry_run:
        print("--- Slack message (dry run) ---\n" + text + "\n---")
        return True
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("::error::SLACK_BOT_TOKEN is not set: the alert below was not posted.\n" + text)
        return False
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": SLACK_CHANNEL, "text": text, "unfurl_links": False}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        answer = json.loads(r.read())
    if not answer.get("ok"):
        print(f"::error::Slack refused the message: {answer.get('error')}")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", help="JSON file with the previous run's state; rewritten")
    ap.add_argument("--browser", action="store_true", help="also render the page in headless Chromium")
    ap.add_argument("--dry-run", action="store_true", help="print the Slack messages instead of posting them")
    ap.add_argument("--site", action="append", help="NAME=URL[,DEEP_PATH] instead of the Hub and the Portal")
    ap.add_argument("--test-message", action="store_true", help="post a test message to check the Slack token and channel, then exit")
    ap.add_argument("--asset-host", action="append", default=[], help="another host whose assets count as the site's own (tests)")
    args = ap.parse_args()

    if args.test_message:
        ok = post_slack(f":test_tube: Uptime check of the Hub and the Portal: test message, alerts will land here. <{RUN_URL}|Run>", args.dry_run)
        sys.exit(0 if ok else 1)

    sites = SITES
    if args.site:
        sites = []
        for s in args.site:
            name, rest = s.split("=", 1)
            url, _, deep = rest.partition(",")
            sites.append((name, url.rstrip("/"), deep or None))

    state = {}
    if args.state and os.path.exists(args.state):
        with open(args.state) as f:
            state = json.load(f)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    down, posted_ok = [], True
    summary = [f"## Uptime check, {now:%Y-%m-%d %H:%M} UTC", ""]
    for name, base, deep in sites:
        print(f"[{name}] {base}")
        problems = check_with_retries(base, deep, args.browser, tuple(args.asset_host))
        for p in problems:
            print(f"  DOWN: {p}")
        if not problems:
            print("  up")
        else:
            down.append(name)
        message, new_state = decide(name, base, problems, state.get(name, {}), now)
        if message and not post_slack(message, args.dry_run):
            posted_ok = False
            new_state = state.get(name, {})  # not posted: the next run tries again
        state[name] = new_state
        summary.append(f"- **{name}** {base}: " + ("up" if not problems else "DOWN: " + " / ".join(problems)))
    if args.state and not args.dry_run:
        with open(args.state, "w") as f:
            json.dump(state, f, indent=1)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("\n".join(summary) + "\n")
    # A red run in Actions while a site is down, or when an alert could not be posted.
    sys.exit(1 if down or not posted_ok else 0)


if __name__ == "__main__":
    main()
