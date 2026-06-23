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

The Hub aggregates the security checks that **EDAMAME Security** (workstations) and **EDAMAME Posture** (CI/CD runners and build hosts) evaluate on every enrolled endpoint, then rolls them up across the fleet. Each check appears in the **Security Checks** catalog with per-device pass/fail rates, on each device's detail page (passed vs. failed lists), and feeds the **Security Score** (5 dimensions: Credentials, Network, System Services, System Integrity, Applications) and **Compliance** views.

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

Screenshots are captured **manually on your machine** (Playwright against
production). CI only rebuilds the wiki from committed PNGs.

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
