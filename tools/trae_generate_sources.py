#!/usr/bin/env python3
"""TRAE — Daily Cybersecurity Newsletter (DATA ONLY).

Generates only JSON parts + email drafts (no PDF/posters). Sources are limited to the
netsecid RSS allowlist (English + active feeds only).

Windowing rules:
- Default window: last 24h relative to ISSUE_DATE 07:00 WIB.
- Fallback window: last 48h.
- If still insufficient to fill 10/10/10, backfill from previous issue day's JSON
  outputs (local read only, no web fetch).

Age tags:
- >24h from issue time: "[+24h Old] "
- >48h from issue time: "[+48h Old] "
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

WIB = dt.timezone(dt.timedelta(hours=7), name="WIB")
ISSUE_TIME_STR = "17:00 WIB"
ISSUE_HOUR = 17
ALLOWLIST_URL = "https://raw.githubusercontent.com/netsecid/cybersecurity-rss-sources/main/feeds/all.json"
ALLOWLIST_CACHE = Path(__file__).parent / "rss_allowlist_cache.json"

# Remove common tracking params to help dedup canonical URLs.
_TRACKING_QS_PREFIXES = (
    "utm_",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
)


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    category: str
    language: str


@dataclass
class Candidate:
    title: str
    link: str
    published_utc: dt.datetime
    source_name: str
    source_url: str
    category_hint: str
    description: str


def now_wib() -> dt.datetime:
    return dt.datetime.now(tz=WIB)


def issue_base(issue_date: dt.date) -> dt.datetime:
    return dt.datetime.combine(issue_date, dt.time(hour=ISSUE_HOUR), tzinfo=WIB)


def fetch_text(url: str, timeout_s: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "cyber-news-daily-updates/trae (rss-to-json)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read()
    # be permissive: decode with utf-8 then fallback.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def load_allowlist() -> list[Feed]:
    # Coba cache lokal dulu biar gak kena rate limit GitHub
    raw = None
    if ALLOWLIST_CACHE.exists():
        try:
            raw = ALLOWLIST_CACHE.read_text("utf-8")
        except Exception:
            raw = None
    if not raw:
        raw = fetch_text(ALLOWLIST_URL)
    obj = json.loads(raw)
    feeds: list[Feed] = []
    for cat in obj.get("categories", []):
        cat_name = str(cat.get("name") or "").strip() or "(unknown)"
        for f in cat.get("feeds", []) or []:
            if not f or not f.get("active"):
                continue
            url = str(f.get("url") or "").strip()
            if not url:
                continue
            lang = str(f.get("language") or "").strip().lower()
            # Allowlist policy: use ONLY English feeds for consistency.
            if lang != "en":
                continue
            # Skip VulDB — terlalu banyak CVE generic, lebih pilih NVD/ZDI/Rapid7
            name_lower = str(f.get("name") or "").strip().lower()
            if "vuldb" in name_lower:
                continue
            feeds.append(
                Feed(
                    name=str(f.get("name") or url).strip(),
                    url=url,
                    category=cat_name,
                    language=lang,
                )
            )

    feeds.sort(key=lambda x: (x.category, x.name))
    return feeds


def _parse_dt_any(s: str) -> Optional[dt.datetime]:
    s = (s or "").strip()
    if not s:
        return None

    # RFC822 / RSS pubDate
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d is not None:
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc)
    except Exception:
        pass

    # ISO 8601
    s2 = s
    if s2.endswith("Z"):
        s2 = s2[:-1] + "+00:00"
    try:
        d = dt.datetime.fromisoformat(s2)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _clean_text(s: str) -> str:
    s = s or ""
    s = html.unescape(s)
    # strip HTML tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except Exception:
        return url

    qs = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        lk = k.lower()
        if any(lk.startswith(p) for p in _TRACKING_QS_PREFIXES):
            continue
        qs.append((k, v))

    new_query = urlencode(qs, doseq=True)
    # drop fragment
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, ""))


def norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def parse_feed_items(xml_text: str, feed: Feed) -> list[Candidate]:
    # Use ElementTree without external deps.
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    items: list[Candidate] = []

    root_tag = strip_ns(root.tag).lower()
    if root_tag == "feed":
        # Atom
        for entry in root.findall(".//{*}entry"):
            title = _clean_text("".join(entry.findtext("{*}title") or ""))

            link = ""
            for ln in entry.findall("{*}link"):
                rel = (ln.attrib.get("rel") or "alternate").lower()
                href = ln.attrib.get("href")
                if rel == "alternate" and href:
                    link = href
                    break
            if not link:
                link = entry.findtext("{*}link") or ""

            published = entry.findtext("{*}published") or entry.findtext("{*}updated") or ""
            published_utc = _parse_dt_any(published)
            if not published_utc:
                continue

            desc = (
                entry.findtext("{*}summary")
                or entry.findtext("{*}content")
                or ""
            )
            desc = _clean_text(desc)

            if title and link:
                items.append(
                    Candidate(
                        title=title,
                        link=canonical_url(link),
                        published_utc=published_utc,
                        source_name=feed.name,
                        source_url=feed.url,
                        category_hint=feed.category,
                        description=desc,
                    )
                )
    else:
        # RSS (default)
        for it in root.findall(".//channel/item") + root.findall(".//{*}item"):
            title = _clean_text(it.findtext("title") or it.findtext("{*}title") or "")
            link = _clean_text(it.findtext("link") or it.findtext("{*}link") or "")

            pub = (
                it.findtext("pubDate")
                or it.findtext("{*}pubDate")
                or it.findtext("dc:date")
                or it.findtext("{*}date")
                or ""
            )
            published_utc = _parse_dt_any(pub)
            if not published_utc:
                continue

            desc = it.findtext("description") or it.findtext("{*}description") or ""
            if not desc:
                # some feeds use content:encoded
                desc = it.findtext("{*}encoded") or ""
            desc = _clean_text(desc)

            if title and link:
                items.append(
                    Candidate(
                        title=title,
                        link=canonical_url(link),
                        published_utc=published_utc,
                        source_name=feed.name,
                        source_url=feed.url,
                        category_hint=feed.category,
                        description=desc,
                    )
                )

    return items


_VULN_KW = (
    "cve-",
    "vulnerability",
    "advisory",
    "patch",
    "poc",
    "exploit",
    "rce",
    "remote code",
    "sql injection",
    "xss",
    "privilege escalation",
    "authentication bypass",
    "heap overflow",
    "buffer overflow",
    "path traversal",
    "0-day",
    "zero day",
)

_DATA_KW = (
    "breach",
    "data leak",
    "leak",
    "exfiltration",
    "stolen",
    "ransomware",
    "extortion",
    "fraud",
    "scam",
    "arrest",
    "indict",
    "cybercrime",
    "carding",
    "skimmer",
)

_TI_KW = (
    "apt",
    "campaign",
    "malware",
    "botnet",
    "phishing",
    "infostealer",
    "backdoor",
    "trojan",
    "ddos",
    "ioc",
    "ttp",
    "supply chain",
    "worm",
    "loader",
)


def score_category(c: Candidate) -> tuple[str, int]:
    text = f"{c.title} {c.description} {c.category_hint}".lower()

    vul = 0
    db = 0
    ti = 0

    if "cve-" in text:
        vul += 6

    for kw in _VULN_KW:
        if kw in text:
            vul += 2

    for kw in _DATA_KW:
        if kw in text:
            db += 2

    for kw in _TI_KW:
        if kw in text:
            ti += 2

    # Category hint from allowlist
    hint = c.category_hint.lower()
    if "vulner" in hint:
        vul += 3
    if "breach" in hint or "cybercrime" in hint:
        db += 3
    if "threat" in hint or "intel" in hint or "malware" in hint:
        ti += 3

    scores = {
        "vulnerabilities": vul,
        "data_breach": db,
        "threat_intel": ti,
    }

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] == 0:
        # No clear signal → do not force into a section (helps relevance).
        return ("other", 0)
    return best[0], best[1]


def _sentence_truncate(s: str, max_chars: int = 320) -> str:
    s = _clean_text(s)
    if not s:
        return ""
    if len(s) <= max_chars:
        return s

    cut = s[: max_chars - 1].rstrip()
    # try to cut at sentence boundary
    m = re.search(r"[.!?]\s+", cut[::-1])
    if m:
        # reverse index of boundary
        idx_from_end = m.end()
        idx = len(cut) - idx_from_end
        if idx > 120:
            cut = cut[:idx].rstrip()
    return cut + "…"


def build_summary(c: Candidate) -> str:
    base = c.description or ""
    if not base:
        base = c.title
    return _sentence_truncate(base, max_chars=360)


def build_why_and_reco(section: str, c: Candidate) -> tuple[str, str]:
    t = c.title.lower()
    d = c.description.lower()
    blob = f"{t} {d}"

    if section == "vulnerabilities":
        why = "Exploit-ready vulnerabilities can rapidly translate into compromise—especially for internet-facing services and widely deployed products."
        reco = "Prioritize patching/mitigations, review exposure, and add detection for exploitation attempts (e.g., WAF/EDR signatures and logs)."
        if "0-day" in blob or "zero day" in blob:
            why = "Publicly discussed 0-days often see rapid weaponization, increasing the risk of opportunistic attacks at scale."
            reco = "Apply vendor guidance immediately, reduce attack surface, and monitor for IoCs/exploitation telemetry until patches are fully deployed."
        return why, reco

    if section == "data_breach":
        why = "Breaches and cybercrime activity signal where attackers are focusing and what data types are actively monetized."
        reco = "Validate incident-response readiness, monitor for exposed credentials, and reinforce MFA, phishing resistance, and data-loss controls."
        if "ransomware" in blob:
            why = "Ransomware operations combine disruption with extortion, making recovery speed and data-resilience core business risks."
            reco = "Verify offline backups, test restores, harden remote access, and review segmentation to limit lateral movement."
        return why, reco

    # threat_intel
    why = "Threat-actor tradecraft and active campaigns help defenders anticipate techniques likely to be used against their environment."
    reco = "Update detections and threat hunts using reported TTPs/IOCs, review email/web controls, and harden high-risk internet-facing services."
    if "phishing" in blob:
        reco = "Tighten email authentication and filtering, run targeted user awareness, and monitor for lookalike domains and suspicious inbox rules."
    if "supply chain" in blob:
        reco = "Audit build pipelines, rotate CI/CD secrets, enforce package integrity controls, and review developer workstation hardening."
    return why, reco


_AGE_PREFIX_RE = re.compile(r"^\[\+(?:24h|48h)\s+Old\]\s+", flags=re.IGNORECASE)


def strip_age_prefix(title: str) -> str:
    return _AGE_PREFIX_RE.sub("", title or "").strip()


def apply_age_prefix(title: str, published_wib: dt.datetime, cutoff_24h: dt.datetime, cutoff_48h: dt.datetime) -> str:
    base = strip_age_prefix(title)
    if published_wib < cutoff_48h:
        return "[+48h Old] " + base
    if published_wib < cutoff_24h:
        return "[+24h Old] " + base
    return base


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def required_outputs(report_dir: Path, issue_date: str) -> list[Path]:
    year = issue_date[:4]
    issue_root = report_dir / year / issue_date
    src = issue_root / "source"
    return [
        issue_root / f"email_subject_{issue_date}.txt",
        issue_root / f"email_body_{issue_date}.txt",
        src / "meta.json",
        src / "highlights.json",
        src / "threat_intel.json",
        src / "vulnerabilities.json",
        src / "data_breach.json",
        src / "readme_summary.json",
    ]


def all_exist(paths: Iterable[Path]) -> bool:
    return all(p.exists() for p in paths)


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"months": {}, "issues": {}, "updated_at_wib": None}
    return json.loads(state_path.read_text(encoding="utf-8"))


def compute_vol(state: dict, issue_date: str) -> str:
    issues = state.setdefault("issues", {})
    months = state.setdefault("months", {})

    if issue_date in issues:
        return str(issues[issue_date])

    month_key = issue_date[:7]
    if month_key in months:
        vol = str(months[month_key])
    else:
        # increment from max existing month vol; start at 001
        max_vol = 0
        for v in months.values():
            try:
                max_vol = max(max_vol, int(str(v)))
            except Exception:
                continue
        vol = f"{max_vol + 1:03d}" if max_vol else "001"
        months[month_key] = vol

    issues[issue_date] = vol
    return str(vol)


def dedup_candidates(cands: list[Candidate]) -> list[Candidate]:
    by_url: dict[str, Candidate] = {}
    out: list[Candidate] = []

    for c in sorted(cands, key=lambda x: x.published_utc, reverse=True):
        cu = canonical_url(c.link)
        nt = norm_title(c.title)

        if cu in by_url:
            continue

        # soft title dedup against last ~80 items to keep cost low
        dupe = False
        for prev in out[:80]:
            if similar(nt, norm_title(prev.title)) >= 0.92:
                dupe = True
                break
        if dupe:
            continue

        by_url[cu] = c
        out.append(c)

    return out


def pick_sections(cands: list[Candidate], issue_cutoff_24h_utc: dt.datetime) -> tuple[list[Candidate], list[Candidate], list[Candidate]]:
    # NOTE: We intentionally do NOT cross-fill sections using leftovers. If a section
    # is short, it will be backfilled from previous issue outputs (data-only) to
    # preserve topical relevance.
    buckets: dict[str, list[tuple[int, Candidate]]] = {
        "threat_intel": [],
        "vulnerabilities": [],
        "data_breach": [],
        "other": [],
    }

    for c in cands:
        sec, score = score_category(c)
        buckets.setdefault(sec, []).append((score, c))

    def finalize(key: str) -> list[Candidate]:
        ranked = buckets.get(key, [])
        ranked.sort(key=lambda sc: (sc[1].published_utc, sc[0]), reverse=True)
        return [c for _s, c in ranked[:10]]

    return finalize("threat_intel"), finalize("vulnerabilities"), finalize("data_breach")


def build_section_json(section_key: str, items: list[Candidate], cutoff_24h_wib: dt.datetime) -> list[dict]:
    out = []
    for c in items:
        published_wib = c.published_utc.astimezone(WIB)
        # 48h tag is applied only if the item is older than 48h from issue time.
        cutoff_48h_wib = cutoff_24h_wib - dt.timedelta(hours=24)
        title = apply_age_prefix(c.title, published_wib, cutoff_24h_wib, cutoff_48h_wib)
        summary = build_summary(c)
        why, reco = build_why_and_reco(section_key, c)
        out.append(
            {
                "title": title,
                "published_wib": published_wib.isoformat(),
                "summary": summary,
                "why_it_matters": why,
                "recommendation": reco,
                "sources": [canonical_url(c.link)][:3],
            }
        )
    return out


def build_email(issue_date: str, vol: str, highlights: list[str], ti: list[dict], vul: list[dict], db: list[dict]) -> tuple[str, str]:
    # Subject summary: 2–3 highlights
    clean_h = [re.sub(r"\s+", " ", h).strip() for h in highlights if h.strip()]
    subject_items = clean_h[:3]
    if len(subject_items) > 2:
        summary = "; ".join(subject_items[:3])
    else:
        summary = "; ".join(subject_items)
    if len(summary) > 120:
        summary = "; ".join(subject_items[:2]) + "…"

    subject = f"[Cybersecurity Daily] Vol. {vol} | {issue_date}: {summary}"

    def section_sentence(name: str, items: list[dict], default_focus: str) -> str:
        if not items:
            # Keep template expectation: max 2 sentences
            return (
                f"{name}: No items were captured from the allowed RSS sources in the time window. "
                "Consider running a forced re-run if a prior run was incomplete."
            )
        top = items[0]["title"]
        # remove [+24h Old] in summary sentence to reduce noise
        top = top.replace("[+24h Old] ", "").replace("[+48h Old] ", "")
        # Template expectation: <2 sentence>
        return f"{name}: {len(items)} items, led by {top}. {default_focus}."

    body = "\n".join(
        [
            "Hi there,",
            "",
            "Here is your Cybersecurity Daily Update for the last 24 hours (with a limited 48-hour fallback where needed).",
            "",
            "Quick Highlights (max 5):",
            *[f"- {h}" for h in clean_h[:5]],
            "",
            "Section Summaries:",
            f"- {section_sentence('Threat Intelligence', ti, 'with ongoing campaign and malware activity signals')}",
            f"- {section_sentence('Latest Vulnerabilities', vul, 'prioritizing patching and exposure reduction for high-impact issues')}",
            f"- {section_sentence('Data Breach & Cybercrime', db, 'highlighting extortion, leakage, and law-enforcement actions where reported')}",
            "",
            "CTA: Full report and infographics attached below.",
            "",
            "---",
        ]
    )

    return subject.strip() + "\n", body.strip() + "\n"


def _pick_best_item(items: list[dict], keywords: tuple[str, ...]) -> Optional[dict]:
    if not items:
        return None
    if not keywords:
        return items[0]
    for it in items:
        blob = f"{it.get('title','')} {it.get('summary','')}".lower()
        if any(k in blob for k in keywords):
            return it
    return items[0]


def build_readme_summaries(
    *,
    ti_json: list[dict],
    vul_json: list[dict],
    db_json: list[dict],
) -> dict:
    # These strings are inserted after fixed leading clauses in README.md.
    v1 = strip_age_prefix(str(vul_json[0].get("title") or "")) if vul_json else ""
    v2 = strip_age_prefix(str(vul_json[1].get("title") or "")) if len(vul_json) > 1 else ""
    led_by_vulns = (
        f"{v1} and {v2}. "
        "Treat newly published PoCs and early exploitation signals as immediate patch/mitigation triggers for internet-facing and fleet-wide infrastructure."
    ).strip()

    ti_best = _pick_best_item(
        ti_json,
        (
            "malware",
            "botnet",
            "campaign",
            "apt",
            "phishing",
            "infostealer",
            "backdoor",
            "supply chain",
        ),
    )
    ti_title = strip_age_prefix(str((ti_best or {}).get("title") or "")).strip()
    endpoint_pressure = (
        f"{ti_title}. "
        "Tighten EDR coverage, block known IoCs where available, and validate software supply-chain integrity in build and CI/CD."
    ).strip()

    db_best = _pick_best_item(
        db_json,
        (
            "credential",
            "account",
            "login",
            "auth",
            "oauth",
            "mfa",
            "vpn",
            "gateway",
            "edge",
            "remote access",
            "breach",
            "leak",
            "ransomware",
            "extortion",
        ),
    )
    db_title = strip_age_prefix(str((db_best or {}).get("title") or "")).strip()
    identity_edge = (
        f"{db_title}. "
        "Prioritize MFA enforcement, phishing-resistant authentication, and reduce management-plane exposure for edge services and remote access."
    ).strip()

    return {
        "highlights_led_by_exploit_ready_vulns": led_by_vulns,
        "endpoint_posture_under_pressure": endpoint_pressure,
        "identity_and_edge_access_risks": identity_edge,
    }


def _load_prev_issue_parts(report_root: Path, issue_date: dt.date) -> dict[str, list[dict]]:
    """Load previous day's JSON parts (if present) for backfill.

    This is a local read only: it does NOT fetch web content and stays within repo.
    """
    prev_date = issue_date - dt.timedelta(days=1)
    prev_dir = report_root / str(prev_date.year) / prev_date.isoformat() / "source"
    if not prev_dir.exists():
        return {}
    out: dict[str, list[dict]] = {}
    for key, fname in [
        ("threat_intel", "threat_intel.json"),
        ("vulnerabilities", "vulnerabilities.json"),
        ("data_breach", "data_breach.json"),
    ]:
        p = prev_dir / fname
        if p.exists():
            try:
                out[key] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                out[key] = []
    return out


def _backfill_section(
    *,
    current: list[dict],
    prev: list[dict],
    need: int,
    cutoff_24h_wib: dt.datetime,
    cutoff_48h_wib: dt.datetime,
    seen_urls: set[str],
) -> list[dict]:
    if need <= 0:
        return current

    for it in prev or []:
        if len(current) >= 10:
            break
        try:
            src0 = canonical_url((it.get("sources") or [""])[0])
        except Exception:
            src0 = ""
        if src0 and src0 in seen_urls:
            continue

        try:
            pub_wib = dt.datetime.fromisoformat(str(it.get("published_wib") or ""))
        except Exception:
            continue

        # Re-apply age prefix relative to *today's* issue time.
        it2 = dict(it)
        it2["title"] = apply_age_prefix(str(it2.get("title") or ""), pub_wib, cutoff_24h_wib, cutoff_48h_wib)
        current.append(it2)
        if src0:
            seen_urls.add(src0)

    return current


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-re-run", action="store_true", help="Regenerate even if ISSUE_DATE already exists")
    ap.add_argument("--issue-date", default=None, help="Override ISSUE_DATE (YYYY-MM-DD); default = today in WIB")
    ap.add_argument("--max-feeds", type=int, default=0, help="Optional cap for number of feeds fetched (0 = no cap)")
    args = ap.parse_args(argv)

    wib_now = now_wib()
    if args.issue_date:
        issue_date = dt.date.fromisoformat(args.issue_date)
    else:
        issue_date = wib_now.date()

    issue_dt = issue_base(issue_date)
    cutoff_24h_wib = issue_dt - dt.timedelta(hours=24)
    cutoff_48h_wib = issue_dt - dt.timedelta(hours=48)
    cutoff_24h_utc = cutoff_24h_wib.astimezone(dt.timezone.utc)

    repo_root = Path(__file__).resolve().parents[1]
    report_root = repo_root / "Report"
    state_path = repo_root / "newsletter_state.json"

    year_dir = report_root / str(issue_date.year)
    issue_root = year_dir / issue_date.isoformat()
    source_dir = issue_root / "source"

    req_files = required_outputs(report_root, issue_date.isoformat())
    if all_exist(req_files) and not args.force_re_run:
        print(f"[no-search] Outputs already exist for {issue_date}. Exiting.")
        return 0

    if (issue_root.exists() or source_dir.exists()) and not args.force_re_run:
        # Do not re-fetch in default rerun mode.
        missing = [str(p.relative_to(repo_root)) for p in req_files if not p.exists()]
        if missing:
            print("[no-search] Some required outputs are missing:")
            for m in missing:
                print(f"  - {m}")
            print("Re-run with --force-re-run to rebuild (this will fetch RSS feeds).")
            return 2

    # Load/compute volume
    state = load_state(state_path)
    vol = compute_vol(state, issue_date.isoformat())
    state["updated_at_wib"] = issue_dt.isoformat()

    # Fetch allowlist + feeds
    feeds = load_allowlist()
    if args.max_feeds and args.max_feeds > 0:
        feeds = feeds[: args.max_feeds]

    def in_window(published_utc: dt.datetime, hours: int) -> bool:
        start = issue_dt.astimezone(dt.timezone.utc) - dt.timedelta(hours=hours)
        end = issue_dt.astimezone(dt.timezone.utc)
        return start <= published_utc <= end

    # First try 24h; if insufficient, expand to 48h.
    all_items: list[Candidate] = []
    for f in feeds:
        try:
            xml_text = fetch_text(f.url)
        except Exception:
            continue
        for it in parse_feed_items(xml_text, f):
            if in_window(it.published_utc, 48):
                all_items.append(it)

    all_items = dedup_candidates(all_items)

    # Build 24h-only pool and check if it can fill 10/10/10.
    pool_24h = [c for c in all_items if in_window(c.published_utc, 24)]

    ti24, vul24, db24 = pick_sections(pool_24h, cutoff_24h_utc)

    if len(ti24) >= 10 and len(vul24) >= 10 and len(db24) >= 10:
        ti_sel, vul_sel, db_sel = ti24, vul24, db24
    else:
        pool_48h = [c for c in all_items if in_window(c.published_utc, 48)]
        ti_sel, vul_sel, db_sel = pick_sections(pool_48h, cutoff_24h_utc)

    # Materialize JSON parts (may be <10; we will backfill from previous issue if needed)
    ensure_dir(source_dir)
    ensure_dir(issue_root)
    ensure_dir(year_dir)

    # Ensure year folder exists in git (optional)
    gitkeep = year_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    meta = {
        "issue_date": issue_date.isoformat(),
        "issue_time_wib": ISSUE_TIME_STR,
        "vol": f"{int(vol):03d}" if str(vol).isdigit() else str(vol),
    }

    ti_json = build_section_json("threat_intel", ti_sel[:10], cutoff_24h_wib)
    vul_json = build_section_json("vulnerabilities", vul_sel[:10], cutoff_24h_wib)
    db_json = build_section_json("data_breach", db_sel[:10], cutoff_24h_wib)

    # Backfill from previous day's outputs if RSS pool is insufficient to reach 10/10/10.
    if len(ti_json) < 10 or len(vul_json) < 10 or len(db_json) < 10:
        prev_parts = _load_prev_issue_parts(report_root, issue_date)
        seen_urls: set[str] = set()
        for sec in (ti_json + vul_json + db_json):
            try:
                u = canonical_url((sec.get("sources") or [""])[0])
            except Exception:
                u = ""
            if u:
                seen_urls.add(u)

        ti_json = _backfill_section(
            current=ti_json,
            prev=prev_parts.get("threat_intel", []),
            need=10 - len(ti_json),
            cutoff_24h_wib=cutoff_24h_wib,
            cutoff_48h_wib=cutoff_48h_wib,
            seen_urls=seen_urls,
        )
        vul_json = _backfill_section(
            current=vul_json,
            prev=prev_parts.get("vulnerabilities", []),
            need=10 - len(vul_json),
            cutoff_24h_wib=cutoff_24h_wib,
            cutoff_48h_wib=cutoff_48h_wib,
            seen_urls=seen_urls,
        )
        db_json = _backfill_section(
            current=db_json,
            prev=prev_parts.get("data_breach", []),
            need=10 - len(db_json),
            cutoff_24h_wib=cutoff_24h_wib,
            cutoff_48h_wib=cutoff_48h_wib,
            seen_urls=seen_urls,
        )

    # Hard validation: do not write partial outputs (prevents downstream broken artifacts).
    if len(ti_json) < 10 or len(vul_json) < 10 or len(db_json) < 10:
        print(
            "[error] Not enough items to fill 10/10/10 after 48h RSS fallback + previous-day backfill.",
            file=sys.stderr,
        )
        print(
            f"[error] Counts: threat_intel={len(ti_json)}, vulnerabilities={len(vul_json)}, data_breach={len(db_json)}",
            file=sys.stderr,
        )
        print(
            "[error] Aborting without writing outputs.",
            file=sys.stderr,
        )
        return 3

    # Highlights: 5 newest among final 30 items (with age prefix applied)
    combined_items: list[tuple[dt.datetime, str]] = []
    for it in (ti_json + vul_json + db_json):
        try:
            pub = dt.datetime.fromisoformat(str(it.get("published_wib") or ""))
        except Exception:
            continue
        title = apply_age_prefix(str(it.get("title") or ""), pub, cutoff_24h_wib, cutoff_48h_wib)
        combined_items.append((pub, title))

    combined_items.sort(key=lambda x: x[0], reverse=True)
    highlights = [t for _p, t in combined_items[:5]]

    if len(highlights) < 5:
        print(
            f"[error] Not enough items to build 5 highlights (got {len(highlights)}). Aborting.",
            file=sys.stderr,
        )
        return 3

    subject, body = build_email(
        issue_date=issue_date.isoformat(),
        vol=meta["vol"],
        highlights=highlights,
        ti=ti_json,
        vul=vul_json,
        db=db_json,
    )

    readme_summary = build_readme_summaries(ti_json=ti_json, vul_json=vul_json, db_json=db_json)
    readme_summary["issue_date"] = issue_date.isoformat()
    readme_summary["vol"] = meta["vol"]

    (issue_root / f"email_subject_{issue_date.isoformat()}.txt").write_text(subject, encoding="utf-8")
    (issue_root / f"email_body_{issue_date.isoformat()}.txt").write_text(body, encoding="utf-8")

    (source_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (source_dir / "highlights.json").write_text(json.dumps(highlights, indent=2) + "\n", encoding="utf-8")
    (source_dir / "threat_intel.json").write_text(json.dumps(ti_json, indent=2) + "\n", encoding="utf-8")
    (source_dir / "vulnerabilities.json").write_text(json.dumps(vul_json, indent=2) + "\n", encoding="utf-8")
    (source_dir / "data_breach.json").write_text(json.dumps(db_json, indent=2) + "\n", encoding="utf-8")
    (source_dir / "readme_summary.json").write_text(json.dumps(readme_summary, indent=2) + "\n", encoding="utf-8")

    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(f"Generated DATA-ONLY newsletter parts for {issue_date.isoformat()} (Vol. {meta['vol']}).")
    print("Next step: commit & push Report/**/source/** + email drafts; GitHub Actions will generate PDF/JPG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
