# EDAMAME Hub

> Part of the **[EDAMAME Agents](https://github.com/edamametechnologies#edamame-agents)** family - AI-powered security assistants for the modern SDLC with shared LLM subscription via [EDAMAME Portal](https://portal.edamame.tech).

## Overview

EDAMAME Hub is the no-MDM security management dashboard for organizations. It provides centralized visibility into endpoint security posture, compliance, access control policies, and user onboarding — without requiring an MDM agent.

**Dashboard**: [hub.edamame.tech](https://hub.edamame.tech)

**Note: The dashboard application source lives in `edamame-services`. This repository is used for feature documentation, screenshots, and the wiki pipeline.**

## Key Features

- **Overview Dashboard** — Real-time security score, device activity, and alert summary
- **User Management** — Onboarding workflows, user roles, device association
- **Device Inventory** — Endpoint monitoring with OS, score, location, and compliance status
- **Security Scoring** — 5-dimension security scores (Credentials, Network, System Services, System Integrity, Applications)
- **Compliance Frameworks** — PCI-DSS, ISO 27001, SOC 2, CIS, HIPAA compliance tracking
- **Access Control Policies** — Conditional access rules with integration triggers (GitHub, Azure, Google, GitLab, Fortigate, NetBird, Tailscale)
- **Security Checks** — Catalog of security benchmarks with pass/fail rates per device
- **Escalations & Engagement** — Automated alerts for missing signals, inactive devices, policy violations
- **Integrations** — GitHub, Vanta, VPN providers, identity providers
- **GitHub Audit** — Audit trail of GitHub organization activity

## Feature Wiki

Full feature descriptions with screenshots are available in the project wiki: [github.com/edamametechnologies/edamame_hub/wiki](https://github.com/edamametechnologies/edamame_hub/wiki)

## Screenshot Generation

To capture dashboard screenshots for the wiki:

```bash
pip install -r requirements.txt
playwright install chromium

# First run: log in interactively to save auth state
python src/generate_screenshots.py --login --domain-id YOUR_DOMAIN_ID

# Subsequent runs: reuse saved auth
python src/generate_screenshots.py --domain-id YOUR_DOMAIN_ID
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
