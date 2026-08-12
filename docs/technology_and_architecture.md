# Clipboard DLP Tool — Technology Stack & Architecture

> Chat session summary — Clipboard Data Leakage Prevention Tool project

---

## Project Overview

A cross-platform, real-time clipboard security agent designed to detect, alert, and prevent sensitive data leakage at the endpoint level. Developed as a Bachelor's thesis project in **Cybersecurity and Ethical Hacking**.

**Core attack vectors defended:**
- ClipBanker / Clipboard Hijackers
- Credential Harvesting
- Accidental Data Exposure

---

## Technology Stack by Layer

### Core Runtime
| Component | Technology |
|---|---|
| Language | Python 3.10+ |

### Clipboard Access
| Component | Technology |
|---|---|
| Cross-platform R/W | `pyperclip` |
| Windows hook-based | `pywin32` (`WM_CLIPBOARDUPDATE`) |

> Switching from polling to Windows clipboard hooks via `pywin32` is the most impactful upgrade — catches clipboard changes in real time without CPU overhead.

---

## System Architecture

See the original project README for an annotated architecture diagram and component breakdown.

---

*Generated from project planning session — Clipboard DLP Tool (Bachelor's Thesis, Cybersecurity & Ethical Hacking)*
