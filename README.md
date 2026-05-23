# Cyber News Daily Updates

This repository stores **daily cybersecurity newsletters** (English) generated from an **RSS allowlist** and published on a regular basis.

## Support Me by Ko-fi
![Ko-fi](https://storage.ko-fi.com/cdn/logomarkLogo.png) https://ko-fi.com/mirfansulaiman

> Note: The section below is **auto-updated by GitHub Actions** after PDF + poster images are generated.

<!-- AUTO-GENERATED:START -->
## Today Updates

Waiting for the first successful artifact generation run.
<!-- AUTO-GENERATED:END -->

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
