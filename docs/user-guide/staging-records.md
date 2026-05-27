# SignalMDM Phase 1 — User Guide  
## Module: Staging Records

**Document type:** End-user system manual  
**Audience:** Data stewards, operations users, tenant administrators, platform administrators  
**Phase:** Foundation Layer (Phase 1)  
**Classification:** Internal — Operational use

---

## Document control

| Field | Value |
|-------|--------|
| Module name | Staging Records |
| Menu path | Foundation → Staging Records |
| Access | Users with Staging Records view permission |
| Last updated | Phase 1 release |

---

## 1. Module purpose and scope

### 1.1 What Staging Records is

Staging Records is the **downstream inspection workspace** for data that has been **prepared** after raw landing. Each row represents one **staging record** linked to exactly one raw record from the same ingestion batch. In Phase 1, the staged content is a **direct copy** of what was received from the source—mapping and golden-record rules are planned for later phases.

Staging Records helps you answer:

- Did every raw row produce a staging row (1:1 alignment)?
- What is the current **staging state** of each record?
- How do raw input and staged output compare side by side?
- Are duplicate fingerprints visible at the staging layer?

### 1.2 Where Staging Records fits in the workflow

1. **Upload Data** — upload and validate a file.  
2. **Ingestion Runs** — execute the batch.  
3. **Raw Landing** — verify immutable source rows.  
4. **Staging Records** — review prepared rows before enterprise mapping (Phase 2+).

Open Staging Records when the ingestion run has reached **Staging created** or **Completed**, and raw and staging counts on the runs table show **1:1** lineage.

### 1.3 What you can and cannot do in Phase 1

| Allowed | Not available in Phase 1 |
|---------|---------------------------|
| Select a run and browse staging rows | Change staging state (e.g. mark as Mapped) |
| Search and filter records | Edit staged field values |
| Open the record drawer (four tabs) | Export the full table (button disabled) |
| Compare raw vs staged JSON in the drawer | Approve records for golden master |
| Delete an entire ingestion run (with confirmation) | Delete a single staging row |
| Navigate to Raw Landing for the same run | View a combined list across all runs |

### 1.4 Who can access Staging Records

You need permission to view the **Staging Records** screen. Platform administrators must select the correct **tenant** in **Tenant Scope** before records load. The breadcrumb shows **Platform → {Tenant name} → Staging Records** for platform users.

[INSERT SCREENSHOT — Staging Records — Page header and breadcrumb]

---

## 2. Screen layout overview

### 2.1 Page header

- **Title:** Staging Records  
- **Description:** Staging rows are scoped per ingestion run and should align 1:1 with Raw Landing for that batch.  
- **Refresh:** Reloads data.  
- **Export:** Disabled in Phase 1.

[INSERT SCREENSHOT — Staging Records — Header with Refresh and disabled Export]

### 2.2 Ingestion runs table (lineage picker)

The same **ingestion runs** table used on Raw Landing appears at the top. Select a run to load its staging grid.

| Column | What it tells you |
|--------|-------------------|
| Run ID | Batch identifier (short form) |
| Source | Source system name |
| Entity | Entity type |
| Run type | Ingestion type |
| Status | Batch job state |
| Raw | Raw record count |
| Staging | Staging record count |
| Lineage | **1:1** or **mismatch** |
| Started | Start time |
| Actions | **Raw**, **Staging**, **Delete** |

Click a row or **Staging** in Actions to activate the run.

[INSERT SCREENSHOT — Staging Records — Ingestion runs table]

### 2.3 Lineage banner

When a run is selected, a banner displays:

- Run identifier and entity type  
- Raw → staging counts and whether they match Raw Landing **1:1**  
- **View raw records →** — opens Raw Landing for the same batch  

[INSERT SCREENSHOT — Staging Records — Lineage banner with link to Raw Landing]

### 2.4 Overview hint

If you have not selected a run but the runs table shows batches with **mismatch** lineage, a short hint may appear explaining that mixed “all runs” record lists are hidden because counts are tracked per batch.

### 2.5 Empty state

With no run selected, the staging table is hidden and a message instructs you to **select an ingestion run** in the table above.

[INSERT SCREENSHOT — Staging Records — Empty state when no run is selected]

### 2.6 Summary cards (run selected)

| Card | Meaning |
|------|---------|
| Total (this run) | Total staging rows for the batch |
| Loaded | Rows loaded on the current screen |
| Ready for mapping | Rows in staging state **Ready for mapping** |
| Mapped | Rows in state **Mapped** (uncommon in Phase 1) |
| Rejected | Rows in state **Rejected** |
| Avg DQ (placeholder) | Average data-quality score (illustrative in Phase 1) |

[INSERT SCREENSHOT — Staging Records — Summary cards]

### 2.7 Search, filters, and record table

**Search** — Find by staging ID, source record ID, raw ID, entity, or source name.

**Filters:**

- **All sources** — One source system  
- **All entities (from runs)** — Entity types present in loaded runs  
- **All staging states** — Ready for mapping, Mapped, Rejected  
- **All validation** — Passed, Failed, Partial, Pending  
- **Run** — Switch batch or overview  

**Table columns:**

| Column | Description |
|--------|-------------|
| Staging ID | System identifier for the staging row |
| Source record ID | Business key from the source |
| Entity type | Entity label |
| Staging state | Ready for mapping, Mapped, or Rejected |
| Validation | Validation outcome (Phase 1 placeholder) |
| DQ score | Data quality score 0–100 (Phase 1 placeholder) |
| Created at | When the staging row was created |
| Actions | Click the row to open the **record drawer** |

**Pagination** — Twenty-five rows per page.

[INSERT SCREENSHOT — Staging Records — Record table with filters]

---

## 3. Staging state reference

| Staging state | Meaning in Phase 1 | Typical volume |
|---------------|-------------------|----------------|
| **Ready for mapping** | Row created by the pipeline; awaiting future mapping rules | Most rows after a successful run |
| **Mapped** | Reserved for when mapping is applied in a later phase | Rare in Phase 1 |
| **Rejected** | Reserved for rejected records in a later phase | Rare in Phase 1 |

In Phase 1, a successful ingestion leaves essentially all rows in **Ready for mapping**.

[INSERT SCREENSHOT — Staging Records — Staging state badges in table]

---

## 4. Validation and data quality (Phase 1)

### 4.1 Validation column

The **Validation** column shows one of:

| Value | Typical display meaning (Phase 1) |
|-------|-----------------------------------|
| **PASSED** | Row is in Ready for mapping or Mapped state |
| **FAILED** | Row is in Rejected state |
| **PENDING** | Other cases |
| **PARTIAL** | Shown when applicable in filters |

Phase 1 uses **illustrative** validation until a full rules engine is delivered. Treat validation as orientation, not a legal compliance sign-off.

### 4.2 DQ score column

The **DQ score** is a number from 0 to 100 shown with color:

| Score range | Color indication |
|-------------|------------------|
| 90 and above | High (green) |
| 65 to 89 | Medium (amber) |
| Below 65 | Low (red) |

The summary card **Avg DQ (placeholder)** averages scores for loaded rows. In Phase 1 this score is **for demonstration only** and does not reflect a production data-quality engine.

[INSERT SCREENSHOT — Staging Records — DQ score colors in table]

---

## 5. Duplicate records

Duplicate detection mirrors Raw Landing: rows with the same data fingerprint within your tenant may show duplicate indicators.

| UI element | Meaning |
|------------|---------|
| Highlighted table row | Row is flagged duplicate |
| **Within-run dup** / **Cross-run dup** | Scope of the duplicate |
| **First by** / date under status | Who introduced the first occurrence |

Open the **Overview** tab in the record drawer for the full duplicate callout, including references to the original raw record, run, and staging ID when available.

[INSERT SCREENSHOT — Staging Records — Duplicate row in table]

[INSERT SCREENSHOT — Staging Records — Drawer Overview tab with duplicate callout]

---

## 6. Record drawer (detail panel)

Click any table row to open the **drawer** on the right. It has four tabs.

### 6.1 Overview tab

Shows:

- Staging ID and Raw Record ID  
- Tenant name  
- Staging state and Validation status badges  
- Source system, Created at, Ingestion run, Run pipeline state, Entity  
- Duplicate callout (if applicable)  
- **Data quality score** card with bar (Phase 1 placeholder)  

[INSERT SCREENSHOT — Staging Records — Drawer Overview tab]

### 6.2 Raw Payload tab

- Full JSON as received in raw landing  
- **Copy JSON** button  
- Field count  

Use this tab to confirm what entered the platform.

[INSERT SCREENSHOT — Staging Records — Drawer Raw Payload tab]

### 6.3 Canonical / Staged tab

- Note: *Phase 1: staged payload is a verbatim copy of raw. Mapping transforms arrive in later phases.*  
- Side-by-side panels: **Raw input** and **Staged entity_data**  
- **Copy staged JSON** button  

For Phase 1, both panels should match. Differences in future phases indicate mapping activity.

[INSERT SCREENSHOT — Staging Records — Drawer Canonical Staged tab side by side]

### 6.4 Validation tab

- Note: *Phase 1: rule rows are illustrative until DQ engine is wired.*  
- **DQ rules** list with PASS, FAIL, WARN, or PENDING per rule  
- Example rules: Payload not empty, Source key present, Tenant scope, Run consistency, Duplicate check (Phase 2)  
- DQ score card repeated  

[INSERT SCREENSHOT — Staging Records — Drawer Validation tab]

Close the drawer with **✕** or by clicking the dimmed area outside.

---

## 7. Ingestion run actions

### 7.1 Delete an ingestion run

| Step | System behavior |
|------|-----------------|
| 1 | Click **Delete** on a run that is not **Running** |
| 2 | If still running, alert: wait or manage from **Ingestion Runs** |
| 3 | Confirm: *Delete this ingestion run and all of its raw and staging records? This cannot be undone.* |
| 4 | On success | Green notification: **Ingestion run deleted successfully.** Run removed from list |
| 5 | On failure | Red notification: **Failed to delete run:** followed by reason; error banner may also appear |

[INSERT SCREENSHOT — Staging Records — Delete run confirmation dialog]

[INSERT SCREENSHOT — Staging Records — Success notification after delete]

### 7.2 Deep links

You can open Staging Records directly for a batch if your administrator shares a link that includes the run identifier in the browser address.

---

## 8. Procedure: Review staging records after ingestion

**Objective:** Confirm staging rows exist and align with raw landing for a completed batch.

**Prerequisites:**

- Ingestion run status **Completed** (or **Staging created** with counts stable).  
- Staging Records view permission.  
- Correct tenant selected (platform administrators).

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open **Foundation → Staging Records** | Runs table visible |
| 2 | Confirm tenant scope (platform admin) | Breadcrumb shows correct tenant |
| 3 | Find the batch; check **Lineage** column | **1:1** when pipeline succeeded |
| 4 | Click the run row | Summary cards and table appear |
| 5 | Review **Ready for mapping** count | Should match raw row count for successful runs |
| 6 | Filter **All staging states** → Ready for mapping | Table shows expected rows |
| 7 | Click a row | Drawer opens on Overview |
| 8 | Open **Raw Payload** and **Canonical / Staged** tabs | Content matches in Phase 1 |
| 9 | Open **Validation** tab | Illustrative rules and DQ score display |
| 10 | For duplicates, read Overview callout | First-seen user and references shown |
| 11 | Click **View raw records →** | Raw Landing opens for same batch |

[INSERT SCREENSHOT — Staging Records — End-to-end workflow with drawer open]

---

## 9. Messages, errors, and troubleshooting

| Message / state | Cause | Recommended action |
|-----------------|-------|-------------------|
| *Loading staging records…* | Fetch in progress | Wait |
| *No staging records found* | No rows or filters too narrow | Clear filters; verify run on Ingestion Runs |
| Empty state (no run) | No run selected | Select a run above |
| Red error banner | Load or permission failure | Refresh; check tenant scope |
| **Ingestion run deleted successfully.** | Delete completed | None — run removed |
| **Failed to delete run:** … | Delete rejected | Read reason; check if run is still Running |
| Lineage **mismatch** | Partial or failed pipeline | See tooltip; review **Ingestion Runs** and **Raw Landing** |
| Export disabled | Phase 1 | Use drawer copy actions for samples |

### 9.1 When raw and staging counts do not match

| Situation | What it usually means |
|-----------|------------------------|
| Staging count lower than raw | Run failed mid-pipeline or staging still processing |
| Staging count higher than raw | Unexpected — contact support with run ID |
| Banner note not 1:1 | Read the pipeline note text on the banner |

---

## 10. Security and data handling notes

- Staging Records displays the same sensitive source data as Raw Landing. Handle exports and screenshots per policy.  
- Deleting a run from this screen removes **all** related raw and staging data permanently. Restrict delete permission to authorized administrators.  
- Tenant scope must be correct before interpreting duplicate or volume metrics.

---

## 11. Screenshot index (for document production)

1. [INSERT SCREENSHOT — Staging Records — Page header and breadcrumb]  
2. [INSERT SCREENSHOT — Staging Records — Header with Refresh and disabled Export]  
3. [INSERT SCREENSHOT — Staging Records — Ingestion runs table]  
4. [INSERT SCREENSHOT — Staging Records — Lineage banner with link to Raw Landing]  
5. [INSERT SCREENSHOT — Staging Records — Empty state when no run is selected]  
6. [INSERT SCREENSHOT — Staging Records — Summary cards]  
7. [INSERT SCREENSHOT — Staging Records — Record table with filters]  
8. [INSERT SCREENSHOT — Staging Records — Staging state badges in table]  
9. [INSERT SCREENSHOT — Staging Records — DQ score colors in table]  
10. [INSERT SCREENSHOT — Staging Records — Duplicate row in table]  
11. [INSERT SCREENSHOT — Staging Records — Drawer Overview tab with duplicate callout]  
12. [INSERT SCREENSHOT — Staging Records — Drawer Overview tab]  
13. [INSERT SCREENSHOT — Staging Records — Drawer Raw Payload tab]  
14. [INSERT SCREENSHOT — Staging Records — Drawer Canonical Staged tab side by side]  
15. [INSERT SCREENSHOT — Staging Records — Drawer Validation tab]  
16. [INSERT SCREENSHOT — Staging Records — Delete run confirmation dialog]  
17. [INSERT SCREENSHOT — Staging Records — Success notification after delete]  
18. [INSERT SCREENSHOT — Staging Records — End-to-end workflow with drawer open]

---

## 12. Related modules

| Module | Menu path | When to use |
|--------|-----------|-------------|
| Raw Landing | Foundation → Raw Landing | Verify source payloads |
| Ingestion Runs | Foundation → Ingestion Runs | Monitor or troubleshoot batches |
| Upload Data | Foundation → Upload Data | Initial file upload |

---

*End of Staging Records user guide — Phase 1*
