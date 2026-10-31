# Chicken Hub – Restaurant Management & Cooking Simulation

A desktop BCA mini project built with **Python 3, Tkinter and SQLite** (Pillow for pictures).
It works fully **offline**. It is a college project and is **not connected to any real restaurant brand**.

## Features
- **Dashboard** – total orders, total revenue, items available, game high score, low-stock alerts (all from SQLite)
- **New Order / Billing** – image cards, cart (+ / − / remove / clear), subtotal, configurable GST, coupons
  (`WELCOME10` = 10% off ₹200+, `CHICKEN50` = ₹50 off ₹400+), printable receipt with order number (can be saved as .txt)
- **Kitchen tracking** – Received → Preparing → Ready → Completed, saved in SQLite, same orders as billing
- **Inventory** – stock table, low-stock highlight, set/add/remove stock (staff PIN **1234**), validation
- **Menu Management** – add items, change price, hide items, change GST %, "Reset Demo Data" (with confirmation)
- **Sales Analytics** – orders, revenue, most popular item, daily summary, 7-day bar chart (drawn with Tk Canvas, no Matplotlib needed), game high score
- **Cooking & Serving Game** – customer orders with pictures, cooking steps, stations, progress bar, countdown timer,
  score + coins, Serve / Next Customer / End Game, 3 missed customers = game over
- **Leaderboard** – top 10 scores (player name, score, coins, date/time), highest first

## Folder structure
```
ChickenHub/
├── main.py              <- RUN THIS (window, sidebar, navigation)
├── database.py          <- all SQLite code (tables, orders, stock, scores)
├── billing.py           <- bill maths, coupon rules, receipt text
├── game.py              <- cooking game RULES (no Tkinter)
├── game_screen.py       <- cooking game WINDOW
├── screens.py           <- dashboard, billing, kitchen, inventory, menu, analytics, leaderboard
├── styles.py            <- colours, fonts, buttons, image loading with fallbacks
├── generate_assets.py   <- redraws the food pictures (only needed if images are missing)
├── requirements.txt
├── assets/images/       <- burger, fries, drink, bucket, wrap, ice cream, nuggets, logo (PNG)
├── data/                <- chicken_hub.db is created here on first run
├── receipts/            <- saved receipts (.txt)
├── tests/               <- test_core.py, gui_smoke_test.py, gui_fallback_test.py
└── docs/                <- TESTING_REPORT.md, VIVA_AND_EXPLANATION.md
```

## Run on Windows with PyCharm (Hinglish)
1. Python 3.9+ install karo (python.org). Install karte time **"Add Python to PATH"** tick karna. Tkinter Python ke saath hi aata hai.
2. ZIP ko **Extract All** karo (zip ke andar se mat chalao). Folder ka naam `ChickenHub`.
3. PyCharm kholo → **File → Open** → `ChickenHub` folder select karo.
4. **File → Settings → Project → Python Interpreter** me Python 3 select karo (naya `.venv` bana sakte ho).
5. PyCharm ke neeche **Terminal** kholo aur likho: `pip install -r requirements.txt`
6. `main.py` pe right-click → **Run 'main'**. Window khul jayegi, database apne aap ban jayega.
7. Tests chalane ke liye Terminal me: `python -m unittest discover -s tests -v`
   (GUI test: `python tests/gui_smoke_test.py` – ye window kholkar buttons ko code se dabata hai.)

Extra: agar images gayab ho jayein to `python generate_assets.py` chalao, ya app khud placeholder/emoji dikha dega.

## Rules in short
- **Billing:** discount is taken from the subtotal first, GST is charged on the discounted amount.
  Stock is reduced only when the order is saved successfully (one SQLite transaction). Not enough stock = nothing is saved.
- **Game points:** `max(10, 50 × dishes + seconds left − 5 × mistakes)`; `coins = points ÷ 10`.
  The game never changes restaurant stock. Score is saved only if at least one customer was served.
- **Staff PIN** (inventory/menu changes): `1234` (asked once per session).

## Troubleshooting
| Problem | Fix |
|---|---|
| `No module named 'PIL'` | Terminal: `pip install -r requirements.txt` (app still runs with emoji if Pillow is missing) |
| `No module named '_tkinter'` / `tkinter` | Re-run the Python installer → Modify → tick **tcl/tk and IDLE** |
| `python` is not recognised | Re-install Python with "Add to PATH", or use the PyCharm interpreter |
| Pictures look like coloured boxes | `assets/images` is missing → run `python generate_assets.py` |
| Window is too big for a small screen | The app sizes itself to your screen (min 1000×640); set Windows display scaling to 100–125% |
| "database is locked" | Close any second copy of the app or a DB viewer that has `chicken_hub.db` open |
| Want a fresh start | Menu Management → **Reset Demo Data…** (or close the app and delete `data/chicken_hub.db`) |
