# 🔐 Clipboard Data Leakage Prevention Tool

> A cross-platform, real-time clipboard security agent designed to detect, alert, and prevent sensitive data leakage at the endpoint level.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-green?style=flat-square)
![License](https://img.shields.io/badge/License-Educational-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-yellow?style=flat-square)

---

## 📌 Overview

Clipboard-based attacks are an underrepresented but critical class of endpoint threats. Malicious software silently monitors the system clipboard to intercept passwords, cryptocurrency wallet addresses, OTPs, and financial credentials — often without any user awareness.

This project implements a lightweight **Data Loss Prevention (DLP)** agent focused entirely on clipboard security. It runs as a background monitor thread inside a desktop dashboard, continuously watching clipboard state, classifying copied content by risk level, firing OS-native notifications on sensitive detections, and keeping a queryable history database.

**Core attack vectors this tool defends against:**
- **ClipBanker / Clipboard Hijackers** — malware that swaps copied crypto addresses with attacker-controlled ones
- **Credential Harvesting** — passive clipboard sniffing for passwords and tokens
- **Accidental Data Exposure** — users unknowingly pasting sensitive data into untrusted applications

---

## 🎯 Objectives

- Monitor clipboard activity in real-time across Windows, Linux, and macOS
- Detect sensitive data using extensible regex + YARA pattern analysis
- Notify the user instantly when sensitive data is copied
- Keep a full clipboard history with source-application capture
- Provide a functional, demonstrable proof-of-concept for endpoint DLP
- Document real-world attack scenarios and threat model for academic analysis

---

## ⚙️ Features

### Core Features

| Feature | Description |
|---|---|
| 📋 Real-time Clipboard Monitoring | Background poll thread (configurable interval, non-blocking) |
| 🧠 Pattern-Based Detection | Regex engine for 12+ sensitive data types + YARA rules |
| 🚨 Alert Notifications | OS-native notifications (notify-send, win10toast, osascript, plyer) |
| 💾 SQLite History | Full copy history with timestamps, content, and source app |
| 🔍 Source Application Capture | Foreground window / process identification (xdotool, win32gui) |
| 🖥️ Desktop Dashboard | Dark-themed Tkinter GUI: search, preview, pause, export |

### GUI Features

| Feature | Description |
|---|---|
| 🔎 Live Search / Filter | Filter history by content with entry counter |
| 📄 Full-Content Preview | Right-hand pane with sensitive-data summary per entry |
| ⏸ Pause / Resume | Suspend monitoring without quitting |
| ⎘ Copy Entry | Recopy with a "⚠️ Sensitive data copied" warning prefix on flagged content |
| ✕ Delete / ⌫ Clear All | Per-entry delete and full history wipe (with confirmation) |
| ↯ Export CSV | Export history as CSV for thesis reporting |
| 🗔 System Tray | Windows: hides to tray and keeps monitoring; Linux/macOS: ask + minimize fallback |
| ⚠️ Sensitive Highlight | Detected entries marked with a red strip in the list |

### CLI Features (`clipboard-dlp`)

| Command | Description |
|---|---|
| `info` | Show project info message |
| `analyze --text "<string>"` | Analyze text: matches, entropy, risk tier |
| `backup` | Snapshot the history database to `backups/` |
| `show-docs` | List available documentation files |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────┐
│              Clipboard Layer                 │
│   Wayland: wl-paste / wl-copy               │
│   X11:     xclip / xsel                     │
│   Fallback: pyperclip (Win / macOS)         │
│   Hard 2s subprocess timeouts (no blocking) │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          Monitor Thread (monitor.py)        │
│   Poll loop → dedupe → source capture →     │
│   store → detect → notify → UI queue        │
└──────────────┬──────────────┬───────────────┘
               │              │
               ▼              ▼
┌────────────────────────┐  ┌─────────────────────────────┐
│   Detection Engine     │  │   Persistence (db.py)       │
│   detector.py          │  │   SQLite history table      │
│   regex patterns +     │  │   (id, timestamp, content,  │
│   password-like        │  │    source) · daily backups  │
│   heuristic + YARA     │  │   · 0600 perms · backups/   │
│   (optional rules)     │  └─────────────────────────────┘
└──────────────┬────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│          Presentation Layer                 │
│   app.py (Tkinter dashboard) · dialogs.py   │
│   widgets.py (list rows, buttons)           │
│   notifier.py (OS notifications)            │
│   pystray tray icon (lazy, Windows)         │
└─────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Core runtime |
| GUI Framework | `Tkinter` (stdlib) | Dark-themed dashboard, dialogs, widgets |
| CLI | `click` | `clipboard-dlp` command-line interface |
| Clipboard Access | `wl-paste`/`wl-copy`, `xclip`/`xsel`, `pyperclip` | Cross-platform clipboard read/write |
| Pattern Matching | `re` (stdlib) + Shannon entropy | Sensitive data detection |
| YARA Rules | `yara` (optional) | Additional signature-based detection |
| Storage | `sqlite3` (stdlib) | Clipboard history DB + automatic backups |
| Notifications | `notify-send`/`zenity`, `win10toast`, `osascript`, `plyer` | OS-native desktop alerts |
| Process Detection | `xdotool`, `pywin32` + `psutil` | Active application identification |
| System Tray | `pystray` + `pillow` | Background tray icon (lazy-created) |

---

## 🔍 Detection Engine

The detector (`detector.py`) combines three layers:

1. **Regex patterns** — precompiled patterns for common sensitive formats
2. **Password-like heuristic** — bare unlabeled credentials (`_@B4g@mZ$RfyE3N`, `mypassword123`)
3. **YARA rules** (optional) — signature rules in `src/clipboard_dlp/yara/` (private key blocks, Slack/GitHub tokens, Bearer tokens, DB connection strings, .env lines, …)

| Data Type | Pattern Example | Source |
|---|---|---|
| 📧 Email Addresses | `user@domain.com` | regex |
| 🔑 AWS Access Keys | `AKIA...` | regex + YARA |
| 🪪 JWT Tokens | `eyJ...` (anchored on `eyJ`) | regex |
| 🌐 IPv4 Addresses | `192.168.1.1` | regex |
| 🪪 SSN | `123-45-6789` | regex |
| 💳 Credit Card Numbers | Visa / Mastercard / Amex lengths | regex |
| 📱 Phone Numbers | Local + international formats | regex |
| 🔐 Passwords | `password: hunter2`, `pwd is xyz` | regex + YARA |
| 🔑 API Keys / Secrets | `secret = ...`, `api_key: ...` | regex + YARA |
| 🌱 .env Secrets | `DB_PASSWORD=...`, `SECRET_KEY=...` | regex + YARA |
| 🔢 OTP / 2FA Codes | `your verification code is 482913` | regex |
| 🔢 PIN Codes | `PIN: 1234` | regex |
| 🧩 Password-like Strings | `_@B4g@mZ$RfyE3N` (4-char-class heuristic) | heuristic |
| 🧬 YARA signatures | `-----BEGIN RSA PRIVATE KEY-----`, `xoxb-...` | YARA |
| 💰 Crypto Wallet Addresses | BTC `1A1zP1eP...`, ETH `0x...40 hex` | CLI analyzer |

The CLI analyzer (`analyzer.py`) additionally computes **Shannon entropy** and a four-tier risk assignment (LOW → CRITICAL) for ad-hoc analysis:

```
$ clipboard-dlp analyze --text "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
Matches: ['BTC_ADDRESS']
Entropy: 4.59
Risk: CRITICAL
```

---

## 🚨 Notification Behavior

| Risk | Desktop Notification | Content in Notification | History Stored |
|---|---|---|---|
| Any detection | ✅ Yes (throttled, 2s cooldown) | ❌ Never (labels only) | ✅ |
| No detection | ❌ Silent | — | ✅ |

Notifications are duration-capped at 5s (enforced via D-Bus `CloseNotification` on Linux) and never contain the raw sensitive value — only type labels — since OS notifications can appear on lock screens.

---

## 💻 Platform Support

| OS | Status | Notes |
|---|---|---|
| Windows 10/11 | ✅ Supported | pyperclip + win10toast + pywin32 source capture, tray icon |
| Ubuntu / Debian Linux | ✅ Supported | `wl-paste` (Wayland) / `xclip` / `xsel`; `notify-send`; optional `xdotool` for source capture |
| macOS | ✅ Supported | pyperclip + osascript notifications |

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Shr1H4x/clipboard-security-tool.git
cd clipboard-security-tool
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
# or, for console scripts:
pip install -e .
```

### 3. Linux Clipboard Backend (Required on Linux)

```bash
# Wayland:
sudo apt install wl-clipboard
# X11:
sudo apt install xclip xsel
# optional — source application capture:
sudo apt install xdotool
```

### 4. Verify Installation

```bash
PYTHONPATH=src python3 -m clipboard_dlp.cli info
```

---

## ▶️ Usage

### Desktop Dashboard (GUI)

```bash
PYTHONPATH=src python3 -m clipboard_dlp.app
```

or after `pip install -e .`:

```bash
clipboard-dlp-gui
```

### Command-Line Interface

```bash
clipboard-dlp info
clipboard-dlp analyze --text "hello world"
clipboard-dlp backup
clipboard-dlp show-docs
```

---

## 🗂️ Project Structure

```
CLIPBOARD-DLP/
│
├── requirements.txt
├── scripts/
│   └── build_windows.bat      # PyInstaller build for Windows
│
├── src/clipboard_dlp/
│   ├── __init__.py            # Package version
│   ├── app.py                 # Tkinter dashboard (entry: clipboard-dlp-gui)
│   ├── cli.py                 # click CLI (entry: clipboard-dlp)
│   ├── monitor.py             # Background poll thread + source capture
│   ├── clipboard.py           # wl-paste/xclip/pyperclip with hard timeouts
│   ├── detector.py            # Regex + heuristic + YARA detection
│   ├── analyzer.py            # CLI analyzer: patterns + entropy + risk tier
│   ├── db.py                  # SQLite history + daily backups
│   ├── notifier.py            # Cross-platform notifications
│   ├── constants.py           # Paths, colors, fonts
│   ├── widgets.py             # Buttons, entries, history rows
│   ├── dialogs.py             # Notify / confirm / export dialogs
│   └── yara/                  # Optional YARA rule sets
│       ├── credentials.yar
│       ├── passwords.yar
│       └── secrets.yar
│
├── tests/                     # pytest suite (7 modules)
│   ├── test_analyzer.py       ├── test_db.py
│   ├── test_cli.py            ├── test_monitor.py
│   ├── test_detector.py       ├── test_notifier.py
│   └── test_ui.py
│
└── *.md                       # README, how-to-run, architecture docs
```

---

## 🧪 Demo Scenarios

### Scenario 1: Cryptocurrency Address Swap Attack

```
1. User copies their BTC wallet address to send funds
2. ClipBanker malware silently replaces it with attacker address
3. ❌ Without tool: User pastes attacker address → funds lost
4. ✅ With tool: Tool detects the crypto address, notifies the user,
   and re-copying from history prepends a "Sensitive data copied" warning
```

### Scenario 2: Accidental Password Copy

```
1. Developer copies database password from a config file
2. Switches window, pastes into Slack chat by mistake
3. ❌ Without tool: Credential exposed in chat logs
4. ✅ With tool: Monitor fires a desktop notification ("Detected: Password,
   .env secret..."), the entry is flagged in history, and re-copying
   prepends a warning header so the paste destination is visibly warned
```

### Scenario 3: API Key Leakage

```
1. User copies an AWS access key (AKIA...) from a terminal
2. Tool detects the AKIA pattern (regex + YARA) → notification fired
3. Entry stored with source application (e.g. "firefox - AWS Console")
4. Notification shows only the label "AWS access key" — never the key itself
```

---

## 🗄️ Data Storage

- **Database:** SQLite `clipboard_history.db` stored in the user data directory
  (`~/.local/share/clipboard_dlp/` on Linux, `%LOCALAPPDATA%\clipboard_dlp\` on Windows, `~/Library/Application Support/clipboard_dlp/` on macOS)
- **Schema:** `history(id, timestamp, content, source)` — source is the capturing application when available
- **Protection:** file permissions restricted to owner (0600), automatic daily backup to `backups/` (10 snapshots kept)
- **Isolation:** set `CLIPBOARD_DLP_DB=/path/to/db` to use a custom database location (useful for tests)
- **Recovery:** `Clear All` and `delete` operations snapshot the DB first, so accidental wipes are recoverable

---

## 🧪 Testing

```bash
PYTHONPATH=src python3 -m pytest tests/
# or
./tests/run_tests.sh
```

---

## ⚠️ Known Limitations

- Regex-based detection produces false positives on high-entropy random strings
- Cannot inspect clipboard content from elevated/privileged processes on some OS configurations
- Polling-based monitoring (no OS clipboard hook on Linux; `WM_CLIPBOARDUPDATE` hook is a future improvement)
- YARA detection is optional and requires the `yara` package
- Linux clipboard access depends on `wl-paste`/`xclip`/`xsel`; source capture needs `xdotool` (X11)

---

## 🔬 Threat Model

This tool is designed against the following attacker profile:

- **Attacker position:** Unprivileged malware running in user context on the target machine
- **Attack goal:** Silent clipboard exfiltration or address substitution
- **Known malware families:** ClipBanker, Trojan.CliptoShuffler, ComboJack, Evrial
- **Out of scope:** Kernel-level keyloggers, hypervisor attacks, hardware implants

---

## 📚 Future Improvements

- ML-based content classification to reduce false positives
- Integration with enterprise DLP platforms (Symantec, Microsoft Purview)
- Behavioral analysis: detect clipboard polling by third-party processes
- OS clipboard hooks (Windows `WM_CLIPBOARDUPDATE`, Linux `clipnotify`) to replace polling
- Encrypted clipboard vault for secure temporary storage
- Auto-clear of sensitive clipboard content after configurable delay

---

## 🎓 Academic Context

Developed as a Bachelor's thesis project in **Cybersecurity and Ethical Hacking**.

**Research focus:** Endpoint-level data loss prevention with emphasis on clipboard attack vectors, including real-world malware analysis (ClipBanker family) and defensive tool design.

**Thesis structure alignment:**
- Chapter 3 — Threat modeling and attack surface analysis
- Chapter 4 — System design and detection engine architecture
- Chapter 5 — Implementation, testing, and demo scenarios
- Chapter 6 — Evaluation, limitations, and future work

---

## 📄 License

This project is developed for educational and authorized security research purposes only. Do not deploy in production environments without proper security review.

---

## 👨‍💻 Author

**Shr1H4x**
Bachelor in Cybersecurity & Ethical Hacking

---

## ⭐ Acknowledgements

- Real-world clipboard hijacking malware analysis (ClipBanker, Evrial, ComboJack)
- Python open-source community: `click`, `pyperclip`, `pystray`, `plyer`, `yara-python`
- OWASP Data Leakage Prevention guidelines
