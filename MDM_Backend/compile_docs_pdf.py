import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import HexColor

# ── Palette & Design System ──────────────────────────────────────────────────
PRIMARY      = HexColor("#0F172A") # Slate Dark
SECONDARY    = HexColor("#1E293B") # Slate Medium
ACCENT       = HexColor("#0284C7") # Sky Blue (Primary Action/Border)
LIGHT_BLUE   = HexColor("#E0F2FE") # Sky Light (Info Box BG)
MID_GREY     = HexColor("#CBD5E1") # Slate Grid / Borders
LIGHT_GREY   = HexColor("#F8FAFC") # Slate Very Light (Alternating Rows / Code BG)
WHITE        = colors.white
BLACK        = HexColor("#1E293B")

# Alert callout palette
ALERT_RED_BG     = HexColor("#FEF2F2")
ALERT_RED_BORDER = HexColor("#EF4444")
ALERT_RED_TEXT   = HexColor("#991B1B")

ALERT_GREEN_BG     = HexColor("#F0FDF4")
ALERT_GREEN_BORDER = HexColor("#22C55E")
ALERT_GREEN_TEXT   = HexColor("#166534")

ALERT_AMBER_BG     = HexColor("#FFFBEB")
ALERT_AMBER_BORDER = HexColor("#F59E0B")
ALERT_AMBER_TEXT   = HexColor("#92400E")

ALERT_BLUE_BG     = HexColor("#F0F9FF")
ALERT_BLUE_BORDER = HexColor("#0284C7")
ALERT_BLUE_TEXT   = HexColor("#075985")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Typography & Styles ──────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def create_style(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE_STYLE = create_style("DocTitle",
    fontName="Helvetica-Bold", fontSize=24,
    textColor=WHITE, alignment=TA_CENTER,
    spaceAfter=8, leading=30)

SUBTITLE_STYLE = create_style("DocSubtitle",
    fontName="Helvetica", fontSize=11,
    textColor=HexColor("#BAE6FD"), alignment=TA_CENTER,
    spaceAfter=4, leading=15)

META_STYLE = create_style("DocMeta",
    fontName="Helvetica", fontSize=9,
    textColor=HexColor("#E0F2FE"), alignment=TA_CENTER,
    spaceAfter=3, leading=12)

SECTION_STYLE = create_style("SectionHeader",
    fontName="Helvetica-Bold", fontSize=13,
    textColor=WHITE, alignment=TA_LEFT,
    spaceAfter=0, leading=17)

H2_STYLE = create_style("H2Style",
    fontName="Helvetica-Bold", fontSize=12,
    textColor=SECONDARY, alignment=TA_LEFT,
    spaceBefore=12, spaceAfter=5, leading=16)

H3_STYLE = create_style("H3Style",
    fontName="Helvetica-Bold", fontSize=10,
    textColor=ACCENT, alignment=TA_LEFT,
    spaceBefore=8, spaceAfter=4, leading=14)

BODY_STYLE = create_style("BodyTextCustom",
    fontName="Helvetica", fontSize=9.2,
    textColor=HexColor("#334155"), alignment=TA_JUSTIFY,
    spaceAfter=5, leading=13.5)

# Hanging indentation styles for level-nested bullet lists (10pt indent offset)
BULLET_STYLE_L1 = create_style("BulletCustomL1",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=14, firstLineIndent=-10, spaceAfter=3, leading=13)

BULLET_STYLE_L2 = create_style("BulletCustomL2",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=28, firstLineIndent=-10, spaceAfter=3, leading=13)

BULLET_STYLE_L3 = create_style("BulletCustomL3",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=42, firstLineIndent=-10, spaceAfter=3, leading=13)

NUMBERED_STYLE_L1 = create_style("NumberedCustomL1",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=14, firstLineIndent=-10, spaceAfter=3, leading=13)

NUMBERED_STYLE_L2 = create_style("NumberedCustomL2",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=28, firstLineIndent=-10, spaceAfter=3, leading=13)

NUMBERED_STYLE_L3 = create_style("NumberedCustomL3",
    fontName="Helvetica", fontSize=9.0,
    textColor=HexColor("#334155"), alignment=TA_LEFT,
    leftIndent=42, firstLineIndent=-10, spaceAfter=3, leading=13)

CODE_BLOCK_STYLE = create_style("CodeBlock",
    fontName="Courier", fontSize=7.5,
    textColor=HexColor("#0F172A"), alignment=TA_LEFT,
    leading=10.5)

TABLE_HEADER_STYLE = create_style("THeader",
    fontName="Helvetica-Bold", fontSize=8.5,
    textColor=WHITE, alignment=TA_LEFT, leading=11)

TABLE_CELL_STYLE = create_style("TCell",
    fontName="Helvetica", fontSize=8.2,
    textColor=HexColor("#1E293B"), alignment=TA_LEFT, leading=11.5)

# ── Dynamic Header & Footer ──────────────────────────────────────────────────
def page_layout_callback(canvas, doc):
    canvas.saveState()
    w, h = A4
    
    # Top header bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, h - 10*mm, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 11.5*mm, w, 1.5*mm, fill=1, stroke=0)
    
    # Header text
    canvas.setFillColor(HexColor("#F0F9FF"))
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(MARGIN, h - 7*mm, "SignalMDM Platform Specifications Suite")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - MARGIN, h - 7*mm, "ENTERPRISE TECHNICAL DOCUMENTATION")
    
    # Bottom footer bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(MID_GREY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN, 3.5*mm, "CONFIDENTIAL  |  Antigravity AI Platform Architect Team")
    canvas.drawRightString(w - MARGIN, 3.5*mm, f"Page {doc.page}")
    canvas.restoreState()

def first_page_layout_callback(canvas, doc):
    canvas.saveState()
    w, h = A4
    
    # Decorative vertical stripe on the left edge of the cover page
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, 8*mm, h, fill=1, stroke=0)
    canvas.setFillColor(PRIMARY)
    canvas.rect(8*mm, 0, 2*mm, h, fill=1, stroke=0)
    
    # Bottom footer on cover page
    canvas.setFillColor(PRIMARY)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN + 10*mm, 8*mm, "CONFIDENTIAL")
    canvas.setFillColor(HexColor("#475569"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN + 35*mm, 8*mm, "|   SignalMDM Enterprise System Specifications Suite")
    canvas.drawRightString(w - MARGIN, 8*mm, "2026 EDITION")
    canvas.restoreState()

# ── Custom Flowable Elements ─────────────────────────────────────────────────
def section_band(title):
    p = Paragraph(title.upper(), SECTION_STYLE)
    t = Table([[p]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SECONDARY),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    return t

def render_code_box(code_lines):
    flowables = []
    if not code_lines:
        return flowables
        
    table_rows = []
    for line in code_lines:
        leading_spaces = len(line) - len(line.lstrip(' '))
        # Preserving indentation using non-breaking spaces
        clean_line = "&nbsp;" * leading_spaces + html_escape(line.lstrip(' '))
        if not clean_line.strip():
            clean_line = "&nbsp;"
            
        p = Paragraph(f"<font face='Courier' size='7'>{clean_line}</font>", CODE_BLOCK_STYLE)
        table_rows.append([p])
        
    # Multi-row table design splits beautifully across pages, preventing crash bug
    t = Table(table_rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 0.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0.5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("LINELEFT",      (0,0), (0,-1), 2.5, ACCENT),
    ]))
    
    flowables.append(Spacer(1, 4))
    flowables.append(t)
    flowables.append(Spacer(1, 6))
    return flowables

# ── Markdown Parser Utilities ────────────────────────────────────────────────
def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline_formatting(text):
    text = html_escape(text)
    
    # 1. Clean up standard URL references [text](url) -> <b>text</b> FIRST to avoid regex collisions
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"<b>\1</b>", text)
    
    # 2. Bold **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    
    # 3. Italic *text* (avoiding double asterisks)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    
    # 4. Inline code `code`
    text = re.sub(r"`(.*?)`", r"<font face='Courier' color='#0284C7'><b>\1</b></font>", text)
    
    return text

def parse_markdown_to_flowables(filepath):
    flowables = []
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return flowables

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []
    in_blockquote = False
    blockquote_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle Fenced Code Blocks
        if stripped.startswith("```"):
            # If in blockquote or table, close them first
            if in_table:
                flowables.extend(flush_table(table_rows))
                in_table = False
            if in_blockquote:
                flowables.extend(flush_blockquote(blockquote_lines))
                in_blockquote = False
                
            if in_code_block:
                # End block
                flowables.extend(render_code_box(code_lines))
                code_lines = []
                in_code_block = False
            else:
                # Start block
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line.rstrip("\n"))
            i += 1
            continue

        # Handle Tables
        if stripped.startswith("|"):
            if in_blockquote:
                flowables.extend(flush_blockquote(blockquote_lines))
                in_blockquote = False
                
            if not in_table:
                in_table = True
                table_rows = []
            
            # Check if it's the markdown table header separator (e.g. |---|---|)
            if re.match(r"^\|[\s\-\:\|]+$", stripped):
                i += 1
                continue
            
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flowables.extend(flush_table(table_rows))
                in_table = False

        # Handle Blockquotes & Alerts
        if stripped.startswith(">"):
            if not in_blockquote:
                in_blockquote = True
                blockquote_lines = []
            
            clean_quote = re.sub(r"^>\s*", "", stripped)
            blockquote_lines.append(clean_quote)
            i += 1
            continue
        else:
            if in_blockquote:
                flowables.extend(flush_blockquote(blockquote_lines))
                in_blockquote = False

        if not stripped:
            i += 1
            continue

        # Horizontal rules
        if stripped in ["---", "***", "___"]:
            flowables.append(HRFlowable(width="100%", thickness=0.8, color=MID_GREY, spaceAfter=8, spaceBefore=8))
            i += 1
            continue

        # Headers (Support up to level 6)
        if stripped.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if match:
                level = len(match.group(1))
                title_text = inline_formatting(match.group(2))
                if level == 1:
                    flowables.append(section_band(title_text))
                    flowables.append(Spacer(1, 8))
                elif level == 2:
                    flowables.append(Paragraph(title_text, H2_STYLE))
                    flowables.append(Spacer(1, 4))
                else:
                    flowables.append(Paragraph(title_text, H3_STYLE))
                    flowables.append(Spacer(1, 3))
            i += 1
            continue

        # Lists with levels of nesting based on indentation
        leading_spaces = len(line) - len(line.lstrip(' '))
        if leading_spaces >= 8:
            list_level = 3
        elif leading_spaces >= 3:
            list_level = 2
        else:
            list_level = 1

        # Bullet lists with custom colored hanging bullets
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("+ "):
            bullet_char = "&bull;"
            if list_level == 2:
                bullet_char = "&#9702;"
                bullet_style = BULLET_STYLE_L2
            elif list_level == 3:
                bullet_char = "&#9642;"
                bullet_style = BULLET_STYLE_L3
            else:
                bullet_style = BULLET_STYLE_L1
                
            bullet_text = inline_formatting(stripped[2:])
            bullet_html = f"<font color='{ACCENT.hexval()}'><b>{bullet_char}</b></font>&nbsp;&nbsp;{bullet_text}"
            flowables.append(Paragraph(bullet_html, bullet_style))
            i += 1
            continue

        # Numbered lists with custom hanging numerals
        if re.match(r"^\d+\.\s+", stripped):
            match = re.match(r"^(\d+\.\s+)(.+)$", stripped)
            num_prefix = match.group(1)
            item_text = match.group(2)
            
            if list_level == 2:
                numbered_style = NUMBERED_STYLE_L2
            elif list_level == 3:
                numbered_style = NUMBERED_STYLE_L3
            else:
                numbered_style = NUMBERED_STYLE_L1
                
            numbered_text = f"<font color='{ACCENT.hexval()}'><b>{num_prefix}</b></font>&nbsp;&nbsp;{inline_formatting(item_text)}"
            flowables.append(Paragraph(numbered_text, numbered_style))
            i += 1
            continue

        # Default Paragraph
        flowables.append(Paragraph(inline_formatting(stripped), BODY_STYLE))
        flowables.append(Spacer(1, 4))
        i += 1

    # End of file flushes
    if in_code_block and code_lines:
        flowables.extend(render_code_box(code_lines))
    if in_table and table_rows:
        flowables.extend(flush_table(table_rows))
    if in_blockquote and blockquote_lines:
        flowables.extend(flush_blockquote(blockquote_lines))

    return flowables

# ── Flushing Complex Blocks ──────────────────────────────────────────────────
def flush_table(table_rows):
    flowables = []
    if not table_rows:
        return flowables
        
    num_cols = len(table_rows[0])
    cleaned_rows = []
    for r in table_rows:
        if len(r) < num_cols:
            r = r + [""] * (num_cols - len(r))
        else:
            r = r[:num_cols]
        cleaned_rows.append(r)
        
    formatted_rows = []
    # Header styling
    headers = [Paragraph(inline_formatting(c), TABLE_HEADER_STYLE) for c in cleaned_rows[0]]
    formatted_rows.append(headers)
    
    # Cells styling
    for row in cleaned_rows[1:]:
        formatted_rows.append([Paragraph(inline_formatting(c), TABLE_CELL_STYLE) for c in row])
        
    # Proportional column width algorithm
    col_lengths = [0] * num_cols
    for row in cleaned_rows:
        for col_idx, cell in enumerate(row):
            col_lengths[col_idx] += len(cell)
            
    total_len = sum(col_lengths)
    if total_len > 0:
        col_widths = []
        raw_ratios = [l / total_len for l in col_lengths]
        # 50/50 blend of raw proportional ratio and equal width prevents extremes
        for ratio in raw_ratios:
            smoothed = 0.5 * ratio + 0.5 * (1.0 / num_cols)
            col_widths.append(smoothed * CONTENT_W)
    else:
        col_widths = [CONTENT_W / num_cols] * num_cols
        
    t = Table(formatted_rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), PRIMARY),
        ("GRID",          (0,0), (-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GREY]),
    ]))
    flowables.append(t)
    flowables.append(Spacer(1, 8))
    return flowables

def flush_blockquote(blockquote_lines):
    flowables = []
    if not blockquote_lines:
        return flowables
        
    alert_type = "NOTE"
    bg_color = ALERT_BLUE_BG
    border_color = ALERT_BLUE_BORDER
    label_color = ALERT_BLUE_TEXT
    
    combined_quote = "\n".join(blockquote_lines)
    first_line_clean = blockquote_lines[0].upper()
    
    # Detect Alert Types
    if "IMPORTANT" in first_line_clean:
        alert_type = "IMPORTANT"
        bg_color = ALERT_RED_BG
        border_color = ALERT_RED_BORDER
        label_color = ALERT_RED_TEXT
    elif "WARNING" in first_line_clean:
        alert_type = "WARNING"
        bg_color = ALERT_RED_BG
        border_color = ALERT_RED_BORDER
        label_color = ALERT_RED_TEXT
    elif "TIP" in first_line_clean:
        alert_type = "TIP"
        bg_color = ALERT_GREEN_BG
        border_color = ALERT_GREEN_BORDER
        label_color = ALERT_GREEN_TEXT
    elif "CAUTION" in first_line_clean:
        alert_type = "CAUTION"
        bg_color = ALERT_AMBER_BG
        border_color = ALERT_AMBER_BORDER
        label_color = ALERT_AMBER_TEXT
        
    # Clean up alert tag markers
    cleaned_quote_lines = []
    for line in blockquote_lines:
        l_clean = re.sub(r"^\[\!.*?\]\s*", "", line, flags=re.IGNORECASE)
        if l_clean.strip():
            cleaned_quote_lines.append(l_clean)
            
    if not cleaned_quote_lines:
        cleaned_quote_lines = blockquote_lines
        
    quote_html = "<br/>".join([inline_formatting(l) for l in cleaned_quote_lines])
    alert_prefix = f"<b>{alert_type}</b>: "
    paragraph_content = f"<font color='{label_color.hexval()}'>{alert_prefix}</font><i>{quote_html}</i>"
    
    p = Paragraph(paragraph_content, BODY_STYLE)
    t = Table([[p]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg_color),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("LINELEFT",      (0,0), (0,-1), 3.5, border_color),
    ]))
    flowables.append(t)
    flowables.append(Spacer(1, 6))
    return flowables

# ── Compiler Orchestrator ────────────────────────────────────────────────────
def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_pdf = os.path.join(root_dir, "SignalMDM_Enterprise_Documentation.pdf")
    
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.8*cm,
        bottomMargin=2.0*cm,
        title="SignalMDM Master Specifications Suite",
        author="Antigravity AI Platform Architect Team",
    )

    story = []

    # ═══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════════
    cover_data = [[
        Paragraph("SIGNALMDM PLATFORM", TITLE_STYLE),
    ],[
        Paragraph("Enterprise System Documentation Suite", TITLE_STYLE),
    ],[
        Spacer(1, 8),
    ],[
        Paragraph("Unified Master Technical Reference & Deployment Specifications", SUBTITLE_STYLE),
    ],[
        Spacer(1, 12),
    ],[
        Paragraph("Compilation Date: 2026-05-22 | Version: 1.0.0-RC1", META_STYLE),
    ],[
        Paragraph("Auditors: Antigravity AI — Principal QA & Platform Architecture Team", META_STYLE),
    ],[
        Paragraph("Classification: Internal Technical Confidential", META_STYLE),
    ]]

    cover_table = Table([[row[0]] for row in cover_data], colWidths=[CONTENT_W])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), PRIMARY),
        ("TOPPADDING",    (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("LEFTPADDING",   (0,0), (-1,-1), 20),
        ("RIGHTPADDING",  (0,0), (-1,-1), 20),
        ("LINEABOVE",     (0,0), (-1,0),  2.5, ACCENT),
        ("LINEBELOW",     (0,-1),(-1,-1), 2.5, ACCENT),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 20))

    # Core System Summary Matrix Table
    meta_rows = [
        ["System Identifier", "SignalMDM (Enterprise Multi-Tenant MDM Platform)"],
        ["Target Environments", "Local Dev / UAT Staging / Production Kubernetes"],
        ["Core API Layer", "FastAPI on Python 3.12 / Uvicorn Engine"],
        ["Client Interface", "React 18 / TypeScript / Vite / Express Gateway"],
        ["Persistent Tier", "PostgreSQL 15+ / Strict Multi-Tenant Schema Scopes"],
        ["Caching / Security", "Redis Queue Broker / AES-256 JWT Decryption Filters"]
    ]
    meta_data = [[
        Paragraph(f"<b>{r[0]}</b>", TABLE_CELL_STYLE),
        Paragraph(r[1], TABLE_CELL_STYLE)
    ] for r in meta_rows]
    
    meta_t = Table(meta_data, colWidths=[4.5*cm, CONTENT_W - 4.5*cm])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT_BLUE),
        ("BACKGROUND",    (1,0), (1,-1), WHITE),
        ("GRID",          (0,0), (-1,-1), 0.3, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LIGHT_GREY, WHITE]*3),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_t)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PARSE & COMPILE FILES
    # ═══════════════════════════════════════════════════════════════════════
    md_files = [
        "README.md",
        "ARCHITECTURE.md",
        "DIRECTORY_REFERENCE.md",
        "API_REFERENCE.md",
        "DATABASE_REFERENCE.md",
        "DEPLOYMENT.md",
        "TECHNICAL_REFERENCE.md"
    ]

    for fname in md_files:
        fpath = os.path.join(root_dir, fname)
        print(f"Parsing and appending file: {fname}...")
        
        # Parse file lines
        file_flowables = parse_markdown_to_flowables(fpath)
        if file_flowables:
            story.extend(file_flowables)
            story.append(PageBreak())

    # Build PDF
    print(f"Building final integrated PDF document at: {output_pdf}...")
    doc.build(story, onFirstPage=first_page_layout_callback, onLaterPages=page_layout_callback)
    print("Success! Integrated documentation PDF generated successfully.")

if __name__ == "__main__":
    main()
