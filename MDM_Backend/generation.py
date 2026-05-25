from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib.colors import HexColor

# ── Colour Palette ──────────────────────────────────────────────────────────
NAVY       = HexColor("#0D1B2A")
STEEL_BLUE = HexColor("#1B4F72")
ACCENT     = HexColor("#2E86C1")
LIGHT_BLUE = HexColor("#D6EAF8")
MID_GREY   = HexColor("#BDC3C7")
LIGHT_GREY = HexColor("#F2F3F4")
WHITE      = colors.white
BLACK      = colors.black
RED_DARK   = HexColor("#922B21")
RED_LIGHT  = HexColor("#FADBD8")
GREEN_DARK = HexColor("#1E8449")
GREEN_LIGHT= HexColor("#D5F5E3")
AMBER      = HexColor("#B7770D")
AMBER_LIGHT= HexColor("#FCF3CF")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ── Style Sheet ──────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE_STYLE = S("DocTitle",
    fontName="Helvetica-Bold", fontSize=22,
    textColor=WHITE, alignment=TA_CENTER,
    spaceAfter=4, leading=28)

SUBTITLE_STYLE = S("DocSubtitle",
    fontName="Helvetica", fontSize=10,
    textColor=HexColor("#AED6F1"), alignment=TA_CENTER,
    spaceAfter=2, leading=14)

META_STYLE = S("DocMeta",
    fontName="Helvetica", fontSize=8.5,
    textColor=HexColor("#D6EAF8"), alignment=TA_CENTER,
    spaceAfter=2, leading=12)

VERDICT_STYLE = S("Verdict",
    fontName="Helvetica-Bold", fontSize=11,
    textColor=WHITE, alignment=TA_CENTER,
    spaceAfter=0, leading=16)

SECTION_STYLE = S("Section",
    fontName="Helvetica-Bold", fontSize=13,
    textColor=WHITE, alignment=TA_LEFT,
    spaceAfter=0, leading=18)

SUBSECTION_STYLE = S("Subsection",
    fontName="Helvetica-Bold", fontSize=10.5,
    textColor=STEEL_BLUE, alignment=TA_LEFT,
    spaceBefore=6, spaceAfter=3, leading=14)

BODY_STYLE = S("Body",
    fontName="Helvetica", fontSize=9.5,
    textColor=HexColor("#1A1A1A"), alignment=TA_JUSTIFY,
    spaceAfter=5, leading=14)

BODY_BOLD = S("BodyBold",
    fontName="Helvetica-Bold", fontSize=9.5,
    textColor=HexColor("#1A1A1A"), alignment=TA_LEFT,
    spaceAfter=3, leading=14)

BULLET_STYLE = S("Bullet",
    fontName="Helvetica", fontSize=9.2,
    textColor=HexColor("#1A1A1A"), alignment=TA_LEFT,
    leftIndent=14, spaceAfter=3, leading=13,
    bulletIndent=4, bulletText="•")

NUM_STYLE = S("Numbered",
    fontName="Helvetica", fontSize=9.2,
    textColor=HexColor("#1A1A1A"), alignment=TA_LEFT,
    leftIndent=14, spaceAfter=3, leading=13)

LABEL_STYLE = S("Label",
    fontName="Helvetica-Bold", fontSize=8.5,
    textColor=STEEL_BLUE, alignment=TA_LEFT,
    spaceAfter=0, leading=12)

SMALL_STYLE = S("Small",
    fontName="Helvetica", fontSize=8,
    textColor=HexColor("#555555"), alignment=TA_LEFT,
    spaceAfter=2, leading=11)

TABLE_HEADER = S("TH",
    fontName="Helvetica-Bold", fontSize=8.5,
    textColor=WHITE, alignment=TA_LEFT, leading=11)

TABLE_CELL = S("TC",
    fontName="Helvetica", fontSize=8.2,
    textColor=BLACK, alignment=TA_LEFT, leading=11)

TABLE_CELL_C = S("TCC",
    fontName="Helvetica", fontSize=8.2,
    textColor=BLACK, alignment=TA_CENTER, leading=11)

CODE_STYLE = S("Code",
    fontName="Courier", fontSize=8,
    textColor=HexColor("#2C3E50"), alignment=TA_LEFT,
    backColor=HexColor("#F8F9FA"), leftIndent=10,
    spaceAfter=4, leading=12)

def th(txt):  return Paragraph(txt, TABLE_HEADER)
def tc(txt):  return Paragraph(str(txt), TABLE_CELL)
def tcc(txt): return Paragraph(str(txt), TABLE_CELL_C)


# ── Header / Footer ──────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Top accent bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 10*mm, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 11.5*mm, w, 1.5*mm, fill=1, stroke=0)
    # Header text
    canvas.setFillColor(HexColor("#AED6F1"))
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(MARGIN, h - 7*mm, "SignalMDM Enterprise QA & Platform Audit Report")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - MARGIN, h - 7*mm, "MDM-P1-AUD-2026-05-22 | CONFIDENTIAL")
    # Bottom bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(MID_GREY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN, 3.5*mm, "Antigravity AI — Principal QA & Platform Architecture Team")
    canvas.drawRightString(w - MARGIN, 3.5*mm, f"Page {doc.page}")
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Full navy header block on cover
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 10*mm, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 11.5*mm, w, 1.5*mm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#AED6F1"))
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(MARGIN, h - 7*mm, "SignalMDM Enterprise QA & Platform Audit Report")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - MARGIN, h - 7*mm, "MDM-P1-AUD-2026-05-22 | CONFIDENTIAL")
    # Footer
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(MID_GREY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN, 3.5*mm, "Antigravity AI — Principal QA & Platform Architecture Team")
    canvas.drawRightString(w - MARGIN, 3.5*mm, f"Page {doc.page}")
    canvas.restoreState()


# ── Helpers ──────────────────────────────────────────────────────────────────
def section_header(number, title):
    """Coloured section header band."""
    data = [[Paragraph(f"{number}. {title.upper()}", SECTION_STYLE)]]
    t = Table(data, colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), STEEL_BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [STEEL_BLUE]),
    ]))
    return t

def tag_cell(text, bg, fg):
    p = Paragraph(f"<b>{text}</b>",
        ParagraphStyle("tag", fontName="Helvetica-Bold", fontSize=8,
                       textColor=fg, alignment=TA_CENTER, leading=10))
    t = Table([[p]], colWidths=[2.2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), bg),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), [3,3,3,3]),
    ]))
    return t

def compliance_tag(status):
    if "COMPLIANT" in status.upper():
        return tag_cell("COMPLIANT", GREEN_LIGHT, GREEN_DARK)
    return tag_cell(status, RED_LIGHT, RED_DARK)

def risk_tag(level):
    colours = {
        "HIGH":   (RED_LIGHT,   RED_DARK),
        "MEDIUM": (AMBER_LIGHT, AMBER),
        "LOW":    (GREEN_LIGHT, GREEN_DARK),
    }
    bg, fg = colours.get(level.upper(), (LIGHT_GREY, BLACK))
    return tag_cell(level, bg, fg)

def maturity_tag(level):
    if "HIGHLY" in level.upper():
        return tag_cell(level, GREEN_LIGHT, GREEN_DARK)
    if "MATURE" in level.upper() and "IM" not in level.upper():
        return tag_cell(level, LIGHT_BLUE, STEEL_BLUE)
    return tag_cell(level, RED_LIGHT, RED_DARK)


# ── Document ─────────────────────────────────────────────────────────────────
def build():
    out = "SignalMDM_QA_Audit_Report.pdf"
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.8*cm, bottomMargin=2.0*cm,
        title="SignalMDM QA & Platform Audit Report",
        author="Antigravity AI",
    )
    doc.multiBuild_page_templates = None

    story = []
    CW = PAGE_W - 2*MARGIN  # content width

    # ═══════════════════════════════════════════════════════════════════════
    # COVER BLOCK
    # ═══════════════════════════════════════════════════════════════════════
    cover_data = [[
        Paragraph("SIGNALMDM ENTERPRISE", TITLE_STYLE),
    ],[
        Paragraph("QA &amp; Platform Audit Report", TITLE_STYLE),
    ],[
        Spacer(1, 6),
    ],[
        Paragraph("Phase 1 Quality Assurance &amp; System Architecture Audit", SUBTITLE_STYLE),
    ],[
        Spacer(1, 10),
    ],[
        Paragraph("Audit Reference: MDM-P1-AUD-2026-05-22", META_STYLE),
    ],[
        Paragraph("Audit Date: 2026-05-22 | Version: 1.0.0-RC1 | Artifact ID: MDM-QA-REPORT-1.0", META_STYLE),
    ],[
        Paragraph("Auditor: Antigravity AI — Principal QA &amp; Platform Architecture Team", META_STYLE),
    ],[
        Paragraph("Classification: Internal Technical Confidential", META_STYLE),
    ],[
        Spacer(1, 14),
    ],[
        Paragraph("AUDIT VERDICT: CONDITIONAL DEVELOPMENT PASS", VERDICT_STYLE),
    ]]

    cover_table = Table([[row[0]] for row in cover_data], colWidths=[CW])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("LINEABOVE",     (0,0), (-1,0),  2, ACCENT),
        ("LINEBELOW",     (0,-1),(-1,-1), 2, ACCENT),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 10))

    # Meta info table under cover
    meta_rows = [
        ["Subject System", "SignalMDM (Enterprise Multi-Tenant MDM)"],
        ["Version / Branch", "1.0.0-rc1 / main"],
        ["Database", "PostgreSQL 15+ / PG12 Compatible"],
        ["Target Environment", "Local Development (Pre-Production Validation)"],
        ["Backend", "FastAPI, Python 3.10+, Uvicorn"],
        ["Frontend", "React 18, TypeScript, Vite, Express"],
        ["Caching / Locking", "Redis (localhost:6379, DB 0/1)"],
        ["Async Task Queue", "Celery 5.3+ (Redis Broker)"],
    ]
    meta_data = [[Paragraph(f"<b>{r[0]}</b>", SMALL_STYLE),
                  Paragraph(r[1], SMALL_STYLE)] for r in meta_rows]
    meta_t = Table(meta_data, colWidths=[4.2*cm, CW - 4.2*cm])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT_BLUE),
        ("BACKGROUND",    (1,0), (1,-1), WHITE),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LIGHT_GREY, WHITE]*6),
        ("GRID",          (0,0), (-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(section_header(1, "Executive Summary"))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "The Principal QA Engineering and Platform Architecture team completed an exhaustive, "
        "line-by-line static and dynamic audit of the SignalMDM enterprise repository. The codebase "
        "demonstrates high architectural rigor and strong compliance with all Phase 1 design patterns. "
        "Key strengths include:", BODY_STYLE))

    strengths = [
        "Multi-tenant data architecture — every base table uses <b>tenant_id</b> foreign keys with <b>ondelete=RESTRICT</b>.",
        "Comprehensive security token pipeline — AES-256-CBC payload encryption, SHA-256 device fingerprint checks, Redis-backed single-use OTPs, and HS256 algorithm pinning.",
        "Robust multi-stage ingestion state machine — async Celery worker chains (raw_worker → staging_worker) with fully transaction-safe status transitions.",
        "High-performance Data Quality pipeline — 50 k batch caps, per-row anomaly logging, MD5 deduplication, and advanced SQLi/XSS regex validation.",
    ]
    for s in strengths:
        story.append(Paragraph(s, BULLET_STYLE))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "However, the penetration test results (Score 43/100, Grade F) present significant vulnerabilities "
        "that must be addressed before production deployment. While deemed acceptable for local development "
        "iterations, the permissive Content Security Policy ('unsafe-inline', 'unsafe-eval'), the Uvicorn "
        "Server information disclosure header, and the OTP lockout omission on non-existent admin_ids are "
        "<b>hard blockers for any public-facing or staging release.</b>", BODY_STYLE))

    # Score summary cards
    score_data = [
        [th("Dimension"), th("Score"), th("Grade"), th("Status")],
        [tc("Phase 1 Requirements Coverage"), tcc("98 %"), tcc("A+"), tcc("✔  PASS")],
        [tc("Security & Hardening Rating"),   tcc("43 %"), tcc("F"),  tcc("✘  FAIL")],
        [tc("Overall Audit Verdict"),         tcc("—"),    tcc("—"),  tcc("CONDITIONAL PASS")],
    ]
    score_t = Table(score_data, colWidths=[8.5*cm, 2.5*cm, 2.5*cm, 3.5*cm])
    score_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        # Colour score cells
        ("TEXTCOLOR", (1,1),(3,1), GREEN_DARK),
        ("TEXTCOLOR", (1,2),(3,2), RED_DARK),
        ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
    ]))
    story.append(Spacer(1, 6))
    story.append(score_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 2. REPOSITORY INVENTORY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(section_header(2, "Repository Inventory"))
    story.append(Spacer(1, 8))

    inv_categories = [
        ("A", "Backend Routers", "11 Files — Mount Point: /api/v1", [
            ("auth_router.py",        "Handles login, OTP validation, 2FA, token refresh, and logout."),
            ("source_router.py",      "Manages source system credentials, mapping configs, and metadata."),
            ("ingestion_router.py",   "Initiates runs, monitors state transitions, and handles fallback sync."),
            ("raw_router.py",         "Landing-zone data search, schema inspection, and audit extraction."),
            ("staging_router.py",     "Mapping verification, survivorship evaluations, and DQ validation states."),
            ("upload_router.py",      "Multi-part data streaming endpoint with size-limit policing."),
            ("tenant_router.py",      "Super-admin routing for managing system tenants."),
            ("admin_router.py",       "Administrative functions including brute-force state manual unlocking."),
            ("platform_rbac_router.py","Granular role-to-permission mapping and updates."),
            ("api_logs_router.py",    "System observability and distributed trace tracking."),
            ("tenant_config_router.py","Configures validation scripts and custom rules per tenant."),
        ]),
        ("B", "Backend Services", "8 Files", [
            ("auth_service.py",         "Encrypted token issuance, OTP gen/verify, bcrypt hashing."),
            ("source_service.py",       "CRUD logic for source systems and custom adapter mapping."),
            ("ingestion_service.py",    "Core ingestion engine, state machine driver, and validation."),
            ("raw_service.py",          "Raw record storage, metadata generation, and integrity checks."),
            ("staging_service.py",      "Unified mapping pipeline, matching/merging rule engine."),
            ("audit_service.py",        "Append-only transactional audit trail compiler."),
            ("tenant_service.py",       "Tenant creation, initialization, and resource allocations."),
            ("platform_rbac_service.py","Dynamic database permission matrix calculations."),
        ]),
        ("C", "Backend Data Models", "18 Files", [
            ("tenant.py",          "Main Tenant class with config_json store."),
            ("platform_admin.py",  "Platform-level operator logins, locked states, and salt hashes."),
            ("platform_role.py",   "Enterprise RBAC role bindings."),
            ("rbac.py",            "Granular platform permissions definitions."),
            ("source_system.py",   "Target source metadata and schema parameters."),
            ("file_upload.py",     "Tracked metadata of chunks/files submitted via upload pipeline."),
            ("upload_session.py",  "Upload pipeline state management."),
            ("ingestion_run.py",   "Full metadata, logs, and telemetry of the execution state machine."),
            ("raw_record.py",      "Raw records JSONB table, MD5 hash integrity checks."),
            ("staging_entity.py",  "Standardised record definitions awaiting mapping or matching."),
            ("entity.py",          "The master Golden Records entity mappings."),
            ("audit.py",           "Append-only system logs, user actions, trace IDs, and old/new snapshots."),
            ("attributes.py … scoring.py","Advanced ML/Graph features — pre-implemented for Phase 2 (out of Phase 1 scope)."),
        ]),
        ("D", "Middleware Layer", "3 Files", [
            ("auth.py",       "Main dependency guards: require_auth, require_admin, is_super_admin."),
            ("token_utils.py","Token encryption, decryption, parsing, and signing logic."),
            ("rate_limit.py", "Redis rate-limiter supporting sliding-window checks."),
        ]),
        ("E", "Workers", "3 Files", [
            ("celery_app.py",    "Asynchronous Celery setup."),
            ("raw_worker.py",    "Extract/Load worker for files and direct database streams."),
            ("staging_worker.py","Matches and transfers raw data to staging schemas."),
        ]),
        ("F", "Utils & Helpers", "1 File", [
            ("sanitize.py","DQ processor supporting empty-row filtering, MD5 deduplication, and sanitization."),
        ]),
    ]

    for letter, cat_name, count, files in inv_categories:
        story.append(Paragraph(
            f"<b>{letter}. {cat_name}</b> &nbsp;&nbsp;<font size='8' color='#5D6D7E'>({count})</font>",
            SUBSECTION_STYLE))
        file_data = [[th("File"), th("Description")]]
        for fname, desc in files:
            file_data.append([
                Paragraph(f"<font name='Courier' size='8'>{fname}</font>", TABLE_CELL),
                tc(desc),
            ])
        ft = Table(file_data, colWidths=[4.8*cm, CW - 4.8*cm])
        ft.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), STEEL_BLUE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
            ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 7),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        story.append(ft)
        story.append(Spacer(1, 6))

    # Frontend
    story.append(Paragraph(
        "<b>G. Frontend</b> &nbsp;&nbsp;<font size='8' color='#5D6D7E'>(11 Pages, 4 Contexts, 1 Server)</font>",
        SUBSECTION_STYLE))
    fe_data = [
        [th("Category"), th("Components")],
        [tc("Pages"),    tc("Login.tsx, SourceSystems.tsx, IngestionRuns.tsx, UploadData.tsx, RawLanding.tsx, StagingRecords.tsx, Tenants.tsx, SystemHealth.tsx, ApiLogs.tsx, DevSetup.tsx, PlatformRBAC.tsx")],
        [tc("Contexts"), tc("AuthContext.tsx, PermissionsContext.tsx, SnackbarContext.tsx, TenantConfigContext.tsx")],
        [tc("Node Server"),tc("serverClient.js — Production server using Express + Helmet")],
    ]
    fe_t = Table(fe_data, colWidths=[3.5*cm, CW - 3.5*cm])
    fe_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY, WHITE]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    story.append(fe_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. PHASE 1 COMPLIANCE MATRIX
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(section_header(3, "Phase 1 Compliance Matrix"))
    story.append(Spacer(1, 8))

    comp_data = [
        [th("Requirement"), th("Expected (Spec)"), th("Implemented"), th("Status"), th("Evidence")],
        [tc("API Versioning"),       tc("Mounted under /api/v1"),             tcc("Yes"), compliance_tag("COMPLIANT"), tc("main.py L362–374")],
        [tc("Multi-Tenancy"),        tc("Soft isolation via tenant_id"),       tcc("Yes"), compliance_tag("COMPLIANT"), tc("tenant.py, models FK ondelete=RESTRICT")],
        [tc("Encrypted Token"),      tc("Client-side encrypted AES-256 JWT"), tcc("Yes"), compliance_tag("COMPLIANT"), tc("token_utils.py L105–130")],
        [tc("Redis OTP Store"),      tc("Temporary OTP with expiry"),          tcc("Yes"), compliance_tag("COMPLIANT"), tc("auth_service.py L98–112")],
        [tc("Ingestion Pipeline"),   tc("State transitions & Worker chains"),  tcc("Yes"), compliance_tag("COMPLIANT"), tc("ingestion_service.py L43–58")],
        [tc("Raw Immutability"),     tc("Read-only raw landing zone"),         tcc("Yes"), compliance_tag("COMPLIANT"), tc("raw_record.py (no update/delete paths)")],
        [tc("Staging Correlation"),  tc("1-to-1 linkage of raw to staging"),   tcc("Yes"), compliance_tag("COMPLIANT"), tc("staging_entity.py L65–70")],
        [tc("Append-Only Audit"),    tc("Old/new snapshots & trace IDs"),      tcc("Yes"), compliance_tag("COMPLIANT"), tc("audit.py & audit_service.py")],
        [tc("Data Quality / DQ"),    tc("Sanitisation and batch scanning"),    tcc("Yes"), compliance_tag("COMPLIANT"), tc("sanitize.py L89–224")],
        [tc("SuperAdmin Overrides"), tc("Platform override headers"),          tcc("Yes"), compliance_tag("COMPLIANT"), tc("auth.py L142–160")],
    ]
    cw = [4.2*cm, 4.2*cm, 2.0*cm, 2.4*cm, CW - 12.8*cm]
    comp_t = Table(comp_data, colWidths=cw, repeatRows=1)
    comp_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(comp_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 4. VALIDATION SECTIONS (5–13)
    # ═══════════════════════════════════════════════════════════════════════
    val_sections = [
        (4, "Frontend Validation", [
            ("Core Technology Stack", "React 18, TypeScript, Vite, React Router v6."),
            ("Components & Layouts",  "Styled with a custom Vanilla CSS design system (dark-mode first, glassmorphic). Complex interactive state components include UploadData.tsx (drag-and-drop ingestion) and PlatformRBAC.tsx (dynamic permissions grid)."),
            ("Route Guarding",        "ProtectedRoute filters access using AuthContext and PermissionsContext. Users lacking proper permissions are redirected gracefully."),
            ("Production Server",     "serverClient.js uses Express configured with Helmet for secure response headers."),
            ("CSP Evaluation",        "The Content-Security-Policy includes 'unsafe-inline' and 'unsafe-eval' (Vite HMR requirements). Acceptable for local development; production release blocker due to elevated XSS risk."),
        ]),
        (5, "Backend Validation", [
            ("Framework & Routing",   "FastAPI with 11 custom routers mapped to core schema areas. All routes map to /api/v1/*."),
            ("Dependency Guards",     "require_auth — verifies cookie-decrypted JWT, user active state, and blacklisting. require_admin — verifies admin or super_admin role. is_super_admin — verifies membership in the 'platform' tenant group."),
            ("Local Dev Mode",        "SQLAlchemy echo tracing is active (useful for debugging; leaks execution parameters in logs). Swagger interactive docs (/docs, /redoc) remain exposed."),
        ]),
        (6, "Database Validation", [
            ("Schema & Tables",       "Organised using SQLAlchemy ORM declarations. All tables include a strict tenant_id column enforcing multi-tenancy."),
            ("Referential Integrity", "Foreign keys referencing the central tenant table include ondelete=RESTRICT, preventing orphaned data deletion."),
            ("Staging Isolation",     "staging_entity.py contains a UNIQUE constraint on raw_record_id, enforcing strict 1-to-1 linkage between raw and staged records."),
            ("Master Indexes",        "B-Tree indices on tenant_id, checksum_md5, performed_at, and external_id guarantee fast retrieval on high-volume datasets."),
        ]),
        (7, "API Validation", [
            ("API Version Layer",     "All endpoints mounted uniformly behind the /api/v1 namespace."),
            ("Routing Boundaries",    "Authentication: /api/v1/auth | Sources: /api/v1/sources | Ingestion: /api/v1/ingestion | File Operations: /api/v1/upload."),
            ("Input Validation",      "Strictly typed Pydantic models reject invalid JSON types at entry boundary with 422 Unprocessable Entity codes. Control plane actions are fully separated from the data plane."),
        ]),
        (8, "Async Processing Validation", [
            ("Async Execution Chains","When a multi-part file is ingested, raw_worker.py performs primary ETL operations, verifies MD5 checksums, and pushes data to Postgres. It then chains directly to staging_worker.py."),
            ("Error Handling",        "Workers are configured with max_retries=3 and apply exponential backoff to prevent thread contention during momentary DB drops."),
            ("Synchronous Fallback",  "ingestion_router.py features a built-in synchronous fallback engine, preserving operational capability when background workers are unresponsive."),
        ]),
        (9, "Multi-Tenancy Validation", [
            ("Logical Isolation",     "Implemented using database-level tenant_id columns. All models (sources, ingestions, records, staging assets) must contain this UUID."),
            ("Referential Protection","FK definitions use ondelete=RESTRICT to prevent orphaned records and accidental cross-tenant updates."),
            ("SuperAdmin Override",   "Members of the 'platform' tenant can append the X-Tenant-ID header to interact with target tenant schema spaces while retaining platform-level logs."),
        ]),
        (10, "Auditability Validation", [
            ("Append-Only Architecture","Enforced on the AuditLog model. The service layer lacks any update or delete actions, guaranteeing log immutability."),
            ("JSONB Mutation Tracking", "Stores data states using JSONB columns old_value and new_value, capturing exact object state changes."),
            ("Trace-ID Tracking",       "Every API transaction generates a unique trace_id in middleware, passed to workers and written to all audit logs for complete end-to-end tracing."),
            ("Manual Overrides",        "Dedicated columns approved_by and approval_reason log human overrides on business logic, preserving administrative accountability."),
        ]),
        (11, "Observability Validation", [
            ("Health Endpoints",      "Exposed at /api/v1/health to monitor Redis, Celery worker, and PostgreSQL connectivity."),
            ("Rate-Limiting",         "Implemented in rate_limit.py as a Redis-backed sliding-window check. Configured to fail open if Redis goes offline, maintaining service availability during local development."),
            ("Observability Interface","Frontend pages ApiLogs.tsx and SystemHealth.tsx consume /api-logs endpoints, displaying execution counts, response distributions, and processing latencies."),
        ]),
    ]

    for sec_num, sec_title, items in val_sections:
        story.append(section_header(sec_num, sec_title))
        story.append(Spacer(1, 8))
        for label, desc in items:
            combined = f"<b>{label}:</b>  {desc}"
            story.append(Paragraph(combined, BODY_STYLE))
        story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. SECURITY VALIDATION (detailed — own section)
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(section_header(12, "Security Validation"))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Client-Side Encrypted Token Pipeline</b>", SUBSECTION_STYLE))
    token_steps = [
        ("Transmission", "During authentication a JWT is generated, containing user authentication claims, dynamic session keys, and a SHA-256 hash of the browser agent fingerprint."),
        ("Encryption",   "The JWT is encrypted using CryptoJS (AES-256-CBC) with an active TOKEN_ENCRYPTION_KEY."),
        ("Decryption",   "FastAPI middleware intercepts the payload and decrypts it using aes_decrypt (token_utils.py L105–130)."),
        ("Revocation",   "Middlewares verify the token has not been revoked via Redis cache records."),
        ("Algorithm Hardening","JWT signature evaluation is pinned to HS256. Dynamic algorithm definitions (e.g. 'none') are discarded automatically."),
    ]
    for i, (step, detail) in enumerate(token_steps, 1):
        story.append(Paragraph(f"<b>{i}. {step}:</b>  {detail}", NUM_STYLE))

    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Penetration Test Summary — Identified Defects</b>", SUBSECTION_STYLE))

    pen_data = [
        [th("Severity"), th("Finding"), th("Description")],
        [risk_tag("HIGH"),   tc("Permissive CSP"),           tc("'unsafe-inline' and 'unsafe-eval' directives permit malicious script execution if an XSS vulnerability occurs.")],
        [risk_tag("HIGH"),   tc("JWT Null-Byte Acceptance"),  tc("The JWT parser accepts malformed inputs containing null bytes, returning 400 Bad Request instead of 401 Unauthorized.")],
        [risk_tag("MEDIUM"), tc("User Enumeration"),         tc("Auth interface returns distinct messages for 'User Not Found' vs 'Wrong Password', enabling user enumeration.")],
        [risk_tag("MEDIUM"), tc("OTP Brute-Force Gap"),      tc("Standard accounts lock after 5 bad attempts; OTPs against invalid admin_id values do not trigger lockout tracking.")],
        [risk_tag("MEDIUM"), tc("Server Header Disclosure"), tc("Uvicorn 'Server' header reveals backend version, simplifying target scanning for attackers.")],
    ]
    pen_t = Table(pen_data, colWidths=[2.4*cm, 4.0*cm, CW - 6.4*cm], repeatRows=1)
    pen_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(pen_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 6. RISK & GAP REGISTERS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(section_header(13, "Risk Register"))
    story.append(Spacer(1, 8))

    risk_data = [
        [th("#"), th("Level"), th("Risk Description"), th("Impact")],
        [tcc("R-1"), risk_tag("HIGH"),   tc("Permissive CSP policies ('unsafe-inline', 'unsafe-eval')"),             tc("Execution of malicious scripts if an XSS vulnerability is triggered.")],
        [tcc("R-2"), risk_tag("HIGH"),   tc("Malformed tokens with null bytes bypass conventional filters"),          tc("Internal handler crashes; unexpected 400 responses instead of 401.")],
        [tcc("R-3"), risk_tag("MEDIUM"), tc("Inconsistent credential responses enable user enumeration"),             tc("Threat actors can confirm valid usernames for targeted attacks.")],
        [tcc("R-4"), risk_tag("MEDIUM"), tc("No OTP lockout for invalid admin_id values"),                           tc("Unlimited parallel OTP brute-forcing against the MFA interface.")],
        [tcc("R-5"), risk_tag("MEDIUM"), tc("Uvicorn 'Server' header discloses backend version"),                    tc("Simplifies target scanning and version-specific exploit selection.")],
    ]
    rw = [1.0*cm, 2.4*cm, 7.2*cm, CW - 10.6*cm]
    risk_t = Table(risk_data, colWidths=rw, repeatRows=1)
    risk_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(risk_t)
    story.append(Spacer(1, 14))

    story.append(section_header(14, "Gap Analysis"))
    story.append(Spacer(1, 8))

    gap_data = [
        [th("#"), th("Gap"), th("Description"), th("Resolution")],
        [tcc("G-1"), tc("Missing Lookup Tables"),   tc("Physical relational tables for domains and entity_types are absent."),           tc("Managed through Pydantic enums and JSON configurations.")],
        [tcc("G-2"), tc("Decoupled File Services"), tc("No centralised FileService; logic is scattered across routers and workers."),    tc("Consolidate into a dedicated FileService module (see Priority 9).")],
        [tcc("G-3"), tc("Placeholder Dashboard"),   tc("Main analytics dashboard uses simulated telemetry data."),                       tc("Implement live telemetry bindings in Phase 2.")],
        [tcc("G-4"), tc("Production Env Guards"),   tc("Backend lacks config switches to block /docs and disable debug logs in prod."),  tc("Add APP_ENV=production guard (see Priority 10).")],
    ]
    gw = [1.0*cm, 3.5*cm, 6.0*cm, CW - 10.5*cm]
    gap_t = Table(gap_data, colWidths=gw, repeatRows=1)
    gap_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(gap_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 7. TECHNICAL DEBT REGISTER
    # ═══════════════════════════════════════════════════════════════════════
    story.append(section_header(15, "Technical Debt Register"))
    story.append(Spacer(1, 8))

    debt_items = [
        ("TD-1", "Permissive Local CORS",     "FastAPI CORS configurations accept wide development parameters requiring narrowing before launch."),
        ("TD-2", "Missing Unit Test Coverage","Services layer lacks automated unit tests for edge-case state machine failure transitions."),
        ("TD-3", "Hardcoded Database String", "Migration files contain fallback references to dev credentials postgresql://postgres:2025@localhost:5432/SignalMDM."),
        ("TD-4", "Synchronous File Parsing",  "Large file uploads are parsed synchronously inside the route thread before handing off to background workers, introducing HTTP timeout risks."),
    ]
    debt_data = [[th("ID"), th("Item"), th("Description")]]
    for did, item, desc in debt_items:
        debt_data.append([tcc(did), Paragraph(f"<b>{item}</b>", TABLE_CELL), tc(desc)])
    debt_t = Table(debt_data, colWidths=[1.4*cm, 4.5*cm, CW - 5.9*cm], repeatRows=1)
    debt_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(debt_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 8. COMPLIANCE SCORING & MATURITY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(section_header(16, "Compliance Scoring"))
    story.append(Spacer(1, 8))

    cs_data = [
        [th("Category"), th("Coverage"), th("Grade"), th("Assessment")],
        [tc("Phase 1 Requirements Coverage"), tcc("98 %"), tcc("A+"),
         tc("Functional requirements for tenant isolation, encrypted token verification, DQ checks, and ingestion tracking are fully met.")],
        [tc("Security & Hardening Rating"), tcc("43 %"), tcc("F"),
         tc("Passed 104 basic security tests. Vulnerabilities in JWT parsing, OTP lockouts, user enumeration, and CSP prevent production certification.")],
    ]
    cs_t = Table(cs_data, colWidths=[4.5*cm, 2.0*cm, 1.8*cm, CW - 8.3*cm], repeatRows=1)
    cs_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [GREEN_LIGHT, RED_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(cs_t)
    story.append(Spacer(1, 14))

    story.append(section_header(17, "Repository Maturity Assessment"))
    story.append(Spacer(1, 8))

    mat_data = [
        [th("Dimension"), th("Rating"), th("Notes")],
        [tc("Code Quality & Typing"), maturity_tag("Mature"),
         tc("Strict Python typing and TypeScript definitions. Robust ORM paradigms and structured Pydantic models.")],
        [tc("System Architecture"), maturity_tag("Highly Mature"),
         tc("Async task architecture, layered routers, and multi-tenant schema isolation reflect modern enterprise best practices.")],
        [tc("Security Hardening"), maturity_tag("Immature"),
         tc("Requires immediate attention: harden CSP directives, fix JWT null-byte handling, and unify auth responses.")],
    ]
    mat_t = Table(mat_data, colWidths=[4.0*cm, 3.0*cm, CW - 7.0*cm], repeatRows=1)
    mat_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY, WHITE]),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(mat_t)
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 9. NEXT WORKSTREAM READINESS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(section_header(18, "Next Workstream Readiness"))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "The repository is <b>95% ready</b> to transition to <b>Phase 2</b> (Entity Resolution, "
        "Graph Matching, and Machine Learning Scoring). Data models for attributes, features, signals, "
        "and scoring are already integrated into the database schema.", BODY_STYLE))
    story.append(Paragraph(
        "Before Phase 2 begins, all security vulnerabilities identified in this audit must be resolved "
        "to establish a secure foundation for advanced data operations.", BODY_STYLE))
    story.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 10. TOP 10 REMEDIATION PRIORITIES
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(section_header(19, "Top 10 Remediation Priorities"))
    story.append(Spacer(1, 8))

    priorities = [
        ("P-01", "HIGH",   "Uniform Authentication Responses",
         "Modify auth_service.py to return the identical message 'Invalid credentials.' for both non-existent users and incorrect passwords."),
        ("P-02", "HIGH",   "Patch JWT Null-Byte Acceptance",
         "Update token_utils.py to immediately reject any token payload containing null bytes (\\x00 or %00), returning a 401 Unauthorized code."),
        ("P-03", "HIGH",   "Enforce OTP Lockout for Invalid Accounts",
         "Update the Redis brute-force middleware to track and lock out failed OTP attempts made against non-existent admin_ids."),
        ("P-04", "HIGH",   "Harden Frontend CSP Directives",
         "Configure serverClient.js to remove 'unsafe-inline' and 'unsafe-eval' directives from the Helmet CSP policy in non-local environments."),
        ("P-05", "MEDIUM", "Set X-Frame-Options to DENY",
         "Update the Helmet configuration in serverClient.js to explicitly send the X-Frame-Options: DENY header."),
        ("P-06", "MEDIUM", "Obscure the Backend Server Header",
         "Configure Uvicorn/FastAPI startup scripts to strip or override the Server header in production environments."),
        ("P-07", "MEDIUM", "Verify Upload Path Sanitisation",
         "Ensure upload_router.py wraps all file uploads with os.path.basename() to eliminate directory traversal risks."),
        ("P-08", "MEDIUM", "Enforce Secure Cookie Flags",
         "Update auth_service.py to set secure=True on all session cookies when running in production."),
        ("P-09", "LOW",    "Implement a Unified FileService",
         "Consolidate file parsing, storage, and validation logic into a dedicated service module to reduce maintenance overhead."),
        ("P-10", "LOW",    "Construct a Production Security Switch",
         "Add an environment-based configuration that disables FastAPI interactive Swagger endpoints when APP_ENV=production."),
    ]

    prio_data = [[th("#"), th("Priority"), th("Action"), th("Details")]]
    for pid, level, action, detail in priorities:
        prio_data.append([tcc(pid), risk_tag(level), Paragraph(f"<b>{action}</b>", TABLE_CELL), tc(detail)])

    pw = [1.2*cm, 2.4*cm, 4.8*cm, CW - 8.4*cm]
    prio_t = Table(prio_data, colWidths=pw, repeatRows=1)
    prio_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), STEEL_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREY]*6),
        ("GRID",          (0,0),(-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(prio_t)
    story.append(Spacer(1, 20))

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL VERDICT BANNER
    # ═══════════════════════════════════════════════════════════════════════
    verdict_lines = [
        [Paragraph("AUDIT VERDICT", ParagraphStyle("vt", fontName="Helvetica-Bold",
            fontSize=11, textColor=HexColor("#AED6F1"), alignment=TA_CENTER, leading=14))],
        [Paragraph("CONDITIONAL DEVELOPMENT PASS", ParagraphStyle("vv", fontName="Helvetica-Bold",
            fontSize=18, textColor=WHITE, alignment=TA_CENTER, leading=22))],
        [Paragraph(
            "SignalMDM is certified for local development, testing, and engineering iterations.<br/>"
            "It is <b>blocked for production staging and public deployment</b> until security remediations are complete.",
            ParagraphStyle("vd", fontName="Helvetica", fontSize=9.5,
                textColor=HexColor("#D6EAF8"), alignment=TA_CENTER, leading=14))],
    ]
    v_t = Table(verdict_lines, colWidths=[CW])
    v_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
        ("LINEABOVE",     (0,0),(-1,0),  2, ACCENT),
        ("LINEBELOW",     (0,-1),(-1,-1),2, ACCENT),
    ]))
    story.append(v_t)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "End of Audit — SignalMDM Platform &nbsp;|&nbsp; "
        "Antigravity AI Principal QA &amp; Platform Architecture Team &nbsp;|&nbsp; 2026-05-22",
        ParagraphStyle("footer_note", fontName="Helvetica", fontSize=8,
            textColor=HexColor("#7F8C8D"), alignment=TA_CENTER)))

    # ── Build ────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print("PDF written to", out)

build()