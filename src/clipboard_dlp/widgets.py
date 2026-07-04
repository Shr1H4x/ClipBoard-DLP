from __future__ import annotations

import tkinter as tk
from typing import Optional

from .constants import (
    BG_BTN, BG_BTN_HOV, BG_BTN_SEC, BG_BTN_HOV2, BG_DANGER, BG_DNG_HOV,
    FG, FONT_UI_B, BG_INPUT, BORDER, BORDER2, FG3, FONT_UI, FONT_MONO,
    FONT_MONO_S, FONT_ICON, BG_ITEM, BG_HOVER, BG_SEL
)


class VSBtn(tk.Label):
    def __init__(self, parent, text, cmd=None,
                 primary=False, danger=False, width=None, **kw):
        bg   = BG_BTN    if primary else (BG_DANGER  if danger  else BG_BTN_SEC)
        hbg  = BG_BTN_HOV if primary else (BG_DNG_HOV if danger  else BG_BTN_HOV2)
        fg   = "#ffffff"
        opts = dict(bg=bg, fg=fg, font=FONT_UI_B,
                    padx=16, pady=5, cursor="hand2", relief="flat")
        if width: opts["width"] = width
        super().__init__(parent, text=text, **opts, **kw)
        self._bg, self._hbg, self._cmd = bg, hbg, cmd
        self.bind("<Enter>",    lambda _: self.config(bg=self._hbg))
        self.bind("<Leave>",    lambda _: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda _: self._cmd() if self._cmd else None)

    def retag(self, text=None, bg=None, hbg=None):
        if text: self.config(text=text)
        if bg:   self._bg  = bg;  self.config(bg=bg)
        if hbg:  self._hbg = hbg


class VSEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, placeholder="", **kw):
        super().__init__(parent, bg=BG_INPUT,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BORDER2, **kw)
        self._ph  = placeholder
        self._var = textvariable or tk.StringVar()
        self._ent = tk.Entry(
            self, textvariable=self._var,
            bg=BG_INPUT, fg=FG, insertbackground=FG,
            relief="flat", font=FONT_UI, bd=4,
            highlightthickness=0
        )
        self._ent.pack(fill=tk.X)
        if placeholder:
            self._show_ph()
            self._ent.bind("<FocusIn>",  self._clear_ph)
            self._ent.bind("<FocusOut>", self._restore_ph)

    def _show_ph(self):
        if not self._ent.get():
            self._ent.insert(0, self._ph)
            self._ent.config(fg=FG3)

    def _clear_ph(self, _):
        if self._ent.get() == self._ph:
            self._ent.delete(0, "end")
            self._ent.config(fg=FG)

    def _restore_ph(self, _):
        self._show_ph()

    def get(self): return self._var.get()
    def bind_trace(self, fn): self._var.trace_add("write", fn)


class ClipRow(tk.Frame):
    def __init__(self, parent, rid, ts, content, idx, on_select, on_dbl, **kw):
        super().__init__(parent, bg=BG_ITEM, **kw)
        self.rid        = rid
        self._on_sel    = on_select
        self._on_dbl    = on_dbl
        self._selected  = False
        self._alert_text = ""

        self._strip = tk.Frame(self, bg=BG_ITEM, width=3)
        self._strip.pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(self, bg=BG_ITEM, padx=10, pady=5)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        meta = tk.Frame(inner, bg=BG_ITEM)
        meta.pack(fill=tk.X)

        self._idx_lbl = tk.Label(meta, text=f" {idx:04d} ",
                   font=FONT_MONO_S, bg="#094771",
                   fg="#4fc3f7", padx=0, pady=0)
        self._idx_lbl.pack(side=tk.LEFT)

        tk.Label(meta, text=f"  {ts}",
                 font=FONT_MONO_S, bg=BG_ITEM, fg=FG3).pack(side=tk.LEFT)

        # Right-aligned container for meta items (length, etc.) to ensure
        # the length label always appears at the far right of the row.
        right_meta = tk.Frame(meta, bg=BG_ITEM)
        right_meta.pack(side=tk.RIGHT)
        clen = len(content)
        self._len_lbl = tk.Label(right_meta, text=f"{clen}c",
                     font=FONT_MONO_S, bg=BG_ITEM, fg=FG3)
        self._len_lbl.pack(side=tk.RIGHT, padx=4)

        self._alert_lbl = tk.Label(
            right_meta,
            text="",
            font=FONT_MONO_S,
            bg=BG_ITEM,
            fg=FG3,
            padx=6,
            pady=0,
            relief="flat"
        )
        self._alert_lbl.pack(side=tk.RIGHT, padx=(0, 6))

        self._alert_icon_lbl = tk.Label(
            right_meta,
            text="",
            font=FONT_ICON,
            bg=BG_ITEM,
            fg=FG3,
            padx=4,
            pady=0,
            relief="flat"
        )
        self._alert_icon_lbl.pack(side=tk.RIGHT, padx=(0, 2))

        preview = content.replace("\n", " ↵ ").replace("\t", " → ")
        preview = (preview[:400] + "…") if len(preview) > 400 else preview
        self._prev_lbl = tk.Label(inner, text=preview,
                                  font=FONT_MONO, bg=BG_ITEM, fg=FG,
                                  anchor="w", justify="left")
        self._prev_lbl.pack(fill=tk.X, pady=(2, 0))

        self._all = [self, inner, meta, self._idx_lbl, self._prev_lbl,
                 self._strip]
        for w in self._all:
            w.bind("<Button-1>",        self._click)
            w.bind("<Double-Button-1>", self._dbl)
            w.bind("<Enter>",           self._hover_on)
            w.bind("<Leave>",           self._hover_off)

    def _click(self, _): self._on_sel(self)
    def _dbl(self, _):   self._on_dbl(self)

    def _hover_on(self, _):
        if not self._selected: self._tint(BG_HOVER)

    def _hover_off(self, _):
        if not self._selected: self._tint(BG_ITEM)

    def select(self):
        self._selected = True
        self._tint(BG_SEL)
        self._strip.config(bg=BORDER2)

    def deselect(self):
        self._selected = False
        self._tint(BG_ITEM)
        self._strip.config(bg=BG_ITEM)

    def _tint(self, c):
        for w in self.winfo_children():
            try: w.config(bg=c)
            except: pass
            for ww in w.winfo_children():
                try: ww.config(bg=c)
                except: pass
        self.config(bg=c)
        try: self._prev_lbl.config(bg=c)
        except: pass

    def set_idx(self, idx: int):
        try:
            self._idx_lbl.config(text=f" {idx:04d} ")
        except Exception:
            pass

    def set_alert(self, text: str = ""):
        self._alert_text = text or ""
        try:
            self._alert_lbl.config(text=self._alert_text)
            self._alert_icon_lbl.config(text="⚠️" if self._alert_text else "")
        except Exception:
            pass
