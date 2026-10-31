# 🍗 Chicken Hub – Restaurant Management & Cooking Simulation

A desktop-based BCA mini project developed using **Python 3, Tkinter, and SQLite**, with Pillow for image processing.

Chicken Hub is an offline desktop application designed to simplify basic restaurant management operations while providing an interactive cooking and serving simulation.

This is an academic project and is not affiliated with or connected to any real restaurant brand.

## ✨ Features

- **Dashboard:** Displays total orders, total revenue, available items, game high score, and low-stock alerts using SQLite data.
- **New Order & Billing:** Includes food image cards, shopping cart functionality (add, decrease, remove, and clear items), subtotal calculation, configurable GST, coupon discounts, and printable receipts with order numbers. Receipts can also be saved as `.txt` files.
- **Kitchen Management:** Tracks order progress through four stages: Received → Preparing → Ready → Completed. Order information is stored in SQLite and synchronized with the billing system.
- **Inventory Management:** Displays stock information, highlights low-stock items, and allows authorized staff to add, remove, or update stock. Changes require a staff PIN (default: `1234`).
- **Menu Management:** Allows users to add food items, update prices, hide items, modify GST percentages, and reset demo data with confirmation.
- **Sales Analytics:** Displays total orders, revenue, popular items, daily sales summaries, a seven-day bar chart, and the game high score.
- **Cooking & Serving Game:** Includes customer orders with pictures, cooking steps, preparation stations, a progress bar, countdown timer, scoring system, coins, and customer-serving functionality. Missing three customers ends the game.
- **Leaderboard:** Displays the top 10 game scores, including player names, scores, coins, and date and time, ranked from highest to lowest.

## 📂 Project Structure

```text
ChickenHub/
│
├── main.py               # Main application, window, sidebar and navigation
├── database.py           # SQLite database, tables, orders, stock and scores
├── billing.py            # Billing calculations, coupon rules and receipts
├── game.py               # Cooking game logic and rules
├── game_screen.py        # Cooking game graphical interface
├── screens.py            # Dashboard, billing, kitchen, inventory, menu,
│                         # analytics and leaderboard screens
├── styles.py             # Colours, fonts, buttons and image loading
├── generate_assets.py    # Generates food images if they are missing
├── requirements.txt      # Required Python libraries
│
├── assets/
│   └── images/           # Food images and application logo
│
├── data/                 # SQLite database created automatically
├── receipts/             # Saved receipt text files
├── tests/                # Project test files
└── docs/                 # Testing report and project documentation
```

## ⚙️ Installation and Setup (Windows)

Follow these steps to install and run the project on Windows using PyCharm.

**Step 1: Install Python**

- Download and install Python 3.9 or above from [python.org](https://www.python.org/).
- During installation, enable the **Add Python to PATH** option.
- Tkinter is included with the standard Windows Python installation.

**Step 2: Extract the Project**

- Extract the downloaded ZIP file using the **Extract All** option.
- Make sure the project folder is named `ChickenHub`.
- Do not run the project directly from inside the ZIP file.

**Step 3: Open the Project in PyCharm**

- Open PyCharm.
- Select **File → Open**.
- Choose the extracted `ChickenHub` folder.

**Step 4: Configure the Python Interpreter**

- Navigate to **File → Settings → Project → Python Interpreter**.
- Select an installed Python 3 interpreter or create a new virtual environment.

**Step 5: Install Required Libraries**

Open the PyCharm terminal and run:

```bash
pip install -r requirements.txt
```

**Step 6: Run the Application**

- Locate `main.py` in the project.
- Right-click the file.
- Select **Run 'main'**.

The application window will open, and the SQLite database will be created automatically on the first run.

**Step 7: Run Tests (Optional)**

To execute the project tests, run:

```bash
python -m unittest discover -s tests -v
```

To run the GUI smoke test separately:

```bash
python tests/gui_smoke_test.py
```

This test opens the application window and performs button interactions programmatically.

**Additional Note:** If application images are missing, run:

```bash
python generate_assets.py
```

The application can also display placeholder images or emojis when original images are unavailable.

## 📋 Application Rules and Logic

### Billing System

- Discounts are applied to the subtotal before GST is calculated.
- GST is charged on the discounted amount.
- Inventory stock is reduced only after an order is successfully saved.
- Database operations use a single SQLite transaction.
- If sufficient stock is unavailable, the order is not saved.

### Cooking Game Scoring

The game calculates points using the following formula:

```text
Points = max(10, 50 × Dishes + Seconds Left − 5 × Mistakes)
```

Coins are calculated as:

```text
Coins = Points ÷ 10
```

- Playing the game does not affect restaurant inventory.
- Game scores are saved only when at least one customer has been served.

### Staff Authentication

- The default staff PIN is `1234`.
- The PIN is required for inventory and menu management operations.
- Staff authentication is requested once per application session.

**Note:** The default PIN is intended for demonstration purposes and is not a secure authentication mechanism.

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `No module named 'PIL'` | Run `pip install -r requirements.txt`. The application can still use emoji placeholders if Pillow is unavailable. |
| `No module named '_tkinter'` or `tkinter` | Modify the Python installation and enable **Tcl/Tk and IDLE**. |
| Python command is not recognized | Reinstall Python with **Add Python to PATH** enabled, or use the PyCharm interpreter. |
| Images appear as coloured boxes | The `assets/images` folder may be missing. Run `python generate_assets.py`. |
| Application window is too large | The application adjusts its size to the screen, with a minimum size of 1000 × 640. Adjust Windows display scaling to 100–125% if needed. |
| Database is locked | Close any additional running copy of the application or any database viewer using the same database file. |
| Need to reset application data | Select **Menu Management → Reset Demo Data** and confirm the action. Alternatively, close the application and delete `data/chicken_hub.db`. |

## 🎯 Project Objective

The primary objective of Chicken Hub is to demonstrate how Python can be used to develop a desktop-based restaurant management application.

The project provides practical implementation of:

- Python programming
- GUI development using Tkinter
- Database connectivity using SQLite
- Billing and calculation logic
- Inventory and order management
- Basic data visualization
- Interactive game development

## 🎓 Academic Project

**Project Name:** Chicken Hub – Restaurant Management & Cooking Simulation

**Project Type:** Python Mini Project

**Platform:** Desktop Application

**Technologies:** Python, Tkinter, SQLite and Pillow

## 👨‍💻 Developer

**Aditya Rangta**

GitHub: [Aditya-Rangta](https://github.com/Aditya-Rangta)

---

⭐ If you find this project interesting, feel free to explore the repository!
