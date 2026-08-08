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

### Detection & Analysis Engine
| Component | Technology |
|---|---|
| Regex matching | `re` (stdlib) |
| Entropy detection | Shannon entropy (custom function, no extra lib) |
| Future ML classifier | `scikit-learn` |

---

### UI / UX & User Interface

Two options depending on project goals:

#### Option A — Desktop GUI (Recommended for thesis)
| Component | Technology |
|---|---|
| GUI framework | `PyQt6` |
| Live charts / dashboard | `pyqtgraph` |
| Styling | QDarkStyleSheet / custom QSS |
| Layout design tool | Qt Designer (exports `.ui` files) |

#### Option B — Web-based Dashboard (More modern)
| Component | Technology |
|---|---|
| Backend | `FastAPI` or `Flask` |
| Frontend | `React` + `Tailwind CSS` + `shadcn/ui` |
| Charts | `Chart.js` or `Recharts` |
| Real-time events | `WebSockets` (`websockets` lib or `Flask-SocketIO`) |

> Option A (PyQt6) is recommended for a thesis — cleaner to demo and distributable as a standalone `.exe`.

---

### Notifications & Alerts
| Component | Technology |
|---|---|
| OS-native toasts | `plyer` |
| Rich Windows 10/11 toasts | `winotify` |
| Alert sound (Critical) | `pygame.mixer` / `winsound` (Windows only) |

---

### System Tray
| Component | Technology |
|---|---|
| Tray agent | `pystray` |
| Dynamic tray icon (threat color) | `Pillow (PIL)` |

---

### Process Detection
| Component | Technology |
|---|---|
| Process enumeration | `psutil` |
| Foreground window (Windows) | `pywin32` (`win32gui`, `win32process`) |

---

### Logging & Storage
| Component | Technology |
|---|---|
| Runtime logs | `logging` (stdlib) |
| Structured event storage | `sqlite3` (stdlib) |
| Report export (CSV/JSON) | `pandas` |

> Using SQLite instead of flat log files is a major upgrade — enables querying, filtering, and clean report export for the thesis appendix.

---

### Configuration
| Component | Technology |
|---|---|
| Config file format | `PyYAML` (`config.yaml`) |
| Config validation | `pydantic` v2 |

---

### Clipboard Snapshot Diffing
| Component | Technology |
|---|---|
| Hash comparison | `hashlib` (stdlib) — SHA-256 |

---

### Packaging & Distribution
| Component | Technology |
|---|---|
| Binary bundler | `PyInstaller` (single `.exe` or Linux binary) |
| Windows installer | `Inno Setup` or `NSIS` |

---

### Testing
| Component | Technology |
|---|---|
| Test framework | `pytest` |
| Mocking clipboard state | `pytest-mock` |
| Test coverage reports | `coverage.py` |

---

## Full Technology Summary Table

| Layer | Technology |
|---|---|
| Core Runtime | Python 3.10+ |
| Clipboard Monitoring | `pyperclip` + `pywin32` (Windows hook) |
| Detection Engine | `re` + Shannon entropy function |
| Desktop GUI | `PyQt6` + `pyqtgraph` |
| OR Web Dashboard | `FastAPI` + `React` + `Tailwind` + `Socket.IO` |
| Notifications | `plyer` + `winotify` (Win) |
| Alert Sound | `pygame.mixer` / `winsound` |
| System Tray | `pystray` + `Pillow` |
| Process Detection | `psutil` + `pywin32` |
| Logging | `logging` + `sqlite3` |
| Report Export | `pandas` |
| Config Validation | `PyYAML` + `pydantic` |
| Packaging | `PyInstaller` + Inno Setup |
| Testing | `pytest` + `pytest-mock` + `coverage.py` |

---

## System Architecture

### Layer Breakdown (Top → Bottom)

```
┌─────────────────────────────────────────────────────────────────┐
│                        OS CLIPBOARD LAYER                       │
│   Windows: pywin32 WM_CLIPBOARDUPDATE hook                      │
│   Linux: xclip / xsel · macOS: pbpaste                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CORE ENGINE                             │
│                                                                 │
│  monitor.py ──► analyzer.py ──► classifier.py                  │
│  (hook loop)    (regex +         (Low / Med /                   │
│                  entropy)         High / Crit)                  │
│                      │                                          │
│               regex_patterns.py                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RESPONSE LAYER                            │
│              responder.py — dispatches by risk level            │
│                                                                 │
│   [Alert]     [Auto-clear]     [Sound]      [Log Event]        │
│   plyer +     pyperclip        pygame       logging +           │
│   winotify    .copy("")        .mixer       sqlite3             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│                                                                 │
│  [System Tray]   [Dashboard GUI]   [Alert Popups]  [Proc Det]  │
│  pystray +       PyQt6 +           PyQt6           psutil +    │
│  Pillow          pyqtgraph         QMessageBox     win32gui    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA & CONFIG LAYER                         │
│                                                                 │
│  [SQLite DB]  [Log File]  [config.yaml]    [Report Export]     │
│  sqlite3      logging     PyYAML +         pandas              │
│  (stdlib)     stdlib      pydantic         CSV / JSON          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        TESTING LAYER                            │
│   pytest + pytest-mock       coverage.py       main.py --test  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BUILD / PACKAGE                            │
│   PyInstaller (.exe / binary)   Inno Setup   requirements.txt  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Architecture Notes

**OS Layer** hooks into the system at the lowest available level. On Windows, `pywin32`'s `WM_CLIPBOARDUPDATE` message replaces polling — far more efficient. On Linux it falls back to `xclip`/`xsel`.

**Core Engine** is a pure data pipeline with no side effects. `monitor.py` captures the clipboard event → `analyzer.py` runs text through `regex_patterns.py` + Shannon entropy check → `classifier.py` assigns the risk tier.

**Response Layer** fans out to four actions in parallel based on risk level. The log event always fires regardless of risk level.

**Presentation Layer** consumes events from the responder — the dashboard and tray are display consumers, not part of the core pipeline. Process detection feeds into the dashboard to show which app triggered each event.

**Data & Config Layer** holds all persistent state. SQLite is the primary store, the flat log file is the human-readable audit trail, `config.yaml` + pydantic validate rules at startup, and `pandas` handles report export.

**Config feed** — the dashed connection from `config.yaml` back up to the core engine means detection thresholds and patterns are runtime-configurable. Change the YAML, restart, get different behavior — no code edits needed.

---

## Detection Engine — Pattern Coverage

| Data Type | Pattern | Default Risk |
|---|---|---|
| BTC Wallet Address | `1A1zP1eP5QGefi2...` | Critical |
| ETH Wallet Address | `0x742d35Cc6634...` | Critical |
| Password-like Strings | High entropy + special chars | High |
| Credit Card Numbers | `4111 1111 1111 1111` | High |
| API Keys / Tokens | `sk-`, `ghp_`, `AKIA...` | High |
| OTP / 2FA Codes | 4–8 digit standalone | Medium |
| Email Addresses | `user@domain.com` | Medium |
| Phone Numbers | Local + international | Medium |
| Private IPs / Internal URLs | `192.168.x.x`, `10.x.x.x` | Low |
| Generic Sensitive Keywords | `password`, `secret`, `token` | Low |

---

## Response Matrix

| Risk Level | Alert | Auto-Clear | Log |
|---|---|---|---|
| Low | Silent log only | No | Yes |
| Medium | Toast notification | No | Yes |
| High | Alert popup | Yes (5s delay) | Yes |
| Critical | Alert + sound | Yes (immediate) | Yes |

---

## Project File Structure

```
clipboard-security-tool/
│
├── main.py                  # Entry point
├── requirements.txt
├── config.yaml              # Detection rules and thresholds
│
├── core/
│   ├── monitor.py           # Clipboard polling / hook loop
│   ├── analyzer.py          # Pattern matching and classification
│   ├── classifier.py        # Risk level assignment logic
│   └── responder.py         # Alert, clear, and log actions
│
├── patterns/
│   └── regex_patterns.py    # All detection patterns (extensible)
│
├── gui/
│   ├── dashboard.py         # Real-time event dashboard (PyQt6)
│   ├── tray.py              # System tray agent (pystray)
│   └── alerts.py            # Alert popup windows (PyQt6)
│
├── logs/
│   └── clipboard_events.log # Runtime log output
│   └── clipboard_events.db  # SQLite event database
│
└── tests/
    ├── test_analyzer.py
    └── test_classifier.py
```

---

*Generated from project planning session — Clipboard DLP Tool (Bachelor's Thesis, Cybersecurity & Ethical Hacking)*
