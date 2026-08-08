# Clipboard DLP Tool — Efficient Storage Strategy

> No database. No RAM persistence. Inspect, classify, discard.

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

## The Problem for a DLP Monitor

A DLP tool is a **monitor**, not an application holding data. To inspect clipboard content you inevitably need to read it once — that read lands in your process memory momentarily. You **cannot avoid that single read**.

What you *can* control is **what happens after that read**.

---

## The Pipeline — Inspect, Classify, Discard

```
Clipboard Event Fires
        ↓
Read content into LOCAL variable (temporary, in stack memory)
        ↓
Run regex + entropy check on it (microseconds)
        ↓
Extract ONLY metadata (type, risk level)
        ↓
del content  ←── explicitly destroy the actual data
        ↓
Log ONLY metadata → .log file (append-only, one line)
        ↓
Done. Nothing stored anywhere.
```

---

## Why Stack Memory Specifically

When you assign a variable inside a function, Python puts it on the **call stack** — not heap, not persistent memory. The moment the function returns or you call `del`, it's gone. No garbage collector delay, no lingering reference.

```python
def on_clipboard_change():
    content = clipboard.read()      # stack variable, lives here only
    result = analyze(content)       # analyze in place
    del content                     # explicitly killed immediately
    log_metadata(result)            # only metadata survives
    # function returns → stack frame destroyed → zero trace
```

**Never pass `content` anywhere outside `on_clipboard_change()`.**
No global variables, no class attributes, no queues carrying the raw text.
Only `result` (the metadata object) leaves the function — never `content`.

---

## What Each Part Uses

| Step | Method | Storage Cost |
|---|---|---|
| Read clipboard | Stack variable | ~bytes, microseconds |
| Regex match | `re` runs on the variable | Zero extra allocation |
| Entropy check | One float calculation | Zero extra allocation |
| `del content` | Stack frame cleared | Back to zero |
| Log metadata | One appended line in `.log` | ~80 bytes per event |
| Dashboard feed | `deque(maxlen=100)` metadata only | ~8KB max, no content |

---

## What You Log vs What You Discard

| Data | Store it? | Why |
|---|---|---|
| Actual clipboard text | ❌ Never | Privacy, security |
| Data type detected | ✅ Yes | `BTC_ADDRESS`, `API_KEY` |
| Risk level | ✅ Yes | `CRITICAL`, `HIGH` |
| Timestamp | ✅ Yes | Audit trail |
| Source application | ✅ Yes | `chrome.exe` |
| Action taken | ✅ Yes | `CLEARED`, `ALERTED` |

Your log entry becomes:
```
[14:32:11] CRITICAL | BTC_ADDRESS | CLEARED | chrome.exe
```
— completely useful for a thesis, zero sensitive data stored.

---

## Bottom Line

There is **no storage mechanism more efficient than no storage**. Wayland proved that — the answer isn't a better database or RAM structure, it's designing the pipeline so the sensitive data is **read → analyzed → discarded** in a single pass, and only metadata survives. That's the professional DLP approach.

---

*Generated from project planning session — Clipboard DLP Tool (Bachelor's Thesis, Cybersecurity & Ethical Hacking)*
