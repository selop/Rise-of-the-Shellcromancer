from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

from shellcromancer import actions
from shellcromancer.buildings import BuildingType
from shellcromancer.economy import mark_dead_if_food_depleted, tick
from shellcromancer.game_state import GameState
from shellcromancer.persistence import load_state, save_state
from shellcromancer.resources import ALL_RESOURCES, ResourceType
from shellcromancer.units import UnitType


@dataclass(frozen=True)
class MenuAction:
    label: str
    cost: str
    resource_costs: dict[ResourceType, float]
    unit_costs: dict[UnitType, int]
    run: Callable[[GameState], actions.ActionResult]
    cooldown_key: str | None = None
    building_costs: dict[BuildingType, int] | None = None


UNIT_ACTIONS = (
    MenuAction(
        label="Worker",
        cost="10 shell",
        resource_costs={ResourceType.SHELL: 10.0},
        unit_costs={},
        run=actions.create_worker,
    ),
    MenuAction(
        label="Soldier",
        cost="1 worker, 5 iron, 5 shell",
        resource_costs={
            ResourceType.IRON: 5.0,
            ResourceType.SHELL: 5.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.upgrade_worker_to_soldier,
    ),
    MenuAction(
        label="Lumberjack",
        cost="1 worker, 5 wood, 2 shell",
        resource_costs={
            ResourceType.WOOD: 5.0,
            ResourceType.SHELL: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.upgrade_worker_to_lumberjack,
    ),
    MenuAction(
        label="Captain",
        cost="1 worker, 10 gold",
        resource_costs={ResourceType.GOLD: 10.0},
        unit_costs={UnitType.WORKER: 1},
        run=actions.promote_worker_to_captain,
    ),
    MenuAction(
        label="Sorcerer",
        cost="1 soldier, 50 shell",
        resource_costs={ResourceType.SHELL: 50.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.upgrade_soldier_to_sorcerer,
    ),
)


BUILDING_ACTIONS = (
    MenuAction(
        label="Farm",
        cost="10 wood, 10 stone, 2 iron, 1 worker",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_farm,
    ),
    MenuAction(
        label="Mine",
        cost="10 wood, 10 stone, 2 iron, 1 worker",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_mine,
    ),
    MenuAction(
        label="Quarry",
        cost="10 wood, 10 stone, 2 iron, 1 worker",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_quarry,
    ),
    MenuAction(
        label="Arcane Tower",
        cost="1 sorcerer, 250 stone",
        resource_costs={ResourceType.STONE: 250.0},
        unit_costs={UnitType.SORCERER: 1},
        run=actions.build_arcane_tower,
    ),
    MenuAction(
        label="Catapult",
        cost="5 gold, 100 wood, 200 stone",
        resource_costs={
            ResourceType.GOLD: 5.0,
            ResourceType.WOOD: 100.0,
            ResourceType.STONE: 200.0,
        },
        unit_costs={},
        run=actions.build_catapult,
    ),
)


ONE_TIME_ACTIONS = (
    MenuAction(
        label="Hunt",
        cost="Requires 1 soldier. May lose the soldier or return with food and shell.",
        resource_costs={},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.hunt,
        cooldown_key=actions.HUNT_ACTION_KEY,
    ),
    MenuAction(
        label="Patrol",
        cost=(
            "3 soldiers, 10 food. Mixed risk with gold, shell income, "
            "worker, food, and iron rewards"
        ),
        resource_costs={ResourceType.FOOD: 10.0},
        unit_costs={UnitType.SOLDIER: 3},
        run=actions.patrol,
        cooldown_key=actions.PATROL_ACTION_KEY,
    ),
    MenuAction(
        label="Kindle the Pyre",
        cost="1 sorcerer, 100 wood. Burn offerings for shell or gold.",
        resource_costs={ResourceType.WOOD: 100.0},
        unit_costs={UnitType.SORCERER: 1},
        run=actions.kindle_the_pyre,
        cooldown_key=actions.KINDLE_PYRE_ACTION_KEY,
    ),
    MenuAction(
        label="Defend",
        cost="Requires 1 catapult. Battle effect will be implemented later.",
        resource_costs={},
        unit_costs={},
        run=actions.defend,
        building_costs={BuildingType.CATAPULT: 1},
    ),
)


MENU_COLUMNS = (UNIT_ACTIONS, BUILDING_ACTIONS, ONE_TIME_ACTIONS)
MENU_ACTIONS = tuple(action for column in MENU_COLUMNS for action in column)
PANEL_WIDTH = 78


class ShellcromancerApp(App[None]):
    CSS = """
    Screen {
        padding: 1 2;
    }

    #game {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("up,k", "select_previous", "Previous action"),
        Binding("down,j", "select_next", "Next action"),
        Binding("left,h", "select_left", "Left column"),
        Binding("right,l", "select_right", "Right column"),
        Binding("enter", "execute_selected", "Execute selected"),
        Binding("r", "reset", "Restart after death"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, save_path: Path | None = None) -> None:
        super().__init__()
        self.save_path = save_path
        self.state = load_state(self.save_path)
        mark_dead_if_food_depleted(self.state)
        self.selected_action_index = 0
        self.game_view = Static(id="game")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield self.game_view

    def on_mount(self) -> None:
        self._refresh_view()
        self.set_interval(1.0, self._on_tick)

    def _on_tick(self) -> None:
        tick(self.state)
        save_state(self.state, self.save_path)
        self._refresh_view()

    def action_select_previous(self) -> None:
        column, row = selected_position(self.selected_action_index)
        self.selected_action_index = action_index(column, max(0, row - 1))
        self._refresh_view()

    def action_select_next(self) -> None:
        column, row = selected_position(self.selected_action_index)
        max_row = len(MENU_COLUMNS[column]) - 1
        self.selected_action_index = action_index(column, min(max_row, row + 1))
        self._refresh_view()

    def action_select_left(self) -> None:
        column, row = selected_position(self.selected_action_index)
        self.selected_action_index = action_index(max(0, column - 1), row)
        self._refresh_view()

    def action_select_right(self) -> None:
        column, row = selected_position(self.selected_action_index)
        self.selected_action_index = action_index(
            min(len(MENU_COLUMNS) - 1, column + 1), row
        )
        self._refresh_view()

    def action_execute_selected(self) -> None:
        if self.state.is_dead:
            self._refresh_view()
            return

        selected_action(self.selected_action_index).run(self.state)
        mark_dead_if_food_depleted(self.state)
        save_state(self.state, self.save_path)
        self._refresh_view()

    def action_reset(self) -> None:
        if not self.state.is_dead:
            return

        self.state = GameState()
        save_state(self.state, self.save_path)
        self._refresh_view()

    def _refresh_view(self) -> None:
        self.game_view.update(render_state(self.state, self.selected_action_index))


def is_action_affordable(state: GameState, menu_action: MenuAction) -> bool:
    if state.is_dead:
        return False

    has_resources = all(
        state.resources[resource] >= amount
        for resource, amount in menu_action.resource_costs.items()
    )
    has_units = all(
        state.units[unit] >= amount for unit, amount in menu_action.unit_costs.items()
    )
    has_buildings = all(
        state.buildings[building] >= amount
        for building, amount in (menu_action.building_costs or {}).items()
    )
    cooldown_ready = (
        menu_action.cooldown_key is None
        or state.action_cooldowns.get(menu_action.cooldown_key, 0.0) <= 0
    )
    return has_resources and has_units and has_buildings and cooldown_ready


def action_status_label(state: GameState, menu_action: MenuAction) -> str:
    if menu_action.cooldown_key is not None:
        cooldown = state.action_cooldowns.get(menu_action.cooldown_key, 0.0)
        if cooldown > 0:
            return f"[red]Cooldown {format_cooldown(cooldown)}[/]"

    if is_action_affordable(state, menu_action):
        return "[green]Ready[/]"
    return "[red]Missing requirements[/]"


def action_index(column: int, row: int) -> int:
    bounded_column = min(max(0, column), len(MENU_COLUMNS) - 1)
    bounded_row = min(max(0, row), len(MENU_COLUMNS[bounded_column]) - 1)
    return (
        sum(len(menu_column) for menu_column in MENU_COLUMNS[:bounded_column])
        + bounded_row
    )


def selected_position(selected_action_index: int) -> tuple[int, int]:
    bounded_index = min(max(0, selected_action_index), len(MENU_ACTIONS) - 1)
    running_total = 0
    for column, menu_column in enumerate(MENU_COLUMNS):
        next_total = running_total + len(menu_column)
        if bounded_index < next_total:
            return column, bounded_index - running_total
        running_total = next_total
    return len(MENU_COLUMNS) - 1, len(MENU_COLUMNS[-1]) - 1


def selected_action(selected_action_index: int) -> MenuAction:
    column, row = selected_position(selected_action_index)
    return MENU_COLUMNS[column][row]


def format_cooldown(seconds: float) -> str:
    remaining = max(0, int(seconds))
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes}:{seconds:02d}"


def format_cell_suffix(state: GameState, menu_action: MenuAction, count: int | None) -> str:
    if menu_action.cooldown_key is not None:
        remaining = state.action_cooldowns.get(menu_action.cooldown_key, 0.0)
        return format_cooldown(remaining)
    if count is None:
        return ""
    return f"{count or 0:>3}"


def format_selectable_cell(
    state: GameState,
    menu_action: MenuAction,
    index: int,
    selected_index: int,
    count: int | None,
) -> str:
    selected = index == selected_index
    affordable = is_action_affordable(state, menu_action)
    marker = ">" if selected else " "
    color = "green" if affordable else "red"
    style = f"reverse {color}" if selected else color
    suffix = format_cell_suffix(state, menu_action, count)
    line = f"{marker} {menu_action.label:<12} {suffix:>5}"
    return f"[{style}]{line:<24}[/]"


def format_overview(state: GameState, selected_action_index: int) -> list[str]:
    headers = ("Creatures", "Buildings", "Actions")
    rows = [
        (UNIT_ACTIONS[0], state.units[UnitType.WORKER]),
        (UNIT_ACTIONS[1], state.units[UnitType.SOLDIER]),
        (UNIT_ACTIONS[2], state.units[UnitType.LUMBERJACK]),
        (UNIT_ACTIONS[3], state.units[UnitType.CAPTAIN]),
        (UNIT_ACTIONS[4], state.units[UnitType.SORCERER]),
    ]
    building_rows = [
        (BUILDING_ACTIONS[0], state.buildings[BuildingType.FARM]),
        (BUILDING_ACTIONS[1], state.buildings[BuildingType.MINE]),
        (BUILDING_ACTIONS[2], state.buildings[BuildingType.QUARRY]),
        (BUILDING_ACTIONS[3], state.buildings[BuildingType.ARCANE_TOWER]),
        (BUILDING_ACTIONS[4], state.buildings[BuildingType.CATAPULT]),
    ]
    action_rows = [(action, None) for action in ONE_TIME_ACTIONS]
    column_rows = (rows, building_rows, action_rows)

    lines = [f"{headers[0]:<27}{headers[1]:<27}{headers[2]}"]
    for row in range(max(len(column) for column in column_rows)):
        cells = []
        for column, entries in enumerate(column_rows):
            if row >= len(entries):
                cells.append(" " * 24)
                continue
            menu_action, count = entries[row]
            cells.append(
                format_selectable_cell(
                    state,
                    menu_action,
                    action_index(column, row),
                    selected_action_index,
                    count,
                )
            )
        lines.append("   ".join(cells))
    return lines


def render_state(state: GameState, selected_action_index: int = 0) -> str:
    if state.is_dead:
        return render_game_over(state)

    resource_lines = []
    for resource in ALL_RESOURCES:
        value = state.resources[resource]
        delta = state.last_delta[resource]
        resource_lines.append(f"{resource.value:<6} {value:>6.1f}   ({delta:+.1f}/s)")

    menu_action = selected_action(selected_action_index)
    readiness = action_status_label(state, menu_action)

    return "\n".join(
        [
            render_panel(
                "Rise of the Shellcromancer",
                ["Gather, build, patrol, and keep the stores from running dry."],
            ),
            "",
            render_panel("Resources", resource_lines),
            "",
            render_panel("Overview", format_overview(state, selected_action_index)),
            "",
            render_panel(
                "Selected",
                [
                    f"{menu_action.label}: {readiness}",
                    f"Cost: {menu_action.cost}",
                ],
            ),
            "",
            render_panel(
                "Keybindings",
                [
                    "up/down or k/j     Select row",
                    "left/right or h/l  Select column",
                    "enter              Use selected unit/building/action",
                    "q                  Quit",
                ],
            ),
            "",
            render_panel("Status", [f"Last action: {state.last_action_message}"]),
        ]
    )


def render_game_over(state: GameState) -> str:
    resource_lines = []
    for resource in ALL_RESOURCES:
        value = state.resources[resource]
        delta = state.last_delta[resource]
        resource_lines.append(f"{resource.value:<6} {value:>6.1f}   ({delta:+.1f}/s)")

    return "\n".join(
        [
            render_panel(
                "Rise of the Shellcromancer",
                ["Game Over", "Food reached 0. The run has ended."],
            ),
            "",
            render_panel("Final Stores", resource_lines),
            "",
            render_panel("Status", [state.last_action_message]),
            "",
            render_panel(
                "Keybindings",
                [
                    "r                  Start a new run",
                    "q                  Quit",
                ],
            ),
        ]
    )


def render_panel(title: str, lines: list[str], width: int = PANEL_WIDTH) -> str:
    content_width = width - 4
    top = render_panel_top(title, width)
    border = "+" + "-" * (width - 2) + "+"
    body = []

    for line in lines or [""]:
        for row in panel_rows(line, content_width):
            body.append(f"| {row:<{content_width}} |")

    return "\n".join([top, *body, border])


def render_panel_top(title: str, width: int) -> str:
    title_text = f" {title} "
    border_width = width - 2
    if len(title_text) >= border_width:
        return "+" + "-" * border_width + "+"
    return "+" + title_text + "-" * (border_width - len(title_text)) + "+"


def panel_rows(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]

    if "[" in line and "]" in line:
        return [line]

    return wrap(line, width=width) or [""]


def main() -> None:
    ShellcromancerApp().run()


if __name__ == "__main__":
    main()
