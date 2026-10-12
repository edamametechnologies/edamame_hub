# Contributing to the EDAMAME Hub documentation

This repository holds the public documentation of EDAMAME Hub: the README, the
[feature wiki](https://github.com/edamametechnologies/edamame_hub/wiki) and the
screenshots both use. The Hub itself is closed source and deployed separately.

**The README is customer-facing.** Write it for customers and administrators:
what the Hub does, for whom, and how to start. Keep out internal operations
(hostnames, CI runs, internal documents, people, customers) and anything about
vulnerabilities or detection internals. Maintainer material belongs here.

## Repository layout

```
├── README.md                         # Customer-facing overview
├── GITHUBAUDIT.md                    # GitHub Audit feature guide
├── features.json                     # Features, sub-features and step-by-step workflows (en/fr)
├── screenshots/                      # Feature screenshots (README + wiki) and hub_build.txt
├── src/
│   ├── generate_screenshots.py       # Playwright capture of every page and workflow step
│   ├── deployed_build.py             # Identifies the deployed Hub build (deploy detection)
│   ├── build_feature_wiki.py         # Wiki markdown generation
│   └── create_screenshot_account.py  # Signs up a regular Hub account for the capture
├── .github/workflows/
│   └── feature-wiki.yml              # Deploy detection, capture, screenshot commit, wiki publish
└── requirements.txt
```

## How the screenshots stay current

`screenshots/` always shows the Hub that is in production. The workflow
`feature-wiki.yml` takes care of it:

1. **Every hour**, its `detect` job reads the build `hub.edamame.tech` serves:
   the content-hashed names of the entry script and stylesheet in its
   `index.html` (`src/deployed_build.py`). Every Hub build changes them.
   `screenshots/hub_build.txt` records the build the committed screenshots come
   from. When the two differ, the Hub was deployed.
2. The `build-wiki` job then captures every page with Playwright against
   production, commits the changed PNGs and the new `hub_build.txt` to `main`
   (as `EDAMAME Dev`, with `[skip ci]`), and republishes the wiki.
3. If the capture fails, nothing is committed, the wiki is rebuilt from the
   committed screenshots, and the run fails. The record still names the old
   build, so the next hourly check tries again.

| Trigger | Captures | Commits the screenshots |
|---|---|---|
| Hourly schedule | only when the deployed build changed | yes, when it captures |
| `hub-deployed` repository dispatch | yes | yes (production only) |
| Push to `main` | yes | when the build changed, or the push changed `features.json` or `src/generate_screenshots.py` |
| Manual run (Actions > *Hub Screenshots and Wiki*) | yes | yes, unless `base_url` or `domain_id` is overridden |

Only captures of production, of the default workspace, from `main`, are
committed. Workflow step screenshots (`wf_*.png`) only feed the wiki and are
gitignored.

The same pipeline keeps the
[EDAMAME Portal documentation](https://github.com/edamametechnologies/edamame_portal)
current; `src/deployed_build.py` is identical in both repositories, so change
them together.

CI only ever adds commits to `main`. Screenshot commits accumulate, so the
maintainers occasionally squash the history of `main` into a single commit,
outside CI; do not build on old screenshot commits.

### Instant trigger from the Hub deploy (optional)

The hourly check finds every deploy without help. To capture right after a
production deploy instead, the Hub deploy workflow can send a repository
dispatch once its deploy step succeeds, with a token that can write to this
repository:

```bash
curl -fsS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/edamametechnologies/edamame_hub/dispatches \
  -d '{"event_type":"hub-deployed","client_payload":{"environment":"prod"}}'
```

The `detect` job waits up to ten minutes for the CDN to serve the new build,
then captures. A dispatch for another environment is ignored.

### Secrets and variables

| Name | Kind | Purpose |
|---|---|---|
| `HUB_SCREENSHOT_EMAIL`, `HUB_SCREENSHOT_PASSWORD` | secret | Demo account login (MFA off). The dashboard shows this account its built-in demo workspace |
| `HUB_SCREENSHOT_ACME_EMAIL`, `HUB_SCREENSHOT_ACME_PASSWORD` | secret, optional | A regular Hub account (MFA off) used instead, to capture the shared demo workspace named by `HUB_SCREENSHOT_DOMAIN_ID`; `src/create_screenshot_account.py` signs one up |
| `HUB_SCREENSHOT_DOMAIN_ID` | variable, optional | Workspace UUID to capture; empty = the workspace the login lands on |
| `HUB_SCREENSHOT_BASE_URL` | variable, optional | Hub origin; empty = production |
| `DEV_GITHUB_TOKEN` | organization secret | Screenshot push to `main`, wiki clone and push |
| `EDAMAME_POSTURE_*` | organization secret / variables | EDAMAME Posture on the runner (also admits it through the organization IP allow list) |

## Capturing locally

```bash
pip install -r requirements.txt
playwright install chromium

# First run: log in interactively; the session is kept in .browser_profile/
python src/generate_screenshots.py --login

# Later runs reuse the session
python src/generate_screenshots.py

# Non-interactive, like CI: put HUB_SCREENSHOT_EMAIL / HUB_SCREENSHOT_PASSWORD
# in .screenshot.env (gitignored), then
python src/generate_screenshots.py --headless

# Which build is in production, and do the committed screenshots match it?
python src/deployed_build.py --base-url https://hub.edamame.tech \
  --compare screenshots/hub_build.txt
```

The script reads the workspace UUID from the post-login redirect
(`/dashboard/<uuid>/home`). A workspace the landing page hides, such as the
shared demo workspace, needs `--domain-id <uuid>` (or
`HUB_SCREENSHOT_DOMAIN_ID` in `.screenshot.env`, see `.screenshot.env.example`).

Committing local captures is rarely needed: the workflow commits the
screenshots of each deploy. If you do, commit only production captures, and
update `screenshots/hub_build.txt` with `src/deployed_build.py` at the same time.

### Static screenshots

A sub-feature with `"static": true` is never captured by the workflow: the PNG
committed under `screenshots/` is kept as is. The four AI Governance tabs are
static because the capture account cannot open that page with a populated
fleet; they were captured by hand on a preprod build with the page's `?demo=1`
synthetic-fleet mode. Re-capture them the same way, and check that nothing in
the shot names a real person, account or device:

```bash
HUB_SCREENSHOT_BASE_URL=<preprod origin> \
HUB_SCREENSHOT_DOMAIN_ID=<workspace uuid> \
python src/generate_screenshots.py --login     # then commit screenshots/07b_*.png
```

Remove `"static": true` once production can show that page to the capture
account; from then on the workflow keeps it current like the others.

## features.json

`features` lists the wiki's feature pages. Each sub-feature has a `name`, a
`path` (route under `/dashboard/<uuid>/`; paths with `{param}` segments are not
captured), `title` / `description` in `en` and `fr`, and a screenshot prefix in
`screenshot_metadata.sub_feature_mappings` (file name `{prefix}_{name}.png`).

`workflows` lists the step-by-step guides, each rendered as its own wiki page
(`workflow-<name>`) and linked from the related feature page. Adding, editing or
removing a workflow or step needs no code change. A workflow has `name`, an
optional `feature` (parent feature slug), `title` / `description`, and
`steps[]`. Each step has a `name`, a `path`, `title` / `instruction`, and
optional `actions[]` run before the screenshot:

- `goto` `{ "path": "..." }`
- `click` `{ "selector": "..." }`
- `fill` `{ "selector": "...", "value": "..." }`
- `press` `{ "key": "ArrowDown", "selector": "..." }` (selector optional)
- `wait` `{ "ms": 1000 }`

A step with an empty `path` stays on the current page, so multi-click flows keep
their state. `highlight` (a CSS or Playwright text selector) draws a red frame
around the element the step is about. Sub-features accept the same `actions`
and `highlight` when several share one route and differ by UI state (tabs).

There is deliberately no submit action: the capture opens pages, tabs and
modals and fills fields, but never presses a final Send, Create or Run button.
Step screenshots are saved as `wf_{workflow}_{NN}_{step}.png`.

## Building the wiki locally

```bash
python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki
```

The workflow publishes the generated pages and images to the
[wiki](https://github.com/edamametechnologies/edamame_hub/wiki); never edit the
wiki by hand, it is overwritten on the next run.
