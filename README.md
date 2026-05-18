# Cyber News Daily Updates

This repository is used to store **daily reports** related to cyber security news and updates, published on a regular basis.

## Today Updates: [Vol. 001 | 2026-05-18 07:00 WIB]

Today's highlights are led by exploit-ready vulnerabilities: DirtyDecrypt (DirtyCBC) Linux kernel page-cache write flaw now has a public root escalation PoC and NGINX Rift (CVE-2026-42945) exploitation begins days after PoC disclosure. Treat newly published PoCs and early exploitation signals as immediate patch/mitigation triggers for internet-facing and fleet-wide infrastructure.

Endpoint posture is also under pressure: MiniPlasma Windows privilege escalation zero-day PoC claims SYSTEM on fully patched Windows 11. Public privilege-escalation PoCs can rapidly turn initial access into full SYSTEM/root control, so monitoring and least-privilege hardening remain critical.

Identity and edge access risks remain elevated: Tycoon2FA phishing kit adds OAuth device-code flow to hijack Microsoft 365 accounts, plus [+24h Old] Cisco Catalyst SD-WAN Controller auth bypass (CVE-2026-20182) actively exploited in zero-day attacks. Prioritize OAuth/conditional-access hardening and minimize management-plane exposure on network control components.

![Cover Poster](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-18/poster_2026-05-18_issue-001.jpg)

### TOP 10 - VULNERABILITIES

![Top 10 Vulnerabilities](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-18/poster_vulnerabilities_2026-05-18_issue-001.jpg)

### TOP 10 - THREAT INTEL

![Top 10 Threat Intel](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-18/poster_threat-intel_2026-05-18_issue-001.jpg)

### TOP 10 - DATA BREACH & CYBERCRIME

![Top 10 Data Breach & Cybercrime](https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-18/poster_data-breach_2026-05-18_issue-001.jpg)

### PDF Report

Download: https://raw.githubusercontent.com/mirfansulaiman/cyber_news_daily_updates/main/Report/2026/2026-05-18/cyber_newsletter_2026-05-18.pdf


## Task Automation
- **Task name**: Daily CyberSecurity Newsletter
- **Purpose**: Generates a daily newsletter summary highlighting key cyber security news/updates, then stores the output in this repository so it can be easily accessed and tracked over time.
- **Frequency**: **Daily** (every day).

## Repository Contents
You will typically find:
- Daily report/newsletter files (file format and naming convention follow the automation configuration).
- Historical reports to help track trends and serve as references.

## Built with TRAE
This workflow runs using **SOLO automation on TRAE**, then pushes the results to GitHub for archiving and reference.
