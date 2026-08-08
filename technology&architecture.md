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
| Package layout | `src/clipboard_dlp/` (src-layout, pip-installable) |
| CLI framework | `click` |

### Clipboard Access (`clipboard.py`)
| Component | Technology |
|---|---|
| Wayland | `wl-paste` / `wl-copy` via `subprocess` |
| X11 | `xclip` / `xsel` via `subprocess` |
| Fallback (Win / macOS) | `pyperclip` |
| Safety | Hard 2s timeouts on every subprocess call — never blocks the monitor thread |

> Linux clipboard tools can block indefinitely (wl-paste waits on the clipboard owner, wl-copy daemonizes and keeps pipes open). Wrapping them in `subprocess.run(timeout=2)` is essential so a stuck clipboard never stalls detection.

### Monitor Thread (`monitor.py`)
| Component | Technology |
|---|---|
| Polling loop | `threading.Thread` + `time.sleep` (0.6s default) |
| Deduplication | in-memory last-value cache + DB last-entry check |
| Source capture | `xdotool` (X11) · `pywin32` + `psutil` (Windows) · regex heuristics (browser/html/email) |
| Notification throttle | 2s cooldown lock |
| UI bridge | `queue.Queue` → Tkinter `after()` polling |

### Detection & Analysis Engine
| Component | Technology |
|---|---|
| Regex patterns (`detector.py`) | `re` (stdlib), 12+ precompiled patterns |
| Password-like heuristic | custom 4-character-class heuristic (upper + lower + digit + symbol, or credential keyword + digit) |
| YARA rules | `yara-python` (optional), rules in `src/clipboard_dlp/yara/` |
| CLI entropy check (`analyzer.py`) | Shannon entropy (custom function, no extra lib) |
| CLI risk tiers | LOW → MEDIUM → HIGH → CRITICAL |

> Detection is layered: cheap regex first, heuristic for bare unlabeled credentials, then optional YARA signatures for private key blocks, Slack/GitHub tokens, Bearer tokens, DB connection strings, and .env credential lines.

### UI / UX & User Interface
| Component | Technology |
|---|---|
| GUI framework | `Tkinter` (stdlib, no external GUI deps) |
| Custom widgets | `widgets.py` (flat buttons, entries, history rows) |
| Dialogs | `dialogs.py` (notify / confirm / export, draggable) |
| Styling | custom dark palette in `constants.py` (GitHub-dark inspired) |
| Layout | `PanedWindow` for resizable list + preview panes |

> Tkinter keeps the app dependency-light and cross-platform. The dashboard shows a live history list with search/filter, a full-content preview pane with a sensitive-data summary, pause/resume, copy, delete, clear-all, and CSV export.

### Notifications & Alerts (`notifier.py`)
| Component | Technology |
|---|---|
| Linux | `notify-send --print-id` (+ D-Bus `CloseNotification`) · fallback `zenity` |
| Windows | `win10toast` |
| macOS | `osascript` (display notification) |
| Last resort | `plyer` |

> Notifications are capped at 5 seconds (enforced via D-Bus on Linux, since GNOME/KDE often ignore the `-t` timeout) and **never include the raw sensitive value** — only type labels — because notifications can appear on lock screens.

### System Tray
| Component | Technology |
|---|---|
| Tray agent | `pystray` (lazy-created on window close) |
| Tray icon | `Pillow (PIL)` — programmatically drawn |

> Windows hides to tray and keeps monitoring. Linux/macOS asks first and falls back to taskbar minimize because tray hosting is unreliable under Wayland/GNOME.

### Storage (`db.py`)
| Component | Technology |
|---|---|
| History DB | `sqlite3` (stdlib) — `history(id, timestamp, content, source)` |
| Auto-backup | daily snapshot to `backups/` (10 most recent kept) |
| Permissions | DB file chmod `0600` on POSIX |
| Isolation | `CLIPBOARD_DLP_DB` env var overrides DB path |
| Concurrency | per-connection `threading.Lock` |

> SQLite is the single source of truth: full content is stored (required by the history UI), with owner-only permissions, automatic daily backups, and snapshot-before-clear safety so accidental wipes are recoverable.

### Configuration & Packaging
| Component | Technology |
|---|---|
| Dependencies | `requirements.txt` (click, pyperclip, pystray, psutil, pydantic, PyYAML, pytest, pillow, platformdirs, plyer, pywin32 on Windows) |
| Console scripts | `clipboard-dlp` (CLI) · `clipboard-dlp-gui` (GUI) |
| Windows build | `scripts/build_windows.bat` → PyInstaller (`packaging\ClipboardDLP.spec`) |

### Testing
| Component | Technology |
|---|---|
| Test framework | `pytest` |
| Test modules | `test_analyzer`, `test_cli`, `test_db`, `test_detector`, `test_monitor`, `test_notifier`, `test_ui` |
| Runner | `tests/run_tests.sh` |

---

## Full Technology Summary Table

| Layer | Technology |
|---|---|
| Core Runtime | Python 3.10+ (src-layout package) |
| Clipboard Monitoring | `wl-paste`/`wl-copy`, `xclip`/`xsel`, `pyperclip` fallback |
| Monitor Thread | stdlib `threading` + `queue` |
| Detection Engine | `re` + custom heuristic + optional `yara-python` |
| CLI | `click` (`analyze`, `backup`, `info`, `show-docs`) |
| Desktop GUI | `Tkinter` (stdlib) + custom widgets |
| Notifications | `notify-send`/`zenity`, `win10toast`, `osascript`, `plyer` |
| System Tray | `pystray` + `Pillow` |
| Process Detection | `xdotool`, `pywin32` + `psutil` |
| Storage | `sqlite3` + daily backups (10 kept, chmod 0600) |
| Packaging | `pip install -e .` + PyInstaller (`build_windows.bat`) |
| Testing | `pytest` (7 modules) |

---

## System Architecture

### Layer Breakdown (Top → Bottom)

```
┌─────────────────────────────────────────────────────────────────┐
│                        OS CLIPBOARD LAYER                       │
│   Wayland: wl-paste / wl-copy  X11: xclip / xsel               │
│   Fallback: pyperclip (Windows / macOS)                        │
│   subprocess timeouts (2s) — never blocks                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          MONITOR THREAD                         │
│   monitor.py — poll loop (0.6s)                                 │
│   dedupe → source capture (xdotool / win32)                     │
│   db.add() → detect_sensitive() → notify() → q.put()           │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│        DETECTION ENGINE         │  │       PERSISTENCE           │
│   detector.py                   │  │   db.py — SQLite            │
│   regex patterns (12+)          │  │   history(id, timestamp,    │
│   password-like heuristic       │  │   content, source)          │
│   YARA rules (optional)         │  │   daily backups (10)        │
│   analyzer.py (CLI): entropy +  │  │   chmod 0600 · env override │
│   risk tier                     │  └─────────────────────────────┘
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│                                                                 │
│  [Dashboard]      [Dialogs]      [Notifications]  [Tray]        │
│  app.py (Tk)      dialogs.py     notifier.py      pystray +     │
│  widgets.py       (confirm/      notify-send,     Pillow        │
│  search, preview,  export)       win10toast,      (lazy, Win)   │
│  pause, export                   osascript, plyer               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CLI & BUILD LAYER                        │
│   cli.py (click): info · analyze --text · backup · show-docs   │
│   console scripts: clipboard-dlp, clipboard-dlp-gui             │
│   build_windows.bat → PyInstaller .exe                          │
└─────────────────────────────────────────────────────────────────┘
```

---

### Architecture Notes

**OS Clipboard Layer** never blocks: every external tool call (`wl-paste`, `xclip`, …) runs under a hard subprocess timeout. `pyperclip` is only a fallback where no native tool exists (Windows/macOS).

**Monitor Thread** is the single writer. Each poll reads the clipboard, strips the app's own "Sensitive data copied" prefix, dedupes against the last seen value and the DB's latest entry, captures the source application (throttled cache), stores the entry, runs detection, fires a throttled notification, and pushes `(rid, text, detections)` onto a queue consumed by the GUI via `root.after()`.

**Detection Engine** is layered for accuracy: precompiled regex for common formats → a conservative password-like heuristic that skips non-credential mixed-case tokens (`iPhone15ProMax`, `Christmas2024`) → optional YARA rules. The CLI analyzer (`analyzer.py`) offers a simpler pattern set plus Shannon entropy and a four-tier risk label.

**Persistence** stores full content in SQLite (the history UI requires it) with strong defaults: owner-only file permissions, automatic daily snapshots in `backups/`, and a backup-before-clear guarantee. The `CLIPBOARD_DLP_DB` env var isolates test/debug instances.

**Presentation Layer** consumes events from the monitor — the dashboard, dialogs, and tray are display consumers, not part of the core pipeline. Sensitive detections are highlighted with a red strip and summarized in the preview pane; notifications only ever carry type labels, never raw content.

**CLI & Build Layer** exposes the same detection/storage machinery headlessly (`analyze`, `backup`, `info`, `show-docs`) and packages the GUI as a Windows executable via PyInstaller.

---

## Detection Engine — Pattern Coverage

### Regex patterns (`detector.py`)

| Data Type | Pattern Example | Label |
|---|---|---|
| Email address | `user@domain.com` | Email address |
| AWS access key | `AKIA...` (16 chars) | AWS access key |
| JWT | `eyJ...` (3 base64url segments, `eyJ`-anchored) | JWT |
| IPv4 | `192.168.1.1` | IP address |
| SSN | `123-45-6789` | SSN |
| Credit card | Visa / Mastercard / Amex lengths | Credit card |
| Phone number | `+91 98765 43210` | Phone number |
| Password | `password: hunter2` · `the password is xyz` | Password |
| API key/secret | `api_key: sk-...` | API key/secret |
| .env secret | `DB_PASSWORD=...` · `SECRET_KEY=...` | Environment secret |
| OTP | `your verification code is 482913` | OTP |
| PIN | `PIN: 1234` · `pin is 987654` | PIN code |

### Heuristic

| Data Type | Description |
|---|---|
| Password-like string | Bare unlabeled tokens with all 4 character classes (`_@B4g@mZ$RfyE3N`) or credential keywords + digits/symbols (`mypassword123`) |

### YARA rules (`yara/`)

| Rule Set | Detects |
|---|---|
| `credentials.yar` | Private key blocks (PEM/OpenSSH/PGP), Slack tokens/webhooks, Bearer tokens, DB connection strings, basic-auth URLs, GitHub tokens, API keys |
| `passwords.yar` | Password/secret/env assignment lines, SSH credential pairs |
| `secrets.yar` | API keys (AWS/Google/GitHub) |

### CLI analyzer (`analyzer.py`)

| Data Type | Risk |
|---|---|
| BTC address / ETH address | Critical |
| API-key-like token or entropy > 4.5 | High |
| Credit card / OTP / PIN | High |
| Other match | Medium |
| No match | Low |

---

## Notification Matrix

| Detection | Desktop Notification | Raw Value in Notification | Stored |
|---|---|---|---|
| Sensitive | Yes (2s cooldown, 5s duration cap) | Never — labels only | Yes |
| Normal copy | No | — | Yes |

---

## Project File Structure

```
CLIPBOARD-DLP/
│
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── how-to-run.md             # Run instructions
├── technology&architecture.md
├── clipboard_dlp_storage_strategy.md
│
├── scripts/
│   └── build_windows.bat     # PyInstaller build for Windows
│
├── src/clipboard_dlp/
│   ├── __init__.py           # Version
│   ├── app.py                # Tkinter dashboard entry point
│   ├── cli.py                # click CLI entry point
│   ├── monitor.py            # Background poll thread, dedupe, source capture
│   ├── clipboard.py          # wl-paste/xclip/pyperclip with hard timeouts
│   ├── detector.py           # Regex + heuristic + YARA detection
│   ├── analyzer.py           # CLI patterns + entropy + risk tiers
│   ├── db.py                 # SQLite history + daily backups
│   ├── notifier.py           # Cross-platform notifications
│   ├── constants.py          # Paths, colors, fonts
│   ├── widgets.py            # Custom Tk widgets (buttons, rows, entries)
│   ├── dialogs.py            # Notify / confirm / export dialogs
│   └── yara/
│       ├── credentials.yar
│       ├── passwords.yar
│       └── secrets.yar
│
├── tests/
│   ├── test_analyzer.py
│   ├── test_cli.py
│   ├── test_db.py
│   ├── test_detector.py
│   ├── test_monitor.py
│   ├── test_notifier.py
│   ├── test_ui.py
│   └── run_tests.sh
│
└── logs/                     # Legacy runtime logs
```

---

*Generated from project planning session — Clipboard DLP Tool (Bachelor's Thesis, Cybersecurity & Ethical Hacking)*
