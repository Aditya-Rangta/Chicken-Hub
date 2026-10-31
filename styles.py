"""
styles.py - Colors, fonts, small reusable widgets and image loading.

Images are loaded with Pillow and resized WITHOUT stretching. If an image file is
missing (or Pillow is not installed) we show a coloured placeholder or an emoji instead,
so the program never crashes because of a picture.
"""
import os
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    PIL_OK = True
except ImportError:                      # Pillow not installed -> emoji fallback only
    PIL_OK = False

COLORS = {
    "red": "#B3121E", "dark_red": "#8A0E17", "cream": "#FFF4E0", "white": "#FFFFFF",
    "charcoal": "#2B2B2B", "gray": "#6B6B6B", "light_gray": "#E6DCCB",
    "green": "#2E8B57", "amber": "#D98E04", "pink": "#FBE3DD",
    "gold": "#F5C542", "silver": "#D9D9D9", "bronze": "#E3B07A",
}

FONT = "Segoe UI"
F_TITLE = (FONT, 22, "bold")
F_HEAD = (FONT, 15, "bold")
F_BODY = (FONT, 11)
F_BOLD = (FONT, 11, "bold")
F_SMALL = (FONT, 9)
F_BIG = (FONT, 26, "bold")
F_EMOJI = ("Segoe UI Emoji", 40)


# --------------------------------------------------------------------- images
def load_pil_image(folder, filename, size, label="?"):
    """Return a size x size RGBA PIL image (aspect ratio kept). Missing file -> placeholder."""
    if not PIL_OK:
        return None
    resample = getattr(Image, "Resampling", Image).LANCZOS
    path = os.path.join(folder, filename) if filename else ""
    try:
        if path and os.path.isfile(path):
            pic = Image.open(path).convert("RGBA")
            pic.thumbnail((size, size), resample)          # keeps the aspect ratio
        else:
            pic = make_placeholder(size, label)
    except Exception:                                      # damaged image file
        pic = make_placeholder(size, label)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(pic, ((size - pic.width) // 2, (size - pic.height) // 2), pic)
    return canvas


def make_placeholder(size, label="?"):
    """A simple rounded coloured square with the first letter of the item name."""
    pic = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pic)
    draw.rounded_rectangle((2, 2, size - 3, size - 3), radius=size // 6, fill=COLORS["pink"],
                           outline=COLORS["red"], width=3)
    letter = (label or "?").strip()[:1].upper() or "?"
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        try:
            font = ImageFont.load_default(size // 2)
        except Exception:
            font = ImageFont.load_default()
    draw.text((size / 2, size / 2), letter, fill=COLORS["red"], font=font, anchor="mm")
    return pic


class ImageStore:
    """Loads images once and keeps them in memory (Tkinter loses images that are not stored)."""

    def __init__(self, folder):
        self.folder = folder
        self._cache = {}

    def get(self, filename, size, label="?"):
        key = (filename, size)
        if key not in self._cache:
            photo = None
            pil = load_pil_image(self.folder, filename, size, label)
            if pil is not None:
                try:
                    photo = ImageTk.PhotoImage(pil)
                except Exception:
                    photo = None
            self._cache[key] = photo
        return self._cache[key]


def image_label(parent, store, filename, emoji, size, bg, label="?"):
    """A Label showing the picture, or the emoji if the picture could not be loaded."""
    photo = store.get(filename, size, label)
    if photo is not None:
        lab = tk.Label(parent, image=photo, bg=bg, bd=0)
        lab.image = photo
        return lab
    return tk.Label(parent, text=emoji or "🍽", font=("Segoe UI Emoji", max(16, size // 2)), bg=bg)


# -------------------------------------------------------------------- widgets
_BUTTON_STYLES = {
    "primary": ("red", "white", "dark_red"),
    "secondary": ("charcoal", "white", "gray"),
    "success": ("green", "white", "#236B43"),
    "danger": ("dark_red", "white", "charcoal"),
    "light": ("light_gray", "charcoal", "#D2C6B1"),
}


def make_button(parent, text, command, style="primary", width=None, font=F_BOLD, padx=14, pady=6):
    bg_key, fg_key, hover_key = _BUTTON_STYLES[style]
    bg = COLORS.get(bg_key, bg_key)
    fg = COLORS.get(fg_key, fg_key)
    hover = COLORS.get(hover_key, hover_key)
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font,
                    activebackground=hover, activeforeground=fg, relief="flat", bd=0,
                    padx=padx, pady=pady, cursor="hand2", width=width,
                    disabledforeground="#BDBDBD")
    btn._normal_bg, btn._hover_bg = bg, hover

    def on_enter(_e):
        if str(btn["state"]) == "normal":
            btn.config(bg=btn._hover_bg)

    def on_leave(_e):
        btn.config(bg=btn._normal_bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def card(parent, **kw):
    """A white card with a thin border."""
    opts = dict(bg=COLORS["white"], highlightthickness=1, highlightbackground=COLORS["light_gray"])
    opts.update(kw)
    return tk.Frame(parent, **opts)


class ScrollFrame(tk.Frame):
    """A frame that scrolls vertically. Put your widgets inside `.inner`."""

    def __init__(self, parent, bg=None):
        bg = bg or COLORS["cream"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


def apply_ttk_theme(root):
    """Style ttk widgets (Treeview, Progressbar, Combobox, Scrollbar) with our colours."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", background=COLORS["white"], fieldbackground=COLORS["white"],
                    foreground=COLORS["charcoal"], rowheight=30, font=F_BODY, borderwidth=0)
    style.configure("Treeview.Heading", background=COLORS["red"], foreground="white",
                    font=F_BOLD, relief="flat", padding=6)
    style.map("Treeview.Heading", background=[("active", COLORS["dark_red"])])
    style.map("Treeview", background=[("selected", COLORS["gold"])],
              foreground=[("selected", COLORS["charcoal"])])
    style.configure("Red.Horizontal.TProgressbar", troughcolor=COLORS["light_gray"],
                    background=COLORS["red"], bordercolor=COLORS["light_gray"],
                    lightcolor=COLORS["red"], darkcolor=COLORS["red"], thickness=18)
    style.configure("Green.Horizontal.TProgressbar", troughcolor=COLORS["light_gray"],
                    background=COLORS["green"], bordercolor=COLORS["light_gray"],
                    lightcolor=COLORS["green"], darkcolor=COLORS["green"], thickness=18)
    style.configure("TCombobox", padding=4)
