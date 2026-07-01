# CLAUDE.md — edamame_hub

> **Feature documentation, screenshots, and wiki generation for EDAMAME Hub.**
> This repo is documentation-only: it defines Hub features (`features.json`),
> captures screenshots against the live Hub, and rebuilds the GitHub wiki.
> The Hub app source itself lives in `edamame-services/applications/hub/`.

Cursor also loads the scoped rule at `.cursor/rules/feature-wiki.mdc` (same
pipeline, glob-scoped). Keep this file and that `.mdc` in sync via the central
`edamame_rules` repo.

## Overview

```
features.json → generate_screenshots.py (local Playwright) → screenshots/*.png
             → commit + push → feature-wiki.yml (CI) → GitHub wiki
```

| Step | Where | What |
|------|-------|------|
| 1. Define routes | `features.json` | Feature/sub-feature paths + i18n copy |
| 2. Capture PNGs | **Local** `src/generate_screenshots.py` | Playwright vs live Hub |
| 3. Commit | `edamame_hub/screenshots/` | PNGs are source of truth |
| 4. Wiki | CI `feature-wiki.yml` | `build_feature_wiki.py` → `edamame_hub.wiki` |

**Screenshots are captured manually on a developer machine** (Playwright against
production). CI only rebuilds the GitHub wiki from committed PNGs — unlike
`edamame_security`, which captures via Flutter golden tests in `edamame_app` CI.

## Prerequisites

```bash
cd edamame_hub
pip install -r requirements.txt
playwright install chromium
```

### Domain UUID — auto-detected (with one exception)

The script resolves the domain the same way the app does: after login it reads
the post-login redirect `…/dashboard/<uuid>/home` (falling back to navigating to
`/dashboard`). So **you normally pass nothing**.

**Exception — the `acme.com` demo workspace.** `DashboardLanding.tsx`
deliberately filters out the reserved name `acme.com`
(`domains.filter(d => d.domainName !== 'acme.com')`), so the app never
auto-redirects to it and auto-detection returns nothing. For that workspace,
pass the UUID explicitly with `--domain-id <uuid>` (read it from the Hub URL
after opening the workspace manually), or persist it via `.screenshot.env`
(`HUB_SCREENSHOT_DOMAIN_ID`). When `--domain-id` is given, the script navigates
straight to `…/dashboard/<uuid>/home`, so the session check passes even for the
hidden demo domain.

## Screenshot capture (manual, local)

### First run — save Cognito session

```bash
python src/generate_screenshots.py --login            # domain auto-detected
python src/generate_screenshots.py --login --domain-id <uuid>   # acme.com demo
```

1. Chromium opens (headed).
2. Complete Cognito login (Google/GitHub OAuth if configured).
3. Wait until the dashboard home loads — the script auto-continues.
4. Auth is stored in `.browser_profile/` (gitignored).

### Subsequent runs — reuse session

```bash
python src/generate_screenshots.py                    # domain auto-detected
python src/generate_screenshots.py --domain-id <uuid> # acme.com demo
```

Re-run after Hub UI changes. If you see `session expired`, use `--login` again.

**Headless** (only when session is still valid):

```bash
python src/generate_screenshots.py --headless [--domain-id <uuid>]
```

### What gets captured

- Viewport: 1440×900, full-page PNG
- Filename: `{prefix}_{subfeature_name}.png` from `screenshot_metadata.sub_feature_mappings`
- Skipped: paths with dynamic params (`{device_id}`, `{username}`, etc.)
- Modals dismissed before capture

### After capture

```bash
# Preview wiki locally (optional)
python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki

# Commit screenshots, then push — CI updates the wiki
git add screenshots/ features.json
git commit -m "docs: refresh Hub feature screenshots"
git push origin main
```

## features.json structure

```json
{
  "screenshot_metadata": {
    "patterns": { "default": "{prefix}_{subfeature_name}.png" },
    "sub_feature_mappings": {
      "overview_main": { "prefix": "01" }
    }
  },
  "features": [
    {
      "name": "overview",
      "title": { "en": "Overview", "fr": "Vue d'ensemble" },
      "sub_features": [
        {
          "name": "overview_main",
          "path": "home",
          "title": { "en": "...", "fr": "..." }
        }
      ]
    }
  ]
}
```

- **name** — slug for screenshot matching (lowercase, underscores)
- **path** — route under `/dashboard/{domain_id}/` (no dynamic segments for auto-capture)

## CI workflow (wiki only)

- **Trigger:** push to `main` or `workflow_dispatch`
- **Does NOT** run Playwright or re-capture screenshots
- Reads committed `screenshots/`, runs `build_feature_wiki.py`, pushes to `edamametechnologies/edamame_hub.wiki`

## Adding a new feature

1. Ship the Hub UI in `edamame-services/applications/hub/`
2. Add feature + `sub_feature_mappings` + static `path` in `features.json`
3. Run `generate_screenshots.py` locally (`--login` if needed)
4. Commit PNGs + `features.json`, push — wiki updates on `main`

## Comparison with edamame_security

| | Hub | Security app |
|---|-----|----------------|
| Capture | Manual Playwright vs production | Automated Flutter goldens in `edamame_app` CI |
| Auth | Interactive Cognito (`.browser_profile/`) | Demo mode, no login |
| CI | Wiki build only | Screenshot commit + wiki build |
