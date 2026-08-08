from __future__ import annotations

import os
import csv
import queue
import sys
import datetime
import tkinter as tk
from tkinter import filedialog
from typing import Optional

from .constants import (DB_PATH, BG, BG_PANEL, BORDER, BG_INPUT, BG_DIALOG, FONT_UI, FONT_UI_S,
                        FONT_UI_B, FG, FG2, FG3, FONT_MONO_S, FONT_MONO, FONT_TITLE, BORDER2,
                        BG_ITEM, BG_HOVER, BG_SEL, BG_BTN, BG_BTN_HOV, BG_BTN_SEC, BG_BTN_HOV2,
                        FG_GREEN, FG_YELLOW, FG_ACCENT, BG_ACCENT, BG_STAT, BG_DANGER)
from .db import ClipDB
from .monitor import Monitor
from .widgets import VSBtn, ClipRow
from .detector import detect_sensitive, format_sensitive_copy, summarize_detections
from .dialogs import NotifyDialog, ConfirmDialog, ExportDialog, VSDialog


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clipboard DLP Monitor")
        self.root.configure(bg=BG)
        self.root.geometry("820x640")
        self.root.minsize(640, 460)

        self.db   = ClipDB()
        self.q    = queue.Queue()
        self._rows: list[ClipRow] = []
        self._sel:  Optional[ClipRow] = None
        self._root_scroll_binds_set = False
        self._tray_icon = None  # pystray Icon, lazily created on first close

        self._build()
        self.monitor = Monitor(self.db, self.q)
        self.monitor.start()
        self._poll()
        self._clock()

    def _build(self):
        tbar = tk.Frame(self.root, bg=BG_PANEL, pady=0)
        tbar.pack(fill=tk.X)

        left = tk.Frame(tbar, bg=BG_PANEL, padx=14, pady=10)
        left.pack(side=tk.LEFT)

        tk.Label(left, text="⬡", font=(FONT_UI[0], 14), bg=BG_PANEL,
                 fg=FG_ACCENT).pack(side=tk.LEFT)
        tk.Label(left, text="Clipboard DLP Monitor",
                 font=FONT_TITLE, bg=BG_PANEL, fg=FG).pack(side=tk.LEFT)
        tk.Label(left, text="  —  Security Agent",
                 font=FONT_MONO_S, bg=BG_PANEL, fg=FG3).pack(side=tk.LEFT)

        right = tk.Frame(tbar, bg=BG_PANEL, padx=14)
        right.pack(side=tk.RIGHT, anchor="center")

        self._dot_cv = tk.Canvas(right, width=9, height=9, bg=BG_PANEL,
                                 highlightthickness=0)
        self._dot_cv.pack(side=tk.LEFT, padx=(0, 5))
        self._dot = self._dot_cv.create_oval(1, 1, 8, 8, fill=FG_GREEN, outline="")

        self._stat_txt = tk.Label(right, text="Monitoring",
                                  font=FONT_UI, bg=BG_PANEL, fg=FG_GREEN)
        self._stat_txt.pack(side=tk.LEFT)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        sbar = tk.Frame(self.root, bg=BG, padx=0, pady=0)
        sbar.pack(fill=tk.X)

        search_frm = tk.Frame(sbar, bg=BG_INPUT,
                              highlightthickness=1,
                              highlightbackground=BORDER,
                              highlightcolor=BORDER2)
        search_frm.pack(fill=tk.X)

        tk.Label(search_frm, text=" 🔍 ", font=(FONT_UI[0], 9),
                 bg=BG_INPUT, fg=FG3).pack(side=tk.LEFT)

        self._sv = tk.StringVar()
        self._sv.trace_add("write", lambda *_: self._filter())
        se = tk.Entry(search_frm, textvariable=self._sv,
                      bg=BG_INPUT, fg=FG, insertbackground=FG,
                      relief="flat", font=FONT_UI, bd=0,
                      selectbackground=BG_SEL,
                      highlightthickness=0)
        se.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))

        self._count_lbl = tk.Label(search_frm, text="",
                                   font=FONT_MONO_S, bg=BG_INPUT, fg=FG3)
        self._count_lbl.pack(side=tk.RIGHT, padx=8)

        tb = tk.Frame(self.root, bg=BG_PANEL, padx=12, pady=8)
        tb.pack(fill=tk.X)

        self._pause_btn = VSBtn(tb, "⏸  Pause", cmd=self._toggle_pause, primary=True)
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 6))

        VSBtn(tb, "⎘  Copy", cmd=self._copy).pack(side=tk.LEFT, padx=(0, 6))
        VSBtn(tb, "✕  Delete", cmd=self._delete).pack(side=tk.LEFT, padx=(0, 6))
        VSBtn(tb, "↯  Export", cmd=self._export).pack(side=tk.LEFT, padx=(0, 6))
        VSBtn(tb, "⌫  Clear All", cmd=self._clear, danger=True).pack(side=tk.RIGHT)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        ch = tk.Frame(self.root, bg=BG_PANEL, padx=20, pady=4)
        ch.pack(fill=tk.X)
        tk.Label(ch, text=" TIMESTAMP              LEN    CONTENT PREVIEW",
                 font=FONT_MONO_S, bg=BG_PANEL, fg=FG3).pack(anchor="w")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # Use a PanedWindow so the preview/source pane on the right is resizable
        pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief='raised', bg=BG)
        pane.pack(fill=tk.BOTH, expand=True)

        list_frm = tk.Frame(bg=BG, master=pane, highlightthickness=0)
        pane.add(list_frm, stretch='always')
        # keep references for sash enforcement
        self._main_pane = pane
        self._list_frame = list_frm

        self._canvas = tk.Canvas(list_frm, bg=BG_ITEM, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(list_frm, orient="vertical", command=self._canvas.yview,
                  bg=BG_PANEL, troughcolor=BG, activebackground=BG_HOVER,
                  width=10)
        # hide visible scrollbar (kept for yscrollcommand wiring)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._lf = tk.Frame(self._canvas, bg=BG_ITEM)
        self._cw = self._canvas.create_window((0, 0), window=self._lf, anchor="nw")

        self._lf.bind("<Configure>", lambda _: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._cw, width=e.width))
        self._bind_scrollable(self._canvas, widget_y=self._canvas)
        self._bind_scrollable(self._lf, widget_y=self._canvas)

        pvfrm = tk.Frame(master=pane, bg=BG_PANEL, width=320, highlightthickness=1, highlightbackground=BORDER)
        pane.add(pvfrm, minsize=200)
        pvfrm.pack_propagate(False)
        self._pv_frame = pvfrm

        tk.Label(pvfrm, text="PREVIEW", font=FONT_UI_S, bg=BG_PANEL, fg=FG3, padx=12, pady=8).pack(anchor="w")
        self._sensitive_lbl = tk.Label(
            pvfrm,
            text="",
            font=FONT_MONO_S,
            bg=BG_PANEL,
            fg=FG3,
            padx=12,
            pady=0,
            wraplength=280,
            justify="left"
        )
        self._sensitive_lbl.pack(anchor="w", fill=tk.X)
        tk.Frame(pvfrm, bg=BORDER, height=1).pack(fill=tk.X)

        preview_container = tk.Frame(pvfrm, bg=BG_PANEL)
        preview_container.pack(fill=tk.BOTH, expand=True)

        self._preview = tk.Text(
            preview_container, bg=BG_PANEL, fg=FG, insertbackground=FG,
            font=FONT_MONO_S, relief="flat", bd=0,
            state="disabled", wrap="word",
            selectbackground=BG_SEL,
            padx=10, pady=8,
            highlightthickness=0
        )
        vsb = tk.Scrollbar(preview_container, orient="vertical", command=self._preview.yview,
                   bg=BG_PANEL, troughcolor=BG)
        # hide visible preview scrollbar
        self._preview.configure(yscrollcommand=vsb.set)
        self._preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._bind_scrollable(self._preview, widget_y=self._preview, widget_x=self._preview)
        self._preview_container = preview_container

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        tk.Frame(self.root, bg=BG_ACCENT, height=2).pack(fill=tk.X)

        stbar = tk.Frame(self.root, bg=BG_STAT, padx=12, pady=5)
        stbar.pack(fill=tk.X)

        self._sb_left = tk.Label(stbar, text="", font=FONT_UI_S, bg=BG_STAT, fg=FG3)
        self._sb_left.pack(side=tk.LEFT)

        self._sb_right = tk.Label(stbar, text="", font=FONT_MONO_S, bg=BG_STAT, fg=FG2)
        self._sb_right.pack(side=tk.RIGHT)

        self._reload()
        # Bind sash events to enforce min/max limits after user drags sash
        try:
            self._main_pane.bind("<ButtonRelease-1>", lambda e: self._enforce_pane_limits())
            self._main_pane.bind("<B1-Motion>", lambda e: self._enforce_pane_limits())
        except Exception:
            pass

    def _reload(self):
        for w in self._lf.winfo_children():
            w.destroy()
        self._rows.clear()
        self._sel = None
        entries = self.db.list(10000)
        for i, e in enumerate(entries, start=1):
            # support legacy rows (id,ts,content) and new rows (id,ts,content,source)
            if len(e) == 4:
                rid, ts, content, source = e
            else:
                rid, ts, content = e
                source = None
            row = self._add_row(rid, ts, content, prepend=False)
            # Run detection for existing DB rows so stored sensitive items show alerts
            try:
                detections = detect_sensitive(content)
                row.set_alert(summarize_detections(detections))
                if detections:
                    try:
                        row._strip.config(bg=BG_DANGER)
                    except Exception:
                        pass
            except Exception:
                pass
            # store source on row (optional)
            try:
                row.source = source
            except Exception:
                pass
        children = [w for w in self._lf.winfo_children() if isinstance(w, ClipRow)]
        self._rows = children
        self._update_sb()

    def _add_row(self, rid, ts, content, prepend=False):
        row = ClipRow(self._lf, rid, ts, content,
                  on_select=self._select,
                  on_dbl=lambda r: self._view_full(r))
        if prepend:
            children = self._lf.winfo_children()
            if children:
                row.pack(fill=tk.X, pady=(0, 1), before=children[0])
            else:
                row.pack(fill=tk.X, pady=(0, 1))
            self._rows.insert(0, row)
        else:
            row.pack(fill=tk.X, pady=(0, 1))
            self._rows.append(row)
        return row

    def _filter(self):
        q = self._sv.get().lower().strip()
        visible = 0
        for row in self._rows:
            content = self.db.get(row.rid) or ""
            show    = not q or q in content.lower()
            if show:
                row.pack(fill=tk.X, pady=(0, 1))
                visible += 1
            else:
                row.pack_forget()
        self._count_lbl.config(
            text=f"{visible}/{len(self._rows)}" if q else "")

    def _select(self, row: ClipRow):
        if self._sel:
            self._sel.deselect()
        self._sel = row
        row.select()
        content = self.db.get(row.rid) or ""
        detections = []
        try:
            detections = detect_sensitive(content)
        except Exception:
            detections = []
        sensitive_text = summarize_detections(detections)
        self._preview.config(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("1.0", content)
        try:
            # Ensure preview is scrolled to top after inserting
            self._preview.yview_moveto(0)
        except Exception:
            pass
        self._preview.config(state="disabled")
        try:
            if sensitive_text:
                self._sensitive_lbl.config(text=f"Sensitive: {sensitive_text}", fg=FG_YELLOW)
            else:
                self._sensitive_lbl.config(text="Sensitive: none detected", fg=FG3)
        except Exception:
            pass
        # Update status bar
        try:
            base = f"  ⬡Clipboard DLP  ·  {self.db.count()} entries  ·  {os.path.basename(DB_PATH)}"
            self._sb_left.config(text=base)
        except Exception:
            pass

    def _toggle_pause(self):
        self.monitor.toggle()
        if self.monitor.paused:
            self._pause_btn.retag("▶  Resume", bg=BG_BTN_SEC, hbg=BG_BTN_HOV2)
            self._dot_cv.itemconfig(self._dot, fill=FG_YELLOW)
            self._stat_txt.config(text="Paused", fg=FG_YELLOW)
        else:
            self._pause_btn.retag("⏸  Pause", bg=BG_BTN, hbg=BG_BTN_HOV)
            self._dot_cv.itemconfig(self._dot, fill=FG_GREEN)
            self._stat_txt.config(text="Monitoring", fg=FG_GREEN)

    def _copy(self, row=None):
        r = row or self._sel
        if not r:
            NotifyDialog(self.root, "Nothing Selected",
                         "Select an entry first.", kind="warn").wait()
            return
        content = self.db.get(r.rid)
        if not content: return
        detections = []
        try:
            detections = detect_sensitive(content)
        except Exception:
            pass
        from .clipboard import copy as clipboard_copy
        if not clipboard_copy(format_sensitive_copy(content, detections)):
            NotifyDialog(self.root, "Copy Failed",
                         "No clipboard backend available on this system.",
                         kind="error").wait()
            return
        try:
            self.monitor.mark_seen(content)
        except Exception:
            pass
        self._flash("Copied to clipboard  ✔")

    def _delete(self):
        if not self._sel:
            NotifyDialog(self.root, "Nothing Selected",
                         "Select an entry to delete.", kind="warn").wait()
            return
        dlg = ConfirmDialog(
            self.root,
            title="Delete Entry",
            message="Delete this clipboard entry?\nThis action cannot be undone.",
            confirm_text="Delete",
            danger=True
        )
        if dlg.wait():
            self.db.delete(self._sel.rid)
            self._reload()
            self._clear_preview()

    def _clear(self):
        count = self.db.count()
        if count == 0:
            NotifyDialog(self.root, "Already Empty",
                         "No entries to clear.", kind="info").wait()
            return
        dlg = ConfirmDialog(
            self.root,
            title="Clear All History",
            message=f"Permanently delete all {count} clipboard entries?\nThis cannot be undone.",
            confirm_text="Clear All",
            danger=True,
            width=440, height=180
        )
        if dlg.wait():
            self.db.clear()
            try:
                self.db.reset_sequence()
            except Exception:
                pass
            self._reload()
            self._clear_preview()

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Clipboard History"
        )
        if not path: return
        rows = self.db.list(10000)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "timestamp", "content"])
                for r in rows:
                    w.writerow(r)
            ExportDialog(self.root, len(rows),
                         os.path.basename(path)).wait()
        except Exception as e:
            NotifyDialog(self.root, "Export Failed", str(e), kind="error").wait()

    def _clear_preview(self):
        self._preview.config(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.config(state="disabled")
        try:
            self._sensitive_lbl.config(text="")
        except Exception:
            pass

    def _view_full(self, row: ClipRow):
        content = self.db.get(row.rid) or ""
        dlg = VSDialog(self.root, "Full Entry", width=640, height=420)
        txt = tk.Text(dlg._body, bg=BG_PANEL, fg=FG, insertbackground=FG,
                      font=FONT_MONO_S, relief="flat", bd=0, wrap="word",
                      padx=10, pady=8)
        txt.insert("1.0", content)
        txt.config(state="disabled")
        self._bind_scrollable(txt, widget_y=txt, widget_x=txt)
        txt.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(dlg._body, bg=BG_DIALOG)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        def _copy_full():
            from .clipboard import copy as clipboard_copy
            detections = []
            try:
                detections = detect_sensitive(content)
            except Exception:
                pass
            if not clipboard_copy(format_sensitive_copy(content, detections)):
                NotifyDialog(self.root, "Copy Failed",
                             "No clipboard backend available on this system.",
                             kind="error").wait()
                return
            try:
                self.monitor.mark_seen(content)
            except Exception:
                pass
            dlg.destroy()
            self._flash("Copied full entry to clipboard  ✔")

        VSBtn(btn_row, "  Copy Full  ", cmd=_copy_full, primary=True).pack(side=tk.RIGHT)
        VSBtn(btn_row, "  Close  ", cmd=dlg.destroy).pack(side=tk.RIGHT, padx=(0, 8))
        dlg.wait()

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                # support (rid, text) or (rid, text, detections)
                if isinstance(item, tuple) and len(item) == 3:
                    rid, text, detections = item
                else:
                    rid, text = item
                    detections = []
                ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = self._add_row(rid, ts, text, prepend=True)
                try:
                    # fetch source saved by monitor/db and attach to row
                    row.source = self.db.get_source(rid)
                except Exception:
                    row.source = None
                try:
                    row.set_alert(summarize_detections(detections))
                except Exception:
                    pass
                # mark visual alert if detections present
                try:
                    if detections:
                        try:
                            row._strip.config(bg=BG_DANGER)
                        except Exception:
                            pass
                        self._flash("Sensitive data detected  ⚠", ms=3000)
                except Exception:
                    pass
                self._update_sb()
        except queue.Empty:
            pass
        self.root.after(300, self._poll)

    def _update_sb(self):
        c = self.db.count()
        self._sb_left.config(text=f"  ⬡ Clipboard DLP  ·  {c} entries  ·  {os.path.basename(DB_PATH)}")

    def _flash(self, msg, ms=2500):
        orig = self._sb_left.cget("text")
        self._sb_left.config(text=f"  {msg}")
        self.root.after(ms, lambda: self._sb_left.config(text=orig))

    def _clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self._sb_right.config(text=f"{now}  ")
        self.root.after(1000, self._clock)

    def _bind_scrollable(self, widget, widget_y=None, widget_x=None):
        """Bind cross-platform scrolling for a widget.

        Widget-level bindings return "break" so Tk class bindings (e.g. the
        Text widget) and the root-level bind_all handlers never scroll the
        same widget twice. The root handlers resolve the scroll target from
        the widget under the pointer on every event, so scrolling can never
        "stall" because of stale Enter/Leave state.

        widget_y: target for vertical scrolling (yview_scroll).
        widget_x: target for horizontal scrolling (xview_scroll).
        """

        def _wheel(e):
            try:
                wy.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                try:
                    wy.yview_scroll(1, "units")
                except Exception:
                    pass
            return "break"

        def _shift_wheel(e):
            try:
                wx.xview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                try:
                    wx.xview_scroll(1, "units")
                except Exception:
                    pass
            return "break"

        def _up(_e):
            try:
                wy.yview_scroll(-1, "units")
            except Exception:
                pass
            return "break"

        def _down(_e):
            try:
                wy.yview_scroll(1, "units")
            except Exception:
                pass
            return "break"

        widget.bind("<MouseWheel>", _wheel)
        widget.bind("<Shift-MouseWheel>", _shift_wheel)
        widget.bind("<Button-4>", _up)
        widget.bind("<Button-5>", _down)

        # Root-level bindings capture wheel events over child widgets
        # (e.g. the ClipRow frames inside the list canvas).
        if not getattr(self, "_root_scroll_binds_set", False):
            try:
                self.root.bind_all("<MouseWheel>", self._on_root_mousewheel)
                self.root.bind_all("<Shift-MouseWheel>", self._on_root_shift_mousewheel)
                self.root.bind_all("<Button-4>", self._on_root_button4)
                self.root.bind_all("<Button-5>", self._on_root_button5)
            except Exception:
                pass
            self._root_scroll_binds_set = True

    def _resolve_scroll_target(self, e):
        """Return (y_target, x_target) for the widget under the pointer,
        or (None, None) when it is not scrollable."""
        w = getattr(e, "widget", None)
        while w is not None:
            if w is self._canvas or w is self._lf:
                return self._canvas, None
            if w is self._preview or w is self._preview_container:
                return self._preview, self._preview
            w = getattr(w, "master", None)
        return None, None

    def _enforce_pane_limits(self):
        """Enforce min/max widths for the main horizontal pane (list vs preview)."""
        try:
            pane = getattr(self, "_main_pane", None)
            left = getattr(self, "_list_frame", None)
            right = getattr(self, "_pv_frame", None)
            if not (pane and left and right):
                return
            total_w = pane.winfo_width() or self.root.winfo_width()
            left_w = left.winfo_width()
            left_min = 200
            left_max = max(200, total_w - 200)
            new_left = min(max(left_w, left_min), left_max)
            if new_left != left_w:
                try:
                    pane.sash_place(0, new_left, 0)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_root_mousewheel(self, e):
        wy, _ = self._resolve_scroll_target(e)
        if not wy:
            return
        try:
            lines = int(-1 * (e.delta / 120))
        except Exception:
            lines = 1
        try:
            wy.yview_scroll(lines, "units")
        except Exception:
            pass

    def _on_root_shift_mousewheel(self, e):
        _, wx = self._resolve_scroll_target(e)
        if not wx:
            return
        try:
            lines = int(-1 * (e.delta / 120))
        except Exception:
            lines = 1
        try:
            wx.xview_scroll(lines, "units")
        except Exception:
            pass

    def _on_root_button4(self, e):
        wy, _ = self._resolve_scroll_target(e)
        if not wy:
            return
        try:
            wy.yview_scroll(-1, "units")
        except Exception:
            pass

    def _on_root_button5(self, e):
        wy, _ = self._resolve_scroll_target(e)
        if not wy:
            return
        try:
            wy.yview_scroll(1, "units")
        except Exception:
            pass


    # ── System tray / background ───────────────────────────────────────────
    def _on_close(self):
        """Window close button: keep monitoring in the background when the
        platform allows it, otherwise ask the user.

        - Windows: tray icons are reliable → hide to tray, keep monitoring.
        - Linux/macOS: tray hosting is unreliable (esp. Wayland/GNOME), so ask
          first and fall back to taskbar minimize, which can always be restored.
        """
        tray_ok = self._ensure_tray()
        if sys.platform.startswith("win") and tray_ok:
            self.root.withdraw()
            return

        dlg = ConfirmDialog(
            self.root,
            title="Keep Monitoring?",
            message="Keep Clipboard DLP running in the background?\n"
                    "Clipboard activity will still be recorded.",
            confirm_text="Keep Running",
        )
        if dlg.wait():
            if tray_ok:
                self.root.withdraw()
            else:
                self.root.iconify()
        else:
            self._shutdown()

    def _shutdown(self):
        self.monitor.stop()
        try:
            if self._tray_icon is not None:
                self._tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

    def _ensure_tray(self) -> bool:
        """Lazily create the tray icon. Returns True if a working tray icon
        exists (or was just created). Never raises."""
        if self._tray_icon is not None:
            return True
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return False
        try:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([4, 4, 60, 60], radius=14, fill="#2457a6")
            d.rounded_rectangle([26, 30, 38, 48], radius=4, fill="#ffffff")
            d.ellipse([22, 20, 42, 34], fill="#ffffff")
            menu = pystray.Menu(
                pystray.MenuItem("Open Clipboard DLP", self._tray_open, default=True),
                pystray.MenuItem("Quit", self._tray_quit),
            )
            icon = pystray.Icon("clipboard-dlp", img, "Clipboard DLP Monitor", menu)
            icon.run_detached()
            self._tray_icon = icon
            return True
        except Exception:
            self._tray_icon = None
            return False

    def _tray_open(self, *args):
        # pystray callbacks run on the tray thread; marshal back to Tk.
        self.root.after(0, self._restore_from_tray)

    def _tray_quit(self, *args):
        self.root.after(0, self._shutdown)

    def _restore_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()


def main():
    root = tk.Tk()
    app  = App(root)
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
