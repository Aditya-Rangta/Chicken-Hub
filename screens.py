"""
screens.py - Every screen (page) of the restaurant app except the cooking game.

Each screen is a tk.Frame with:
  on_show()    - called every time the screen is opened (reloads data from SQLite)
  can_leave()  - lets a screen stop the user from leaving (the game uses this)
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox

from billing import (calculate_bill, apply_coupon, format_receipt, rupees,
                     CouponError, COUPONS)
from database import Database, DatabaseError, StockError, STATUSES, BASE_DIR
from styles import (COLORS, F_TITLE, F_HEAD, F_BODY, F_BOLD, F_SMALL, F_BIG,
                    make_button, card, ScrollFrame, image_label)

RECEIPT_DIR = os.path.join(BASE_DIR, "receipts")
CATEGORIES = ["Burgers", "Sides", "Buckets", "Wraps", "Drinks", "Desserts", "General"]
EMOJI_BY_CATEGORY = {"Burgers": "🍔", "Sides": "🍟", "Buckets": "🍗", "Wraps": "🌯",
                     "Drinks": "🥤", "Desserts": "🍨"}
STATUS_COLORS = {"In Stock": COLORS["green"], "Low Stock": COLORS["amber"],
                 "Out of Stock": COLORS["red"], "Inactive": COLORS["gray"]}


class BaseScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["cream"])
        self.app = app
        self.db = app.db
        self.images = app.images

    def make_header(self, title, subtitle=""):
        head = tk.Frame(self, bg=COLORS["cream"])
        head.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(head, text=title, font=F_TITLE, bg=COLORS["cream"], fg=COLORS["red"]).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, font=F_BODY, bg=COLORS["cream"],
                     fg=COLORS["gray"]).pack(anchor="w")
        return head

    def on_show(self):
        pass

    def can_leave(self):
        return True


def make_tree(parent, columns, height=10):
    """columns = [(id, heading, width, anchor, stretch)] -> Treeview with a scrollbar."""
    wrap = tk.Frame(parent, bg=COLORS["white"])
    tree = ttk.Treeview(wrap, columns=[c[0] for c in columns], show="headings",
                        height=height, selectmode="browse")
    for col_id, heading, width, anchor, stretch in columns:
        tree.heading(col_id, text=heading)
        tree.column(col_id, width=width, anchor=anchor, stretch=stretch)
    bar = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    tree.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    return wrap, tree


def clear_tree(tree):
    tree.delete(*tree.get_children())


# =========================================================================== Dashboard
class DashboardScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Welcome to Chicken Hub", "Restaurant Management & Cooking Simulation")

        row = tk.Frame(self, bg=COLORS["cream"])
        row.pack(fill="x", padx=18)
        self.stat_labels = {}
        for key, title, color in [("orders", "Total Orders", COLORS["red"]),
                                  ("revenue", "Total Revenue", COLORS["green"]),
                                  ("menu", "Menu Items Available", COLORS["amber"]),
                                  ("score", "Game High Score", COLORS["charcoal"])]:
            c = card(row)
            c.pack(side="left", fill="both", expand=True, padx=6)
            tk.Frame(c, bg=color, height=5).pack(fill="x")
            tk.Label(c, text=title, font=F_BODY, bg=COLORS["white"],
                     fg=COLORS["gray"]).pack(anchor="w", padx=14, pady=(10, 0))
            lab = tk.Label(c, text="0", font=F_BIG, bg=COLORS["white"], fg=COLORS["charcoal"])
            lab.pack(anchor="w", padx=14, pady=(0, 10))
            self.stat_labels[key] = lab

        lower = tk.Frame(self, bg=COLORS["cream"])
        lower.pack(fill="both", expand=True, padx=18, pady=12)

        actions = card(lower)
        actions.pack(side="left", fill="both", expand=True, padx=6)
        tk.Label(actions, text="Quick Actions", font=F_HEAD, bg=COLORS["white"],
                 fg=COLORS["charcoal"]).pack(anchor="w", padx=16, pady=(12, 6))
        grid = tk.Frame(actions, bg=COLORS["white"])
        grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        buttons = [("New Order", "billing", "primary"), ("Kitchen", "kitchen", "secondary"),
                   ("Inventory", "inventory", "secondary"), ("Cooking Game", "game", "success"),
                   ("Sales Analytics", "analytics", "secondary"),
                   ("Game Leaderboard", "leaderboard", "primary")]
        for i, (text, target, style) in enumerate(buttons):
            btn = make_button(grid, text, lambda t=target: self.app.show_screen(t), style,
                              font=(F_BOLD[0], 13, "bold"), pady=16)
            btn.grid(row=i // 2, column=i % 2, padx=6, pady=6, sticky="nsew")
        for c in range(2):
            grid.columnconfigure(c, weight=1)
        for r in range(3):
            grid.rowconfigure(r, weight=1)

        alerts = card(lower, width=360)
        alerts.pack(side="right", fill="y", padx=6)
        alerts.pack_propagate(False)
        tk.Label(alerts, text="Low-Stock Alerts", font=F_HEAD, bg=COLORS["white"],
                 fg=COLORS["charcoal"]).pack(anchor="w", padx=16, pady=(12, 6))
        self.alert_box = tk.Frame(alerts, bg=COLORS["white"])
        self.alert_box.pack(fill="both", expand=True, padx=16)
        self.kitchen_label = tk.Label(alerts, text="", font=F_BODY, bg=COLORS["white"],
                                      fg=COLORS["gray"])
        self.kitchen_label.pack(anchor="w", padx=16, pady=(0, 12))

    def on_show(self):
        menu = self.db.get_menu()
        available = sum(1 for m in menu if m["stock"] > 0)
        self.stat_labels["orders"].config(text=str(self.db.total_orders()))
        self.stat_labels["revenue"].config(text=rupees(self.db.total_revenue()))
        self.stat_labels["menu"].config(text=f"{available} / {len(menu)}")
        self.stat_labels["score"].config(text=str(self.db.high_score()))
        for w in self.alert_box.winfo_children():
            w.destroy()
        low = self.db.low_stock_items()
        if not low:
            tk.Label(self.alert_box, text="All items are well stocked.", font=F_BODY,
                     bg=COLORS["white"], fg=COLORS["green"]).pack(anchor="w")
        for item in low[:8]:
            color = COLORS["red"] if item["stock"] == 0 else COLORS["amber"]
            text = (f"{item['name']}: OUT OF STOCK" if item["stock"] == 0
                    else f"{item['name']}: only {item['stock']} left")
            tk.Label(self.alert_box, text="• " + text, font=F_BOLD, bg=COLORS["white"],
                     fg=color).pack(anchor="w", pady=2)
        counts = self.db.count_by_status()
        waiting = counts["Received"] + counts["Preparing"] + counts["Ready"]
        self.kitchen_label.config(text=f"Orders in kitchen right now: {waiting}")


# ================================================================== Receipt window
def show_receipt(parent, order):
    """Pop-up window with the bill. Can also save it as a .txt file in receipts/."""
    win = tk.Toplevel(parent)
    win.title(f"Receipt {order['order_no']}")
    win.configure(bg=COLORS["white"])
    win.transient(parent.winfo_toplevel())
    tk.Label(win, text=f"Order {order['order_no']} placed! Sent to the kitchen.",
             font=F_BOLD, bg=COLORS["white"], fg=COLORS["green"]).pack(padx=14, pady=(12, 0))
    text = format_receipt(order)
    box = tk.Text(win, font=("Consolas", 11), width=44, height=text.count("\n") + 2,
                  bg=COLORS["cream"], relief="flat", padx=10, pady=10)
    box.insert("1.0", text)
    box.config(state="disabled")
    box.pack(padx=14, pady=10)

    def save():
        try:
            os.makedirs(RECEIPT_DIR, exist_ok=True)
            path = os.path.join(RECEIPT_DIR, f"{order['order_no']}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Saved", f"Receipt saved to:\n{path}", parent=win)
        except OSError as e:
            messagebox.showerror("Could not save", str(e), parent=win)

    row = tk.Frame(win, bg=COLORS["white"])
    row.pack(pady=(0, 14))
    make_button(row, "Save Receipt (.txt)", save, "secondary").pack(side="left", padx=6)
    make_button(row, "Close", win.destroy, "primary").pack(side="left", padx=6)
    win.update_idletasks()
    root = parent.winfo_toplevel()
    x = root.winfo_rootx() + max(0, (root.winfo_width() - win.winfo_width()) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - win.winfo_height()) // 2)
    win.geometry(f"+{x}+{y}")
    win.grab_set()
    return win


# =========================================================================== Billing
class BillingScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.cols = 3             # number of food cards per row (changes with window width)
        self.cart = {}            # item_id -> quantity
        self.coupon = None        # applied coupon code or None
        self._placing = False     # stops double-clicks creating two orders
        self.make_header("New Order", "Tap an item to add it to the cart")

        body = tk.Frame(self, bg=COLORS["cream"])
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        panel = card(body, width=390)
        panel.pack(side="right", fill="y", padx=(10, 6))
        panel.pack_propagate(False)
        self.menu_scroll = ScrollFrame(body)
        self.menu_scroll.pack(side="left", fill="both", expand=True)
        self.menu_scroll.canvas.bind("<Configure>", self._on_menu_resize, add="+")
        self._build_cart_panel(panel)

    # ---- cart panel -----------------------------------------------------
    def _build_cart_panel(self, panel):
        tk.Label(panel, text="Your Cart", font=F_HEAD, bg=COLORS["white"],
                 fg=COLORS["charcoal"]).pack(anchor="w", padx=14, pady=(10, 4))

        bottom = tk.Frame(panel, bg=COLORS["white"])
        bottom.pack(side="bottom", fill="x", padx=14, pady=(4, 12))

        tk.Label(bottom, text="Customer name (optional)", font=F_SMALL, bg=COLORS["white"],
                 fg=COLORS["gray"]).pack(anchor="w")
        self.name_var = tk.StringVar()
        tk.Entry(bottom, textvariable=self.name_var, font=F_BODY, relief="solid", bd=1).pack(fill="x", pady=(0, 6))

        tk.Label(bottom, text="Coupon code (try WELCOME10 or CHICKEN50)", font=F_SMALL,
                 bg=COLORS["white"], fg=COLORS["gray"]).pack(anchor="w")
        crow = tk.Frame(bottom, bg=COLORS["white"])
        crow.pack(fill="x")
        self.coupon_var = tk.StringVar()
        entry = tk.Entry(crow, textvariable=self.coupon_var, font=F_BODY, relief="solid", bd=1)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.apply_coupon_click())
        make_button(crow, "Apply", self.apply_coupon_click, "secondary", padx=10, pady=2).pack(side="left", padx=(6, 0))
        self.coupon_msg = tk.Label(bottom, text="", font=F_SMALL, bg=COLORS["white"],
                                   fg=COLORS["gray"], wraplength=350, justify="left")
        self.coupon_msg.pack(anchor="w", pady=(2, 4))

        self.sum_labels = {}
        for key, text in [("subtotal", "Subtotal"), ("discount", "Discount"),
                          ("gst", "GST"), ("total", "TOTAL")]:
            r = tk.Frame(bottom, bg=COLORS["white"])
            r.pack(fill="x")
            big = key == "total"
            left = tk.Label(r, text=text, font=F_HEAD if big else F_BODY, bg=COLORS["white"],
                            fg=COLORS["red"] if big else COLORS["charcoal"])
            left.pack(side="left")
            right = tk.Label(r, text="₹0.00", font=F_HEAD if big else F_BODY, bg=COLORS["white"],
                             fg=COLORS["red"] if big else COLORS["charcoal"])
            right.pack(side="right")
            self.sum_labels[key] = (left, right)
        self.place_btn = make_button(bottom, "Place Order", self.place_order, "success",
                                     font=(F_BOLD[0], 13, "bold"), pady=10)
        self.place_btn.pack(fill="x", pady=(8, 0))

        btns = tk.Frame(panel, bg=COLORS["white"])
        btns.pack(side="bottom", fill="x", padx=14)
        make_button(btns, "+", lambda: self.change_selected(+1), "light", padx=12, pady=2).pack(side="left")
        make_button(btns, "−", lambda: self.change_selected(-1), "light", padx=12, pady=2).pack(side="left", padx=4)
        make_button(btns, "Remove", self.remove_selected, "light", padx=8, pady=2).pack(side="left")
        make_button(btns, "Clear Cart", self.clear_cart, "danger", padx=8, pady=2).pack(side="right")

        wrap, self.tree = make_tree(panel, [
            ("item", "Item", 130, "w", True), ("qty", "Qty", 46, "center", False),
            ("price", "Price", 70, "e", False), ("total", "Total", 80, "e", False)], height=5)
        wrap.pack(fill="both", expand=True, padx=14, pady=4)

    # ---- menu cards ---------------------------------------------------------
    def on_show(self):
        self._clamp_cart()
        self._render_menu()
        self._refresh_cart()

    def _on_menu_resize(self, event):
        """Use 2, 3 or 4 cards per row so the cards never get squeezed."""
        cols = max(2, min(4, event.width // 185))
        if cols != self.cols:
            self.cols = cols
            self._render_menu()

    def _render_menu(self):
        inner = self.menu_scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        for c in range(6):
            inner.columnconfigure(c, weight=0, uniform="")
        for c in range(self.cols):
            inner.columnconfigure(c, weight=1, uniform="menu")
        items = self.db.get_menu()
        if not items:
            tk.Label(inner, text="The menu is empty. Add items in Menu Management.",
                     font=F_BODY, bg=COLORS["cream"]).grid(row=0, column=0, padx=20, pady=20)
        for n, item in enumerate(items):
            self._make_card(inner, item).grid(row=n // self.cols, column=n % self.cols,
                                              padx=8, pady=8, sticky="nsew")

    def _make_card(self, parent, item):
        f = card(parent)
        image_label(f, self.images, item["image"], item["emoji"], 100, COLORS["white"],
                    item["name"]).pack(pady=(12, 4))
        tk.Label(f, text=item["name"], font=F_BOLD, bg=COLORS["white"], fg=COLORS["charcoal"]).pack()
        tk.Label(f, text=rupees(item["price"]), font=F_HEAD, bg=COLORS["white"], fg=COLORS["red"]).pack()
        status = Database.stock_status(item)
        tk.Label(f, text=f"{status} ({item['stock']} left)", font=F_SMALL, bg=COLORS["white"],
                 fg=STATUS_COLORS[status]).pack()
        btn = make_button(f, "Add to Cart", lambda i=item["id"]: self.add_to_cart(i), "primary")
        if item["stock"] <= 0:
            btn.config(state="disabled", text="Out of Stock", bg=COLORS["gray"])
            btn._normal_bg = COLORS["gray"]
        btn.pack(fill="x", padx=12, pady=(6, 12))
        return f

    # ---- cart logic -----------------------------------------------------------
    def add_to_cart(self, item_id, amount=1):
        item = self.db.get_item(item_id)
        if item is None or not item["active"]:
            messagebox.showwarning("Not available", "This item is no longer on the menu.")
            self.on_show()
            return
        if item["stock"] <= 0:
            messagebox.showwarning("Out of stock", f"{item['name']} is out of stock.")
            return
        new_qty = self.cart.get(item_id, 0) + amount
        if new_qty > item["stock"]:
            messagebox.showwarning("Not enough stock",
                                   f"Only {item['stock']} x {item['name']} available.")
            return
        if new_qty <= 0:
            self.cart.pop(item_id, None)
        else:
            self.cart[item_id] = new_qty
        self._refresh_cart(select=item_id)

    def _selected_item(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def change_selected(self, delta):
        item_id = self._selected_item()
        if item_id is None:
            messagebox.showinfo("Select an item", "Click an item in the cart first.")
            return
        self.add_to_cart(item_id, delta)

    def remove_selected(self):
        item_id = self._selected_item()
        if item_id is None:
            messagebox.showinfo("Select an item", "Click an item in the cart first.")
            return
        self.cart.pop(item_id, None)
        self._refresh_cart()

    def clear_cart(self):
        self.cart.clear()
        self.coupon = None
        self.coupon_var.set("")
        self._refresh_cart()

    def _clamp_cart(self):
        """Fix the cart if stock changed (e.g. staff reduced stock)."""
        for item_id in list(self.cart):
            item = self.db.get_item(item_id)
            if item is None or not item["active"] or item["stock"] <= 0:
                del self.cart[item_id]
            elif self.cart[item_id] > item["stock"]:
                self.cart[item_id] = item["stock"]

    def _cart_subtotal(self):
        total = 0.0
        for item_id, qty in self.cart.items():
            item = self.db.get_item(item_id)
            if item is not None:
                total += item["price"] * qty
        return total

    def _refresh_cart(self, select=None):
        clear_tree(self.tree)
        subtotal = 0.0
        for item_id, qty in list(self.cart.items()):
            item = self.db.get_item(item_id)
            if item is None or not item["active"]:
                del self.cart[item_id]
                continue
            subtotal += item["price"] * qty
            self.tree.insert("", "end", iid=str(item_id), values=(
                item["name"], qty, f"{item['price']:.2f}", f"{item['price'] * qty:.2f}"))
        if select is not None and str(select) in self.tree.get_children():
            self.tree.selection_set(str(select))
        gst = self.db.get_gst_percent()
        note = ""
        try:
            bill = calculate_bill(subtotal, gst, self.coupon)
        except CouponError as e:          # e.g. items removed, coupon minimum no longer met
            note = f"Coupon removed: {e}"
            self.coupon = None
            self.coupon_var.set("")
            bill = calculate_bill(subtotal, gst, None)
        self.sum_labels["subtotal"][1].config(text=rupees(bill["subtotal"]))
        self.sum_labels["discount"][1].config(text="-" + rupees(bill["discount"]))
        self.sum_labels["gst"][0].config(text=f"GST ({gst:g}%)")
        self.sum_labels["gst"][1].config(text=rupees(bill["tax"]))
        self.sum_labels["total"][1].config(text=rupees(bill["total"]))
        if self.coupon:
            self.coupon_msg.config(text=f"✔ {self.coupon}: {COUPONS[self.coupon]['description']}",
                                   fg=COLORS["green"])
        else:
            self.coupon_msg.config(text=note, fg=COLORS["red"])

    def apply_coupon_click(self):
        code = self.coupon_var.get().strip().upper()
        if not code:
            self.coupon = None
            self._refresh_cart()
            return
        if not self.cart:
            messagebox.showinfo("Cart is empty", "Add items to the cart before applying a coupon.")
            return
        try:
            apply_coupon(code, self._cart_subtotal())
        except CouponError as e:
            self.coupon = None
            self._refresh_cart()
            self.coupon_msg.config(text=str(e), fg=COLORS["red"])
            return
        self.coupon = code
        self._refresh_cart()

    # ---- placing the order ------------------------------------------------------
    def place_order(self):
        if self._placing:
            return
        if not self.cart:
            messagebox.showwarning("Empty cart", "Your cart is empty. Add some items first.")
            return
        self._placing = True
        self.place_btn.config(state="disabled")
        try:
            order_id = self.db.place_order(dict(self.cart), self.name_var.get(), self.coupon)
        except StockError as e:
            messagebox.showwarning("Not enough stock", str(e))
            self.on_show()
        except DatabaseError as e:
            messagebox.showerror("Order failed", str(e))
        else:
            order = self.db.get_order(order_id)
            self.cart.clear()
            self.coupon = None
            self.coupon_var.set("")
            self.name_var.set("")
            self._render_menu()
            self._refresh_cart()
            show_receipt(self, order)
        finally:
            self._placing = False
            self.place_btn.config(state="normal")


# =========================================================================== Kitchen
class KitchenScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Kitchen Orders", "Received → Preparing → Ready → Completed")

        row = tk.Frame(self, bg=COLORS["cream"])
        row.pack(fill="x", padx=18)
        self.count_labels = {}
        colors = {"Received": COLORS["amber"], "Preparing": COLORS["red"],
                  "Ready": COLORS["green"], "Completed": COLORS["gray"]}
        for status in STATUSES:
            c = card(row)
            c.pack(side="left", fill="both", expand=True, padx=6)
            tk.Frame(c, bg=colors[status], height=4).pack(fill="x")
            tk.Label(c, text=status, font=F_BODY, bg=COLORS["white"], fg=COLORS["gray"]).pack(pady=(6, 0))
            lab = tk.Label(c, text="0", font=(F_BIG[0], 20, "bold"), bg=COLORS["white"])
            lab.pack(pady=(0, 6))
            self.count_labels[status] = lab

        panel = card(self)
        panel.pack(fill="both", expand=True, padx=24, pady=10)
        wrap, self.tree = make_tree(panel, [
            ("order", "Order No", 95, "center", False), ("time", "Order Time", 150, "center", False),
            ("items", "Items (qty x item)", 200, "w", True), ("total", "Total", 85, "e", False),
            ("status", "Status", 100, "center", False)], height=10)
        wrap.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.tag_configure("Received", background="#FFF3CD")
        self.tree.tag_configure("Preparing", background="#FFE0D6")
        self.tree.tag_configure("Ready", background="#D9F2E3")
        self.tree.tag_configure("Completed", background="#EEEEEE")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_button())

        bar = tk.Frame(self, bg=COLORS["cream"])
        bar.pack(fill="x", padx=24, pady=(0, 14))
        self.advance_btn = make_button(bar, "Select an order", self.advance, "success",
                                       font=(F_BOLD[0], 12, "bold"), pady=8)
        self.advance_btn.pack(side="left")
        make_button(bar, "Refresh", self.refresh, "secondary").pack(side="left", padx=8)
        self.show_done = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Show completed orders", variable=self.show_done, bg=COLORS["cream"],
                       font=F_BODY, command=self.refresh, activebackground=COLORS["cream"]).pack(side="left", padx=10)
        self._update_button()

    def on_show(self):
        self.refresh()

    def refresh(self):
        selected = self.tree.selection()
        clear_tree(self.tree)
        for r in self.db.get_kitchen_orders(self.show_done.get()):
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["status"],), values=(
                r["order_no"], r["created_at"], r["items_text"], f"₹{r['total']:.2f}", r["status"]))
        if selected and selected[0] in self.tree.get_children():
            self.tree.selection_set(selected[0])
        counts = self.db.count_by_status()
        for status, lab in self.count_labels.items():
            lab.config(text=str(counts[status]))
        self._update_button()

    def _update_button(self):
        sel = self.tree.selection()
        if not sel:
            self.advance_btn.config(text="Select an order", state="disabled", bg=COLORS["gray"])
            self.advance_btn._normal_bg = COLORS["gray"]
            return
        status = self.tree.set(sel[0], "status")
        if status == STATUSES[-1]:
            self.advance_btn.config(text="Order completed", state="disabled", bg=COLORS["gray"])
            self.advance_btn._normal_bg = COLORS["gray"]
        else:
            nxt = STATUSES[STATUSES.index(status) + 1]
            self.advance_btn.config(text=f"Mark as {nxt}  →", state="normal", bg=COLORS["green"])
            self.advance_btn._normal_bg = COLORS["green"]

    def advance(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select an order", "Click an order in the table first.")
            return
        order_id = int(sel[0])
        try:
            self.db.advance_order_status(order_id)
        except DatabaseError as e:
            messagebox.showwarning("Cannot update", str(e))
        self.refresh()


# ========================================================================= Inventory
class InventoryScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Inventory", "Ready-to-sell stock of each menu item")
        tk.Label(self, text="This is FINISHED food stock used by billing. The cooking game uses "
                 "pretend ingredients and never changes this stock.", font=F_SMALL,
                 bg=COLORS["cream"], fg=COLORS["gray"]).pack(anchor="w", padx=24)

        panel = card(self)
        panel.pack(fill="both", expand=True, padx=24, pady=10)
        wrap, self.tree = make_tree(panel, [
            ("name", "Item", 200, "w", True), ("category", "Category", 110, "w", False),
            ("price", "Price", 90, "e", False), ("stock", "Stock", 80, "center", False),
            ("low", "Low level", 100, "center", False), ("status", "Status", 120, "center", False)],
            height=10)
        wrap.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.tag_configure("Low Stock", background="#FFF3CD")
        self.tree.tag_configure("Out of Stock", background="#FADBD8")
        self.tree.tag_configure("Inactive", foreground="#999999")

        bar = tk.Frame(self, bg=COLORS["cream"])
        bar.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(bar, text="Quantity:", font=F_BOLD, bg=COLORS["cream"]).pack(side="left")
        self.qty_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.qty_var, width=8, font=F_BODY, relief="solid", bd=1).pack(side="left", padx=6)
        make_button(bar, "Set Stock To", lambda: self.apply("set"), "primary").pack(side="left", padx=4)
        make_button(bar, "Add Stock", lambda: self.apply("add"), "success").pack(side="left", padx=4)
        make_button(bar, "Remove Stock", lambda: self.apply("remove"), "secondary").pack(side="left", padx=4)
        tk.Label(bar, text="(staff PIN needed)", font=F_SMALL, bg=COLORS["cream"],
                 fg=COLORS["gray"]).pack(side="left", padx=8)

    def on_show(self):
        self.refresh()

    def refresh(self):
        selected = self.tree.selection()
        clear_tree(self.tree)
        for item in self.db.get_menu(include_inactive=True):
            status = Database.stock_status(item)
            self.tree.insert("", "end", iid=str(item["id"]), tags=(status,), values=(
                item["name"], item["category"], f"₹{item['price']:.2f}", item["stock"],
                item["low_stock_level"], status))
        if selected and selected[0] in self.tree.get_children():
            self.tree.selection_set(selected[0])

    def apply(self, mode):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select an item", "Click an item in the table first.")
            return
        try:
            qty = int(self.qty_var.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid quantity", "Please type a whole number, e.g. 10.")
            return
        if qty < 0 or (mode != "set" and qty == 0):
            messagebox.showwarning("Invalid quantity",
                                   "Quantity cannot be negative" + ("." if mode == "set" else " or zero."))
            return
        if not self.app.require_staff():
            return
        item_id = int(sel[0])
        try:
            if mode == "set":
                self.db.set_stock(item_id, qty)
            elif mode == "add":
                self.db.change_stock(item_id, qty)
            else:
                self.db.change_stock(item_id, -qty)
        except DatabaseError as e:
            messagebox.showwarning("Cannot change stock", str(e))
            return
        self.qty_var.set("")
        self.refresh()


# ===================================================================== Menu management
class MenuManagementScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Menu Management", "Add items, change prices, hide items, set GST")
        body = tk.Frame(self, bg=COLORS["cream"])
        body.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        left = card(body)
        left.pack(side="left", fill="both", expand=True)
        wrap, self.tree = make_tree(left, [
            ("name", "Item", 130, "w", True), ("category", "Category", 100, "w", False),
            ("price", "Price", 80, "e", False), ("stock", "Stock", 65, "center", False),
            ("active", "On Menu", 85, "center", False)], height=10)
        wrap.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._load_form())

        right = card(body, width=320)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)
        tk.Label(right, text="Item Details", font=F_HEAD, bg=COLORS["white"]).pack(anchor="w", padx=14, pady=(10, 4))
        self.vars = {k: tk.StringVar() for k in ("name", "category", "price", "stock", "low", "image")}
        self.active_var = tk.BooleanVar(value=True)
        for key, label in [("name", "Name"), ("category", "Category"), ("price", "Price (₹)"),
                           ("stock", "Starting stock (new items only)"), ("low", "Low-stock level"),
                           ("image", "Image file in assets/images (optional)")]:
            tk.Label(right, text=label, font=F_SMALL, bg=COLORS["white"], fg=COLORS["gray"]).pack(anchor="w", padx=14)
            if key == "category":
                w = ttk.Combobox(right, textvariable=self.vars[key], values=CATEGORIES, font=F_BODY)
            else:
                w = tk.Entry(right, textvariable=self.vars[key], font=F_BODY, relief="solid", bd=1)
            w.pack(fill="x", padx=14, pady=(0, 4))
        tk.Checkbutton(right, text="Show this item on the menu", variable=self.active_var,
                       bg=COLORS["white"], font=F_BODY, activebackground=COLORS["white"]).pack(anchor="w", padx=12)
        row = tk.Frame(right, bg=COLORS["white"])
        row.pack(fill="x", padx=14, pady=6)
        make_button(row, "Add New", self.add_item, "success", padx=8, pady=4).pack(side="left")
        make_button(row, "Update", self.update_item, "primary", padx=8, pady=4).pack(side="left", padx=4)
        make_button(row, "Clear", self.clear_form, "light", padx=8, pady=4).pack(side="left")

        tk.Frame(right, bg=COLORS["light_gray"], height=1).pack(fill="x", padx=14, pady=6)
        grow = tk.Frame(right, bg=COLORS["white"])
        grow.pack(fill="x", padx=14)
        tk.Label(grow, text="GST %", font=F_BOLD, bg=COLORS["white"]).pack(side="left")
        self.gst_var = tk.StringVar()
        tk.Entry(grow, textvariable=self.gst_var, width=6, font=F_BODY, relief="solid", bd=1).pack(side="left", padx=6)
        make_button(grow, "Save GST", self.save_gst, "secondary", padx=8, pady=2).pack(side="left")
        make_button(right, "Reset Demo Data…", self.reset_demo, "danger", pady=4).pack(fill="x", padx=14, pady=10)

    def on_show(self):
        self.refresh()
        self.gst_var.set(f"{self.db.get_gst_percent():g}")

    def refresh(self):
        selected = self.tree.selection()
        clear_tree(self.tree)
        for item in self.db.get_menu(include_inactive=True):
            self.tree.insert("", "end", iid=str(item["id"]), values=(
                item["name"], item["category"], f"₹{item['price']:.2f}", item["stock"],
                "Yes" if item["active"] else "No"))
        if selected and selected[0] in self.tree.get_children():
            self.tree.selection_set(selected[0])

    def _load_form(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.db.get_item(int(sel[0]))
        if item is None:
            return
        self.vars["name"].set(item["name"])
        self.vars["category"].set(item["category"])
        self.vars["price"].set(f"{item['price']:g}")
        self.vars["stock"].set(str(item["stock"]))
        self.vars["low"].set(str(item["low_stock_level"]))
        self.vars["image"].set(item["image"] or "")
        self.active_var.set(bool(item["active"]))

    def clear_form(self):
        for v in self.vars.values():
            v.set("")
        self.active_var.set(True)
        self.tree.selection_remove(self.tree.selection())

    def add_item(self):
        if not self.app.require_staff():
            return
        category = self.vars["category"].get().strip() or "General"
        try:
            self.db.add_menu_item(self.vars["name"].get(), category, self.vars["price"].get(),
                                  self.vars["stock"].get() or 0, self.vars["low"].get() or 5,
                                  image=self.vars["image"].get().strip() or None,
                                  emoji=EMOJI_BY_CATEGORY.get(category, "🍽"))
        except DatabaseError as e:
            messagebox.showwarning("Cannot add item", str(e))
            return
        messagebox.showinfo("Added", "New menu item added.")
        self.clear_form()
        self.refresh()

    def update_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select an item", "Click an item in the table first.")
            return
        if not self.app.require_staff():
            return
        try:
            self.db.update_menu_item(int(sel[0]), self.vars["name"].get(),
                                     self.vars["category"].get(), self.vars["price"].get(),
                                     self.vars["low"].get() or 5, self.active_var.get(),
                                     image=self.vars["image"].get().strip() or None)
        except DatabaseError as e:
            messagebox.showwarning("Cannot update item", str(e))
            return
        messagebox.showinfo("Updated", "Menu item updated.")
        self.refresh()

    def save_gst(self):
        if not self.app.require_staff():
            return
        try:
            self.db.set_gst_percent(self.gst_var.get())
        except DatabaseError as e:
            messagebox.showwarning("Invalid GST", str(e))
            return
        messagebox.showinfo("Saved", "GST percentage saved.")

    def reset_demo(self):
        if not messagebox.askyesno(
                "Reset demo data?",
                "This will DELETE all orders and game scores and restore the sample menu.\n\n"
                "This cannot be undone. Continue?", icon="warning"):
            return
        if not self.app.require_staff():
            return
        try:
            self.db.reset_demo_data()
        except DatabaseError as e:
            messagebox.showerror("Reset failed", str(e))
            return
        self.app.screens["billing"].cart.clear()
        self.refresh()
        messagebox.showinfo("Done", "Demo data has been restored.")


# ========================================================================== Analytics
class AnalyticsScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Sales Analytics", "Live numbers from the SQLite database")
        self._chart_data = []
        row = tk.Frame(self, bg=COLORS["cream"])
        row.pack(fill="x", padx=18)
        self.tiles = {}
        for key, title in [("orders", "Total Orders"), ("revenue", "Total Revenue"),
                           ("popular", "Most Popular Item"), ("score", "Game High Score")]:
            c = card(row)
            c.pack(side="left", fill="both", expand=True, padx=6)
            tk.Label(c, text=title, font=F_BODY, bg=COLORS["white"], fg=COLORS["gray"]).pack(anchor="w", padx=12, pady=(8, 0))
            lab = tk.Label(c, text="-", font=(F_BIG[0], 17, "bold"), bg=COLORS["white"], fg=COLORS["red"])
            lab.pack(anchor="w", padx=12, pady=(0, 8))
            self.tiles[key] = lab

        lower = tk.Frame(self, bg=COLORS["cream"])
        lower.pack(fill="both", expand=True, padx=18, pady=10)
        chart_card = card(lower)
        chart_card.pack(side="left", fill="both", expand=True, padx=6)
        tk.Label(chart_card, text="Revenue – last 7 days (₹)", font=F_BOLD, bg=COLORS["white"]).pack(anchor="w", padx=12, pady=(8, 0))
        self.chart = tk.Canvas(chart_card, bg=COLORS["white"], highlightthickness=0, height=240)
        self.chart.pack(fill="both", expand=True, padx=8, pady=8)
        self.chart.bind("<Configure>", lambda e: self._draw_chart())

        table_card = card(lower, width=330)
        table_card.pack(side="right", fill="y", padx=6)
        table_card.pack_propagate(False)
        tk.Label(table_card, text="Daily Sales Summary", font=F_BOLD, bg=COLORS["white"]).pack(anchor="w", padx=12, pady=(8, 0))
        wrap, self.tree = make_tree(table_card, [
            ("date", "Date", 100, "center", False), ("orders", "Orders", 80, "center", False),
            ("revenue", "Revenue", 110, "e", True)], height=8)
        wrap.pack(fill="both", expand=True, padx=8, pady=8)

    def on_show(self):
        self.tiles["orders"].config(text=str(self.db.total_orders()))
        self.tiles["revenue"].config(text=rupees(self.db.total_revenue()))
        pop = self.db.popular_item()
        self.tiles["popular"].config(text=f"{pop[0]} ({pop[1]} sold)" if pop else "No orders yet")
        self.tiles["score"].config(text=str(self.db.high_score()))
        self._chart_data = self.db.daily_sales(7)
        clear_tree(self.tree)
        for d, n, rev in reversed(self._chart_data):       # newest day first
            self.tree.insert("", "end", values=(d[5:], n, rupees(rev)))
        self._draw_chart()

    def _draw_chart(self):
        c = self.chart
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 100 or h < 100:
            return
        data = self._chart_data
        if not data or all(rev == 0 for _, _, rev in data):
            c.create_text(w / 2, h / 2, text="No sales in the last 7 days.\nPlace an order to see the chart.",
                          font=F_BODY, fill=COLORS["gray"], justify="center")
            return
        left, right, top, bottom = 58, 14, 18, 28
        plot_h = h - top - bottom
        max_v = max(rev for _, _, rev in data)
        for i in range(5):                                  # grid lines
            y = top + plot_h * i / 4
            c.create_line(left, y, w - right, y, fill=COLORS["light_gray"])
            c.create_text(left - 6, y, text=f"{max_v * (4 - i) / 4:,.0f}", anchor="e",
                          font=F_SMALL, fill=COLORS["gray"])
        slot = (w - left - right) / len(data)
        for i, (d, _, rev) in enumerate(data):
            x0, x1 = left + i * slot + slot * 0.2, left + (i + 1) * slot - slot * 0.2
            y1 = top + plot_h
            y0 = y1 - plot_h * rev / max_v
            if rev > 0:
                c.create_rectangle(x0, y0, x1, y1, fill=COLORS["red"], outline="")
                c.create_text((x0 + x1) / 2, y0 - 8, text=f"{rev:,.0f}", font=F_SMALL, fill=COLORS["charcoal"])
            c.create_text((x0 + x1) / 2, y1 + 12, text=d[5:], font=F_SMALL, fill=COLORS["gray"])


# ======================================================================== Leaderboard
class LeaderboardScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.make_header("Game Leaderboard", "Top 10 scores from the Cooking Game")
        panel = card(self)
        panel.pack(fill="both", expand=True, padx=24, pady=10)
        wrap, self.tree = make_tree(panel, [
            ("rank", "Rank", 60, "center", False), ("player", "Player", 150, "w", True),
            ("score", "Score", 90, "center", False), ("coins", "Coins", 90, "center", False),
            ("served", "Served", 90, "center", False),
            ("date", "Date & Time", 190, "center", False)], height=10)
        wrap.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.tag_configure("r1", background=COLORS["gold"])
        self.tree.tag_configure("r2", background=COLORS["silver"])
        self.tree.tag_configure("r3", background=COLORS["bronze"])
        bar = tk.Frame(self, bg=COLORS["cream"])
        bar.pack(fill="x", padx=24, pady=(0, 14))
        make_button(bar, "Play the Cooking Game", lambda: self.app.show_screen("game"), "success").pack(side="left")
        make_button(bar, "Refresh", self.on_show, "secondary").pack(side="left", padx=8)
        self.coins_label = tk.Label(bar, text="", font=F_BOLD, bg=COLORS["cream"], fg=COLORS["charcoal"])
        self.coins_label.pack(side="right")

    def on_show(self):
        clear_tree(self.tree)
        rows = self.db.get_leaderboard(10)
        for rank, r in enumerate(rows, start=1):
            tag = (f"r{rank}",) if rank <= 3 else ()
            self.tree.insert("", "end", tags=tag, values=(
                rank, r["player_name"], r["score"], r["coins"], r["customers_served"], r["played_at"]))
        self.coins_label.config(text=f"Total coins earned in all games: {self.db.total_coins()}")
