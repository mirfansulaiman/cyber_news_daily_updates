# Cyber News Daily Updates

This repository stores **daily cybersecurity newsletters** (English) generated from an **RSS allowlist** and published on a regular basis.

## Support Me by Ko-fi
![Ko-fi](https://storage.ko-fi.com/cdn/logomarkLogo.png) https://ko-fi.com/mirfansulaiman

> Note: The section below is **auto-updated by GitHub Actions** after PDF + poster images are generated.

<!-- AUTO-GENERATED:START -->
## Today Updates

Waiting for the first successful artifact generation run.
<!-- AUTO-GENERATED:END -->

## Today Updates: [Vol. 001 | 2026-05-23 07:00 WIB]

Today's highlights are led by exploit-ready vulnerabilities: 2026-05-22: SmartApeSG ClickFix --> Unidentified RAT --> NetSupport RAT and A Russian speaker and jailbroken Gemini went on a hacking spree and emptied at least one MAGA victim's crypto wallets. Treat newly published PoCs and early exploitation signals as immediate patch/mitigation triggers for internet-facing and fleet-wide infrastructure.

Endpoint posture is also under pressure: Ubiquiti patches three critical vulnerabilities in UniFi OS. Public privilege-escalation PoCs can rapidly turn initial access into full SYSTEM/root control, so monitoring and least-privilege hardening remain critical.

Identity and edge access risks remain elevated: Cisco warns of AI inaccuracies in security incident reports, plus Organizations knowingly ship vulnerable code amid shrinking exploit windows. Prioritize OAuth/conditional-access hardening and minimize management-plane exposure on network control components.

![Cover Poster](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-23/poster_2026-05-23_issue-001.jpg)

### TOP 10 - VULNERABILITIES

![Top 10 Vulnerabilities](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-23/poster_vulnerabilities_2026-05-23_issue-001.jpg)

### TOP 10 - THREAT INTEL

![Top 10 Threat Intel](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-23/poster_threat-intel_2026-05-23_issue-001.jpg)

### TOP 10 - DATA BREACH & CYBERCRIME

![Top 10 Data Breach & Cybercrime](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-23/poster_data-breach_2026-05-23_issue-001.jpg)

### PDF Report

Download: https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-23/cyber_newsletter_2026-05-23.pdf

## Task Automation

### Data-only generation (TRAE)
TRAE generates **ONLY** the data + email drafts:
- `Report/<YEAR>/<ISSUE_DATE>/source/{meta.json,highlights.json,threat_intel.json,vulnerabilities.json,data_breach.json}`
- `Report/<YEAR>/<ISSUE_DATE>/email_subject_<ISSUE_DATE>.txt`
- `Report/<YEAR>/<ISSUE_DATE>/email_body_<ISSUE_DATE>.txt`
- `newsletter_state.json`

### PDF & poster images (GitHub Actions)
GitHub Actions materializes:
- `Report/<YEAR>/<ISSUE_DATE>/cyber_newsletter_<ISSUE_DATE>.pdf`
- `Report/<YEAR>/<ISSUE_DATE>/poster_<ISSUE_DATE>_issue-<VOL>.jpg`
- `Report/<YEAR>/<ISSUE_DATE>/poster_{vulnerabilities,threat-intel,data-breach}_<ISSUE_DATE>_issue-<VOL>.jpg`

After the artifacts are generated, the workflow also updates `README.md` to point to the latest issue.

## Data Source
RSS allowlist: https://github.com/netsecid/cybersecurity-rss-sources
