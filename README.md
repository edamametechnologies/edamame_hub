# EDAMAME Hub

## Overview

EDAMAME Hub is the no-MDM security management dashboard for organizations. It provides centralized visibility into endpoint security posture (including AI agent posture), compliance, access control policies, and user onboarding — without requiring an MDM agent.

**Dashboard**: [hub.edamame.tech](https://hub.edamame.tech)

**Note: The dashboard application source lives in `edamame-services`. This repository is used for feature documentation, screenshots, and the wiki pipeline.**

## Key Features

- **Overview Dashboard** — Real-time security score, device activity, and alert summary
- **User Management** — Onboarding workflows, user roles, device association
- **Device Inventory** — Endpoint monitoring with OS, score, location, and compliance status
- **Security Scoring** — 5-dimension security scores (Credentials, Network, System Services, System Integrity, Applications)
- **Compliance Frameworks** — PCI-DSS, ISO 27001, SOC 2, CIS, HIPAA compliance tracking
- **Access Control Policies** — Conditional access rules with integration triggers (GitHub, Azure, Google, GitLab, Fortigate, NetBird, Tailscale)
- **Security Checks** — Catalog of security benchmarks (CIS, NIST) and EDAMAME internal checks — including AI agent posture (`unsecured_*`) and EDAMAME Helper status — with pass/fail rates per device
- **Escalations & Engagement** — Automated alerts for missing signals, inactive devices, policy violations
- **Integrations** — GitHub, Vanta, VPN providers, identity providers
- **[GitHub Audit](./GITHUBAUDIT.md)** — Audit trail of GitHub organization activity


## Security Checks

The Hub aggregates the security checks that **EDAMAME Security** (workstations) and **EDAMAME Posture** (CI/CD runners and any server running AI agents, cloud or self-hosted) evaluate on every enrolled endpoint, then rolls them up across the fleet. Each check appears in the **Security Checks** catalog with per-device pass/fail rates, on each device's detail page (passed vs. failed lists), and feeds the **Security Score** (5 dimensions: Credentials, Network, System Services, System Integrity, Applications) and **Compliance** views.

Checks come from the open-source [EDAMAME threat models](https://github.com/edamametechnologies/threatmodels) — industry benchmarks such as CIS and NIST, mapped to ISO 27001, SOC 2, PCI-DSS, and HIPAA — and fall into four implementation types:

- **System checks** — direct inspection of system configuration, file presence, or settings
- **Command-line checks** — safe, vetted commands that read system state
- **Business rules** — optional custom user-space scripts for organization-specific policy
- **Internal checks** — evaluated directly by the EDAMAME Core engine, with no external script

### Internal checks

Internal checks are computed by EDAMAME itself rather than by a benchmark script, and they surface in the Hub exactly like any other check (catalog, device detail, score, and compliance roll-ups). They include:

- **AI agent posture** — the `unsecured_*` family (`unsecured_cursor`, `unsecured_claude_code`, `unsecured_claude_desktop`, `unsecured_openclaw`, `unsecured_codex`, `unsecured_hermes`), part of the **Applications** dimension and tagged **AI Agent Posture**. Each fires when its AI coding agent is discovered on the endpoint but the EDAMAME transcript observer for that agent is paused — i.e. the agent is running without two-plane divergence monitoring. This brings [EDAMAME Security's Agent Detection & Response](https://github.com/edamametechnologies/edamame_security) coverage into the fleet view.
- **EDAMAME Helper status** — part of the **System Services** dimension; flags endpoints where the privileged helper required for full Security Score analysis and remediation is inactive or out of date.
- **Business rules compliance** — flags endpoints where one or more configured organization business rules are not respected.

No Hub-specific setup is required: as soon as an endpoint reports its posture, its internal checks (including any unsecured AI agents) appear in the Security Checks catalog, contribute to the device's score dimensions, and roll up into domain-wide compliance.


## Feature Wiki

Full feature descriptions with screenshots are available in the project wiki: [github.com/edamametechnologies/edamame_hub/wiki](https://github.com/edamametechnologies/edamame_hub/wiki)

## Screenshot Generation

Screenshots can be captured **automatically in CI** or **manually on your
machine** (Playwright against production).

- **CI (automatic):** `feature-wiki.yml` logs in headlessly with email +
  password, captures every feature and workflow screenshot, then rebuilds and
  pushes the wiki. It runs on push to `main`, on a weekly schedule, and via
  `workflow_dispatch`. Required GitHub secrets:
  - `HUB_SCREENSHOT_EMAIL` (secret) — screenshot account email
  - `HUB_SCREENSHOT_PASSWORD` (secret) — screenshot account password (the
    account must have **MFA disabled** for headless login)

  CI captures the **`acme.com` demo workspace** (Enterprise plan, simulated
  fleet including AI-capable devices, so the AI Governance page and the device
  AI posture card are populated). That reserved workspace is hidden from the
  post-login landing page, so its UUID cannot be auto-detected: it is read from
  the **`HUB_SCREENSHOT_DOMAIN_ID`** repository *variable*. The login must be a
  regular Hub account, held in the **`HUB_SCREENSHOT_ACME_EMAIL`** /
  **`HUB_SCREENSHOT_ACME_PASSWORD`** secrets (MFA off; every confirmed Hub
  account is added to `acme.com` as a viewer, so it can open the workspace —
  `src/create_screenshot_account.py` signs one up). `demo@edamame.tech`
  (`HUB_SCREENSHOT_EMAIL` / `_PASSWORD`, the fallback when the ACME secrets are
  unset) is hard-wired by the dashboard to a client-side mock workspace
  (`edamame.demo`, Business plan) whatever the URL says, so it never renders
  `acme.com`. A `workflow_dispatch` run can pass a `domain_id` input to capture
  another workspace once; an empty value falls back to auto-detecting the UUID
  from the post-login redirect (`/dashboard/<uuid>/home`). If live capture
  fails, the step is non-blocking and the wiki still builds from any PNGs
  committed under `screenshots/`.

- **Local (manual):** interactive login as below.

The script normally **auto-detects** the domain UUID from the post-login
redirect (`/dashboard/<uuid>/home`), so you don't pass it. The exception is the
demo workspace `acme.com`: the dashboard landing page deliberately hides that
reserved name, so auto-detection can't resolve it and you must pass the UUID
explicitly with `--domain-id` (find it in the Hub URL after manually opening the
workspace).

```bash
pip install -r requirements.txt
playwright install chromium

# First run: log in interactively to save auth state (domain auto-detected)
python src/generate_screenshots.py --login

# Subsequent runs: reuse saved auth
python src/generate_screenshots.py

# Demo "acme.com" workspace: auto-detect is hidden, pass the UUID explicitly
python src/generate_screenshots.py --domain-id <uuid>
# Or persist it so you can omit the flag:
cp .screenshot.env.example .screenshot.env   # then set HUB_SCREENSHOT_DOMAIN_ID

# Commit PNGs, then push — feature-wiki.yml updates the GitHub wiki
git add screenshots/ && git commit -m "docs: refresh Hub screenshots"
```

For non-interactive local capture (same path CI uses), set the credentials in
`.screenshot.env` (`HUB_SCREENSHOT_EMAIL`, `HUB_SCREENSHOT_PASSWORD`) and run the
script without `--login`.

## Workflows (step-by-step tutorials)

The `workflows` array in `features.json` defines step-by-step tutorials that are
rendered as their own wiki pages (linked from the Home index and from the
related feature page). The whole pipeline is **data-driven**: adding, editing, or
removing a workflow or step in `features.json` needs no code changes.

Each workflow has `name`, an optional `feature` (parent feature slug for
cross-linking), `title`/`description` (`en`/`fr`), and `steps[]`. Each step has a
`name`, `path` (route), `title`/`instruction` (`en`/`fr`), and optional
`actions[]` performed before the screenshot is taken:

- `goto` `{ "path": "..." }`
- `click` `{ "selector": "..." }`
- `fill` `{ "selector": "...", "value": "..." }`
- `press` `{ "key": "ArrowDown", "selector": "..." }` (selector optional)
- `wait` `{ "ms": 1000 }`

A feature `sub_feature` accepts the same optional `actions[]` and `highlight`
when several sub-features share one route and differ only by UI state (e.g. the
AI Governance *Overview* / *Allowlists* pill tabs).

A sub-feature with `"static": true` is **not captured by CI**: the PNG committed
under `screenshots/` is used as is. The four AI Governance tabs are static: the
CI account cannot see the Enterprise-only page, so they were captured by hand on
the preprod build (`https://d2uilxq0a99b7n.cloudfront.net`, workspace
`wikishots.test` owned by the E2E account of `edamame-services`) with `?demo=1`,
the page's synthetic-fleet demo mode. Re-capture the same way — or drop the
flag once production ships the demo mode:

```bash
HUB_SCREENSHOT_BASE_URL=https://d2uilxq0a99b7n.cloudfront.net \
HUB_SCREENSHOT_DOMAIN_ID=b9de36b9-98c8-40df-a133-407d5c3587ef \
python src/generate_screenshots.py --login     # then commit screenshots/07b_*.png
```

A step with an omitted/empty `path` stays on the current page instead of
re-navigating, so multi-click flows (e.g. connect -> start audit -> view
results) keep their state across steps.

A step can also set `highlight` to a selector (CSS or Playwright text selector,
e.g. `"[data-cy=createPoliciesButton]"` or `"button:has-text('Connect')"`). The
capture draws a red rectangle around that element before taking the screenshot,
so the reader's eye is drawn to the button/field the step is about.

There is **no destructive action type** (no submit): workflow capture navigates,
opens tabs/modals, and fills fields, but never clicks the final
Send/Create/Run button. This keeps automated capture safe to run against the
live demo workspace. Workflow step screenshots are saved as
`wf_{workflow}_{NN}_{step}.png`.

## Wiki Generation

```bash
python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki
```

## Repository Structure

```
├── features.json                    # Feature definitions (i18n, paths, descriptions)
├── screenshots/                     # Captured dashboard screenshots
├── src/
│   ├── generate_screenshots.py      # Playwright-based screenshot capture
│   └── build_feature_wiki.py        # Wiki markdown generation
├── .github/workflows/
│   └── feature-wiki.yml             # CI to generate and push wiki
└── requirements.txt                 # Python dependencies
```
