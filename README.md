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

- `tab` / mouse: move between controls and tabs
- `s`: open the Scribe tab
- `r`: open the Reign tab
- `b`: open the Battle tab
- `l`: open the Logs tab
- `e`: open the Encyclopedia tab
- `up` / `down`: select a shop row within the current column
- `left` / `right`: move between the unit, building, and action shop columns
- `enter`: create or use the selected shop item
- `n`: start a new run after game over
- `q`: quit

The Scribe tab shows current stores, per-second changes, and separate owned
unit and building lists. The Reign tab splits units, buildings, and actions into
three columns. The Battle tab shows the next threat roll and current threat
countdowns. The Logs tab shows the last 25 action and event messages. The
Encyclopedia tab lists current resources, units, buildings, actions, and threats
from game data. Green entries are ready to buy or use, while blocked entries are
red and cooldowns are yellow.

The status panel shows the current run time while playing. Game over shows the
final run length.

Only the currently selected shop item shows its recipe or cost below the shop.

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
- rangers have no upkeep or production
- captains have no upkeep or production
- watchposts have no upkeep or production
- sorcerers have no upkeep or production
- each farm: +0.2 food
- each mine: +0.2 iron
- each quarry: +0.2 stone
- each arcane tower: +0.1 shell
- storage buildings do not produce resources; each one raises every resource
  capacity by 100

Resource capacity:

- each resource has a base capacity of 100
- each Storage building adds +100 capacity to every resource
- positive passive production and action rewards are discarded above capacity
- spending and negative production still reduce resources normally

One-time actions:

- Hunt: requires 1 soldier, has a 1 minute cooldown, and can lose the soldier,
  gain 5 food, or gain 5 food and 5 shell.
- Patrol: requires 3 soldiers, costs 10 food, has a 2 minute cooldown, and can
  lose soldiers, return peacefully, find gold, catch a shell fairy, rescue a
  worker, stir up a new threat, or recover food and iron.
- Expedition: requires 1 captain and 10 soldiers, costs 25 food and 5 gold, has
  a 5 minute cooldown, and can lose soldiers, recover large resource caches,
  find a shell shrine, liberate workers, stir up a new threat, or recruit a
  captain.
- Kindle the Pyre: requires 1 sorcerer and 1 arcane tower, costs 100 wood, has
  a 10 minute cooldown, and can leave only ash, reveal 10-50 shell, or yield
  5-10 gold. Rewards scale with sorcerers and arcane towers.
- Defend: requires 1 catapult and an active threat, has a 5 minute cooldown,
  and has a 25-75% chance to stop the oldest active threat. Each catapult and
  captain adds 10% success chance, capped at 75%. Any defense attempt has a
  15% chance to break 1 catapult.

Rangers:

- Ranger: costs 1 soldier, 5 gold, and 10 shell.
- While at least 1 ranger exists, hunts automatically depart whenever the hunt
  cooldown and normal hunt prerequisites are ready.
- Automated Hunt entries are labeled Hunt (A).

Captains:

- Captain: costs 1 soldier and 10 gold.
- While at least 1 captain exists, patrols automatically depart whenever the
  patrol cooldown and normal patrol prerequisites are ready.
- Automated Patrol entries are labeled Patrol (A).
- Expeditions are never automatic.

Sorcery and siege:

- Watchpost: costs 10 gold and 50 wood.
- While at least 1 watchpost exists, Defend automatically runs whenever the
  defend cooldown and normal defend prerequisites are ready.
- Automated Defend entries are labeled Defend (A).
- Sorcerer: costs 1 soldier and 50 shell.
- Arcane Tower: costs 1 sorcerer and 250 stone.
- Catapult: costs 5 gold, 100 wood, and 200 stone.
- Storage: costs scale by the next Storage number: 1st costs 1 worker, 50 wood,
  and 25 stone; 2nd costs 2 workers, 100 wood, and 50 stone; adds +100 capacity
  to every resource.

Threats:

- Every 10 minutes, a new threat is added.
- Each threat has a 5 minute countdown.
- Run time increases threat criticality every 10 minutes: threats destroy 1
  additional building and arrive 30 seconds faster per tier, capped at 5
  destroyed buildings and a 90 second countdown.
- Goblin Raid destroys up to 2 farms when its countdown reaches zero.
- Mine Saboteurs destroy up to 1 mine when their countdown reaches zero.
- Quarry Raiders destroy up to 1 quarry when their countdown reaches zero.
- Tower Arson destroys up to 1 arcane tower when its countdown reaches zero.
- Defend can remove the oldest active threat before it can resolve.

Story:

- The Story panel shows the last 3 action and event messages.
- The Logs tab shows the last 25 action and event messages.

Resource values are clamped at zero. If food reaches zero, the player dies, the
run ends, and the game opens to the saved game-over state until restarted.

## Current Scope

This prototype includes resource production, worker creation, worker upgrades,
farm, mine, quarry, and storage construction, resource capacity limits,
persistent saves, food-based game over,
threat countdowns, defensive catapults, an encyclopedia, a keyboard-first TUI,
and placeholder PvE target data in code for later work. Attack planning and
progression systems are intentionally out of scope for the initial commit.
