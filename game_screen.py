"""
game_screen.py - The window (screen) of the Cooking & Serving game.

All game RULES are in game.py (GameEngine). This file only:
  * draws the customer order, stations, timer, score
  * forwards button clicks to the engine
  * saves the final score to SQLite

Timer safety: every tick remembers the round it belongs to (round_id). If the round
changed, the game ended, or the player left the screen, the old tick does nothing and the
pending `after` call is cancelled.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from database import DatabaseError
from game import (GameEngine, GameError, DISHES, ACTIONS, STATIONS, MAX_MISSES,
                  IDLE, ACTIVE, SERVED, FAILED, OVER)
from screens import BaseScreen
from styles import (COLORS, F_HEAD, F_BODY, F_BOLD, F_SMALL, F_TITLE, make_button, card, image_label)

HOW_TO_PLAY = (
    "1.  A customer arrives and shows an order with pictures.\n"
    "2.  Press the cooking buttons in the right order (see the steps on each dish).\n"
    "3.  When the progress bar is full, press  Serve Order.\n"
    "4.  Be quick! Extra seconds give bonus points. Wrong buttons cost 5 points.\n"
    "5.  Missing 3 customers ends the game. Your score and coins are saved automatically."
)


def set_button(btn, enabled, color):
    """Enable/disable one of our custom buttons and fix its colours."""
    shade = color if enabled else COLORS["gray"]
    btn.config(state="normal" if enabled else "disabled", bg=shade)
    btn._normal_bg = shade


class GameScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.engine = None
        self._after_id = None
        self.action_buttons = {}
        self.step_labels = []
        self.name_labels = []
        self.name_var = tk.StringVar(value="Player")
        self.make_header("Cooking & Serving Game", "Cook the order and serve it before time runs out!")
        self.container = tk.Frame(self, bg=COLORS["cream"])
        self.container.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.intro = self._build_intro()
        self.play = self._build_play()
        self.over = self._build_over()
        self._show_panel(self.intro)

    # ------------------------------------------------------------------ panels
    def _show_panel(self, panel):
        for p in (self.intro, self.play, self.over):
            p.pack_forget()
        panel.pack(fill="both", expand=True)

    def _build_intro(self):
        f = card(self.container)
        tk.Label(f, text="How to play", font=F_HEAD, bg=COLORS["white"], fg=COLORS["red"]).pack(pady=(24, 6))
        tk.Label(f, text=HOW_TO_PLAY, font=F_BODY, bg=COLORS["white"], justify="left").pack(padx=30)
        pics = tk.Frame(f, bg=COLORS["white"])
        pics.pack(pady=(14, 0))
        for dish in DISHES.values():
            image_label(pics, self.images, dish["image"], dish["emoji"], 64, COLORS["white"],
                        dish["name"]).pack(side="left", padx=8)
        row = tk.Frame(f, bg=COLORS["white"])
        row.pack(pady=14)
        tk.Label(row, text="Player name:", font=F_BOLD, bg=COLORS["white"]).pack(side="left")
        tk.Entry(row, textvariable=self.name_var, width=18, font=F_BODY, relief="solid", bd=1).pack(side="left", padx=8)
        make_button(f, "Start Game", self.start_game, "success", font=(F_BOLD[0], 14, "bold"),
                    padx=30, pady=10).pack()
        self.intro_stats = tk.Label(f, text="", font=F_BODY, bg=COLORS["white"], fg=COLORS["gray"])
        self.intro_stats.pack(pady=16)
        return f

    def _build_play(self):
        f = tk.Frame(self.container, bg=COLORS["cream"])

        # top bar: player / customer / score / coins / missed / time
        bar = card(f)
        bar.pack(fill="x")
        self.top = {}
        for key, title in [("player", "Player"), ("customer", "Customer"), ("score", "Score"),
                           ("coins", "Coins"), ("missed", "Missed"), ("time", "Time left")]:
            cell = tk.Frame(bar, bg=COLORS["white"])
            cell.pack(side="left", expand=True, fill="x", padx=6, pady=4)
            tk.Label(cell, text=title, font=F_SMALL, bg=COLORS["white"], fg=COLORS["gray"]).pack()
            lab = tk.Label(cell, text="-", font=(F_BOLD[0], 15, "bold"), bg=COLORS["white"],
                           fg=COLORS["charcoal"])
            lab.pack()
            self.top[key] = lab

        # customer order (+ feedback message on the right of the title row)
        self.order_card = card(f)
        self.order_card.pack(fill="x", pady=8)
        head = tk.Frame(self.order_card, bg=COLORS["white"])
        head.pack(fill="x", padx=12, pady=(6, 0))
        self.order_title = tk.Label(head, text="", font=F_BOLD, bg=COLORS["white"], fg=COLORS["red"])
        self.order_title.pack(side="left")
        self.feedback = tk.Label(head, text="", font=F_BOLD, bg=COLORS["white"], fg=COLORS["charcoal"],
                                 wraplength=520, justify="right")
        self.feedback.pack(side="right")
        self.order_row = tk.Frame(self.order_card, bg=COLORS["white"])
        self.order_row.pack(fill="x", padx=6, pady=(0, 6))

        # kitchen stations (buttons)
        grid = tk.Frame(f, bg=COLORS["cream"])
        grid.pack(fill="x")
        for n, (title, actions) in enumerate(STATIONS):
            st = card(grid)
            st.grid(row=n // 3, column=n % 3, padx=4, pady=4, sticky="nsew")
            tk.Label(st, text=title, font=F_SMALL, bg=COLORS["white"], fg=COLORS["gray"]).pack(pady=(4, 0))
            for aid in actions:
                btn = make_button(st, ACTIONS[aid][0], lambda a=aid: self.do_action(a), "secondary",
                                  font=(F_BOLD[0], 10, "bold"), pady=3)
                btn.pack(fill="x", padx=8, pady=2)
                self.action_buttons[aid] = btn
            tk.Frame(st, height=4, bg=COLORS["white"]).pack()
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="stations")

        # one row: progress bar + Serve / Next / End buttons
        ctl = tk.Frame(f, bg=COLORS["cream"])
        ctl.pack(fill="x", pady=(8, 0))
        tk.Label(ctl, text="Order progress", font=F_BOLD, bg=COLORS["cream"]).pack(side="left")
        self.progress = ttk.Progressbar(ctl, style="Red.Horizontal.TProgressbar", maximum=1, value=0)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_text = tk.Label(ctl, text="0 / 0", font=F_BOLD, bg=COLORS["cream"])
        self.progress_text.pack(side="left", padx=(0, 10))
        self.serve_btn = make_button(ctl, "Serve Order", self.serve, "success", padx=16, pady=6)
        self.serve_btn.pack(side="left")
        self.next_btn = make_button(ctl, "Next Customer", self.next_customer, "primary", padx=12, pady=6)
        self.next_btn.pack(side="left", padx=6)
        self.end_btn = make_button(ctl, "End Game", self.end_game_click, "danger", padx=12, pady=6)
        self.end_btn.pack(side="left")
        return f

    def _build_over(self):
        f = card(self.container)
        tk.Label(f, text="Game Over", font=F_TITLE, bg=COLORS["white"], fg=COLORS["red"]).pack(pady=(30, 4))
        self.over_reason = tk.Label(f, text="", font=F_BODY, bg=COLORS["white"], fg=COLORS["gray"])
        self.over_reason.pack()
        self.over_summary = tk.Label(f, text="", font=(F_BOLD[0], 14, "bold"), bg=COLORS["white"], justify="center")
        self.over_summary.pack(pady=14)
        self.over_saved = tk.Label(f, text="", font=F_BODY, bg=COLORS["white"], fg=COLORS["green"])
        self.over_saved.pack()
        row = tk.Frame(f, bg=COLORS["white"])
        row.pack(pady=20)
        make_button(row, "Play Again", self._back_to_intro, "success", pady=8).pack(side="left", padx=6)
        make_button(row, "View Leaderboard", lambda: self.app.show_screen("leaderboard"), "primary",
                    pady=8).pack(side="left", padx=6)
        return f

    # ------------------------------------------------------------- show / leave
    def on_show(self):
        if self.engine is None or self.engine.state == OVER:
            self._back_to_intro()

    def _back_to_intro(self):
        self._cancel_timer()
        self.engine = None
        self.intro_stats.config(
            text=f"High score: {self.db.high_score()}     Total coins earned: {self.db.total_coins()}")
        self._show_panel(self.intro)

    def can_leave(self):
        """Called by the app before switching screens."""
        if self.engine is not None and self.engine.state in (ACTIVE, SERVED, FAILED):
            if not messagebox.askyesno("Game in progress",
                                       "Leave the game now? The game will end and your score will be saved."):
                return False
            self._finish_game("You left the game.")
        return True

    def shutdown(self):
        """Called when the window closes."""
        self._cancel_timer()

    # ------------------------------------------------------------------- timer
    def _cancel_timer(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _schedule_tick(self):
        self._cancel_timer()
        round_id = self.engine.round_id
        self._after_id = self.after(1000, lambda: self._on_tick(round_id))

    def _on_tick(self, round_id):
        self._after_id = None
        # Ignore ticks from an old round or after the round/game ended.
        if self.engine is None or round_id != self.engine.round_id or self.engine.state != ACTIVE:
            return
        state = self.engine.tick()
        self._refresh()
        if state == ACTIVE:
            self._schedule_tick()
        else:
            self._handle_timeout()

    def _handle_timeout(self):
        self._cancel_timer()
        if self.engine.game_over:
            self._finish_game(f"You missed {MAX_MISSES} customers.")
            return
        self._say(f"Time's up! The customer left angry. (Missed {self.engine.misses}/{MAX_MISSES})", False)
        self._refresh()

    # --------------------------------------------------------------- game flow
    def start_game(self):
        self.engine = GameEngine(self.name_var.get())
        self.engine.start_game()
        self._show_panel(self.play)
        self._build_order_cards()
        self._say("First customer! Follow the steps on the dish card.", True)
        self._refresh()
        self._schedule_tick()

    def next_customer(self):
        if self.engine is None:
            return
        try:
            self.engine.next_customer()
        except GameError as e:
            self._say(str(e), False)
            return
        self._build_order_cards()
        self._say("New customer arrived!", True)
        self._refresh()
        self._schedule_tick()

    def do_action(self, action_id):
        if self.engine is None:
            return
        ok, message = self.engine.perform_action(action_id)
        if ok and self.engine.is_complete():
            message = "All steps done! Press Serve Order."
        self._say(message, ok)
        self._refresh()

    def serve(self):
        if self.engine is None:
            return
        result = self.engine.serve()
        if not result["ok"]:
            self._say(result["message"], False)
            return
        self._cancel_timer()                       # stop the countdown for this round
        self._say(f"Customer is happy!  +{result['points']} points,  +{result['coins']} coins", True)
        self._refresh()

    def end_game_click(self):
        if self.engine is None:
            return
        if messagebox.askyesno("End game", "End the game and save your score?"):
            self._finish_game("You ended the game.")

    def _finish_game(self, reason=""):
        self._cancel_timer()
        summary = self.engine.end_game()
        saved_text = "No customers were served, nothing to save."
        if self.engine.should_save():
            try:
                self.db.save_score(summary["player_name"], summary["score"], summary["coins"],
                                   summary["customers_served"])
                self.engine.mark_saved()
                saved_text = "Your score and coins were saved to the leaderboard."
            except DatabaseError as e:
                saved_text = f"Could not save the score: {e}"
        self.over_reason.config(text=reason)
        self.over_summary.config(text=(
            f"{summary['player_name']}\nScore: {summary['score']}     Coins: {summary['coins']}\n"
            f"Customers served: {summary['customers_served']}"))
        self.over_saved.config(text=saved_text)
        self._show_panel(self.over)

    # ------------------------------------------------------------------- drawing
    def _say(self, text, good):
        self.feedback.config(text=text, fg=COLORS["green"] if good else COLORS["red"])

    def _build_order_cards(self):
        for w in self.order_row.winfo_children():
            w.destroy()
        self.step_labels, self.name_labels = [], []
        self.order_title.config(text=f"Customer #{self.engine.customer_number} wants:")
        for key in self.engine.order:
            dish = DISHES[key]
            f = tk.Frame(self.order_row, bg=COLORS["cream"], highlightthickness=1,
                         highlightbackground=COLORS["light_gray"])
            f.pack(side="left", padx=5, pady=4, fill="y")
            image_label(f, self.images, dish["image"], dish["emoji"], 60, COLORS["cream"],
                        dish["name"]).pack(padx=10, pady=(4, 0))
            name = tk.Label(f, text=dish["name"], font=F_BOLD, bg=COLORS["cream"])
            name.pack()
            self.name_labels.append(name)
            labels = []
            for _ in dish["steps"]:
                lab = tk.Label(f, text="", font=F_SMALL, bg=COLORS["cream"], anchor="w")
                lab.pack(anchor="w", padx=10)
                labels.append(lab)
            tk.Frame(f, height=4, bg=COLORS["cream"]).pack()
            self.step_labels.append(labels)

    def _refresh(self):
        e = self.engine
        if e is None:
            return
        for i, key in enumerate(e.order):
            steps = DISHES[key]["steps"]
            done = e.progress[i]
            for j, aid in enumerate(steps):
                lab = self.step_labels[i][j]
                if j < done:
                    lab.config(text="✔ " + ACTIONS[aid][1], fg=COLORS["green"], font=F_SMALL)
                elif j == done:
                    lab.config(text="► " + ACTIONS[aid][1], fg=COLORS["charcoal"], font=(F_SMALL[0], 9, "bold"))
                else:
                    lab.config(text="○ " + ACTIONS[aid][1], fg=COLORS["gray"], font=F_SMALL)
            self.name_labels[i].config(
                text=DISHES[key]["name"] + (" ✔" if done == len(steps) else ""),
                fg=COLORS["green"] if done == len(steps) else COLORS["charcoal"])
        self.top["player"].config(text=e.player_name)
        self.top["customer"].config(text=f"#{e.customer_number}")
        self.top["score"].config(text=str(e.score))
        self.top["coins"].config(text=str(e.coins))
        self.top["missed"].config(text=f"{e.misses} / {MAX_MISSES}")
        low = e.state == ACTIVE and e.remaining <= 10
        self.top["time"].config(text=f"{e.remaining}s", fg=COLORS["red"] if low else COLORS["charcoal"])
        self.progress.config(maximum=max(1, e.total_steps), value=e.steps_done)
        self.progress_text.config(text=f"{e.steps_done} / {e.total_steps}")
        active = e.state == ACTIVE
        for btn in self.action_buttons.values():
            set_button(btn, active, COLORS["charcoal"])
        set_button(self.serve_btn, e.can_serve(), COLORS["green"])
        set_button(self.next_btn, e.state in (SERVED, FAILED) and not e.game_over, COLORS["red"])
