# Rise of the Shellcromancer

Rise of the Shellcromancer is a single-player PvE semi-idle incremental TUI
game. You are the Shellcromancer, gathering resources, creating creatures,
building production, and preparing for future attacks against PvE targets.

## Tech Stack

- Python
- Textual
- pytest

## Install

```bash
uv sync
```

## Run

```bash
uv run shellcromancer
```

You can also run the module directly:

```bash
uv run python -m shellcromancer.app
```

## Controls

- `up` / `down`: select a row
- `k` / `j`: select a row
- `left` / `right`: select a column
- `h` / `l`: select a column
- `enter`: create or use the selected creature, building, or action
- `r`: start a new run after game over
- `q`: quit

The unit and building overview acts as the create menu. Green entries are ready,
and red entries are missing required resources or workers. The cost panel below
the overview only shows the cost for the currently selected entry.

The Actions column contains one-time actions. Cooldowns are shown behind the
action name.

Game progress is saved automatically to the Linux XDG data directory. By
default, the save file is `~/.local/share/shellcromancer/save.json`; if
`XDG_DATA_HOME` is set, the game uses `$XDG_DATA_HOME/shellcromancer/save.json`.

## Current Economy Rules

The game ticks once per second. All per-second resource deltas are calculated
first, then applied to the game state before the UI refreshes.

Starting resources:

- wood: 10
- stone: 10
- iron: 10
- food: 10
- shell: 10
- gold: 0

Per-second economy:

- base: +0.1 wood, stone, iron, food, and shell
- gold has no base increment
- each worker: -0.1 food
- each soldier: -0.2 food
- each lumberjack: +0.2 wood, -0.1 food
- captains have no upkeep or production
- sorcerers have no upkeep or production
- each farm: +0.2 food
- each mine: +0.2 iron
- each quarry: +0.2 stone
- each arcane tower: +0.1 shell

One-time actions:

- Hunt: requires 1 soldier, has a 1 minute cooldown, and can lose the soldier,
  gain 5 food, or gain 5 food and 5 shell.
- Patrol: requires 3 soldiers, costs 10 food, has a 2 minute cooldown, and can
  lose soldiers, return peacefully, find gold, catch a shell fairy, rescue a
  worker, or recover food and iron.
- Kindle the Pyre: requires 1 sorcerer, costs 100 wood, has a 10 minute
  cooldown, and can leave only ash, reveal 10-50 shell, or yield 5-10 gold.
- Defend: requires 1 catapult. The battle effect is not implemented yet.

Captains:

- Captain: costs 1 worker and 10 gold.
- While at least 1 captain exists, patrols automatically depart whenever the
  patrol cooldown and normal patrol prerequisites are ready.

Sorcery and siege:

- Sorcerer: costs 1 soldier and 50 shell.
- Arcane Tower: costs 1 sorcerer and 250 stone.
- Catapult: costs 5 gold, 100 wood, and 200 stone.

Resource values are clamped at zero. If food reaches zero, the player dies, the
run ends, and the game opens to the saved game-over state until restarted.

## Current Scope

This prototype includes resource production, worker creation, worker upgrades,
farm, mine, and quarry construction, persistent saves, food-based game over, a
one-screen keyboard-first TUI, and placeholder PvE target data in code for later
work. The TUI only shows implemented gameplay features. Combat, attack
planning, and progression systems are intentionally out of scope for the initial
commit.
