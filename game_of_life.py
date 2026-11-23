
import random
import tkinter as tk
from collections import Counter
from tkinter import ttk

ROWS, COLS, CELL = 45, 70, 14

ALIVE = "#290087"
DEAD = "#A230A4"
GRID = "#E2E0A4"
GRID_LINE = "#bc92cd"

PATTERNS = {
    "Glider": [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],

    "R-pentomino": [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)],

    "Acorn": [(0, 1), (1, 3), (2, 0), (2, 1),
              (2, 4), (2, 5), (2, 6)],

    "Lightweight spaceship": [
        (0, 1), (0, 4), (1, 0), (2, 0), (2, 4),
        (3, 0), (3, 1), (3, 2), (3, 3)
    ],

    "Gosper glider gun": [
        (c, r) for r, c in [
            (5, 1), (5, 2), (6, 1), (6, 2),
            (5, 11), (6, 11), (7, 11), (4, 12),
            (8, 12), (3, 13), (9, 13), (3, 14),
            (9, 14), (6, 15), (4, 16), (8, 16),
            (5, 17), (6, 17), (7, 17), (6, 18),
            (3, 21), (4, 21), (5, 21), (3, 22),
            (4, 22), (5, 22), (2, 23), (6, 23),
            (1, 25), (2, 25), (6, 25), (7, 25),
            (3, 35), (4, 35), (3, 36), (4, 36)
        ]
    ],
}


class LifeApp:

    def __init__(self, root):
        self.root = root

        root.title("Game of Life")
        root.configure(bg="#f6ffe9")

        self.live = set()
        self.generation = 0
        self.running = False
        self.paint_value = True

        self.wrap = tk.BooleanVar(value=True)
        self.speed = tk.IntVar(value=10)

        self.build_controls()
        self.build_canvas()
        self._bind_keys()
        self.update_status()

    # -------- UI --------

    def build_controls(self):

        bar = ttk.Frame(self.root, padding=6)
        bar.pack(fill="x")

        self.play_btn = ttk.Button(
            bar, text="⁙ play", width=8,
            command=self.toggle
        )
        self.play_btn.pack(side="left", padx=2)

        ttk.Button(
            bar, text="« step", width=8,
            command=self.step_once
        ).pack(side="left", padx=2)

        ttk.Button(
            bar, text="⁖ clear", width=8,
            command=self.clear
        ).pack(side="left", padx=2)

        ttk.Button(
            bar, text="⟳ random", width=8,
            command=self.randomize
        ).pack(side="left", padx=2)

        ttk.Label(bar, text=" Pattern:").pack(side="left")

        self.pattern_box = ttk.Combobox(
            bar,
            values=list(PATTERNS),
            state="readonly",
            width=20
        )

        self.pattern_box.set("Glider")
        self.pattern_box.pack(side="left", padx=2)

        ttk.Button(
            bar, text="Place", width=6,
            command=self.place_pattern
        ).pack(side="left", padx=2)

        ttk.Checkbutton(
            bar, text="Wrap",
            variable=self.wrap
        ).pack(side="left", padx=10)

        ttk.Label(bar, text="Speed:").pack(side="left", padx=10)

        ttk.Scale(
            bar,
            from_=1,
            to=60,
            variable=self.speed,
            length=120
        ).pack(side="left", padx=2)

        self.status = ttk.Label(bar, text="")
        self.status.pack(side="right", padx=6)

    # -------- Drawing canvas --------

    def build_canvas(self):

        self.canvas = tk.Canvas(
            self.root,
            width=COLS * CELL,
            height=ROWS * CELL,
            bg=GRID,
            highlightthickness=0
        )

        self.canvas.pack(padx=6, pady=(0, 6))

        self.rects = [
            [
                self.canvas.create_rectangle(
                    c * CELL,
                    r * CELL,
                    (c + 1) * CELL,
                    (r + 1) * CELL,
                    fill=DEAD,
                    outline=GRID_LINE
                )
                for c in range(COLS)
            ]
            for r in range(ROWS)
        ]

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def _bind_keys(self):

        self.root.bind("<space>", lambda e: self.toggle())
        self.root.bind("<Return>", lambda e: self.step_once())
        self.root.bind("<Escape>", lambda e: self.clear())
        self.root.bind("r", lambda e: self.randomize())
        self.root.bind("p", lambda e: self.place_pattern())

    # -------- Drawing --------

    def cell_at(self, event):

        c = event.x // CELL
        r = event.y // CELL

        if 0 <= r < ROWS and 0 <= c < COLS:
            return (r, c)

        return None

    def set_cell_color(self, r, c):

        color = ALIVE if (r, c) in self.live else DEAD

        self.canvas.itemconfig(
            self.rects[r][c],
            fill=color
        )

    def redraw_all(self):

        for r in range(ROWS):
            for c in range(COLS):
                self.set_cell_color(r, c)

        self.update_status()

    def update_status(self):

        self.status.config(
            text=f"Generation: {self.generation} | "
                 f"Live cells: {len(self.live)}"
        )

    # -------- Mouse events --------

    def on_press(self, event):

        cell = self.cell_at(event)

        if cell:
            self.paint_value = cell not in self.live
            self.paint(cell)

    def on_drag(self, event):

        cell = self.cell_at(event)

        if cell:
            self.paint(cell)

    def paint(self, cell):

        if self.paint_value:
            self.live.add(cell)
        else:
            self.live.discard(cell)

        self.set_cell_color(*cell)
        self.update_status()

    # -------- Simulation logic --------

    def next_generation(self):

        counts = Counter()
        wrap = self.wrap.get()

        for r, c in self.live:

            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):

                    if dr == 0 and dc == 0:
                        continue

                    nr = r + dr
                    nc = c + dc

                    if wrap:
                        nr %= ROWS
                        nc %= COLS

                    elif not (
                        0 <= nr < ROWS and
                        0 <= nc < COLS
                    ):
                        continue

                    counts[(nr, nc)] += 1

        new_live = {
            cell
            for cell, count in counts.items()
            if count == 3 or (
                cell in self.live and count == 2
            )
        }

        return new_live

    def step_once(self):

        new = self.next_generation()

        changed = self.live ^ new

        self.live = new

        for cell in changed:
            self.set_cell_color(*cell)

        self.generation += 1
        self.update_status()

    def loop(self):

        if self.running:

            self.step_once()

            delay = max(1, int(1000 / self.speed.get()))

            self.root.after(delay, self.loop)

    def toggle(self):

        self.running = not self.running

        self.play_btn.config(
            text="⁙ pause" if self.running else "⁙ play"
        )

        if self.running:
            self.loop()

    # -------- Actions --------

    def clear(self):

        self.running = False
        self.play_btn.config(text="⁙ play")

        self.live.clear()
        self.generation = 0

        self.redraw_all()

    def randomize(self):

        self.live = {
            (r, c)
            for r in range(ROWS)
            for c in range(COLS)
            if random.random() < 0.3
        }

        self.generation = 0
        self.redraw_all()

    def place_pattern(self):

        pattern_name = self.pattern_box.get()
        cells = PATTERNS[pattern_name]

        if pattern_name == "Gosper glider gun":
            off_r, off_c = 2, 2
        else:
            off_r = ROWS // 2 - 2
            off_c = COLS // 2 - 2

        for r, c in cells:

            nr = r + off_r
            nc = c + off_c

            if 0 <= nr < ROWS and 0 <= nc < COLS:
                self.live.add((nr, nc))

        self.redraw_all()


# -------- Main execution --------

if __name__ == "__main__":

    root = tk.Tk()

    app = LifeApp(root)

    root.mainloop()
