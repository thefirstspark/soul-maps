#!/usr/bin/env python3
"""Build Soul Map Generator Algorithm Spec PDF for filing."""
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "Soul_Map_Generator_Algorithm_Spec.pdf"
# Also copy-friendly path on Desktop
OUT_DESKTOP = Path.home() / "Desktop" / "Soul_Map_Generator_Algorithm_Spec.pdf"
# Repo-root alias (optional)
OUT_REPO = Path(__file__).resolve().parent.parent / "docs" / "Soul_Map_Generator_Algorithm_Spec.pdf"

# Brand palette
VOID = colors.HexColor("#0B0B0C")
GOLD = colors.HexColor("#d4af37")
CYAN = colors.HexColor("#22d3ee")
VIOLET = colors.HexColor("#8b5cf6")
EMBER = colors.HexColor("#ff6a3d")
WHITE = colors.HexColor("#f0ece4")
DIM = colors.HexColor("#888888")
PANEL = colors.HexColor("#14141a")
RULE = colors.HexColor("#3a3540")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_brand": ParagraphStyle(
            "cover_brand",
            fontName="Helvetica",
            fontSize=9,
            textColor=CYAN,
            alignment=TA_CENTER,
            letterSpacing=3,
            spaceAfter=8,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=GOLD,
            alignment=TA_CENTER,
            leading=32,
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=11,
            textColor=WHITE,
            alignment=TA_CENTER,
            leading=16,
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=9,
            textColor=DIM,
            alignment=TA_CENTER,
            leading=13,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=GOLD,
            spaceBefore=16,
            spaceAfter=8,
            leading=18,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=CYAN,
            spaceBefore=12,
            spaceAfter=6,
            leading=14,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=VIOLET,
            spaceBefore=8,
            spaceAfter=4,
            leading=13,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=WHITE,
            alignment=TA_JUSTIFY,
            leading=13,
            spaceAfter=6,
        ),
        "body_left": ParagraphStyle(
            "body_left",
            fontName="Helvetica",
            fontSize=9,
            textColor=WHITE,
            alignment=TA_LEFT,
            leading=13,
            spaceAfter=6,
        ),
        "mono": ParagraphStyle(
            "mono",
            fontName="Courier",
            fontSize=8,
            textColor=CYAN,
            leading=11,
            spaceAfter=4,
            leftIndent=8,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=9,
            textColor=WHITE,
            leading=12,
            leftIndent=12,
            spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=DIM,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=DIM,
            alignment=TA_CENTER,
        ),
        "warn": ParagraphStyle(
            "warn",
            fontName="Helvetica",
            fontSize=9,
            textColor=EMBER,
            leading=12,
            spaceAfter=4,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=8,
            textColor=WHITE,
            leading=11,
        ),
        "table_head": ParagraphStyle(
            "table_head",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=GOLD,
            leading=11,
        ),
        "formula": ParagraphStyle(
            "formula",
            fontName="Courier",
            fontSize=8.5,
            textColor=GOLD,
            leading=12,
            leftIndent=10,
            spaceBefore=4,
            spaceAfter=6,
            backColor=PANEL,
        ),
    }
    return styles


def hr():
    return HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=4, spaceAfter=8)


def dark_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(VOID)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # top gold rule
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.2)
    canvas.line(MARGIN, PAGE_H - 0.45 * inch, PAGE_W - MARGIN, PAGE_H - 0.45 * inch)
    # footer
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 0.55 * inch, PAGE_W - MARGIN, 0.55 * inch)
    canvas.setFillColor(DIM)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 0.35 * inch, "CONFIDENTIAL — Proprietary Algorithm Spec")
    canvas.drawRightString(
        PAGE_W - MARGIN,
        0.35 * inch,
        f"Page {doc.page}  ·  The First Spark / Kate's Paint LLC",
    )
    canvas.restoreState()


def cover_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(VOID)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # decorative frame
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.5)
    inset = 0.5 * inch
    canvas.rect(inset, inset, PAGE_W - 2 * inset, PAGE_H - 2 * inset, fill=0, stroke=1)
    canvas.setStrokeColor(VIOLET)
    canvas.setLineWidth(0.6)
    canvas.rect(inset + 8, inset + 8, PAGE_W - 2 * inset - 16, PAGE_H - 2 * inset - 16, fill=0, stroke=1)
    canvas.restoreState()


def P(text, style):
    return Paragraph(text, style)


def bullet_list(items, styles):
    flow = []
    for item in items:
        flow.append(P(f"•  {item}", styles["bullet"]))
    return flow


def section_table(headers, rows, styles, col_widths):
    head = [P(h, styles["table_head"]) for h in headers]
    body = []
    for row in rows:
        body.append([P(str(c), styles["table_cell"]) for c in row])
    data = [head] + body
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1520")),
                ("BACKGROUND", (0, 1), (-1, -1), PANEL),
                ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def build():
    styles = make_styles()
    story = []

    # ========== COVER ==========
    story.append(Spacer(1, 1.8 * inch))
    story.append(P("THE FIRST SPARK", styles["cover_brand"]))
    story.append(P("SOUL MAP GENERATOR", styles["cover_title"]))
    story.append(P("Algorithm Specification &amp; System Record", styles["cover_sub"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(hr())
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        P(
            "Source of truth: <font color='#22d3ee'>soul_map_generator.py</font><br/>"
            "Companion systems: webhook_server.py · monthly_regenerate.py · signatures.json",
            styles["cover_meta"],
        )
    )
    story.append(Spacer(1, 0.35 * inch))
    story.append(
        P(
            f"Document date: {date.today().isoformat()}<br/>"
            "Version: 1.0 — Algorithm filing copy<br/>"
            "Owner: Kate's Paint LLC / The First Spark<br/>"
            "Contact: kate@thefirstspark.shop",
            styles["cover_meta"],
        )
    )
    story.append(Spacer(1, 0.6 * inch))
    story.append(
        P(
            "PROPRIETARY &amp; CONFIDENTIAL<br/>"
            "This document describes the complete computational algorithm used to generate Soul Maps. "
            "It is intended for internal filing, IP record, and engineering reference. "
            "Do not distribute outside authorized parties without written permission.",
            styles["cover_meta"],
        )
    )
    story.append(PageBreak())

    # ========== 1. PURPOSE ==========
    story.append(P("1. Purpose &amp; Scope", styles["h1"]))
    story.append(hr())
    story.append(
        P(
            "The Soul Map Generator is a deterministic pipeline that transforms a person's "
            "<b>full legal (or preferred) name</b>, <b>date of birth</b>, and optionally "
            "<b>birth time + city</b> into a branded HTML Soul Map page. The map combines "
            "Pythagorean numerology, Western sun-sign astrology, Chinese zodiac, the proprietary "
            "Selector Model, Color Codex assignment, permanent identity minting (quantum signature / "
            "activation code / resonance frequency), narrative synthesis, and monthly-cycle updates.",
            styles["body"],
        )
    )
    story.append(
        P(
            "Outputs are committed to the public GitHub Pages host "
            "(soul-maps.thefirstspark.shop) and optionally emailed to the purchaser. "
            "Core identity fields are permanent after first mint (first-write-wins registry).",
            styles["body"],
        )
    )

    # ========== 2. PIPELINE ==========
    story.append(P("2. End-to-End Pipeline", styles["h1"]))
    story.append(hr())
    story.append(P("2.1 Buyer journey", styles["h2"]))
    for line in [
        "Sales page → Whop checkout ($22 product).",
        "Post-purchase redirect → success.html intake form (name, DOB, time, city, email).",
        "POST /generate on webhook_server.py (background thread).",
        "generate_soul_map() builds HTML + summary dict.",
        "generate_monthly_update() builds current-month page.",
        "deploy_to_github() writes both files + updates archive index.",
        "add_subscriber() stores 12-month entitlement in subscribers.json.",
        "Resend email delivers live URL.",
        "Cron (1st of month): monthly_regenerate.py refreshes active subscribers.",
    ]:
        story.append(P(f"→  {line}", styles["bullet"]))

    story.append(P("2.2 Primary entry points", styles["h2"]))
    story.append(
        section_table(
            ["Function / Endpoint", "Role"],
            [
                ["generate_soul_map(name, dob, time?, city?)", "Full map HTML + summary dict"],
                ["generate_monthly_update(name, dob, y?, m?)", "Monthly cycle HTML"],
                ["get_or_mint_signature(...)", "Permanent UUID registry (first mint wins)"],
                ["deploy_to_github(html, filename, ...)", "GitHub Contents API commit"],
                ["POST /generate", "Webhook intake (async generation)"],
                ["monthly_regenerate.py", "Batch monthly updates for active subs"],
            ],
            styles,
            [3.2 * inch, 3.5 * inch],
        )
    )

    # ========== 3. INPUTS ==========
    story.append(P("3. Inputs &amp; Normalization", styles["h1"]))
    story.append(hr())
    story.append(
        section_table(
            ["Field", "Format", "Required", "Notes"],
            [
                ["full_name", "string", "Yes", "NFKC normalize; collapse whitespace; strip ZWSP/BOM"],
                ["birth_date", "YYYY-MM-DD → date", "Yes", "Core numerology + sun + Chinese year"],
                ["birth_time", "HH:MM → (h, m)", "No", "Enables Moon/Rising + planets via kerykeion"],
                ["birth_city", "string", "No*", "Required with time for full chart"],
                ["birth_country", "ISO-ish", "No", "Default US"],
                ["memorial_date / birthday_from", "string", "No", "Ceremony banner modes"],
            ],
            styles,
            [1.4 * inch, 1.5 * inch, 0.8 * inch, 3.0 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(P("Name canonicalization (normalize_name)", styles["h2"]))
    story.append(
        P(
            "Unicode NFKC → replace exotic spaces with ASCII space → strip zero-width / BOM → "
            "collapse runs of whitespace → strip ends. Does <b>not</b> force Title Case "
            "(preserves McDonald-style casing). Letter math uppercases inside numerology only.",
            styles["body"],
        )
    )
    story.append(P("identity_key = casefold(normalize_name) + '|' + ISO date", styles["formula"]))

    # ========== 4. NUMEROLOGY ==========
    story.append(P("4. Numerology Engine (Core Algorithm)", styles["h1"]))
    story.append(hr())
    story.append(
        P(
            "System: <b>Pythagorean</b> letter values. Master numbers preserved: "
            "<b>11, 22, 33</b> when <font face='Courier'>preserve_masters=True</font>.",
            styles["body"],
        )
    )

    story.append(P("4.1 Letter map (PYTHAGOREAN_MAP)", styles["h2"]))
    story.append(
        section_table(
            ["Value", "Letters"],
            [
                ["1", "A J S"],
                ["2", "B K T"],
                ["3", "C L U"],
                ["4", "D M V"],
                ["5", "E N W"],
                ["6", "F O X"],
                ["7", "G P Y"],
                ["8", "H Q Z"],
                ["9", "I R"],
            ],
            styles,
            [1.0 * inch, 5.7 * inch],
        )
    )
    story.append(P("Vowels for Soul Urge: A E I O U only (Y treated as consonant).", styles["caption"]))

    story.append(P("4.2 Reduction function", styles["h2"]))
    story.append(
        P(
            "reduce_number(n, preserve_masters=True): while n &gt; 9, if preserve_masters and n ∈ {11,22,33} "
            "return n; else n = sum of decimal digits.",
            styles["body"],
        )
    )

    story.append(P("4.3 Core numbers", styles["h2"]))
    formulas = [
        ("Life Path", "reduce( reduce(month) + reduce(day) + reduce(digit_sum(year)) ) — masters preserved on each step and final"),
        ("Expression", "name_to_number(all letters A–Z)"),
        ("Soul Urge", "name_to_number(vowels only)"),
        ("Personality", "name_to_number(consonants only)"),
        ("Birthday", "reduce(day of month)"),
        ("Maturity", "reduce(Expression + Life Path)"),
        ("Hidden Passion", "most frequent digit 1–9 in name letters; ties → lowest digit"),
        ("Karmic Lessons", "digits 1–9 absent from name letter values"),
        ("Personal Year", "reduce( reduce(month, no master) + reduce(day, no master) + reduce(digit_sum(calendar_year), no master), masters yes )"),
        ("Personal Month", "reduce(PersonalYear + calendar_month)"),
        ("Personal Day", "reduce(PersonalMonth + reduce(calendar_day, no master))"),
        ("Pinnacles", "P1=M+D; P2=D+Y; P3=P1+P2; P4=M+Y (M,D,Y pre-reduced without masters)"),
        ("Challenges", "C1=|M−D|; C2=|D−Y|; C3=|C1−C2|; C4=|M−Y| then reduce"),
    ]
    for name, formula in formulas:
        story.append(P(f"<b>{name}</b>", styles["h3"]))
        story.append(P(formula, styles["formula"]))

    story.append(P("4.4 Reference computation (audit fixture)", styles["h2"]))
    story.append(
        P(
            "Name: <b>Katelin Jill Puzakulics</b> · DOB: <b>1988-05-19</b> · as of mid-2026",
            styles["body_left"],
        )
    )
    story.append(
        section_table(
            ["Field", "Value"],
            [
                ["Life Path", "5"],
                ["Expression", "11"],
                ["Soul Urge", "4"],
                ["Personality", "7"],
                ["Birthday", "1"],
                ["Maturity", "7"],
                ["Hidden Passion", "3"],
                ["Karmic Lessons", "4, 6"],
                ["Personal Year 2026", "7"],
                ["Pinnacles", "6 / 9 / 6 / 4"],
                ["Challenges", "4 / 7 / 3 / 3"],
                ["Sun", "Taurus"],
                ["Chinese", "Earth Dragon"],
                ["Selector Layer", "Temporal — Freedom frequency"],
                ["Color Codex", "Violet · The Transformer · Purple"],
                ["Quantum (12-hex)", "E1855DD782A3"],
                ["Resonance Hz", "824.43"],
                ["Activation", "1C245658[LP5]"],
                ["Base filename", "KJP51988.html"],
            ],
            styles,
            [2.2 * inch, 4.5 * inch],
        )
    )

    # ========== 5. ASTRO ==========
    story.append(PageBreak())
    story.append(P("5. Astrology Layers", styles["h1"]))
    story.append(hr())
    story.append(P("5.1 Sun sign (always)", styles["h2"]))
    story.append(
        P(
            "Table-driven tropical date ranges (Aries Mar 21–Apr 19 … Pisces Feb 19–Mar 20). "
            "Capricorn wraps year boundary (Dec 22–Jan 19). Implemented in sun_sign().",
            styles["body"],
        )
    )
    story.append(P("5.2 Full chart (optional)", styles["h2"]))
    story.append(
        P(
            "If birth_time and birth_city provided: kerykeion.AstrologicalSubject computes Moon, "
            "Rising (1st house), Mercury, Venus, Mars, Jupiter, Saturn. On failure, map still generates "
            "with a 'birth time needed' placeholder.",
            styles["body"],
        )
    )
    story.append(P("5.3 Chinese zodiac", styles["h2"]))
    story.append(P("animal = ANIMALS[(year − 4) mod 12]", styles["formula"]))
    story.append(P("element = ELEMENTS[(year − 4) mod 10]  // Wood×2, Fire×2, Earth×2, Metal×2, Water×2", styles["formula"]))

    # ========== 6. SELECTOR / CODEX ==========
    story.append(P("6. Selector Model &amp; Color Codex", styles["h1"]))
    story.append(hr())
    story.append(P("6.1 Selector layer (from Life Path)", styles["h2"]))
    story.append(
        section_table(
            ["LP", "Layer", "Frequency tag"],
            [
                ["1", "Temporal", "Pioneer — initiate timelines"],
                ["2", "Relational", "Bridge — weave connection fields"],
                ["3", "Metaphysical", "Expression — transmit through creation"],
                ["4", "Physics", "Structure — build architecture"],
                ["5", "Temporal", "Freedom — collapse fixed timelines"],
                ["6", "Relational", "Harmony — calibrate collective fields"],
                ["7", "Metaphysical", "Seeker — decode hidden patterns"],
                ["8", "Physics", "Power — materialize abstract → concrete"],
                ["9", "Relational", "Completion — integrate signal layers"],
                ["11", "Metaphysical", "Master Intuitive"],
                ["22", "Physics", "Master Builder"],
                ["33", "Relational", "Master Teacher"],
            ],
            styles,
            [0.7 * inch, 1.4 * inch, 4.6 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(P("6.2 Color Codex priority (first match wins)", styles["h2"]))
    for i, rule in enumerate(
        [
            "Gold — LP/EX/SU is 22 or 33, OR ≥2 master numbers in core set",
            "Violet — any single 11 on LP / EX / SU (Transformer)",
            "Rose — Life Path 2 or 6 (Bond)",
            "Silver — Life Path 9 (Mirror)",
            "Spectrum by LP with EX/SU refinements (red/ember/yellow/cyan/green/blue)",
            "Green fallback — Field stabilizer",
        ],
        1,
    ):
        story.append(P(f"{i}.  {rule}", styles["bullet"]))

    # ========== 7. ADVANCED ==========
    story.append(P("7. Advanced / Proprietary Outputs", styles["h1"]))
    story.append(hr())

    story.append(P("7.1 Quantum signature", styles["h2"]))
    story.append(
        P(
            "SHA-256 of concatenated core numbers string f\"{LP}{EX}{SU}{PE}{BD}\"; "
            "first 12 hex chars uppercased. Display form: AAAA·BBBB·CCCC.",
            styles["body"],
        )
    )
    story.append(P("Note: same core numbers → same quantum (name not in hash). Identity uniqueness is name|DOB in the registry.", styles["warn"]))

    story.append(P("7.2 Soul resonance frequency (Hz)", styles["h2"]))
    story.append(
        P(
            "base = 432.0 Hz. Each core number maps to a harmonic multiplier "
            "(1→1.0, 2→1.5, 3→1.25, 4→2.0, 5→1.667, 6→1.2, 7→1.875, 8→2.667, 9→1.111, "
            "11→3.0, 22→4.0, 33→5.333). Weighted average of multipliers for "
            "[LP, EX, SU, PE, BD] × 432, rounded to 2 decimals.",
            styles["body"],
        )
    )

    story.append(P("7.3 Activation code", styles["h2"]))
    story.append(
        P(
            "MD5 of f\"{NAME_UPPER}{DD}{MM}{LP}\" → first 8 hex upper + literal suffix [LP{n}]. "
            "Name is normalize_name().upper() so whitespace quirks do not mint divergent codes.",
            styles["body"],
        )
    )

    story.append(P("7.4 Permanent mint registry (signatures.json)", styles["h2"]))
    story.append(
        P(
            "get_or_mint_signature: if identity_key already exists, reuse quantum / resonance / activation / "
            "codex fields (marketing claim of permanent UUID). Else compute, store locally, and best-effort "
            "push to GitHub via GITHUB_PAT. formula_version currently = 1.",
            styles["body"],
        )
    )

    story.append(P("7.5 Supporting modules", styles["h2"]))
    story.append(
        section_table(
            ["Module", "Behavior"],
            [
                ["rarity_detection", "Score 0–100 from master counts + pattern flags"],
                ["predictive_windows", "90-day scan: birthday-day month shifts, 11/22 master days, next PY"],
                ["power_hour_calculation", "Maps personal day → suggested local hour block"],
                ["evolutionary_trajectory", "Maps 9-year personal year cycle arc"],
                ["oracle_mapping", "LP/EX/SU → Major Arcana trinity"],
                ["destiny_checkpoints", "Pinnacle ages, master PYs ahead, Saturn returns ~29/58"],
                ["shadow_integration_path", "Practices for top karmic lessons"],
                ["karmic_debt_remediation", "Heuristic remedies (see audit notes)"],
                ["auto_soul_synthesis", "Template narrative when no hand-written NARRATIVES entry"],
                ["auto_debugging_notes", "Watch-list bullets from masters / density / lessons"],
            ],
            styles,
            [2.0 * inch, 4.7 * inch],
        )
    )

    # ========== 8. FILE IDS ==========
    story.append(P("8. Filenames &amp; Deployment", styles["h1"]))
    story.append(hr())
    story.append(P("Base ID: initials (first letter of each word) + month + year", styles["formula"]))
    story.append(P("Example: Aaron Joseph Thomas, 1988-09-24 → AJT91988.html", styles["mono"]))
    story.append(P("Monthly: {base}-{YYYY}{MM}.html  e.g. KJP51988-202607.html", styles["mono"]))
    story.append(
        P(
            "Deploy uses GitHub Contents API (create-or-update with SHA). Host: "
            "https://soul-maps.thefirstspark.shop/{filename}. Archive index updated via "
            "update_index_html / _api_update_index.",
            styles["body"],
        )
    )

    # ========== 9. DATA MODEL ==========
    story.append(P("9. Data Artifacts", styles["h1"]))
    story.append(hr())
    story.append(
        section_table(
            ["Artifact", "Purpose"],
            [
                ["signatures.json", "Permanent mints: quantum, Hz, activation, codex, core nums"],
                ["subscribers.json", "Paid entitlement: email, dob, purchase, expiry (+365d), active"],
                ["bonds.json", "Family / resonance graph (related product)"],
                ["HTML map pages", "Customer-facing deliverable on GitHub Pages"],
                ["NARRATIVES dict", "Optional hand-authored synthesis overrides"],
            ],
            styles,
            [1.8 * inch, 4.9 * inch],
        )
    )

    # ========== 10. IP CLAIMS ==========
    story.append(P("10. Proprietary Claim Summary (for filing)", styles["h1"]))
    story.append(hr())
    story.append(
        P(
            "While individual Pythagorean and sun-sign methods are traditional, the following "
            "combination and extensions constitute the Soul Map product system of The First Spark:",
            styles["body"],
        )
    )
    for item in [
        "Multi-layer stack: numerology + tropical sun + Chinese element/animal + Selector Model layer mapping.",
        "Color Codex assignment tree keyed to birth numerology (not aesthetic random hash).",
        "Permanent identity mint (quantum hex + activation + Hz) with first-write-wins registry.",
        "Resonance frequency formula (432 Hz × averaged number harmonics).",
        "Auto narrative synthesis / debugging notes with master-density detection.",
        "Destiny checkpoints combining pinnacles, master-year scan, and Saturn returns in one table.",
        "Fulfillment automation: webhook → generate → GitHub Pages → Resend → 12-month monthly regen.",
        "Brand voice interpretation corpus (LIFE_PATH_MEANINGS and related dictionaries) as expressive IP.",
    ]:
        story.append(P(f"•  {item}", styles["bullet"]))

    # ========== 11. AUDIT ==========
    story.append(PageBreak())
    story.append(P("11. Algorithm Audit Findings (2026-07-26)", styles["h1"]))
    story.append(hr())
    story.append(
        P(
            "This section is the engineering audit run against soul-maps/soul_map_generator.py "
            "and webhook_server.py. Severity: Critical / High / Medium / Low / Info.",
            styles["body"],
        )
    )

    story.append(P("11.1 Critical / High", styles["h2"]))
    findings_high = [
        (
            "H1 — Unauthenticated /generate endpoint",
            "POST /generate has CORS allowlist for shop domains but no payment proof, shared secret, "
            "or Whop webhook signature. Anyone who can reach the server can queue free maps and enroll "
            "subscribers. Recommend: require Whop webhook or signed intake token; rate-limit by IP/email.",
        ),
        (
            "H2 — Master Personal Years unreachable",
            "personal_year() pre-reduces month/day/year with preserve_masters=False, so intermediates "
            "never stay 11/22. Final sum max is 9+9+9=27→9. Master Personal Years (11/22/33) and "
            "destiny_checkpoints master-year scan can never fire. If product copy promises master years, "
            "change reduction policy (preserve masters on day/month before sum, or single-pass reduction).",
        ),
        (
            "H3 — karmic_debt() is a stub",
            "Function always returns {}. True karmic debt (13/14/16/19 unreduced) is not computed. "
            "karmic_debt_remediation() instead flags ALL LP 4/5/7/1 as potential debt — false positives.",
        ),
        (
            "H4 — Filename collisions",
            "get_base_filename uses initials+month+year only. John Doe and Jane Doe both 1990-05 → JD51990. "
            "Later deploy overwrites earlier map. Mitigate: include day, short hash of name, or quantum prefix.",
        ),
    ]
    for title, body in findings_high:
        story.append(P(title, styles["h3"]))
        story.append(P(body, styles["body"]))

    story.append(P("11.2 Medium", styles["h2"]))
    findings_med = [
        (
            "M1 — Quantum signature not name-unique",
            "Hash inputs are only core numbers. Two different people with identical LP/EX/SU/PE/BD share "
            "the same quantum hex. Registry key (name|dob) is unique, but marketing 'fingerprint' can collide.",
        ),
        (
            "M2 — Evolutionary trajectory + master years",
            "cycle math uses personal_year as if always 1–9 (years_remaining = 10 − py). Broken if masters appear. "
            "HTML 'next transition' line uses a fragile birthday-offset expression.",
        ),
        (
            "M3 — Power hour minute field",
            "hour_mapping values are (hour_a, hour_b) pairs but assigned to hour/minute → displays like 08:09 "
            "instead of a real clock range 08:00–09:00.",
        ),
        (
            "M4 — Y vowel policy undocumented in product",
            "Y is always consonant (value 7). Traditional schools sometimes treat Y as vowel. "
            "Document this as intentional system rule on sales page to reduce disputes.",
        ),
        (
            "M5 — Ephemeral subscribers on ephemeral disk",
            "subscribers.json on Railway/Render is not durable across deploys unless volume/Git sync. "
            "Risk of losing monthly entitlement list. Prefer GitHub-backed or DB store (same pattern as signatures).",
        ),
        (
            "M6 — Background thread fire-and-forget",
            "Webhook returns 200 before generation completes. Client has no job id; failures only in server logs. "
            "Add status endpoint or queue with durable jobs.",
        ),
    ]
    for title, body in findings_med:
        story.append(P(title, styles["h3"]))
        story.append(P(body, styles["body"]))

    story.append(P("11.3 Low / Content", styles["h2"]))
    findings_low = [
        (
            "L1 — PINNACLE_MEANINGS all say 'First pinnacle'",
            "P2–P4 reuse first-pinnacle wording; destiny_checkpoints strips prefix but pinnacle section copy is off.",
        ),
        (
            "L2 — Capricorn sun wrap dead clause",
            "Condition (m == 12 and m > sm) never true (sm=12). Capricorn still resolves via other branches — dead code only.",
        ),
        (
            "L3 — Hand narratives sparse",
            "NARRATIVES only hardcodes a few names; everyone else gets auto_soul_synthesis (good fallback, less premium).",
        ),
        (
            "L4 — HTML injection surface",
            "Name and narrative fields are substituted into HTML without HTML-escaping. Malicious name could inject script "
            "into GitHub Pages. Escape user-controlled strings before template insert.",
        ),
    ]
    for title, body in findings_low:
        story.append(P(title, styles["h3"]))
        story.append(P(body, styles["body"]))

    story.append(P("11.4 What is solid", styles["h2"]))
    for item in [
        "Core Pythagorean math for LP/EX/SU/PE/BD is consistent and deterministic.",
        "normalize_name prevents silent identity drift from form whitespace/unicode.",
        "Master number preservation on Life Path path is correct for 11/22/33 intermediates.",
        "Sun sign cusps verified (e.g. Mar 20 Pisces / Mar 21 Aries; Dec 21 Sag / Dec 22 Cap).",
        "Chinese zodiac (year−4) mod tables match standard animal/element cycles.",
        "Color Codex priority tree is explicit and LP5+EX11 → violet (Transformer) matches fixture.",
        "Signature first-mint-wins correctly reuses permanent IDs across regenerations.",
        "Optional kerykeion degrades gracefully when time/city missing or library fails.",
    ]:
        story.append(P(f"•  {item}", styles["bullet"]))

    story.append(P("11.5 Recommended fix order", styles["h2"]))
    for i, item in enumerate(
        [
            "Lock /generate behind payment verification + rate limits.",
            "Decide intentional master Personal Year policy; implement or remove master-year UI.",
            "Implement real unreduced karmic debt (13/14/16/19) or rename 'potential' copy.",
            "Disambiguate filenames (day + short name hash).",
            "HTML-escape all user strings; persist subscribers like signatures.",
            "Fix power-hour display as a range; expand hand narratives for VIP maps.",
        ],
        1,
    ):
        story.append(P(f"{i}.  {item}", styles["bullet"]))

    # ========== 12. CHANGE CONTROL ==========
    story.append(P("12. Change Control", styles["h1"]))
    story.append(hr())
    story.append(
        P(
            "Any change to number reduction rules, letter map, Color Codex priority, quantum/activation "
            "inputs, or identity_key format must bump SIGNATURE_FORMULA_VERSION and be recorded here. "
            "Existing mints must remain stable (first-write-wins) unless an explicit migration is approved.",
            styles["body"],
        )
    )
    story.append(
        section_table(
            ["Version", "Date", "Notes"],
            [
                ["1.0", date.today().isoformat(), "Initial filing copy + full algorithm audit"],
            ],
            styles,
            [1.0 * inch, 1.3 * inch, 4.4 * inch],
        )
    )

    story.append(Spacer(1, 24))
    story.append(hr())
    story.append(
        P(
            "© 2026 Kate's Paint LLC · The First Spark · All rights reserved.<br/>"
            "Reality is programmable. Consciousness is the code.",
            styles["caption"],
        )
    )

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=0.7 * inch,
        bottomMargin=0.75 * inch,
        title="Soul Map Generator — Algorithm Specification",
        author="The First Spark / Kate's Paint LLC",
        subject="Proprietary algorithm specification and audit for Soul Map Generator",
        creator="Soul Map Algorithm Filing Tool",
    )
    doc.build(story, onFirstPage=cover_canvas, onLaterPages=dark_canvas)
    print(f"Wrote: {OUT}")

    import shutil
    try:
        shutil.copy2(OUT, OUT_DESKTOP)
        print(f"Wrote: {OUT_DESKTOP}")
    except Exception as e:
        print(f"[WARN] Desktop copy failed: {e}")


if __name__ == "__main__":
    build()
