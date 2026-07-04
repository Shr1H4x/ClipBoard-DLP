from __future__ import annotations

import os
import csv
import queue
import datetime
import tkinter as tk
from tkinter import filedialog
from typing import Optional

from .constants import DB_PATH, BG, BG_PANEL, BORDER, BG_INPUT, BG_DIALOG, FONT_UI, FONT_UI_S, FONT_UI_B, FG, FG3, FONT_MONO_S, FONT_MONO, FONT_TITLE, BORDER2, BG_ITEM, BG_HOVER, BG_SEL, BG_BTN, BG_BTN_HOV, BG_BTN_SEC, BG_BTN_HOV2, FG_GREEN, FG_YELLOW, BG_DANGER
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
        self.root.geometry("780x600")
        self.root.minsize(600, 420)

        self.db   = ClipDB()
        self.q    = queue.Queue()
        self._rows: list[ClipRow] = []
        self._sel:  Optional[ClipRow] = None
        self._idx   = 0
        self._active_scroll_target = None  # (widget_y, widget_x) when pointer is over a scrollable
        self._root_scroll_binds_set = False

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

        tk.Label(left, text="⬡", font=("Segoe UI", 14), bg=BG_PANEL,
                 fg=BORDER2).pack(side=tk.LEFT)
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

        tk.Label(search_frm, text=" 🔍 ", font=("Segoe UI", 9),
                 bg=BG_INPUT, fg=FG3).pack(side=tk.LEFT)

        self._sv = tk.StringVar()
        self._sv.trace_add("write", lambda *_: self._filter())
        se = tk.Entry(search_frm, textvariable=self._sv,
                      bg=BG_INPUT, fg=FG, insertbackground=FG,
                      relief="flat", font=FONT_UI, bd=0,
                      highlightthickness=0)
        se.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 8))

        self._count_lbl = tk.Label(search_frm, text="",
                                   font=FONT_MONO_S, bg=BG_INPUT, fg=FG3)
        self._count_lbl.pack(side=tk.RIGHT, padx=8)

        tb = tk.Frame(self.root, bg=BG_PANEL, padx=10, pady=6)
        tb.pack(fill=tk.X)

        self._pause_btn = VSBtn(tb, "⏸  Pause", cmd=self._toggle_pause, primary=True)
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 4))

        VSBtn(tb, "⎘  Copy", cmd=self._copy).pack(side=tk.LEFT, padx=(0, 4))
        VSBtn(tb, "✕  Delete", cmd=self._delete).pack(side=tk.LEFT, padx=(0, 4))
        VSBtn(tb, "↯  Export", cmd=self._export).pack(side=tk.LEFT, padx=(0, 4))
        VSBtn(tb, "⌫  Clear All", cmd=self._clear, danger=True).pack(side=tk.RIGHT)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        ch = tk.Frame(self.root, bg=BG_PANEL, padx=24, pady=3)
        ch.pack(fill=tk.X)
        tk.Label(ch, text=" IDX    TIMESTAMP              LEN    CONTENT PREVIEW",
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

        stbar = tk.Frame(self.root, bg="#007acc", padx=10, pady=3)
        stbar.pack(fill=tk.X)

        self._sb_left = tk.Label(stbar, text="", font=FONT_UI_S, bg="#007acc", fg="white")
        self._sb_left.pack(side=tk.LEFT)

        self._sb_right = tk.Label(stbar, text="", font=FONT_MONO_S, bg="#007acc", fg="white")
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
        self._idx = len(entries)
        for i, e in enumerate(entries, start=1):
            # support legacy rows (id,ts,content) and new rows (id,ts,content,source)
            if len(e) == 4:
                rid, ts, content, source = e
            else:
                rid, ts, content = e
                source = None
            row = self._add_row(rid, ts, content, i, prepend=False)
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
        for i, row in enumerate(self._rows, start=1):
            try:
                row.set_idx(i)
            except Exception:
                pass
        self._update_sb()

    def _add_row(self, rid, ts, content, idx, prepend=False):
        row = ClipRow(self._lf, rid, ts, content, idx,
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
        # Debug: log selection to console to help diagnose preview issues
        try:
            print(f"[debug] select id={row.rid} len={len(content)}")
        except Exception:
            pass
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
        try:
            import pyperclip
        except Exception:
            pyperclip = None
        if not pyperclip:
            NotifyDialog(self.root, "pyperclip Missing",
                         "Install pyperclip to enable copy.", kind="error").wait()
            return
        try:
            detections = detect_sensitive(content)
            pyperclip.copy(format_sensitive_copy(content, detections))
            try:
                self.monitor.mark_seen(content)
            except Exception:
                pass
            self._flash("Copied to clipboard  ✔")
        except Exception as e:
            NotifyDialog(self.root, "Copy Failed", str(e), kind="error").wait()

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
        txt.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(dlg._body, bg=BG_DIALOG)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        def _copy_full():
            try:
                import pyperclip
            except Exception:
                pyperclip = None
            if not pyperclip:
                NotifyDialog(self.root, "pyperclip Missing",
                             "Install pyperclip to enable copy.", kind="error").wait()
                return
            try:
                detections = detect_sensitive(content)
                pyperclip.copy(format_sensitive_copy(content, detections))
                try:
                    self.monitor.mark_seen(content)
                except Exception:
                    pass
                dlg.destroy()
                self._flash("Copied full entry to clipboard  ✔")
            except Exception as e:
                NotifyDialog(self.root, "Copy Failed", str(e), kind="error").wait()

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
                row = self._add_row(rid, ts, text, 1, prepend=True)
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
                for i, row in enumerate(self._rows, start=1):
                    try:
                        row.set_idx(i)
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

        - Supports Windows/Mac `<MouseWheel>` (via bind_all while hovered).
        - Supports Linux `<Button-4>`/`<Button-5>` events.
        - Supports horizontal scrolling with `<Shift-MouseWheel>`.
        widget_y: target for vertical scrolling (yview_scroll).
        widget_x: target for horizontal scrolling (xview_scroll).
        """
        wy = widget_y or widget
        wx = widget_x or widget

        def _on_mousewheel(e):
            try:
                lines = int(-1 * (e.delta / 120))
            except Exception:
                # fallback for platforms that expose num instead
                lines = -1 if getattr(e, "delta", 0) < 0 else 1
            try:
                wy.yview_scroll(lines, "units")
            except Exception:
                pass

        def _on_shift_mousewheel(e):
            try:
                lines = int(-1 * (e.delta / 120))
            except Exception:
                lines = -1 if getattr(e, "delta", 0) < 0 else 1
            try:
                wx.xview_scroll(lines, "units")
            except Exception:
                pass

        # When pointer enters the widget, mark it as the active scroll target.
        # This allows root-level wheel events (from touchpad) to scroll the
        # widget even if the widget doesn't have keyboard focus.
        def _enter(_e):
            try:
                self._active_scroll_target = (wy, wx)
            except Exception:
                self._active_scroll_target = (wy, wx)

        def _leave(_e):
            # Clear only if the same target
            try:
                if self._active_scroll_target and self._active_scroll_target[0] is wy:
                    self._active_scroll_target = None
            except Exception:
                self._active_scroll_target = None

        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)

        # Ensure root-level bindings are installed once to capture touchpad events
        if not getattr(self, "_root_scroll_binds_set", False):
            try:
                self.root.bind_all("<MouseWheel>", self._on_root_mousewheel)
                self.root.bind_all("<Shift-MouseWheel>", self._on_root_shift_mousewheel)
                # X11 wheel events
                self.root.bind_all("<Button-4>", self._on_root_button4)
                self.root.bind_all("<Button-5>", self._on_root_button5)
            except Exception:
                pass
            self._root_scroll_binds_set = True

    def _enforce_pane_limits(self):
        """Enforce min/max sizes for the main horizontal pane and the inner vertical pane."""
        try:
            # main horizontal pane limits (left pane width)
            pane = getattr(self, "_main_pane", None)
            left = getattr(self, "_list_frame", None)
            right = getattr(self, "_pv_frame", None)
            if pane and left and right:
                total_w = pane.winfo_width() or self.root.winfo_width()
                left_w = left.winfo_width()
                # limits (pixels)
                left_min = 200
                left_max = max(200, total_w - 200)
                new_left = min(max(left_w, left_min), left_max)
                if new_left != left_w:
                    try:
                        pane.sash_place(0, new_left, 0)
                    except Exception:
                        pass

            # inner vertical pane limits (preview height)
            ip = getattr(self, "_inner_pane", None)
            top = getattr(self, "_preview_container", None)
            bottom = getattr(self, "_src_frame", None)
            if ip and top and bottom:
                total_h = ip.winfo_height() or self.root.winfo_height()
                top_h = top.winfo_height()
                top_min = 80
                top_max = max(80, total_h - 80)
                new_top = min(max(top_h, top_min), top_max)
                if new_top != top_h:
                    try:
                        ip.sash_place(0, 0, new_top)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_root_mousewheel(self, e):
        if not self._active_scroll_target:
            return
        wy, _wx = self._active_scroll_target
        try:
            # Standardize to "units" lines
            lines = int(-1 * (e.delta / 120))
        except Exception:
            lines = -1 if getattr(e, "delta", 0) < 0 else 1
        try:
            wy.yview_scroll(lines, "units")
        except Exception:
            pass

    def _on_root_shift_mousewheel(self, e):
        if not self._active_scroll_target:
            return
        _wy, wx = self._active_scroll_target
        try:
            lines = int(-1 * (e.delta / 120))
        except Exception:
            lines = -1 if getattr(e, "delta", 0) < 0 else 1
        try:
            wx.xview_scroll(lines, "units")
        except Exception:
            pass

    def _on_root_button4(self, e):
        if not self._active_scroll_target:
            return
        wy, _ = self._active_scroll_target
        try:
            wy.yview_scroll(-1, "units")
        except Exception:
            pass

    def _on_root_button5(self, e):
        if not self._active_scroll_target:
            return
        wy, _ = self._active_scroll_target
        try:
            wy.yview_scroll(1, "units")
        except Exception:
            pass


def main():
    root = tk.Tk()
    app  = App(root)
    root.protocol("WM_DELETE_WINDOW",
                  lambda: (app.monitor.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
