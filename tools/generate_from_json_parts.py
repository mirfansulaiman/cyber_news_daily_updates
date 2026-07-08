#!/usr/bin/env python3
"""Generate PDF + posters from Report/**/source JSON files.

Tujuan:
- Menghindari upload file biner via MCP GitHub.
- Push hanya data (JSON) + email drafts.
- Biarkan GitHub Actions membangkitkan PDF/JPG dan commit ke repo.
- Update README.md ditangani oleh workflow (bukan oleh script ini).

Input per issue folder:
Report/<YEAR>/<ISSUE_DATE>/source/
  - meta.json
  - highlights.json
  - threat_intel.json
  - vulnerabilities.json
  - data_breach.json
  - readme_summary.json (untuk memastikan README bisa terisi lengkap)

Output per issue folder:
  - cyber_newsletter_<ISSUE_DATE>.pdf
  - poster_<ISSUE_DATE>_issue-XXX.jpg
  - poster_threat-intel_<ISSUE_DATE>_issue-XXX.jpg
  - poster_vulnerabilities_<ISSUE_DATE>_issue-XXX.jpg
  - poster_data-breach_<ISSUE_DATE>_issue-XXX.jpg

Catatan:
- Isi konten newsletter tetap Bahasa Inggris (requirement newsletter).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


NEON_YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

REPO_OWNER = "mirfansulaiman"
REPO_NAME = "cyber_news_daily_updates"
REPO_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"

DASH_REPLACEMENTS = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
    "\u00ad": "-",
}

# Some RSS feeds include broken HTML-entity sequences like "GitHub&#;x26;#;39;s".
# ReportLab's Paragraph parser treats "&...;" as markup/entities and will crash on
# malformed sequences. We normalize the most common ones and then escape the rest.
MALFORMED_ENTITY_REPLACEMENTS = {
    "&#;x26;#;39": "'",  # &apos;
    "&#;x26;#;34": '"',  # &quot;
    "&#;x26;#;38": "&",  # &amp;
    "&#;x26;#;60": "<",  # &lt;
    "&#;x26;#;62": ">",  # &gt;
}


def normalize_text(text: str) -> str:
    for old, new in DASH_REPLACEMENTS.items():
        text = text.replace(old, new)
    return text


def reportlab_safe_text(text: str) -> str:
    """Make arbitrary text safe for ReportLab Paragraph (no markup)."""
    text = normalize_text(text)
    for old, new in MALFORMED_ENTITY_REPLACEMENTS.items():
        text = text.replace(old, new)
    # Escape characters with special meaning in ReportLab's mini-markup/XML.
    # Important: escape ampersands first.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text


@dataclass
class Item:
    title: str
    published_wib: str
    summary: str
    why_it_matters: str
    recommendation: str
    sources: list[str]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_issue_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def list_issue_dirs(report_root: Path) -> list[Path]:
    return sorted(report_root.glob("*/????-??-??"))


def issue_dir_date(issue_dir: Path) -> dt.date:
    # issue_dir = Report/<YEAR>/<YYYY-MM-DD>
    return parse_issue_date(issue_dir.name)


def register_fonts() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            pdfmetrics.registerFont(TTFont("DejaVuSans", p))
            return "DejaVuSans"
    return "Helvetica"


def pdf_styles(font_name: str) -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "Title",
            fontName=font_name,
            fontSize=26,
            leading=32,
            alignment=1,
            textColor=HexColor("#1a365d"),
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName=font_name,
            fontSize=12,
            leading=16,
            alignment=1,
            textColor=HexColor("#4a5568"),
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName=font_name,
            fontSize=18,
            leading=24,
            textColor=HexColor("#1a365d"),
            spaceBefore=16,
            spaceAfter=10,
        ),
        "item_title": ParagraphStyle(
            "ItemTitle",
            fontName=font_name,
            fontSize=12,
            leading=16,
            textColor=HexColor("#2d3748"),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            textColor=HexColor("#2d3748"),
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "Meta",
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=HexColor("#4a5568"),
            spaceAfter=10,
        ),
    }


def build_pdf(out_pdf: Path, issue_date: str, vol: str, highlights: list[str], sections: dict[str, list[Item]], issue_time_wib: str = "17:00 WIB"):
    font_name = register_fonts()
    styles = pdf_styles(font_name)

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Cybersecurity Daily Newsletter",
        author="GitHub Actions",
    )

    story = []
    story.append(Spacer(1, 0.9 * inch))
    story.append(Paragraph(reportlab_safe_text("Cybersecurity Daily Newsletter"), styles["title"]))
    story.append(Paragraph(reportlab_safe_text(f"Vol. {vol} | {issue_date} {issue_time_wib}"), styles["subtitle"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(normalize_text("<b>Top 5 Highlights</b>"), styles["h1"]))
    for h in highlights[:5]:
        story.append(Paragraph(reportlab_safe_text(f"• {h}"), styles["body"]))
    story.append(PageBreak())

    def add_section(title: str, items: list[Item]):
        story.append(Paragraph(reportlab_safe_text(title), styles["h1"]))
        for idx, it in enumerate(items, 1):
            story.append(
                Paragraph(
                    normalize_text(f"<b>{idx:02d}. {reportlab_safe_text(it.title)}</b>"),
                    styles["item_title"],
                )
            )
            story.append(Paragraph(reportlab_safe_text(it.summary), styles["body"]))
            story.append(
                Paragraph(
                    normalize_text(f"<b>Why it matters:</b> {reportlab_safe_text(it.why_it_matters)}"),
                    styles["body"],
                )
            )
            story.append(
                Paragraph(
                    normalize_text(f"<b>Recommendation:</b> {reportlab_safe_text(it.recommendation)}"),
                    styles["body"],
                )
            )
            srcs = " | ".join(reportlab_safe_text(s) for s in it.sources[:3])
            story.append(
                Paragraph(
                    normalize_text(f"<font color='#4a5568'>Sources:</font> {srcs}"),
                    styles["meta"],
                )
            )

    add_section("Threat Intelligence (10)", sections["threat_intelligence"])
    add_section("Latest Vulnerabilities (10)", sections["latest_vulnerabilities"])
    add_section("Data Breach & Cybercrime (10)", sections["data_breach_cybercrime"])

    doc.build(story)


def load_mono_font(size: int) -> ImageFont.FreeTypeFont:
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def synthwave_background(w: int, h: int, seed: int) -> Image.Image:
    random.seed(seed)
    img = Image.new("RGB", (w, h), (10, 0, 25))
    draw = ImageDraw.Draw(img)

    top = (10, 0, 35)
    mid = (60, 0, 90)
    bottom = (0, 0, 10)
    for y in range(h):
        t = y / (h - 1)
        if t < 0.7:
            tt = t / 0.7
            c = (
                int(top[0] + (mid[0] - top[0]) * tt),
                int(top[1] + (mid[1] - top[1]) * tt),
                int(top[2] + (mid[2] - top[2]) * tt),
            )
        else:
            tt = (t - 0.7) / 0.3
            c = (
                int(mid[0] + (bottom[0] - mid[0]) * tt),
                int(mid[1] + (bottom[1] - mid[1]) * tt),
                int(mid[2] + (bottom[2] - mid[2]) * tt),
            )
        draw.line([(0, y), (w, y)], fill=c)

    for _ in range(140):
        x = random.randint(0, w - 1)
        y = random.randint(0, int(h * 0.55))
        b = random.randint(160, 255)
        draw.point((x, y), fill=(b, b, b))

    sun_r = int(w * 0.18)
    sun_cx, sun_cy = int(w * 0.75), int(h * 0.28)
    draw.ellipse((sun_cx - sun_r, sun_cy - sun_r, sun_cx + sun_r, sun_cy + sun_r), fill=(255, 80, 200))

    horizon_y = int(h * 0.62)
    for i in range(60):
        draw.line([(0, horizon_y + i), (w, horizon_y + i)], fill=(255, 0, 180))

    grid_top = horizon_y
    grid_bottom = h
    grid_color = (255, 0, 210)
    for i in range(1, 18):
        yy = int(grid_top + (i / 18) ** 2 * (grid_bottom - grid_top))
        draw.line([(0, yy), (w, yy)], fill=grid_color, width=1)
    for i in range(-16, 17):
        x0 = w // 2 + i * 55
        draw.line([(x0, grid_bottom), (w // 2 + i * 8, grid_top)], fill=grid_color, width=1)

    return img


def truncate_token(token: str, max_width: int, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont) -> str:
    if draw.textlength(token, font=font) <= max_width:
        return token
    ell = "…"
    lo, hi = 1, len(token)
    best = ell
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = token[:mid] + ell
        if draw.textlength(cand, font=font) <= max_width:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def wrap_numbered_lines(items: list[str], draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for i, txt in enumerate(items, 1):
        prefix = f"{i:02d}. "
        indent = " " * len(prefix)
        words = txt.split()
        cur = prefix
        for w in words:
            test = (cur + (" " if cur.strip() != prefix.strip() else "") + w) if cur != prefix else (cur + w)
            if draw.textlength(test, font=font) <= max_width:
                cur = test
                continue
            if cur == prefix:
                w2 = truncate_token(w, max_width - int(draw.textlength(prefix, font=font)), draw, font)
                lines.append(prefix + w2)
                cur = indent
            else:
                lines.append(cur)
                cur = indent + w
        if cur.strip():
            lines.append(cur)
    return lines


def fit_text_block(header_lines: list[str], body_items: list[str], panel_w: int, panel_h: int) -> tuple[int, list[str]]:
    for size in range(46, 18, -2):
        header_font = load_mono_font(size)
        body_font = load_mono_font(size - 6)
        dummy = Image.new("RGB", (10, 10))
        d = ImageDraw.Draw(dummy)
        header_h = int(header_font.size * 1.25) * len(header_lines)
        body_lines = wrap_numbered_lines(body_items, d, body_font, panel_w)
        body_h = int(body_font.size * 1.35) * len(body_lines)
        if header_h + 24 + body_h <= panel_h:
            return size, body_lines
    size = 18
    body_font = load_mono_font(size - 4)
    dummy = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(dummy)
    body_lines = wrap_numbered_lines(body_items, d, body_font, panel_w)
    return size, body_lines


def draw_poster(out_path: Path, header: str, subheader: str, items: list[str], seed: int, vol: str, issue_date: str, issue_time_wib: str = "17:00 WIB"):
    W, H = 1080, 1350
    bg = synthwave_background(W, H, seed)
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    panel_margin = 70
    panel_x0, panel_y0 = panel_margin, 190
    panel_x1, panel_y1 = W - panel_margin, H - 110
    panel_w, panel_h = panel_x1 - panel_x0, panel_y1 - panel_y0

    panel = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 170))
    img.alpha_composite(panel, dest=(panel_x0, panel_y0))

    header_lines = [header, subheader]
    base_size, body_lines = fit_text_block(header_lines, items, panel_w - 80, panel_h - 60)
    header_font = load_mono_font(base_size)
    body_font = load_mono_font(max(12, base_size - 6))
    header_line_h = int(header_font.size * 1.25)
    body_line_h = int(body_font.size * 1.35)

    total_h = len(header_lines) * header_line_h + 24 + len(body_lines) * body_line_h
    start_y = panel_y0 + (panel_h - total_h) // 2
    x_text = panel_x0 + 40

    y = start_y
    draw.text((x_text, y), header_lines[0], font=header_font, fill=CYAN)
    y += header_line_h
    draw.text((x_text, y), header_lines[1], font=header_font, fill=NEON_YELLOW)
    y += header_line_h + 24

    for line in body_lines:
        draw.text((x_text, y), line, font=body_font, fill=(230, 230, 230))
        y += body_line_h

    footer_font = load_mono_font(18)
    footer = f"Vol. {vol} | {issue_date} {issue_time_wib}"
    tw = draw.textlength(footer, font=footer_font)
    draw.text((W - panel_margin - tw, H - 70), footer, font=footer_font, fill=CYAN)

    img.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True, progressive=True)


def build_readme_summary_paragraphs(highlights: list[str]) -> list[str]:
    h = list(highlights[:5])
    while len(h) < 5:
        h.append("")

    return [
        (
            "Today's highlights are led by exploit-ready vulnerabilities: "
            f"{h[0]} and {h[1]}. "
            "Treat newly published PoCs and early exploitation signals as immediate patch/mitigation triggers for internet-facing and fleet-wide infrastructure."
        ),
        (
            "Endpoint posture is also under pressure: "
            f"{h[2]}. "
            "Public privilege-escalation PoCs can rapidly turn initial access into full SYSTEM/root control, so monitoring and least-privilege hardening remain critical."
        ),
        (
            "Identity and edge access risks remain elevated: "
            f"{h[3]}, plus {h[4]}. "
            "Prioritize OAuth/conditional-access hardening and minimize management-plane exposure on network control components."
        ),
    ]


def update_readme_today_updates(readme_path: Path, issue_date: str, vol: str, issue_time_wib: str = "17:00 WIB"):
    year = issue_date[:4]
    issue_tag = f"issue-{vol}"
    base = f"{RAW_BASE}/Report/{year}/{issue_date}"

    pdf = f"{base}/cyber_newsletter_{issue_date}.pdf"
    cover = f"{base}/poster_{issue_date}_{issue_tag}.jpg"
    pti = f"{base}/poster_threat-intel_{issue_date}_{issue_tag}.jpg"
    pv = f"{base}/poster_vulnerabilities_{issue_date}_{issue_tag}.jpg"
    pdb = f"{base}/poster_data-breach_{issue_date}_{issue_tag}.jpg"

    # Load highlights for this issue
    highlights_path = Path(f"Report/{year}/{issue_date}/source/highlights.json")
    highlights = json.loads(highlights_path.read_text(encoding="utf-8")) if highlights_path.exists() else []
    p1, p2, p3 = build_readme_summary_paragraphs(highlights)

    new_block = "\n".join(
        [
            f"## Today Updates: [Vol. {vol} | {issue_date} {issue_time_wib}]",
            "",
            p1,
            "",
            p2,
            "",
            p3,
            "",
            f"![Cover Poster]({cover})",
            "",
            "### TOP 10 - VULNERABILITIES",
            "",
            f"![Top 10 Vulnerabilities]({pv})",
            "",
            "### TOP 10 - THREAT INTEL",
            "",
            f"![Top 10 Threat Intel]({pti})",
            "",
            "### TOP 10 - DATA BREACH & CYBERCRIME",
            "",
            f"![Top 10 Data Breach & Cybercrime]({pdb})",
            "",
            "### PDF Report",
            "",
            f"Download: {pdf}",
            "",
        ]
    )

    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
    else:
        content = "# Cyber News Daily Updates\n\n"

    pattern = r"## Today Updates:[\s\S]*?(?=\n## Task Automation)"
    if re.search(pattern, content, flags=re.MULTILINE):
        updated = re.sub(pattern, new_block.rstrip() + "\n\n", content, flags=re.MULTILINE)
    else:
        # If template missing, append before Task Automation if exists
        if "## Task Automation" in content:
            updated = content.replace("## Task Automation", new_block + "\n## Task Automation")
        else:
            updated = content + "\n" + new_block

    readme_path.write_text(updated, encoding="utf-8")


def process_issue_folder(issue_dir: Path):
    source = issue_dir / "source"
    if not source.exists():
        return False

    # Pastikan semua input data JSON tersedia sebelum generate (hindari run parsial).
    required = [
        source / "meta.json",
        source / "highlights.json",
        source / "threat_intel.json",
        source / "vulnerabilities.json",
        source / "data_breach.json",
        source / "readme_summary.json",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("[skip] incomplete source inputs in", issue_dir, "missing:", ", ".join(p.name for p in missing))
        return False

    meta = load_json(source / "meta.json")
    highlights = load_json(source / "highlights.json")
    ti = [Item(**x) for x in load_json(source / "threat_intel.json")]
    vul = [Item(**x) for x in load_json(source / "vulnerabilities.json")]
    db = [Item(**x) for x in load_json(source / "data_breach.json")]

    # Validasi counts minimal agar PDF/poster konsisten.
    if len(highlights) < 5 or len(ti) != 10 or len(vul) != 10 or len(db) != 10:
        print(
            "[skip] invalid counts in",
            issue_dir,
            f"highlights={len(highlights)} ti={len(ti)} vul={len(vul)} db={len(db)}",
        )
        return False

    issue_date = meta["issue_date"]
    vol = meta["vol"]
    issue_time_wib = meta.get("issue_time_wib", "17:00 WIB")
    issue_tag = f"issue-{vol}"

    # PDF
    pdf_path = issue_dir / f"cyber_newsletter_{issue_date}.pdf"
    build_pdf(
        out_pdf=pdf_path,
        issue_date=issue_date,
        vol=vol,
        highlights=highlights,
        sections={
            "threat_intelligence": ti,
            "latest_vulnerabilities": vul,
            "data_breach_cybercrime": db,
        },
        issue_time_wib=issue_time_wib,
    )

    # Posters
    draw_poster(
        issue_dir / f"poster_{issue_date}_{issue_tag}.jpg",
        header="CYBERSECURITY DAILY NEWSLETTER",
        subheader=f"VOL. {vol} | {issue_date} {issue_time_wib}",
        items=highlights,
        seed=hash((issue_date, "cover")) & 0xFFFFFFFF,
        vol=vol,
        issue_date=issue_date,
        issue_time_wib=issue_time_wib,
    )

    draw_poster(
        issue_dir / f"poster_threat-intel_{issue_date}_{issue_tag}.jpg",
        header="TOP 10 — THREAT INTELLIGENCE",
        subheader=f"VOL. {vol} | {issue_date}",
        items=[x.title for x in ti],
        seed=hash((issue_date, "ti")) & 0xFFFFFFFF,
        vol=vol,
        issue_date=issue_date,
        issue_time_wib=issue_time_wib,
    )

    draw_poster(
        issue_dir / f"poster_vulnerabilities_{issue_date}_{issue_tag}.jpg",
        header="TOP 10 — LATEST VULNERABILITIES",
        subheader=f"VOL. {vol} | {issue_date}",
        items=[x.title for x in vul],
        seed=hash((issue_date, "vul")) & 0xFFFFFFFF,
        vol=vol,
        issue_date=issue_date,
        issue_time_wib=issue_time_wib,
    )

    draw_poster(
        issue_dir / f"poster_data-breach_{issue_date}_{issue_tag}.jpg",
        header="TOP 10 — DATA BREACH & CYBERCRIME",
        subheader=f"VOL. {vol} | {issue_date}",
        items=[x.title for x in db],
        seed=hash((issue_date, "db")) & 0xFFFFFFFF,
        vol=vol,
        issue_date=issue_date,
        issue_time_wib=issue_time_wib,
    )

    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Path to Report/ root")
    ap.add_argument("--issue-date", default=None, help="Generate hanya untuk 1 tanggal (YYYY-MM-DD)")
    ap.add_argument("--from-date", default=None, help="Awal range tanggal (YYYY-MM-DD)")
    ap.add_argument("--to-date", default=None, help="Akhir range tanggal (YYYY-MM-DD)")
    ap.add_argument("--all", action="store_true", help="Generate untuk semua tanggal yang ada di Report/")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        return

    processed: list[tuple[str, str]] = []  # (issue_date, vol)

    issue_dirs = list_issue_dirs(root)
    if not issue_dirs:
        print("no issues found under", root)
        return

    target_dirs: list[Path]
    if args.all:
        target_dirs = issue_dirs
    elif args.issue_date:
        d = parse_issue_date(args.issue_date)
        target_dirs = [p for p in issue_dirs if issue_dir_date(p) == d]
    elif args.from_date or args.to_date:
        d_from = parse_issue_date(args.from_date) if args.from_date else issue_dir_date(issue_dirs[0])
        d_to = parse_issue_date(args.to_date) if args.to_date else issue_dir_date(issue_dirs[-1])
        if d_from > d_to:
            d_from, d_to = d_to, d_from
        target_dirs = [p for p in issue_dirs if d_from <= issue_dir_date(p) <= d_to]
    else:
        # Default: hanya generate untuk tanggal laporan terakhir yang ada di repo.
        target_dirs = [issue_dirs[-1]]

    # Iterate selected issue folders
    for issue_dir in target_dirs:
        changed = process_issue_folder(issue_dir)
        if changed:
            src_meta = issue_dir / "source" / "meta.json"
            meta = load_json(src_meta)
            processed.append((meta["issue_date"], meta["vol"]))
            print("generated", issue_dir)

    # README update ditangani oleh workflow terpisah.
    if processed:
        latest_issue_date, latest_vol = sorted(processed, key=lambda x: x[0])[-1]
        print("latest processed:", latest_issue_date, latest_vol)
    else:
        print("no issue generated (inputs incomplete or no matching targets)")


if __name__ == "__main__":
    main()
