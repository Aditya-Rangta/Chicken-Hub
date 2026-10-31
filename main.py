"""
main.py - START HERE.  Run this file to open Chicken Hub.

It creates the window, the left navigation menu and all screens, and opens the database.
(This is a college project. It is not connected to any real restaurant brand.)
"""
import os
import tkinter as tk
from tkinter import messagebox, simpledialog

from database import Database, DatabaseError, BASE_DIR
from game_screen import GameScreen
from screens import (DashboardScreen, BillingScreen, KitchenScreen, InventoryScreen,
                     MenuManagementScreen, AnalyticsScreen, LeaderboardScreen)
from styles import COLORS, F_BOLD, F_SMALL, ImageStore, apply_ttk_theme, image_label

ASSETS_DIR = os.path.join(BASE_DIR, "assets", "images")

NAV = [("dashboard", "Dashboard"), ("billing", "New Order"), ("kitchen", "Kitchen"),
       ("inventory", "Inventory"), ("menu", "Menu Management"), ("game", "Cooking Game"),
       ("analytics", "Sales Analytics"), ("leaderboard", "Leaderboard")]


def ensure_assets():
    """If the images folder is missing/empty, redraw the pictures with Pillow (safe if it fails)."""
    try:
        import generate_assets
        generate_assets.generate_all(force=False)
    except Exception:
        pass     # the app still works: missing pictures become placeholders/emoji


class App(tk.Tk):
    def __init__(self, db=None):
        super().__init__()
        self.title("Chicken Hub – Restaurant Management & Cooking Simulation")
        width = min(1240, self.winfo_screenwidth() - 60)
        height = min(740, self.winfo_screenheight() - 90)
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1000, 640)
        self.configure(bg=COLORS["cream"])
        apply_ttk_theme(self)

        self.db = db or Database()
        self.images = ImageStore(ASSETS_DIR)
        self.staff_unlocked = False
        self.current = None
        self.nav_buttons = {}

        self._build_sidebar()
        self.content = tk.Frame(self, bg=COLORS["cream"])
        self.content.pack(side="right", fill="both", expand=True)

        self.screens = {
            "dashboard": DashboardScreen(self.content, self),
            "billing": BillingScreen(self.content, self),
            "kitchen": KitchenScreen(self.content, self),
            "inventory": InventoryScreen(self.content, self),
            "menu": MenuManagementScreen(self.content, self),
            "game": GameScreen(self.content, self),
            "analytics": AnalyticsScreen(self.content, self),
            "leaderboard": LeaderboardScreen(self.content, self),
        }
        self.show_screen("dashboard")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_sidebar(self):
        bar = tk.Frame(self, bg=COLORS["red"], width=225)
        bar.pack(side="left", fill="y")
        bar.pack_propagate(False)
        image_label(bar, self.images, "logo.png", "🍗", 110, COLORS["red"], "C").pack(pady=(18, 2))
        tk.Label(bar, text="CHICKEN HUB", font=(F_BOLD[0], 15, "bold"), bg=COLORS["red"],
                 fg=COLORS["cream"]).pack()
        tk.Label(bar, text="Restaurant Management", font=F_SMALL, bg=COLORS["red"],
                 fg=COLORS["cream"]).pack(pady=(0, 14))
        for key, text in NAV:
            btn = tk.Button(bar, text="   " + text, anchor="w", font=(F_BOLD[0], 11, "bold"),
                            bg=COLORS["red"], fg="white", activebackground=COLORS["dark_red"],
                            activeforeground="white", relief="flat", bd=0, padx=8, pady=9,
                            cursor="hand2", command=lambda k=key: self.show_screen(k))
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

    # -------------------------------------------------------------- navigation
    def show_screen(self, key):
        if key == self.current:
            self.screens[key].on_show()
            return
        # ask the screen we are leaving (the game asks "end game?")
        if self.current is not None and not self.screens[self.current].can_leave():
            return
        if self.current is not None:
            self.screens[self.current].pack_forget()
        self.current = key
        self.screens[key].pack(fill="both", expand=True)
        for k, btn in self.nav_buttons.items():
            btn.config(bg=COLORS["dark_red"] if k == key else COLORS["red"])
        try:
            self.screens[key].on_show()
        except DatabaseError as e:
            messagebox.showerror("Database error", str(e))

    # ------------------------------------------------------------- staff access
    def require_staff(self):
        """Ask for the staff PIN once per session. Returns True if allowed."""
        if self.staff_unlocked:
            return True
        pin = simpledialog.askstring("Staff PIN", "Enter the staff PIN (default: 1234):",
                                     show="*", parent=self)
        if pin is None:
            return False
        if self.db.verify_pin(pin.strip()):
            self.staff_unlocked = True
            return True
        messagebox.showerror("Wrong PIN", "That PIN is not correct.")
        return False

    def on_close(self):
        self.screens["game"].shutdown()      # cancel any pending game timer
        self.db.close()
        self.destroy()


def main():
    ensure_assets()
    try:
        db = Database()
    except DatabaseError as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Chicken Hub", f"The program cannot start.\n\n{e}")
        root.destroy()
        return
    app = App(db)
    app.mainloop()


if __name__ == "__main__":
    main()
