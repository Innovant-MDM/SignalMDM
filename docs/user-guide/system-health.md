# SignalMDM Phase 1 — User Guide  
## Module: System Health

**Document type:** End-user system manual  
**Audience:** Platform administrators, IT operations, system administrators  
**Phase:** Foundation Layer (Phase 1)  
**Classification:** Internal — Operational use

---

## Document control

| Field | Value |
|-------|--------|
| Module name | System Health |
| Menu path | Admin → System Health |
| Access | Users with System Health view permission (typically administrators) |
| Last updated | Phase 1 release |

---

## 1. Module purpose and scope

### 1.1 What System Health is

System Health is an **operations dashboard** that gives administrators a single place to check whether core platform components are available and to view **high-level counts** of tenants, source systems, and ingestion runs across the installation.

Use System Health for **infrastructure readiness checks**—for example after deployment, maintenance, or when users report that ingestion jobs are not progressing.

### 1.2 What System Health is not

| System Health | API Logs (separate module) |
|---------------|----------------------------|
| Component up/down and latency summary | Individual HTTP request history |
| Aggregate tenant/source/run counts | Searchable request and error traces |
| Short operational summary panel | Full audit trail for API troubleshooting |

System Health does **not** replace **Ingestion Runs**, **Raw Landing**, or **Staging Records** for investigating data in a specific batch.

### 1.3 Who can access System Health

Access is restricted to **administrative** roles. Standard tenant data stewards typically do not see **Admin → System Health** in the menu. If you receive an access denied message when opening the page, request the **System Health** permission from your platform administrator.

[INSERT SCREENSHOT — Health System Preview page — Full dashboard]

---

## 2. Screen layout overview

The page is divided into a header and three main panels arranged in a grid.

### 2.1 Page header

- **Title:** System Health  
- **Subtitle:** Real-time monitoring of platform components and infrastructure.  
- **Refresh Now:** Immediately runs a new health check. While loading, the button label changes to **Refreshing...** and the button is disabled.

[INSERT SCREENSHOT — Health System Preview page — Header and Refresh Now button]

### 2.2 Error banner

If the health check cannot be loaded (network outage, session expired, or server error), a **red banner** appears below the header with a message such as:

**Failed to load system health.**

Resolve connectivity or sign in again, then click **Refresh Now**.

[INSERT SCREENSHOT — Health System Preview page — Error banner on load failure]

### 2.3 Infrastructure Health panel

Located in the upper-left card, titled **Infrastructure Health**. Lists platform components with:

- A colored status indicator (green = healthy, red = unhealthy)  
- Component name  
- Response time where applicable (e.g. milliseconds for database)  
- Text status: **UP** or **DOWN**

[INSERT SCREENSHOT — Health System Preview page — Infrastructure Health panel all UP]

### 2.4 Platform Summary panel

Located in the upper-right card, titled **Platform Summary**.

**Metric tiles:**

| Metric | What it represents |
|--------|-------------------|
| **Tenants** | Total number of tenants registered on the platform |
| **Sources** | Total number of source systems registered |
| **Runs** | Total number of ingestion runs recorded |

**Important:** These counts are **platform-wide**. They are **not** filtered by the Tenant Scope bar used on data screens. A platform administrator viewing tenant “Acme” will still see global totals here.

**Environment details** (below the metrics):

| Badge | Meaning |
|-------|---------|
| **ENV:** | Deployment environment label (e.g. DEVELOPMENT) |
| **UPDATED:** | Local time of the last successful health check |

[INSERT SCREENSHOT — Health System Preview page — Platform Summary metrics and environment badges]

### 2.5 System Logs (Operational) panel

Full-width panel at the bottom with a dark console-style area. It shows **summary lines** generated when the page loads or refreshes—not a live tail of the **API Logs** database.

Typical line types:

| Prefix | Color (on screen) | Example content |
|--------|-------------------|-----------------|
| [INFO] | Green | Health check routine initiated |
| [INFO] | Green | Component connectivity verified with latency |
| [DEBUG] | Blue | Active ingestion runs tracked: {count} |
| [WARN] | Amber | No source systems detected (when source count is zero) |
| [INFO] | Green | All system components operational |

[INSERT SCREENSHOT — Health System Preview page — System Logs Operational panel]

---

## 3. Infrastructure components reference

| Component | What is monitored | Healthy indication | Unhealthy indication |
|-----------|-------------------|--------------------|-----------------------|
| **API Server** | Application server responding | UP | DOWN (unusual in normal operation) |
| **PostgreSQL** | Database connectivity and response time | UP with latency (e.g. 2.45ms) | DOWN |
| **Redis Cache** | Cache layer used by background processing | UP | DOWN |
| **Background Worker** | Worker availability (Phase 1 summary) | UP | DOWN |

### 3.1 Latency display

- Database checks show a time in milliseconds (e.g. **12.34ms**).  
- Some components show **N/A** when latency is not measured.  
- Use latency trends informally: a sudden large increase may warrant investigation even if status remains UP.

[INSERT SCREENSHOT — Health System Preview page — Component with PostgreSQL latency]

### 3.2 Component DOWN — operational impact

| Component DOWN | Likely user impact |
|----------------|-------------------|
| PostgreSQL | Most screens fail to load data; sign-in may fail |
| Redis Cache | Background ingestion jobs may not run; runs may stay **Running** |
| API Server | Entire application unavailable |
| Background Worker | Files may upload but batches do not complete |

[INSERT SCREENSHOT — Health System Preview page — Redis or PostgreSQL DOWN example]

---

## 4. Auto-refresh and manual refresh

| Behavior | Detail |
|----------|--------|
| **Automatic refresh** | Every **30 seconds** while you remain on the page |
| **Manual refresh** | Click **Refresh Now** at any time |
| **During refresh** | Button shows **Refreshing...**; panels update when complete |
| **Leaving the page** | Auto-refresh stops |

After infrastructure changes (database restart, cache flush, deployment), perform a manual refresh to confirm recovery.

[INSERT SCREENSHOT — Health System Preview page — Refresh in progress]

---

## 5. Procedure: Monitor platform health

**Objective:** Confirm the platform is fit for ingestion and browsing operations.

**Prerequisites:**

- Administrator account with System Health access.  
- Browser access to the SignalMDM application.

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Sign in with an administrator account | Admin menu visible |
| 2 | Open **Admin → System Health** | Dashboard loads |
| 3 | Review **Infrastructure Health** | API Server, PostgreSQL, Redis, Background Worker show **UP** |
| 4 | Note PostgreSQL latency | Reasonable value (environment-specific) |
| 5 | Review **Platform Summary** | Tenant, source, and run counts plausible for your environment |
| 6 | Check **ENV** and **UPDATED** badges | Environment correct; UPDATED shows recent time |
| 7 | Scroll **System Logs (Operational)** | Green INFO lines; no red failure lines |
| 8 | Click **Refresh Now** | Panels update; UPDATED time changes |
| 9 | If any component is DOWN | Follow Section 6 troubleshooting; check **API Logs** for related errors |

[INSERT SCREENSHOT — Health System Preview page — End-to-end healthy state]

---

## 6. Troubleshooting guide

### 6.1 Symptom: Failed to load system health

| Possible cause | Action |
|----------------|--------|
| Backend not running | Verify application service with IT |
| Network or VPN | Retry connection |
| Session expired | Sign out and sign in again |
| Insufficient permission | Confirm administrator role |

### 6.2 Symptom: PostgreSQL DOWN

| Possible cause | Action |
|----------------|--------|
| Database service stopped | Restart database; contact DBA |
| Wrong connection configuration | Escalate to deployment team |
| Firewall blocking | Verify network rules |

Users will typically see errors on **all data modules** until PostgreSQL is UP.

### 6.3 Symptom: Redis Cache DOWN

| Possible cause | Action |
|----------------|--------|
| Redis service stopped | Restart Redis |
| Ingestion stuck in **Running** | After Redis UP, refresh **Ingestion Runs**; may need to retry failed batches |

### 6.4 Symptom: Metrics show zero tenants or sources

| Possible cause | Action |
|----------------|--------|
| Fresh environment | Expected until tenants and sources are registered |
| Operational panel [WARN] | Register source systems; confirm tenant onboarding |

This does not necessarily mean a component is DOWN.

### 6.5 Symptom: Health page OK but users report ingestion failures

1. Confirm health page still shows UP on refresh.  
2. Open **Admin → API Logs** and search for failed requests around the incident time.  
3. Open **Ingestion Runs** for the affected tenant and inspect the specific batch status and error summary.  
4. Do not rely on **System Logs (Operational)** alone—it is a summary, not a full log store.

---

## 7. Understanding the operational log panel

### 7.1 Purpose in Phase 1

The operational log panel provides a **human-readable snapshot** after each refresh. It helps operators confirm that a health cycle ran and which components passed.

### 7.2 Limitations (important)

- Lines are **assembled on the health screen** from the latest check results—they are **not** copied line-for-line from API Logs.  
- Timestamps on each line reflect **your browser’s current time** when the panel renders, not necessarily the server log timestamp.  
- You **cannot** search, export, or filter this panel like API Logs.

For incident investigation, always use **API Logs** in addition to System Health.

[INSERT SCREENSHOT — Health System Preview page — Operational log panel close-up]

---

## 8. Security and governance notes

- System Health reveals **platform-scale** information (total tenants, total runs). Limit access to operations and administration teams.  
- Do not expose this screen in untrusted environments (public kiosks, unsecured displays).  
- Screenshots of health dashboards may contain environment names—classify according to policy.  
- A healthy dashboard does not guarantee data correctness in individual batches; always validate business data on **Raw Landing** and **Staging Records** when required.

---

## 9. Screenshot index (for document production)

1. [INSERT SCREENSHOT — Health System Preview page — Full dashboard]  
2. [INSERT SCREENSHOT — Health System Preview page — Header and Refresh Now button]  
3. [INSERT SCREENSHOT — Health System Preview page — Error banner on load failure]  
4. [INSERT SCREENSHOT — Health System Preview page — Infrastructure Health panel all UP]  
5. [INSERT SCREENSHOT — Health System Preview page — Platform Summary metrics and environment badges]  
6. [INSERT SCREENSHOT — Health System Preview page — System Logs Operational panel]  
7. [INSERT SCREENSHOT — Health System Preview page — Component with PostgreSQL latency]  
8. [INSERT SCREENSHOT — Health System Preview page — Redis or PostgreSQL DOWN example]  
9. [INSERT SCREENSHOT — Health System Preview page — Refresh in progress]  
10. [INSERT SCREENSHOT — Health System Preview page — End-to-end healthy state]  
11. [INSERT SCREENSHOT — Health System Preview page — Operational log panel close-up]

---

## 10. Related modules

| Module | Menu path | When to use |
|--------|-----------|-------------|
| API Logs | Admin → API Logs | Per-request errors and debugging |
| Ingestion Runs | Foundation → Ingestion Runs | Batch-level status when health is UP but jobs fail |
| Tenants | Platform → Tenants | Tenant onboarding (platform administrators) |

---

*End of System Health user guide — Phase 1*
