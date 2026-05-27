# SignalMDM Phase 1 — User Guide  
## Module: Raw Landing

**Document type:** End-user system manual  
**Audience:** Data stewards, operations users, tenant administrators, platform administrators  
**Phase:** Foundation Layer (Phase 1)  
**Classification:** Internal — Operational use

---

## Document control

| Field | Value |
|-------|--------|
| Module name | Raw Landing |
| Menu path | Foundation → Raw Landing |
| Access | Users with Raw Landing view permission |
| Last updated | Phase 1 release |

---

## 1. Module purpose and scope

### 1.1 What Raw Landing is

Raw Landing is the **audit and inspection workspace** for source data **as it was received** by SignalMDM. After you upload a file and an ingestion run processes that batch, every parsed row appears here as a **raw record**. These records are **read-only**: the system does not allow you to change or delete individual rows from this screen.

Raw Landing answers operational questions such as:

- Did the expected number of rows land for this ingestion batch?
- What exact field values did the source system deliver?
- Are any rows flagged as duplicates within this tenant?
- Is the batch ready to review in Staging Records?

### 1.2 Where Raw Landing fits in the workflow

Raw Landing is the **third step** in the Phase 1 data path:

1. **Upload Data** — prepare and validate a file against an entity type.  
2. **Ingestion Runs** — start and monitor the batch job.  
3. **Raw Landing** — inspect immutable source rows for the selected run.  
4. **Staging Records** — review the prepared copy of each row for downstream mapping (future phases).

You should open Raw Landing **after** an ingestion run has at least finished loading raw data (status **Raw loaded** or **Completed**).

### 1.3 What you can and cannot do in Phase 1

| Allowed | Not available in Phase 1 |
|---------|---------------------------|
| Select an ingestion run and browse its rows | Edit a raw record’s payload |
| Search and filter within a run | Delete a single raw row |
| Open payload and metadata views | Re-run mapping from this screen |
| Download one row as a JSON file | Export the full table (button is disabled) |
| Navigate to Staging Records for the same run | Mix records from multiple runs in one table |

### 1.4 Who can access Raw Landing

Access is controlled by your organization’s role. You must have permission to view the **Raw Landing** screen. If the menu item is missing or the page shows an access error, contact your platform administrator.

**Platform administrators** (users operating across tenants) must **select a tenant** in the **Tenant Scope** bar at the top of the application before data appears. The breadcrumb at the top of the page shows your context, for example: **Platform → Acme Corp → Raw Landing**.

**Tenant users** are automatically scoped to their own organization; the breadcrumb shows the screen name only.

[INSERT SCREENSHOT — Raw Landing — Page header and breadcrumb]

---

## 2. Screen layout overview

When you open Raw Landing, the screen is organized into distinct areas from top to bottom.

### 2.1 Page header

- **Title:** Raw Landing  
- **Description:** Explains that records are scoped **per ingestion run** and that each run is a separate batch.  
- **Refresh:** Reloads run list and record data for the current tenant.  
- **Export:** Shown but **disabled** in Phase 1. Hovering indicates that export is not yet available.

[INSERT SCREENSHOT — Raw Landing — Header with Refresh and disabled Export]

### 2.2 Ingestion runs table (lineage picker)

The large table at the top lists **all ingestion runs** for the current tenant. This is your **run selector**. You must choose a run before the main record grid appears.

**Columns:**

| Column | What it tells you |
|--------|-------------------|
| Run ID | Short identifier for the batch (full ID is used internally) |
| Source | Name of the registered source system |
| Entity | Entity type for this batch (e.g. CUSTOMER) |
| Run type | Type of ingestion (e.g. full load) |
| Status | Current state of the batch job |
| Raw | Number of raw records loaded for this run |
| Staging | Number of staging records created for this run |
| Lineage | **1:1** if raw and staging counts match; **mismatch** if they do not (hover for explanation) |
| Started | Date and time the run started |
| Actions | Shortcuts to open **Raw** or **Staging** for this run, and **Delete** (when permitted) |

**How to select a run:** Click anywhere on the run’s row. The active run is highlighted. You can also use the **Raw** action button in the Actions column.

[INSERT SCREENSHOT — Raw Landing — Ingestion runs table with one run selected]

### 2.3 Run summary banner

After you select a run, a banner appears below the runs table. It shows:

- The active run identifier  
- Entity type for the batch  
- Raw count versus staging count, and whether they are aligned **1:1**  
- A link **View staging →** to open Staging Records for the same batch  

Use this banner to confirm the pipeline completed as expected before drilling into individual rows.

[INSERT SCREENSHOT — Raw Landing — Run summary banner with View staging link]

### 2.4 Empty state (no run selected)

If no run is selected, the record table area is replaced by a message explaining that you must **select an ingestion run** above. Raw Landing intentionally does **not** show a combined list of all runs’ records in one grid, to avoid mixing batches.

[INSERT SCREENSHOT — Raw Landing — Empty state when no run is selected]

### 2.5 Summary cards (run selected)

Six summary cards appear above the record table:

| Card | Meaning |
|------|---------|
| Total (this run) | Total record count reported for this batch |
| Loaded | Rows currently loaded on screen |
| Completed | Rows whose processing status is **Completed** |
| Processing | Rows still in **Processing** |
| Failed | Rows whose processing status is **Failed** |
| Duplicates | Rows flagged as **Duplicate** |

Use these cards for a quick health check before opening individual records.

[INSERT SCREENSHOT — Raw Landing — Summary cards]

### 2.6 Search, filters, and record table

**Search box** — Type to find records by ID, source record ID, entity, or source name. The system also refreshes results from the server after you pause typing.

**Filter dropdowns:**

- **All Sources** — Limit to one source system.  
- **All Entities** — Limit to one entity type.  
- **All Statuses** — Limit to Pending, Processing, Completed, Failed, or Duplicate.  
- **Run** — Switch to another run or return to overview (no records).

A label shows how many rows match your filters and how many appear on the current page.

**Record table columns:**

| Column | Description |
|--------|-------------|
| Raw Record ID | System identifier for the row |
| Source Record ID | Business key from the source file (e.g. customer ID) |
| Entity Type | Entity label for this row |
| Source System | Name of the source system |
| Processing Status | Current processing state (see Section 4) |
| Received At | When the row was stored |
| Checksum | Short form of the data fingerprint (full value in metadata) |
| Actions | **View Payload**, **Metadata**, **JSON** download |

**Pagination** — Twenty-five rows per page. Use the page numbers or arrows at the bottom to move through large batches.

[INSERT SCREENSHOT — Raw Landing — Record table with filters]

---

## 3. Processing status reference

Each row displays a **Processing Status** that reflects how far the ingestion batch has progressed for that record.

| Status | Typical meaning | What you should do |
|--------|-----------------|-------------------|
| **Pending** | Batch has not finished loading raw data | Wait for the ingestion run to advance; refresh the page |
| **Processing** | Batch is still running through the pipeline | Monitor the run on **Ingestion Runs**; refresh periodically |
| **Completed** | Row is loaded and linked to staging when the run finished successfully | Proceed to Staging Records for mapping readiness |
| **Failed** | The ingestion run failed | Review the run on **Ingestion Runs** for error details |
| **Duplicate** | Row matches another record’s data fingerprint in this tenant | Read duplicate details in the table and in **Metadata** (Section 5) |

Status badges use color coding on screen (green for completed, red for failed, amber for duplicate, and so on).

[INSERT SCREENSHOT — Raw Landing — Processing status badges in table]

---

## 4. Duplicate records

### 4.1 Why duplicates appear

SignalMDM computes a **checksum** (data fingerprint) for each row. If the same payload was seen before **within your tenant**, the row may be marked **Duplicate**.

Two scopes are shown:

| Label in UI | Meaning |
|-------------|---------|
| **Within-run dup** | A later row in the **same batch** shares the same fingerprint as an earlier row in that batch |
| **Cross-run dup** | This batch’s row matches a row that was loaded in an **earlier ingestion run** for the same tenant |

The table may show **who first introduced** the data (**First by** username) and **when**, directly under the status badge.

### 4.2 What duplicate does not mean

- Duplicate does **not** mean the row was rejected. Cross-run duplicates are still stored so you can audit them.  
- Duplicate within the **same file** at upload time may have been skipped during load; you will see fewer rows than file lines in that case. Check the ingestion run summary on **Ingestion Runs**.

### 4.3 How to investigate a duplicate

1. Locate the row with the **Duplicate** status.  
2. Click **Metadata**.  
3. Read the yellow **Duplicate record** callout at the top.  
4. Note **First added by**, **First added at**, and the referenced raw record and run identifiers.  
5. If needed, open the original run from the ingestion runs table and compare payloads.

[INSERT SCREENSHOT — Raw Landing — Duplicate row in table]

[INSERT SCREENSHOT — Raw Landing — Metadata tab with duplicate callout]

---

## 5. Viewing record details

### 5.1 Payload view

1. In the Actions column, click **View Payload**.  
2. A dialog opens showing the full JSON received from the source.  
3. Use **Copy JSON** to copy the content to your clipboard.  
4. Close the dialog with **✕** or by clicking outside.

[INSERT SCREENSHOT — Raw Landing — Payload dialog]

### 5.2 Metadata view

1. Click **Metadata** in the Actions column (or open the dialog and switch to the **Metadata** tab).  
2. Review system fields: Raw Record ID, Source Record ID, Entity, Source System, Tenant, Ingestion Run, Run pipeline state, Processing status, Received At, Field count, and Checksum.  
3. For duplicate rows, additional fields show first-seen attribution.

[INSERT SCREENSHOT — Raw Landing — Metadata dialog]

### 5.3 Download single row as JSON

Click **⬇ JSON** in the Actions column. Your browser downloads a file named with the raw record ID containing the payload. Use this for offline review or to attach evidence to a ticket.

---

## 6. Ingestion run actions from Raw Landing

### 6.1 Switching runs

- Click another row in the **Ingestion runs** table, or  
- Use the **Run** dropdown above the record table, or  
- Open a bookmark or link shared with a run ID in the address bar.

### 6.2 Opening Staging for the same batch

- Click **View staging →** in the run banner, or  
- In the runs table Actions column, click **Staging**.

### 6.3 Deleting an ingestion run

**Delete** removes the entire batch—including files, raw records, and staging records—and cannot be undone.

| Step | System behavior |
|------|-----------------|
| 1 | Click **Delete** on a run that is **not** still **Running** |
| 2 | If the run is still processing, an alert tells you to wait or manage the run from **Ingestion Runs** |
| 3 | Confirm the deletion in the browser dialog |
| 4 | On success, the run disappears from the list; if it was selected, the record area returns to empty state |
| 5 | On failure, a red message appears at the top of the page |

[INSERT SCREENSHOT — Raw Landing — Delete run confirmation dialog]

---

## 7. Procedure: Inspect raw records for an ingestion batch

**Objective:** Verify that source data landed correctly for a completed or raw-loaded batch.

**Prerequisites:**

- You are signed in with Raw Landing access.  
- An ingestion run exists with status **Raw loaded**, **Staging created**, or **Completed**.  
- Platform administrators have selected the correct **tenant** in Tenant Scope.

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Open **Foundation → Raw Landing** | Page loads; ingestion runs table is visible |
| 2 | (Platform admin) Confirm tenant in scope bar and breadcrumb | Correct tenant name appears |
| 3 | Locate your batch in the ingestion runs table | Run shows status and raw count greater than zero |
| 4 | Click the run row or **Raw** in Actions | Run highlights; summary cards and record table appear |
| 5 | Review summary cards | Completed count aligns with expectations; note any Failed or Duplicate counts |
| 6 | Confirm banner shows raw → staging alignment | **1:1** when pipeline finished normally |
| 7 | Use Search or filters to find a specific source record ID | Matching rows appear in the table |
| 8 | Click **View Payload** on a sample row | JSON matches source file content |
| 9 | Click **Metadata** on the same row | IDs, checksum, and run reference are consistent |
| 10 | For duplicates, read Metadata callout | First-seen user and date are documented |
| 11 | Click **View staging →** | Staging Records opens for the same batch |

[INSERT SCREENSHOT — Raw Landing — End-to-end workflow with run selected and table populated]

---

## 8. Messages, errors, and troubleshooting

### 8.1 Common on-screen messages

| Message / state | Cause | Recommended action |
|-----------------|-------|-------------------|
| *Loading raw records…* | Data is being fetched | Wait a few seconds |
| *No raw records found* | Filters exclude all rows, or batch has no rows | Clear filters; verify run on Ingestion Runs |
| *Select an ingestion run…* (empty area) | No run selected | Click a run in the table above |
| Red banner with error text | Network, permission, or server issue | Refresh; verify tenant scope; contact support |
| *This run is still processing…* (alert on delete) | Run status is **Running** | Wait for completion or cancel from Ingestion Runs |
| *Delete this ingestion run…* (confirm) | You initiated delete | Confirm only if batch should be permanently removed |
| Export button disabled | Phase 1 limitation | Use per-row **JSON** download if needed |

### 8.2 Run status reference (ingestion runs table)

| Status | User interpretation |
|--------|---------------------|
| Created | Batch created; processing not started or just started |
| Running | Pipeline actively loading or transforming data |
| Raw loaded | Raw rows stored; staging may still be in progress |
| Staging created | Staging rows created; run may still be finalizing |
| Completed | Batch finished successfully |
| Failed | Batch failed; inspect **Ingestion Runs** for errors |

### 8.3 Lineage mismatch

If the **Lineage** column shows **mismatch** instead of **1:1**, hover for the explanation. Common cases:

- Run **failed** before staging finished — staging count may be lower.  
- Staging still in progress — refresh after the run reaches **Completed**.  
- Unexpected counts — escalate to support with run ID and screenshot.

---

## 9. Security and data handling notes

- Raw Landing displays **production source data**. Follow your organization’s data classification and screen-capture policies when taking screenshots for tickets.  
- Records are **immutable** on this screen to preserve an audit trail of what was received.  
- Duplicate visibility is limited to **your tenant**; you will not see other tenants’ data when scoped correctly.  
- Do not share direct browser links containing run IDs outside approved channels.

---

## 10. Screenshot index (for document production)

Insert the following captures when publishing this manual:

1. [INSERT SCREENSHOT — Raw Landing — Page header and breadcrumb]  
2. [INSERT SCREENSHOT — Raw Landing — Header with Refresh and disabled Export]  
3. [INSERT SCREENSHOT — Raw Landing — Ingestion runs table with one run selected]  
4. [INSERT SCREENSHOT — Raw Landing — Run summary banner with View staging link]  
5. [INSERT SCREENSHOT — Raw Landing — Empty state when no run is selected]  
6. [INSERT SCREENSHOT — Raw Landing — Summary cards]  
7. [INSERT SCREENSHOT — Raw Landing — Record table with filters]  
8. [INSERT SCREENSHOT — Raw Landing — Processing status badges in table]  
9. [INSERT SCREENSHOT — Raw Landing — Duplicate row in table]  
10. [INSERT SCREENSHOT — Raw Landing — Metadata tab with duplicate callout]  
11. [INSERT SCREENSHOT — Raw Landing — Payload dialog]  
12. [INSERT SCREENSHOT — Raw Landing — Metadata dialog]  
13. [INSERT SCREENSHOT — Raw Landing — Delete run confirmation dialog]  
14. [INSERT SCREENSHOT — Raw Landing — End-to-end workflow with run selected and table populated]

---

## 11. Related modules

| Module | Menu path | When to use |
|--------|-----------|-------------|
| Upload Data | Foundation → Upload Data | Before starting a batch |
| Ingestion Runs | Foundation → Ingestion Runs | Start, monitor, or troubleshoot batches |
| Staging Records | Foundation → Staging Records | After raw load; review prepared rows |

---

*End of Raw Landing user guide — Phase 1*
