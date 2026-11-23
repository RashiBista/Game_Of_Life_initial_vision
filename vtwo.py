"""
CELL ARCHITECT - a puzzle game built on Conway's Game of Life.
Standard library only (tkinter). Run with:  python cell_architect.py

How to play
  1. Read the goal, then click/drag inside the blue build zone to place cells.
  2. You only get a limited number of cells - fewer cells used = more stars.
  3. Press Run and watch life unfold. Hit the goal in time to win!

Keys: Space = run/pause   R = reset   H = hint   N = next level

This is still a work in progress. The code is messy, but the game is playable. Enjoy! but not finished yet. Feedback welcome:
"""

import json
import os
import random
import tkinter as tk
from collections import Counter

ROWS, COLS, CELL = 24, 40, 20
W, H = COLS * CELL, ROWS * CELL

# ---------- colours ----------
BG = "#0d0d1a"
EMPTY = "#141428"
GRID = "#1d1d38"
BUILD = "#1b2d52"
TARGET = "#4d4010"
WALL = "#5a5a70"
GOLD = "#ffd700"
PINK = "#ff6ec7"
WARN = "#ff8a65"
GOOD = "#7dffa0"
AGE_COLORS = ["#00f0ff", "#19e6b4", "#2ecc71", "#7bd34f", "#b8d84a"]


def rect(r0, c0, r1, c1):
    """All cells in an inclusive rectangle."""
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}


# ---------- levels ----------
GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
R_PENT = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
ACORN = [(0, 1), (1, 3), (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)]


def shift(cells, dr, dc):
    return [(r + dr, c + dc) for r, c in cells]


LEVELS = [
    dict(
        name="First Spark",
        story="Life is fragile. Some shapes die out, others last forever.",
        goal="survive", n=4, gens=15, budget=6, par=4,
        build=rect(8, 15, 15, 24), walls=set(), target=set(),
        solution=shift([(0, 0), (0, 1), (1, 0), (1, 1)], 10, 18),  # a block
    ),
    dict(
        name="Big Bang",
        story="Tiny seeds can explode into huge colonies. Find one that does.",
        goal="grow", n=45, gens=40, budget=5, par=5,
        build=rect(9, 15, 15, 24), walls=set(), target=set(),
        solution=shift(R_PENT, 11, 18),
    ),
    dict(
        name="The Messenger",
        story="Gliders walk diagonally forever. Deliver one to the golden zone.",
        goal="reach", n=0, gens=100, budget=5, par=5,
        build=rect(1, 1, 6, 8), walls=set(), target=rect(17, 20, 21, 24),
        solution=shift(GLIDER, 2, 5),
    ),
    dict(
        name="The Gate",
        story="Walls kill any cell that touches them. Thread your glider through the gap!",
        goal="reach", n=0, gens=110, budget=5, par=5,
        build=rect(1, 1, 6, 8),
        walls=rect(12, 0, 13, COLS - 1) - rect(12, 13, 13, 18),
        target=rect(17, 20, 21, 24),
        solution=shift(GLIDER, 2, 5),
    ),
    dict(
        name="Supernova",
        story="Now think bigger: 7 cells, a much bigger bang. The R-pentomino won't cut it.",
        goal="grow", n=95, gens=80, budget=7, par=7,
        build=rect(9, 15, 15, 24), walls=set(), target=set(),
        solution=shift(ACORN, 11, 15),
    ),
]

SANDBOX = dict(
    name="Sandbox",
    story="Free play! Draw anything. Click cells while paused to edit live.",
    goal=None, n=0, gens=None, budget=None, par=0,
    build=rect(0, 0, ROWS - 1, COLS - 1), walls=set(), target=set(), solution=[],
)


# ---------- pure game logic (also used by the self-test) ----------
def life_step(live, walls):
    """One generation on a bounded grid. Cells touching walls die."""
    counts = Counter()
    for r, c in live:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        counts[(nr, nc)] += 1
    return {cell for cell, n in counts.items()
            if (n == 3 or (n == 2 and cell in live)) and cell not in walls}


def judge(lv, live, gen):
    """Return ('win', '') / ('lose', reason) / None if still playing."""
    goal = lv["goal"]
    if goal == "reach" and live & lv["target"]:
        return "win", ""
    if goal == "grow" and len(live) >= lv["n"]:
        return "win", ""
    if goal == "survive" and gen >= lv["gens"]:
        if len(live) >= lv["n"]:
            return "win", ""
        return "lose", f"Only {len(live)} cells left - you needed {lv['n']}."
    if not live:
        return "lose", "Everything died out!"
    if gen >= lv["gens"]:
        return "lose", "Out of time!"
    return None


def goal_text(lv):
    g = lv["goal"]
    if g == "survive":
        return f"GOAL: have {lv['n']}+ cells alive at generation {lv['gens']}"
    if g == "reach":
        return f"GOAL: get a living cell into the gold zone within {lv['gens']} generations"
    if g == "grow":
        return f"GOAL: reach {lv['n']} living cells within {lv['gens']} generations"
    return "FREE PLAY: no rules, no limits. Press Run."


# ---------- saved progress ----------
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".cell_architect.json")


def load_progress():
    try:
        with open(SAVE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_progress(progress):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(progress, f)
    except Exception:
        pass


# ---------- the game ----------
class Game:
    def __init__(self, root):
        self.root = root
        root.title("Cell Architect")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.progress = load_progress()
        self.speed = tk.IntVar(value=8)
        self.job = None
        self.ghost_job = None
        self.ghost = set()
        self.colors = {}
        self.placed = set()
        self.live = set()
        self.ages = {}
        self.gen = 0
        self.state = "build"       # build / run / won / lost
        self.paused = False
        self.hint_used = False
        self.paint_value = True

        self._build_ui()
        for key, fn in (("<space>", self.toggle_run), ("r", self.reset),
                        ("h", self.hint), ("n", self.next_level)):
            root.bind(key, lambda e, f=fn: f())

        start = 0
        while str(start) in self.progress and start + 1 < len(LEVELS):
            start += 1
        self.load_level(start)

    # ----- UI -----
    def _btn(self, parent, text, cmd, width=9):
        b = tk.Button(parent, text=text, command=cmd, width=width,
                      bg="#26264a", fg="white", activebackground="#3a3a70",
                      activeforeground="white", relief="flat", bd=0,
                      font=("Helvetica", 11, "bold"), pady=4)
        b.pack(side="left", padx=3)
        return b

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=10, pady=(8, 0))
        self.title_lbl = tk.Label(top, fg=GOLD, bg=BG, anchor="w",
                                  font=("Helvetica", 18, "bold"))
        self.title_lbl.pack(side="left")
        self.stars_lbl = tk.Label(top, fg=GOLD, bg=BG, font=("Helvetica", 13))
        self.stars_lbl.pack(side="right")

        self.story_lbl = tk.Label(self.root, fg="#cfd2ff", bg=BG, anchor="w",
                                  justify="left", wraplength=W - 20,
                                  font=("Helvetica", 11))
        self.story_lbl.pack(fill="x", padx=10)
        self.goal_lbl = tk.Label(self.root, fg="#7df9ff", bg=BG, anchor="w",
                                 font=("Helvetica", 11, "bold"))
        self.goal_lbl.pack(fill="x", padx=10)

        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=EMPTY,
                                highlightthickness=0)
        self.canvas.pack(padx=10, pady=6)
        self.rects = {}
        for r in range(ROWS):
            for c in range(COLS):
                self.rects[(r, c)] = self.canvas.create_rectangle(
                    c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL,
                    fill=EMPTY, outline=GRID)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=10)
        self.run_btn = self._btn(bar, "▶ Run", self.toggle_run)
        self.reset_btn = self._btn(bar, "↺ Reset", self.reset)
        self.hint_btn = self._btn(bar, "💡 Hint", self.hint)
        self.prev_btn = self._btn(bar, "◀ Prev", self.prev_level, 7)
        self.next_btn = self._btn(bar, "Next ▶", self.next_level, 7)
        self.sandbox_btn = self._btn(bar, "Sandbox", self.toggle_sandbox, 9)
        self.random_btn = self._btn(bar, "Random", self.randomize, 8)
        self.clear_btn = self._btn(bar, "Clear", self.clear, 7)

        bar2 = tk.Frame(self.root, bg=BG)
        bar2.pack(fill="x", padx=10, pady=(4, 10))
        tk.Label(bar2, text="Speed", fg="#9aa", bg=BG).pack(side="left", padx=(3, 4))
        tk.Scale(bar2, from_=1, to=30, orient="horizontal", variable=self.speed,
                 length=140, showvalue=False, bg=BG, fg="white",
                 troughcolor="#26264a", highlightthickness=0).pack(side="left")
        self.status_lbl = tk.Label(bar2, fg="white", bg=BG, anchor="e",
                                   font=("Helvetica", 11, "bold"))
        self.status_lbl.pack(side="right")

    def say(self, text, color="#cfd2ff"):
        self.story_lbl.config(text=text, fg=color)

    def update_status(self):
        lv = self.lv
        pop = len(self.live)
        if self.sandbox:
            txt = f"Gen {self.gen}   Population {pop}"
        elif self.state == "build":
            txt = f"Cells left: {lv['budget'] - len(self.placed)}/{lv['budget']}"
        else:
            txt = f"Gen {self.gen}/{lv['gens']}   Population {pop}"
        self.status_lbl.config(text=txt)
        total = sum(self.progress.values())
        self.stars_lbl.config(text=f"★ {total}/{3 * len(LEVELS)}")

    def update_nav(self):
        done = (not self.sandbox) and str(self.lv_idx) in self.progress
        has_next = (not self.sandbox) and self.lv_idx + 1 < len(LEVELS)
        has_prev = (not self.sandbox) and self.lv_idx > 0
        self.next_btn.config(state="normal" if (done and has_next) else "disabled")
        self.prev_btn.config(state="normal" if has_prev else "disabled")
        self.hint_btn.config(state="disabled" if self.sandbox else "normal")
        sb = "normal" if self.sandbox else "disabled"
        self.random_btn.config(state=sb)
        self.clear_btn.config(state=sb)
        self.sandbox_btn.config(text="Levels" if self.sandbox else "Sandbox")

    # ----- drawing -----
    def draw(self):
        lv = self.lv
        building = self.state == "build" and not self.sandbox
        for cell, item in self.rects.items():
            if cell in self.live:
                if cell in lv["target"]:
                    col = GOLD
                else:
                    col = AGE_COLORS[min(self.ages.get(cell, 0), 4)]
            elif cell in self.ghost:
                col = PINK
            elif cell in lv["walls"]:
                col = WALL
            elif cell in lv["target"]:
                col = TARGET
            elif building and cell in lv["build"]:
                col = BUILD
            else:
                col = EMPTY
            if self.colors.get(cell) != col:
                self.colors[cell] = col
                self.canvas.itemconfig(item, fill=col)

    # ----- levels -----
    def load_level(self, idx):
        self.cancel_job()
        self.clear_ghost()
        self.sandbox = idx is None
        self.lv_idx = idx
        self.lv = SANDBOX if self.sandbox else LEVELS[idx]
        self.placed = set()
        self.hint_used = False
        title = "Sandbox" if self.sandbox else f"Level {idx + 1}: {self.lv['name']}"
        self.title_lbl.config(text=title)
        self.goal_lbl.config(text=goal_text(self.lv))
        self.reset()

    def reset(self):
        self.cancel_job()
        self.state = "build"
        self.paused = False
        self.gen = 0
        self.live = set(self.placed)
        self.ages = {c: 0 for c in self.live}
        self.canvas.delete("overlay")
        self.canvas.delete("confetti")
        self.run_btn.config(text="▶ Run")
        self.say(self.lv["story"])
        self.draw()
        self.update_status()
        self.update_nav()

    def next_level(self):
        if str(self.lv_idx) in self.progress and not self.sandbox \
                and self.lv_idx + 1 < len(LEVELS):
            self.load_level(self.lv_idx + 1)

    def prev_level(self):
        if not self.sandbox and self.lv_idx > 0:
            self.load_level(self.lv_idx - 1)

    def toggle_sandbox(self):
        if self.sandbox:
            idx = 0
            while str(idx) in self.progress and idx + 1 < len(LEVELS):
                idx += 1
            self.load_level(idx)
        else:
            self.load_level(None)

    # ----- mouse editing -----
    def cell_at(self, e):
        c, r = e.x // CELL, e.y // CELL
        return (r, c) if 0 <= r < ROWS and 0 <= c < COLS else None

    def on_press(self, e):
        cell = self.cell_at(e)
        if not cell:
            return
        current = self.placed if self.state == "build" else self.live
        self.paint_value = cell not in current
        self.paint(cell)

    def on_drag(self, e):
        cell = self.cell_at(e)
        if cell:
            self.paint(cell)

    def paint(self, cell):
        lv = self.lv
        if self.state == "build":
            if self.paint_value:
                if cell in lv["walls"] or cell not in lv["build"]:
                    return
                if lv["budget"] is not None and len(self.placed) >= lv["budget"]:
                    self.say("Out of cells! Erase one first (click a placed cell).", WARN)
                    return
                self.placed.add(cell)
            else:
                self.placed.discard(cell)
            self.live = set(self.placed)
            self.ages = {c: 0 for c in self.live}
        elif self.sandbox and self.state == "run":
            if self.paint_value:
                self.live.add(cell)
                self.ages[cell] = 0
            else:
                self.live.discard(cell)
        else:
            return
        self.draw()
        self.update_status()

    # ----- running -----
    def cancel_job(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None

    def toggle_run(self):
        if self.state in ("won", "lost"):
            self.reset()
            return
        if self.state == "build":
            if not self.placed:
                self.say("Place some cells first! Click inside the blue zone.", WARN)
                return
            self.state = "run"
            self.paused = False
            self.gen = 0
            self.live = set(self.placed)
            self.ages = {c: 0 for c in self.live}
            self.clear_ghost()
            self.run_btn.config(text="⏸ Pause")
            self.say("Simulating...")
            self.tick()
        elif self.state == "run":
            self.paused = not self.paused
            self.run_btn.config(text="▶ Resume" if self.paused else "⏸ Pause")
            if self.paused:
                self.cancel_job()
            else:
                self.tick()

    def tick(self):
        self.job = None
        if self.state != "run" or self.paused:
            return
        new = life_step(self.live, self.lv["walls"])
        self.ages = {c: (self.ages[c] + 1 if c in self.live else 0) for c in new}
        self.live = new
        self.gen += 1
        self.draw()
        self.update_status()
        if not self.sandbox:
            result = judge(self.lv, self.live, self.gen)
            if result:
                self.finish(*result)
                return
        self.job = self.root.after(max(1, int(1000 / self.speed.get())), self.tick)

    def finish(self, kind, msg):
        if kind == "lose":
            self.state = "lost"
            self.run_btn.config(text="↺ Retry")
            self.say(f"✖ {msg} Press Retry and rethink your design.", WARN)
            return
        self.state = "won"
        self.run_btn.config(text="↺ Replay")
        lv = self.lv
        used = len(self.placed)
        stars = 3 if used <= lv["par"] else 2 if used <= lv["par"] + 2 else 1
        if self.hint_used:
            stars = 1
        key = str(self.lv_idx)
        self.progress[key] = max(self.progress.get(key, 0), stars)
        save_progress(self.progress)
        shown = "★" * stars + "☆" * (3 - stars)
        note = f"Used {used} cells (par {lv['par']})."
        if self.hint_used:
            note += " Hint used: 1 star max."
        self.say(f"✔ Solved in {self.gen} generations! {note}", GOOD)
        self.canvas.create_rectangle(W // 2 - 190, H // 2 - 70, W // 2 + 190, H // 2 + 70,
                                    fill="#000000", stipple="gray50", outline=GOLD,
                                    width=2, tags="overlay")
        self.canvas.create_text(W // 2, H // 2 - 20, text="LEVEL COMPLETE!", fill=GOLD,
                                font=("Helvetica", 26, "bold"), tags="overlay")
        self.canvas.create_text(W // 2, H // 2 + 30, text=shown, fill=GOLD,
                                font=("Helvetica", 30), tags="overlay")
        self.update_status()
        self.update_nav()
        self.confetti()

    def confetti(self):
        palette = [GOLD, PINK, "#00f0ff", "#7dffa0", "#ffffff"]
        parts = []
        for _ in range(70):
            x, y = random.randint(0, W), random.randint(-120, 0)
            item = self.canvas.create_rectangle(
                x, y, x + 7, y + 7, fill=random.choice(palette), outline="",
                tags="confetti")
            parts.append((item, random.uniform(-1.5, 1.5), random.uniform(3, 8)))

        def fall(n=0):
            if n > 70:
                self.canvas.delete("confetti")
                return
            for item, dx, dy in parts:
                self.canvas.move(item, dx, dy)
            self.root.after(30, lambda: fall(n + 1))
        fall()

    # ----- hint / sandbox helpers -----
    def hint(self):
        if self.sandbox or self.state != "build":
            return
        self.hint_used = True
        self.cancel_ghost_job()
        self.ghost = set(self.lv["solution"])
        self.draw()
        self.say("💡 Pink cells show one possible solution. Hint used: max 1 star.", PINK)
        self.ghost_job = self.root.after(4000, self.clear_ghost_and_draw)

    def cancel_ghost_job(self):
        if self.ghost_job is not None:
            self.root.after_cancel(self.ghost_job)
            self.ghost_job = None

    def clear_ghost(self):
        self.cancel_ghost_job()
        self.ghost = set()

    def clear_ghost_and_draw(self):
        self.ghost_job = None
        self.ghost = set()
        self.draw()

    def randomize(self):
        if not self.sandbox:
            return
        self.cancel_job()
        self.placed = {(r, c) for r in range(ROWS) for c in range(COLS)
                       if random.random() < 0.25}
        self.reset()

    def clear(self):
        if not self.sandbox:
            return
        self.cancel_job()
        self.placed = set()
        self.reset()


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()