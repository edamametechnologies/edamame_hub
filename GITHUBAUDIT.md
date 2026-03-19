# GitHub Audit — Security Visibility for Your Organization

> **One-click security intelligence** for your GitHub organization. Understand who did what, where, and how risky it is—without waiting for device enrollment.


https://github.com/user-attachments/assets/087f0569-16cf-47e2-9412-28e79e3ea3e5

---

## Why GitHub Audit?

Your GitHub organization is a critical control plane: repositories, tokens, integrations, and IP allow lists. Security teams need to know:

- **Who** changed what—and was it a human or a bot?
- **Where** activity originated—which IPs and countries?
- **How risky** the activity is—boundary changes, token revocations, member removals?

GitHub Audit in EDAMAME Hub gives you this visibility **immediately**, as soon as you connect GitHub. No device enrollment required. It’s your day‑1 security control tower.

---

## End-to-end workflow

### 1. Start from guided setup (or Settings)

You may open **Audit your GitHub organization** as a short guided flow with three steps:

1. **Your domain** — confirm the workspace domain.
2. **Connect GitHub** — install the **EDAMAME GitHub App** on your organization so Hub can read the org **audit log** (read-only security telemetry).
3. **Run audit** — choose how far back to analyze and start the job.

Alternatively, go to **Settings → Integrations**, use **Connect** on GitHub, then use **Audit** when GitHub is already connected.

### 2. Complete GitHub App installation

After **Connect GitHub**, your browser may show a brief redirect screen while you are sent to **EDAMAME Hub Connector** (or the GitHub App install flow) to finish installation. If the browser does not redirect automatically, use the **setup** link on that screen to continue.

### 3. Choose lookback and start

Pick a **lookback period**—typically **7, 30, 90, or 180 days** (often **30** by default)—then **Start audit**. Hub opens the audit results route for this run.

### 4. Wait while the audit runs

The audit runs **asynchronously** on the server. You see a centered loading state: *Audit is being processed, please wait…* Large organizations can take **several minutes** (often up to **~10 minutes**; allow up to **~15 minutes** before treating a run as stuck). The page **refreshes periodically** until the report is **completed** or **failed**. If a run times out, start a new audit from Integrations.

### 5. Review the report

When processing finishes, the **GitHub Audit Results** view loads with scores, summaries, maps, and the full event list (see **What you see in the report** below).

---

## What you see in the report

### Headline score and summary

- **Audit score (0–100)** in a circular gauge, with a short label such as **Good**, **Needs attention**, or **At risk**.
- **Summary counts**: total activity, **human** vs **non-human** events, **unique actors**, **unique IPs** (IPs appear when your org has enabled GitHub **IP disclosure**).

### Score breakdown

**Factor badges** explain what lowered the score—for example:

- IP allow-list or boundary changes  
- PAT-related activity  
- High-risk patterns such as **anonymous Git access to private repositories**  
- Membership or trust changes (e.g. outside collaborators)

Many badges are **clickable**: they filter the events table so you can inspect the underlying audit events.

### Severity distribution

A horizontal **severity bar** (e.g. **Critical**, **High**, **Medium**, **Info**) shows how events split by risk. **Click a segment** to filter the table to that severity.

### Top actors

Who drove the most activity, with **human** vs **automation** cues (e.g. **CI/CD**, **bots**, **automation accounts**, or **anonymous** actors where applicable). Severity chips per actor show concentration of serious events.

### IP addresses

Source **IPs**, **country**, event counts, and which **actors** used each IP—when GitHub exposes IP data for your org.

### Token and access signals

Where available, the experience surfaces **token fingerprints** (hashes), **token type** (e.g. classic vs fine-grained PAT), and the **user** tied to the credential—so you can tie risky events back to specific tokens.

### Git operations focus

**Git** activity (**clone**, **push**, **fetch**) is broken out so you can see:

- Totals by **actor class**: **Human**, **Anonymous**, **CI/CD**, **Bot**, **Automation**  
- **Top repositories** and **top human actors** for these operations  
- A **prominent warning** if **anonymous** access to **private** repositories appears—often a sign of **leaked credentials** or **misconfigured deploy keys**

You can narrow by operation type (e.g. clones vs pushes).

### Activity map

A **world map** (e.g. OpenStreetMap) with **markers or bubbles** sized by activity. **Tooltips** show location, event counts, and sample IPs/actors (e.g. a city with events from a specific bot).

### Categories and event table

**Pill filters**: **All**, **Boundary**, **PAT**, **Trust**, **Membership**, **Git Ops**, **Other**.

- **Trust** might include outside collaborators, protected branches, webhooks.  
- **Other** often captures routine repo lifecycle (`repo.create`, `repo.update`, merge settings, access).

Below the filters, a **searchable, paginated table** lists every classified row: **Severity**, **Timestamp**, **Actor**, **Action**, **Category**, **Repository**.

You may also see a compact **breakdown by action** (e.g. share of `git.clone` vs `git.push` vs policy events) to spot dominant patterns at a glance.

---

## Score reference (typical model)

| Score band | Meaning |
|------------|---------|
| **80–100** | Good |
| **50–79** | Needs attention |
| **0–49** | At risk |

Typical **factor impacts** include: critical/high/medium event counts, **geographic spread** of IPs, **IP-to-human ratio**, and **boundary** (allow list) churn. Exact labels and math match your Hub build.

---

## Value at a glance

| Need | What GitHub Audit gives you |
|------|-----------------------------|
| **Immediate visibility** | Security insights from day 1, no device enrollment |
| **Boundary drift** | Who changed IP allow lists and when |
| **Token governance** | PAT grants, revocations, fingerprints, and policy signals |
| **Trust & membership** | Apps, collaborators, branches, webhooks |
| **Git misuse signals** | Anonymous or unusual Git access to private repos |
| **Hotspot detection** | Top actors, repos, IPs, and geography |
| **Investigation** | Severity bar, category pills, search, clickable score factors |

---

## Tips

1. Enable **[IP disclosure](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/managing-allowed-ip-addresses-for-your-organization)** in GitHub org settings for richer IP and map data.  
2. Use **30–90 days** for operational reviews; **180 days** aligns with GitHub’s audit retention window for deeper reviews.  
3. Start from **View last audit** in **Settings → Integrations** when you only need the latest completed run.  
4. Treat **anonymous + private repo** alerts as high priority until ruled out.

---

## Where to click in Hub

| Goal | Where |
|------|--------|
| Connect GitHub | **Settings → Integrations → GitHub → Connect** |
| Start a new audit | **Settings → Integrations → GitHub → Audit** (choose lookback, then start) |
| Open latest audit | **View last audit** (same row) or `/dashboard/{domainId}/audit/latest` |
| Open a specific run | `/dashboard/{domainId}/audit/{auditId}` |

---

## Technical notes

- **Data source**: GitHub Organization Audit Log API  
- **Retention**: GitHub retains org audit events for **180 days**  
- **Processing**: Async worker; results stored in object storage; GitHub App authentication  
- **UI detail**: Some layouts (e.g. guided stepper vs. Integrations-only entry) may vary by release; the workflow above is the full intended journey from setup through report.
