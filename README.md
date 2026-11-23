# Conway's Game of Life

A graphical implementation of Conway's Game of Life built with Python and Tkinter.
The application provides a 45 x 70 cell grid, preset patterns, mouse editing,
simulation controls, and adjustable speed.

## Requirements

- Python 3
- Tkinter (included with most standard Python installations)

No third-party packages are required.

## Running the Application

From the project directory, run:

```powershell
python game_of_life.py
```

The project also includes `vtwo.py`, an alternate Tkinter implementation.

## Controls

### Toolbar

- **Play / Pause** — start or stop the simulation
- **Step** — advance exactly one generation
- **Clear** — remove every live cell and reset the generation count
- **Random** — fill the grid with randomly selected live cells
- **Pattern** — choose a preset pattern to place on the grid
- **Place** — add the selected pattern to the grid
- **Wrap** — make the grid edges wrap around
- **Speed** — change the number of generations per second

### Mouse

Click or drag across a cell to add or remove live cells.

### Keyboard

| Key | Action |
| --- | --- |
| `Space` | Play or pause |
| `Enter` | Advance one generation |
| `Escape` | Clear the grid |
| `R` | Randomize the grid |
| `P` | Place the selected pattern |

## Preset Patterns

The application includes:

- Glider
- R-pentomino
- Acorn
- Lightweight spaceship
- Gosper glider gun

## Rules

Each generation uses Conway's rules:

1. A live cell with two or three live neighbors survives.
2. A live cell with fewer than two or more than three neighbors dies.
3. A dead cell with exactly three live neighbors becomes alive.

When **Wrap** is enabled, cells on opposite edges are considered neighbors.

## Demo

<video src="./demo_of_v1.mp4" controls title="Game of Life demo"></video>

[Download or view the demo video](./demo_of_v1.mp4)
