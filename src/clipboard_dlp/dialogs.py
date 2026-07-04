from __future__ import annotations

import tkinter as tk

from .constants import BG_DIALOG, BORDER, BORDER2, BG_DANGER, FG3, FG, FG_GREEN, FG_YELLOW, FG_RED, FONT_UI_S, FONT_UI, FONT_UI_B
from .widgets import VSBtn


class VSDialog(tk.Toplevel):
    def __init__(self, parent, title, width=420, height=180):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=BORDER)
        self.resizable(False, False)
        self.result = None

        parent.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - width  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - height // 2
        self.geometry(f"{width}x{height}+{px}+{py}")

        self.grab_set()
        self.focus_force()
        self.lift()

        shell = tk.Frame(self, bg=BG_DIALOG,
                         highlightthickness=1,
                         highlightbackground=BORDER)
        shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        tbar = tk.Frame(shell, bg="#323233", height=32)
        tbar.pack(fill=tk.X)
        tbar.pack_propagate(False)

        tbar.bind("<ButtonPress-1>",   self._drag_start)
        tbar.bind("<B1-Motion>",       self._drag_move)

        tk.Label(tbar, text="⬡", font=("Segoe UI", 9),
                 bg="#323233", fg=BORDER2).pack(side=tk.LEFT, padx=(10, 4), pady=6)
        self._title_lbl = tk.Label(tbar, text=title, font=FONT_UI_S,
                                   bg="#323233", fg=FG3)
        self._title_lbl.pack(side=tk.LEFT)
        self._title_lbl.bind("<ButtonPress-1>", self._drag_start)
        self._title_lbl.bind("<B1-Motion>",     self._drag_move)

        x_btn = tk.Label(tbar, text=" ✕ ", font=FONT_UI_B,
                         bg="#323233", fg=FG3, cursor="hand2")
        x_btn.pack(side=tk.RIGHT, padx=4)
        x_btn.bind("<Enter>",    lambda _: x_btn.config(bg=BG_DANGER, fg="white"))
        x_btn.bind("<Leave>",    lambda _: x_btn.config(bg="#323233", fg=FG3))
        x_btn.bind("<Button-1>", lambda _: self._close())

        tk.Frame(shell, bg=BORDER, height=1).pack(fill=tk.X)

        self._body = tk.Frame(shell, bg=BG_DIALOG, padx=20, pady=16)
        self._body.pack(fill=tk.BOTH, expand=True)

        self.bind("<Escape>", lambda _: self._close())

        self._dx = self._dy = 0

    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _close(self):
        self.result = None
        self.destroy()

    def wait(self):
        self.wait_window()
        return self.result


class ConfirmDialog(VSDialog):
    def __init__(self, parent, title, message,
                 confirm_text="Confirm", danger=False,
                 width=430, height=185):
        super().__init__(parent, title, width, height)

        icon   = "⚠" if danger else "ℹ"
        icolor = FG_RED if danger else FG_GREEN

        row = tk.Frame(self._body, bg=BG_DIALOG)
        row.pack(fill=tk.X, pady=(0, 20))

        tk.Label(row, text=icon, font=("Segoe UI", 22),
                 bg=BG_DIALOG, fg=icolor,
                 width=2).pack(side=tk.LEFT, anchor="n", pady=2)

        tk.Label(row, text=message,
                 font=FONT_UI, bg=BG_DIALOG, fg=FG,
                 wraplength=330, justify="left",
                 anchor="w").pack(side=tk.LEFT, padx=(10, 0))

        tk.Frame(self._body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

        btn_row = tk.Frame(self._body, bg=BG_DIALOG)
        btn_row.pack(anchor="e")

        VSBtn(btn_row, "  Cancel  ", cmd=self._no).pack(side=tk.LEFT, padx=(0, 8))
        VSBtn(btn_row, f"  {confirm_text}  ",
              cmd=self._yes,
              danger=danger,
              primary=not danger).pack(side=tk.LEFT)

        self.bind("<Return>", lambda _: self._yes())

    def _yes(self): self.result = True;  self.destroy()
    def _no(self):  self.result = False; self.destroy()


class NotifyDialog(VSDialog):
    KIND_MAP = {
        "info":  (FG_GREEN,  "✔",  "Info"),
        "warn":  (FG_YELLOW, "⚠",  "Warning"),
        "error": (FG_RED,    "✖",  "Error"),
    }

    def __init__(self, parent, title, message, kind="info",
                 width=390, height=170):
        super().__init__(parent, title, width, height)
        color, icon, _ = self.KIND_MAP.get(kind, (FG, "•", title))

        tk.Frame(self._body.master, bg=color, height=3).pack(
            fill=tk.X, before=self._body)

        row = tk.Frame(self._body, bg=BG_DIALOG)
        row.pack(fill=tk.X, pady=(4, 18))

        tk.Label(row, text=icon, font=("Segoe UI", 22),
                 bg=BG_DIALOG, fg=color, width=2).pack(side=tk.LEFT, anchor="n")

        tk.Label(row, text=message,
                 font=FONT_UI, bg=BG_DIALOG, fg=FG,
                 wraplength=290, justify="left").pack(side=tk.LEFT, padx=(10, 0))

        tk.Frame(self._body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))

        VSBtn(self._body, "  OK  ", cmd=self.destroy,
              primary=True).pack(anchor="e")
        self.bind("<Return>", lambda _: self.destroy())


class ExportDialog(VSDialog):
    def __init__(self, parent, count, filename, width=430, height=175):
        super().__init__(parent, "Export Complete", width, height)

        tk.Frame(self._body.master, bg=FG_GREEN, height=3).pack(
            fill=tk.X, before=self._body)

        row = tk.Frame(self._body, bg=BG_DIALOG)
        row.pack(fill=tk.X, pady=(4, 18))

        tk.Label(row, text="✔", font=("Segoe UI", 22),
                 bg=BG_DIALOG, fg=FG_GREEN, width=2).pack(side=tk.LEFT, anchor="n")

        msg = f"{count} entries exported successfully.\n\nFile: {filename}"
        tk.Label(row, text=msg,
                 font=FONT_UI, bg=BG_DIALOG, fg=FG,
                 wraplength=320, justify="left").pack(side=tk.LEFT, padx=(10, 0))

        tk.Frame(self._body, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 12))
        VSBtn(self._body, "  OK  ", cmd=self.destroy,
              primary=True).pack(anchor="e")
        self.bind("<Return>", lambda _: self.destroy())
