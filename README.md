# Cyber News Daily Updates

This repository is used to store **daily reports** related to cyber security news and updates, published on a regular basis.

## Support Me by Ko-fi
 ![https://ko-fi.com/mirfansulaiman](https://storage.ko-fi.com/cdn/logomarkLogo.png) https://ko-fi.com/mirfansulaiman

## Today Updates: [Vol. 001 | 2026-05-22 07:00 WIB]

Today's highlights are led by exploit-ready vulnerabilities: Wahlap data leak exposes 18.9 million records from WeChat mini-program ecosystem and Deleted Google API keys remain active for up to 23 minutes, study finds. Treat newly published PoCs and early exploitation signals as immediate patch/mitigation triggers for internet-facing and fleet-wide infrastructure.

Endpoint posture is also under pressure: New Linux malware 'Showboat' targets Middle East telecom provider. Public privilege-escalation PoCs can rapidly turn initial access into full SYSTEM/root control, so monitoring and least-privilege hardening remain critical.

Identity and edge access risks remain elevated: 'First VPN' service used by cybercriminals dismantled in international operation, plus Nvidia releases driver updates to fix 14 critical vulnerabilities. Prioritize OAuth/conditional-access hardening and minimize management-plane exposure on network control components.

![Cover Poster](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-22/poster_2026-05-22_issue-001.jpg)

### TOP 10 - VULNERABILITIES

![Top 10 Vulnerabilities](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-22/poster_vulnerabilities_2026-05-22_issue-001.jpg)

### TOP 10 - THREAT INTEL

![Top 10 Threat Intel](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-22/poster_threat-intel_2026-05-22_issue-001.jpg)

### TOP 10 - DATA BREACH & CYBERCRIME

![Top 10 Data Breach & Cybercrime](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-22/poster_data-breach_2026-05-22_issue-001.jpg)

### PDF Report

Download: https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-22/cyber_newsletter_2026-05-22.pdf


## Task Automation
- **Task name**: Daily CyberSecurity Newsletter
- **Purpose**: Generates a daily newsletter summary highlighting key cyber security news/updates, then stores the output in this repository so it can be easily accessed and tracked over time.
- **Frequency**: **Daily** (every day).

### Data-only generation (TRAE)
TRAE generates **ONLY**:
- `Report/<YEAR>/<ISSUE_DATE>/source/*.json` (meta, highlights, 3 sections)
- `Report/<YEAR>/<ISSUE_DATE>/email_subject_ISSUE_DATE.txt`
- `Report/<YEAR>/<ISSUE_DATE>/email_body_ISSUE_DATE.txt`

Then GitHub Actions materializes the PDF + poster JPGs from the JSON parts.

**Rerun rules (cost-optimized):**
- Default rerun for the same `ISSUE_DATE` is **NO SEARCH** (script exits if outputs exist).
- To rebuild (and re-fetch RSS), run with `--force-re-run`.

Generator script:
- `python tools/trae_generate_sources.py`


## Repository Contents
You will typically find:
- Daily report/newsletter files (file format and naming convention follow the automation configuration).
- Historical reports to help track trends and serve as references.

## Data Source 
We use the news data source from https://github.com/netsecid/cybersecurity-rss-sources.

## Built with TRAE
This workflow runs using **SOLO automation on TRAE**, then pushes the results to GitHub for archiving and reference.
