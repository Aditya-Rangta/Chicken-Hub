"""
game.py - The RULES of the cooking-and-serving game (NO Tkinter here).

Keeping the rules separate from the screen lets us test the game without a window.
The screen (game_screen.py) only shows the state of GameEngine and forwards clicks.

Round life-cycle:  ACTIVE -> SERVED (served in time)  or  FAILED (timer reached 0)
Game  life-cycle:  IDLE -> rounds... -> OVER (End Game, or 3 customers missed)

Scoring (simple and fixed):
  points for a served order = max(10, 50 x dishes + seconds_left - 5 x mistakes)
  coins = points // 10
The game NEVER touches restaurant stock (menu_items). Rewards are saved only in game_scores.
"""
import random

# action id: (button text, step text shown on the order card)
ACTIONS = {
    "cook_patty":      ("Cook Patty",        "Cook the patty"),
    "add_toppings":    ("Add Toppings",      "Add toppings"),
    "assemble_burger": ("Assemble Burger",   "Assemble the burger"),
    "fry_potatoes":    ("Fry Potatoes",      "Fry the potatoes"),
    "add_salt":        ("Add Salt",          "Add salt"),
    "pour_drink":      ("Pour Drink",        "Pour the drink"),
    "grill_chicken":   ("Grill Chicken",     "Grill the chicken"),
    "add_sauce":       ("Add Veggies+Sauce", "Add veggies and sauce"),
    "roll_wrap":       ("Roll Wrap",         "Roll the wrap"),
    "scoop_icecream":  ("Scoop Ice Cream",   "Scoop the ice cream"),
    "add_syrup":       ("Add Syrup",         "Add chocolate syrup"),
    "fry_chicken":     ("Fry Chicken",       "Fry the chicken pieces"),
    "pack_bucket":     ("Pack Bucket",       "Pack the bucket"),
}

# dish key: name, image file (in assets/images), emoji fallback, steps in the correct order
DISHES = {
    "chicken_burger": {"name": "Chicken Burger", "image": "burger.png", "emoji": "🍔",
                       "steps": ["cook_patty", "add_toppings", "assemble_burger"]},
    "french_fries":   {"name": "French Fries", "image": "fries.png", "emoji": "🍟",
                       "steps": ["fry_potatoes", "add_salt"]},
    "cold_drink":     {"name": "Cold Drink", "image": "drink.png", "emoji": "🥤",
                       "steps": ["pour_drink"]},
    "chicken_wrap":   {"name": "Chicken Wrap", "image": "wrap.png", "emoji": "🌯",
                       "steps": ["grill_chicken", "add_sauce", "roll_wrap"]},
    "ice_cream":      {"name": "Ice Cream", "image": "icecream.png", "emoji": "🍨",
                       "steps": ["scoop_icecream", "add_syrup"]},
    "chicken_bucket": {"name": "Chicken Bucket", "image": "bucket.png", "emoji": "🍗",
                       "steps": ["fry_chicken", "pack_bucket"]},
}

# The buttons are grouped into stations like a real kitchen.
STATIONS = [
    ("Burger Station", ["cook_patty", "add_toppings", "assemble_burger"]),
    ("Fry Station", ["fry_potatoes", "add_salt"]),
    ("Drinks Counter", ["pour_drink"]),
    ("Wrap Station", ["grill_chicken", "add_sauce", "roll_wrap"]),
    ("Dessert Counter", ["scoop_icecream", "add_syrup"]),
    ("Bucket Station", ["fry_chicken", "pack_bucket"]),
]

# Orders get harder as the game goes on (2 customers per level).
LEVELS = [
    [["chicken_burger"], ["chicken_wrap"], ["ice_cream"]],
    [["chicken_burger", "french_fries"], ["chicken_wrap", "cold_drink"], ["chicken_bucket"]],
    [["chicken_burger", "french_fries", "cold_drink"], ["chicken_wrap", "ice_cream"],
     ["chicken_bucket", "french_fries"]],
    [["chicken_bucket", "french_fries", "cold_drink"], ["chicken_burger", "chicken_wrap", "ice_cream"],
     ["chicken_burger", "french_fries", "cold_drink", "ice_cream"]],
]

POINTS_PER_DISH = 50
MISTAKE_PENALTY = 5
MIN_POINTS = 10
MAX_MISSES = 3
SECONDS_BASE = 20
SECONDS_PER_STEP = 12

IDLE, ACTIVE, SERVED, FAILED, OVER = "idle", "active", "served", "failed", "over"


class GameError(Exception):
    """Raised when a method is used at the wrong time (e.g. next customer while cooking)."""


class GameEngine:
    def __init__(self, player_name="Player", rng=None):
        self.player_name = (player_name or "").strip()[:20] or "Player"
        self.rng = rng or random.Random()
        self.state = IDLE
        self.score = 0
        self.coins = 0
        self.customers_served = 0
        self.misses = 0
        self.customer_number = 0
        self.round_id = 0          # changes every round; used to ignore old timer callbacks
        self.order = []            # list of dish keys for the current customer
        self.progress = []         # steps finished for each dish
        self.time_limit = 0
        self.remaining = 0
        self.mistakes = 0
        self.last_points = 0
        self.saved = False         # becomes True after the score is written to the database

    # ------------------------------------------------------------- game flow
    def start_game(self):
        """Reset everything and bring the first customer."""
        name = self.player_name
        self.__init__(name, self.rng)
        return self.next_customer()

    def next_customer(self):
        if self.state not in (IDLE, SERVED, FAILED):
            raise GameError("Finish the current customer first." if self.state == ACTIVE
                            else "The game is over. Start a new game.")
        self.customer_number += 1
        self.round_id += 1
        if self.customer_number == 1:
            self.order = ["chicken_burger"]          # very first customer is always easy
        else:
            level = min((self.customer_number - 1) // 2, len(LEVELS) - 1)
            self.order = list(self.rng.choice(LEVELS[level]))
        self.progress = [0] * len(self.order)
        self.time_limit = SECONDS_BASE + SECONDS_PER_STEP * self.total_steps
        self.remaining = self.time_limit
        self.mistakes = 0
        self.last_points = 0
        self.state = ACTIVE
        return list(self.order)

    @property
    def total_steps(self):
        return sum(len(DISHES[d]["steps"]) for d in self.order)

    @property
    def steps_done(self):
        return sum(self.progress)

    @property
    def game_over(self):
        return self.misses >= MAX_MISSES or self.state == OVER

    def is_complete(self):
        return bool(self.order) and all(
            self.progress[i] >= len(DISHES[d]["steps"]) for i, d in enumerate(self.order))

    def can_serve(self):
        return self.state == ACTIVE and self.is_complete()

    # -------------------------------------------------------------- actions
    def next_hint(self):
        """Text telling the player what to do next (used for wrong-click feedback)."""
        for i, dish in enumerate(self.order):
            steps = DISHES[dish]["steps"]
            if self.progress[i] < len(steps):
                return f"{ACTIONS[steps[self.progress[i]]][1]} for the {DISHES[dish]['name']}"
        return "Press Serve Order"

    def perform_action(self, action_id):
        """Try one cooking action. Returns (ok, message)."""
        if self.state != ACTIVE:
            return False, "There is no customer waiting right now."
        if action_id not in ACTIONS:
            return False, "Unknown action."
        for i, dish in enumerate(self.order):
            steps = DISHES[dish]["steps"]
            if self.progress[i] < len(steps) and steps[self.progress[i]] == action_id:
                self.progress[i] += 1
                return True, f"Good! {ACTIONS[action_id][1]} - done."
        self.mistakes += 1
        return False, f"Oops! Not needed right now (-{MISTAKE_PENALTY} points). Next: {self.next_hint()}."

    # ---------------------------------------------------------------- scoring
    def serve(self):
        """Serve the finished order. Returns a dict. Can score only ONCE per customer."""
        if self.state != ACTIVE:
            return {"ok": False, "message": "This customer is already finished.", "points": 0, "coins": 0}
        if not self.is_complete():
            return {"ok": False, "message": "The order is not ready yet. "
                    f"Next: {self.next_hint()}.", "points": 0, "coins": 0}
        points = max(MIN_POINTS, POINTS_PER_DISH * len(self.order) + self.remaining
                     - MISTAKE_PENALTY * self.mistakes)
        coins = points // 10
        self.state = SERVED                 # state change first => a second click cannot score again
        self.score += points
        self.coins += coins
        self.customers_served += 1
        self.last_points = points
        return {"ok": True, "message": "Order served!", "points": points, "coins": coins}

    def tick(self):
        """Call once per second. Returns the current state."""
        if self.state != ACTIVE:
            return self.state               # timer does nothing after the round ends
        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self.state = FAILED
            self.misses += 1
        return self.state

    def end_game(self):
        """Finish the game (safe to call many times). Returns a summary dict."""
        self.state = OVER
        return self.summary()

    def summary(self):
        return {"player_name": self.player_name, "score": self.score, "coins": self.coins,
                "customers_served": self.customers_served, "misses": self.misses,
                "customers_seen": self.customer_number}

    def should_save(self):
        """True only once, and only if at least one customer was served (no empty 0-point entries)."""
        return (not self.saved) and self.customers_served > 0

    def mark_saved(self):
        self.saved = True
