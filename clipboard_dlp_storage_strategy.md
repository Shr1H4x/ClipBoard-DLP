# Clipboard DLP Tool — Storage Strategy

> Inspect, classify, store carefully — with privacy-preserving defaults.

---

## How Wayland Clipboard Actually Works

Wayland clipboard **never stores data at all**. It uses a protocol called **"lazy copy"** or **selection protocol**:

```
App A copies text
    ↓
Wayland compositor says "App A owns the clipboard"
    ↓  (nothing is stored anywhere)
App B requests paste
    ↓
Wayland asks App A directly: "give me your clipboard content NOW"
    ↓
App A streams the data directly to App B
    ↓
Data never touched disk or a central buffer
```

The data **lives inside the source application's own memory** — not in any clipboard manager, not in RAM outside the app, not on disk. It only moves when explicitly requested by a paste action.

---

## What This Means for the DLP Monitor

A DLP tool is a **monitor**: to inspect clipboard content it must read it once — that read lands in its process memory momentarily. You **cannot avoid that single read**, and unlike a passive Wayland observer, this tool is also a **history recorder**, so a design decision was required:

**Option A — "Inspect, classify, discard"** (pure metadata, no content stored):
- Pros: minimal data footprint, strongest privacy posture
- Cons: no clipboard history feature, no audit trail of *what* was copied, weaker thesis demo

**Option B — "Inspect, classify, store securely"** (the implemented choice):
- Store full content in a **local SQLite history** so the dashboard can show what was copied
- Mitigate the privacy cost with strict defaults: owner-only permissions, automatic backups, and content never leaving the machine (no network, notifications carry labels only)

The project implements **Option B** — a local, private, recoverable history — because the dashboard, demo scenarios, and thesis appendix all benefit from an audit trail, while the storage hardening below keeps the sensitive-data risk bounded.

---

## The Implemented Pipeline

```
Clipboard Event Fires
        ↓
safe_paste() — wl-paste / xclip / pyperclip with hard 2s timeout
        ↓
strip_sensitive_copy_prefix(text) — ignore the app's own copy prefix
        ↓
Dedupe — skip if identical to last seen or to the DB's latest entry
        ↓
capture source app (xdotool / win32gui+psutil, throttled cache)
        ↓
db.add(text, source)  ──►  SQLite history table (single writer, locked)
        ↓
detect_sensitive(text)  — regex + heuristic (+ optional YARA)
        ↓
notify()  — desktop notification with TYPE LABELS ONLY, never raw text
        ↓
q.put((rid, text, detections))  — UI queue, consumed by the dashboard
        ↓
Done. Read once, analyzed once, stored once, nothing sent anywhere.
```

---

## What Is Stored vs What Never Leaves

| Data | Stored locally? | Sent over network? | In notifications? |
|---|---|---|---|
| Actual clipboard text | ✅ Yes (SQLite, owner-only perms) | ❌ Never | ❌ Never |
| Data type detected | ✅ Yes (re-derived on load) | ❌ | ✅ (label only) |
| Timestamp | ✅ Yes | ❌ | ❌ |
| Source application | ✅ Yes (`source` column) | ❌ | ❌ |
| Raw sensitive values | ✅ Yes (inside the private DB) | ❌ Never | ❌ Never |

The notification body therefore reads like:

```
⚠️ Sensitive data copied
Detected: AWS access key, API key/secret
```

— useful, and zero raw content exposed to the lock screen or notification center.

---

## Storage Hardening (why it's safe to store)

| Measure | Implementation (`db.py`, `constants.py`) |
|---|---|
| Location | User data dir, not the package dir: `~/.local/share/clipboard_dlp/` (Linux), `%LOCALAPPDATA%\clipboard_dlp\` (Windows), `~/Library/Application Support/clipboard_dlp/` (macOS) |
| Permissions | DB file `chmod 0600` on POSIX (owner read/write only) |
| Backups | Automatic daily snapshot to `backups/` next to the DB; the 10 most recent are kept |
| Wipe safety | `clear()`/`delete` snapshot the DB *first* — accidental wipes are recoverable |
| Migration | First launch migrates a packaged legacy DB into the user data dir |
| Isolation | `CLIPBOARD_DLP_DB=/path/to.db` env var pins a custom DB (tests, debugging) |
| Threading | Single connection guarded by a lock — one writer, no corruption |

---

## Why Not Store Less (Option A) — Honest Trade-off

The metadata-only approach (no content anywhere) is strictly more private, and the original Wayland note stands: **"no storage is more efficient than no storage"** — for the *sniffing* threat. But a clipboard DLP tool without a history is a notification-only box: users cannot review what was copied, the dashboard preview cannot work, and the thesis loses its primary demonstration artifact.

The chosen middle ground:

- **Content never leaves the machine** — no upload, no telemetry, no shared logs
- **Content never enters notification paths** — the highest-exposure surface (lock screen / notification center) only ever sees labels
- **Content on disk is private by default** — 0600 permissions in a user-only directory
- **Content is recoverable by design** — daily snapshots protect against accidents

---

## Bottom Line

The pipeline reads the clipboard **once**, analyzes it once, stores it **securely and locally** (SQLite, owner-only permissions, daily backups), and exposes **only metadata** to the outside world (notifications, CSV export fields). Storage is a deliberate, hardened feature — not a leak vector: anything that can be stored locally is also protected by permissions, backups, and an isolation escape hatch.

---

*Generated from project planning session — Clipboard DLP Tool (Bachelor's Thesis, Cybersecurity & Ethical Hacking)*
