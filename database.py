"""
database.py - ALL SQLite code lives here (no Tkinter in this file).

Tables:
  settings     - small key/value settings (GST %, staff PIN)
  menu_items   - food items with price and READY-TO-SELL stock
  orders       - one row per bill (status: Received -> Preparing -> Ready -> Completed)
  order_items  - the items inside each order
  game_scores  - cooking game scores (separate from restaurant stock)
"""
import os
import sqlite3
from datetime import datetime, timedelta

from billing import calculate_bill, CouponError, DEFAULT_GST_PERCENT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "chicken_hub.db")

STATUSES = ["Received", "Preparing", "Ready", "Completed"]
DEFAULT_PIN = "1234"

# name, category, price, stock, low-stock level, image file, emoji fallback
SEED_MENU = [
    ("Chicken Burger", "Burgers", 149, 30, 8, "burger.png", "🍔"),
    ("Cheese Burger", "Burgers", 169, 25, 8, "cheese_burger.png", "🍔"),
    ("French Fries", "Sides", 89, 40, 10, "fries.png", "🍟"),
    ("Chicken Nuggets", "Sides", 119, 30, 8, "nuggets.png", "🍗"),
    ("Chicken Bucket", "Buckets", 399, 15, 5, "bucket.png", "🍗"),
    ("Chicken Wrap", "Wraps", 129, 25, 8, "wrap.png", "🌯"),
    ("Cold Drink", "Drinks", 59, 50, 10, "drink.png", "🥤"),
    ("Ice Cream Sundae", "Desserts", 79, 20, 6, "icecream.png", "🍨"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS menu_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL DEFAULT 'General',
    price           REAL NOT NULL CHECK (price >= 0),
    stock           INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    low_stock_level INTEGER NOT NULL DEFAULT 5 CHECK (low_stock_level >= 0),
    image           TEXT,
    emoji           TEXT DEFAULT '🍽',
    active          INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no      TEXT UNIQUE,
    customer_name TEXT,
    created_at    TEXT NOT NULL,
    subtotal      REAL NOT NULL,
    discount      REAL NOT NULL DEFAULT 0,
    gst_percent   REAL NOT NULL DEFAULT 5,
    tax           REAL NOT NULL,
    total         REAL NOT NULL,
    coupon_code   TEXT,
    status        TEXT NOT NULL DEFAULT 'Received'
                  CHECK (status IN ('Received','Preparing','Ready','Completed'))
);
CREATE TABLE IF NOT EXISTS order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id    INTEGER NOT NULL REFERENCES menu_items(id),
    item_name  TEXT NOT NULL,
    unit_price REAL NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0)
);
CREATE TABLE IF NOT EXISTS game_scores (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name      TEXT NOT NULL,
    score            INTEGER NOT NULL CHECK (score >= 0),
    coins            INTEGER NOT NULL CHECK (coins >= 0),
    customers_served INTEGER NOT NULL DEFAULT 0,
    played_at        TEXT NOT NULL
);
"""


class DatabaseError(Exception):
    """Any database problem (the message is safe to show to the user)."""


class ValidationError(DatabaseError):
    """User gave wrong input (negative stock, empty name, ...)."""


class StockError(DatabaseError):
    """Not enough stock to complete the order."""


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row            # access columns by name
            self.conn.execute("PRAGMA foreign_keys = ON")   # enforce foreign keys
            self.conn.executescript(SCHEMA)                 # create tables on first launch
            self._seed_if_empty()
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not open the database: {e}")

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # ------------------------------------------------------------------ setup
    def _seed_if_empty(self):
        """Add sample data ONLY when the tables are empty (never deletes user data)."""
        with self.conn:
            if self.conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 0:
                self._insert_seed_menu()
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('gst_percent', ?)",
                              (str(DEFAULT_GST_PERCENT),))
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('staff_pin', ?)",
                              (DEFAULT_PIN,))

    def _insert_seed_menu(self):
        self.conn.executemany(
            "INSERT INTO menu_items (name, category, price, stock, low_stock_level, image, emoji)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)", SEED_MENU)

    def reset_demo_data(self):
        """Delete orders/scores and restore the sample menu. (The UI asks for confirmation first.)"""
        try:
            with self.conn:   # one transaction: all or nothing
                self.conn.execute("DELETE FROM order_items")
                self.conn.execute("DELETE FROM orders")
                self.conn.execute("DELETE FROM game_scores")
                self.conn.execute("DELETE FROM menu_items")
                self.conn.execute("DELETE FROM sqlite_sequence")
                self._insert_seed_menu()
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not reset demo data: {e}")

    # --------------------------------------------------------------- settings
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                              (key, str(value)))

    def get_gst_percent(self):
        try:
            return float(self.get_setting("gst_percent", DEFAULT_GST_PERCENT))
        except ValueError:
            return DEFAULT_GST_PERCENT

    def set_gst_percent(self, percent):
        try:
            percent = float(percent)
        except (TypeError, ValueError):
            raise ValidationError("GST must be a number.")
        if percent < 0 or percent > 100:
            raise ValidationError("GST must be between 0 and 100.")
        self.set_setting("gst_percent", percent)

    def verify_pin(self, pin):
        return str(pin) == self.get_setting("staff_pin", DEFAULT_PIN)

    # ------------------------------------------------------------------- menu
    def get_menu(self, include_inactive=False):
        sql = "SELECT * FROM menu_items"
        if not include_inactive:
            sql += " WHERE active = 1"
        return self.conn.execute(sql + " ORDER BY id").fetchall()

    def get_item(self, item_id):
        return self.conn.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()

    @staticmethod
    def _clean_item_fields(name, category, price, stock, low_level):
        name = (name or "").strip()
        category = (category or "").strip() or "General"
        if not name:
            raise ValidationError("Item name cannot be empty.")
        if len(name) > 40:
            raise ValidationError("Item name is too long (max 40 characters).")
        try:
            price = float(price)
            stock = int(stock)
            low_level = int(low_level)
        except (TypeError, ValueError):
            raise ValidationError("Price must be a number; stock and low-stock level "
                                  "must be whole numbers.")
        if price < 0 or stock < 0 or low_level < 0:
            raise ValidationError("Price, stock and low-stock level cannot be negative.")
        return name, category, round(price, 2), stock, low_level

    def add_menu_item(self, name, category, price, stock, low_level=5, image=None, emoji="🍽"):
        name, category, price, stock, low_level = self._clean_item_fields(
            name, category, price, stock, low_level)
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO menu_items (name, category, price, stock, low_stock_level, image, emoji)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, category, price, stock, low_level, image or None, emoji or "🍽"))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError(f"An item named '{name}' already exists.")
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not add item: {e}")

    def update_menu_item(self, item_id, name, category, price, low_level, active, image=None):
        item = self.get_item(item_id)
        if item is None:
            raise ValidationError("That menu item no longer exists.")
        name, category, price, _, low_level = self._clean_item_fields(
            name, category, price, item["stock"], low_level)
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE menu_items SET name=?, category=?, price=?, low_stock_level=?, active=?,"
                    " image=COALESCE(?, image) WHERE id=?",
                    (name, category, price, low_level, 1 if active else 0, image or None, item_id))
        except sqlite3.IntegrityError:
            raise ValidationError(f"An item named '{name}' already exists.")
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not update item: {e}")

    # -------------------------------------------------------------- inventory
    def set_stock(self, item_id, new_stock):
        """Set stock to an exact number (must be a whole number >= 0)."""
        try:
            new_stock = int(new_stock)
        except (TypeError, ValueError):
            raise ValidationError("Stock must be a whole number.")
        if new_stock < 0:
            raise ValidationError("Stock cannot be negative.")
        if self.get_item(item_id) is None:
            raise ValidationError("That menu item no longer exists.")
        try:
            with self.conn:
                self.conn.execute("UPDATE menu_items SET stock = ? WHERE id = ?",
                                  (new_stock, item_id))
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not update stock: {e}")

    def change_stock(self, item_id, delta):
        """Add (positive) or remove (negative) stock. Result can never go below 0."""
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            raise ValidationError("Quantity must be a whole number.")
        item = self.get_item(item_id)
        if item is None:
            raise ValidationError("That menu item no longer exists.")
        if item["stock"] + delta < 0:
            raise ValidationError(f"Cannot remove {-delta}. Only {item['stock']} in stock.")
        self.set_stock(item_id, item["stock"] + delta)

    def low_stock_items(self):
        return self.conn.execute(
            "SELECT * FROM menu_items WHERE active = 1 AND stock <= low_stock_level "
            "ORDER BY stock, name").fetchall()

    @staticmethod
    def stock_status(item):
        if not item["active"]:
            return "Inactive"
        if item["stock"] == 0:
            return "Out of Stock"
        if item["stock"] <= item["low_stock_level"]:
            return "Low Stock"
        return "In Stock"

    # ---------------------------------------------------------------- orders
    def place_order(self, cart, customer_name="", coupon_code=None):
        """
        Save an order and reduce stock in ONE transaction.
        cart = {item_id: quantity}. Returns the new order id.
        If anything fails, nothing is saved and stock is unchanged (automatic rollback).
        """
        if not cart:
            raise ValidationError("Cart is empty. Add some items first.")
        for qty in cart.values():
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise ValidationError("Quantities must be whole numbers greater than 0.")
        customer_name = (customer_name or "").strip()[:30]
        gst = self.get_gst_percent()
        try:
            with self.conn:   # commits on success, rolls back on any exception
                lines = []
                subtotal = 0.0
                for item_id, qty in cart.items():
                    item = self.get_item(item_id)
                    if item is None or not item["active"]:
                        raise ValidationError("An item in your cart is no longer on the menu.")
                    # Guarded update: only reduces stock if enough is available.
                    cur = self.conn.execute(
                        "UPDATE menu_items SET stock = stock - ? WHERE id = ? AND stock >= ?",
                        (qty, item_id, qty))
                    if cur.rowcount == 0:
                        raise StockError(f"Not enough stock for {item['name']}. "
                                         f"Only {item['stock']} left.")
                    lines.append((item_id, item["name"], item["price"], qty))
                    subtotal += item["price"] * qty
                try:
                    bill = calculate_bill(subtotal, gst, coupon_code)
                except CouponError as e:
                    raise ValidationError(str(e))
                cur = self.conn.execute(
                    "INSERT INTO orders (customer_name, created_at, subtotal, discount, gst_percent,"
                    " tax, total, coupon_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Received')",
                    (customer_name, now_text(), bill["subtotal"], bill["discount"], gst,
                     bill["tax"], bill["total"], bill["coupon_code"]))
                order_id = cur.lastrowid
                self.conn.execute("UPDATE orders SET order_no = ? WHERE id = ?",
                                  (f"CH-{order_id:05d}", order_id))
                self.conn.executemany(
                    "INSERT INTO order_items (order_id, item_id, item_name, unit_price, quantity)"
                    " VALUES (?, ?, ?, ?, ?)",
                    [(order_id, i, n, p, q) for (i, n, p, q) in lines])
            return order_id
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not save the order: {e}")

    def get_order(self, order_id):
        """Return an order as a dict with an 'items' list (or None)."""
        row = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return None
        order = dict(row)
        order["items"] = [dict(r) for r in self.conn.execute(
            "SELECT item_name, unit_price, quantity FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,))]
        return order

    def get_kitchen_orders(self, include_completed=False):
        """Orders for the kitchen table, oldest first, with an item summary text."""
        sql = ("SELECT o.id, o.order_no, o.created_at, o.status, o.total, "
               "(SELECT GROUP_CONCAT(quantity || ' x ' || item_name, ', ') FROM order_items "
               " WHERE order_id = o.id) AS items_text FROM orders o ")
        if not include_completed:
            sql += "WHERE o.status != 'Completed' "
        return self.conn.execute(sql + "ORDER BY o.id").fetchall()

    def advance_order_status(self, order_id):
        """Move an order one step forward. Returns the new status."""
        row = self.conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise ValidationError("Order not found.")
        current = row["status"]
        if current == STATUSES[-1]:
            raise ValidationError("This order is already Completed.")
        new_status = STATUSES[STATUSES.index(current) + 1]
        try:
            with self.conn:
                self.conn.execute("UPDATE orders SET status = ? WHERE id = ? AND status = ?",
                                  (new_status, order_id, current))
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not update status: {e}")
        return new_status

    def count_by_status(self):
        counts = {s: 0 for s in STATUSES}
        for r in self.conn.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status"):
            counts[r["status"]] = r["n"]
        return counts

    # ------------------------------------------------------------- analytics
    def total_orders(self):
        return self.conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    def total_revenue(self):
        return self.conn.execute("SELECT COALESCE(SUM(total), 0) FROM orders").fetchone()[0]

    def popular_item(self):
        """Return (item_name, total_quantity) or None when there are no orders."""
        row = self.conn.execute(
            "SELECT item_name, SUM(quantity) AS q FROM order_items "
            "GROUP BY item_name ORDER BY q DESC, item_name LIMIT 1").fetchone()
        return (row["item_name"], row["q"]) if row else None

    def daily_sales(self, days=7):
        """Last `days` days as [(date_text, order_count, revenue)], oldest first (zeros included)."""
        start = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        found = {r["d"]: (r["n"], r["rev"]) for r in self.conn.execute(
            "SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS n, SUM(total) AS rev "
            "FROM orders WHERE substr(created_at, 1, 10) >= ? GROUP BY d", (start,))}
        result = []
        for i in range(days - 1, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            n, rev = found.get(d, (0, 0))
            result.append((d, n, rev or 0))
        return result

    # ------------------------------------------------------------ game scores
    def save_score(self, player_name, score, coins, customers_served=0):
        player_name = (player_name or "").strip()[:20] or "Player"
        try:
            score, coins, customers_served = int(score), int(coins), int(customers_served)
        except (TypeError, ValueError):
            raise ValidationError("Score and coins must be whole numbers.")
        if score < 0 or coins < 0 or customers_served < 0:
            raise ValidationError("Score and coins cannot be negative.")
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO game_scores (player_name, score, coins, customers_served, played_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (player_name, score, coins, customers_served, now_text()))
            return cur.lastrowid
        except sqlite3.Error as e:
            raise DatabaseError(f"Could not save the score: {e}")

    def get_leaderboard(self, limit=10):
        """Highest score first; if scores are equal the earlier one ranks higher."""
        return self.conn.execute(
            "SELECT * FROM game_scores ORDER BY score DESC, played_at ASC, id ASC LIMIT ?",
            (limit,)).fetchall()

    def high_score(self):
        return self.conn.execute("SELECT COALESCE(MAX(score), 0) FROM game_scores").fetchone()[0]

    def total_coins(self):
        return self.conn.execute("SELECT COALESCE(SUM(coins), 0) FROM game_scores").fetchone()[0]
