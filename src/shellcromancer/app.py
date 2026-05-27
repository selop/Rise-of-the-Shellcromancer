from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
)

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
SHOP_COLUMN_LABELS = ("Units", "Buildings", "Actions")


class ShellcromancerApp(App[None]):
    TITLE = "Rise of the Shellcromancer"

    CSS = """
    Screen {
        layout: vertical;
    }

    TabbedContent {
        height: 1fr;
    }

    DataTable {
        width: 100%;
    }

    .overview-assets {
        height: auto;
    }

    .overview-column {
        width: 1fr;
        height: auto;
    }

    #shop-view {
        padding: 1;
        height: auto;
    }

    #status {
        dock: bottom;
        height: auto;
        padding: 1 2;
        border-top: solid $surface-lighten-1;
    }

    .section-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    #selected {
        padding: 1 1;
        min-height: 4;
    }

    #execute {
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding("up,k", "select_previous", "Previous row", priority=True),
        Binding("down,j", "select_next", "Next row", priority=True),
        Binding("left,h", "select_left", "Previous column", priority=True),
        Binding("right,l", "select_right", "Next column", priority=True),
        Binding("enter", "execute_selected", "Use selected", priority=True),
        Binding("e", "execute_selected", "Use selected", priority=True),
        Binding("r", "reset", "Restart after death"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, save_path: Path | None = None) -> None:
        super().__init__()
        self.save_path = save_path
        self.state = load_state(self.save_path)
        mark_dead_if_food_depleted(self.state)
        self.selected_action_index = 0
        self.resource_table = DataTable(
            id="resource-table", cursor_type="row", zebra_stripes=True
        )
        self.unit_table = DataTable(
            id="unit-table", cursor_type="row", zebra_stripes=True
        )
        self.building_table = DataTable(
            id="building-table", cursor_type="row", zebra_stripes=True
        )
        self.shop_view = Static(id="shop-view")
        self.selected_view = Static(id="selected")
        self.status_view = Static(id="status")
        self.execute_button = Button(
            "Use Selected", id="execute", variant="primary", action="execute_selected"
        )
        self.tables_ready = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="resources-tab"):
            with TabPane("Resources", id="resources-tab"):
                yield Static("Resources", classes="section-title")
                yield self.resource_table
                with Horizontal(classes="overview-assets"):
                    with Vertical(classes="overview-column"):
                        yield Static("Units", classes="section-title")
                        yield self.unit_table
                    with Vertical(classes="overview-column"):
                        yield Static("Buildings", classes="section-title")
                        yield self.building_table
            with TabPane("Shop", id="shop-tab"):
                yield self.shop_view
                yield self.selected_view
                yield self.execute_button
        yield self.status_view
        yield Footer()

    def on_mount(self) -> None:
        self.resource_table.add_columns("Resource", "Amount", "Per Second")
        self.unit_table.add_columns("Unit", "Owned")
        self.building_table.add_columns("Building", "Owned")
        self.tables_ready = True
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
        if not self.tables_ready:
            return

        self._refresh_resource_table()
        self._refresh_unit_table()
        self._refresh_building_table()
        self._refresh_shop_view()
        self._refresh_selected_view()
        self._refresh_status_view()

    def _refresh_resource_table(self) -> None:
        self.resource_table.clear()
        for resource in ALL_RESOURCES:
            self.resource_table.add_row(
                resource.value,
                f"{self.state.resources[resource]:.1f}",
                f"{self.state.last_delta[resource]:+.1f}/s",
            )

    def _refresh_unit_table(self) -> None:
        self.unit_table.clear()
        for menu_action, unit_type in zip(UNIT_ACTIONS, UnitType, strict=True):
            self.unit_table.add_row(menu_action.label, str(self.state.units[unit_type]))

    def _refresh_building_table(self) -> None:
        self.building_table.clear()
        for menu_action, building_type in zip(
            BUILDING_ACTIONS, BuildingType, strict=True
        ):
            self.building_table.add_row(
                menu_action.label, str(self.state.buildings[building_type])
            )

    def _refresh_shop_view(self) -> None:
        self.shop_view.update(format_shop_text(self.state, self.selected_action_index))

    def _refresh_selected_view(self) -> None:
        menu_action = selected_action(self.selected_action_index)
        readiness = action_status_label(self.state, menu_action)
        self.selected_view.update(
            f"{menu_action.label}: {readiness}\nCost: {menu_action.cost}"
        )
        self.execute_button.disabled = self.state.is_dead or not is_action_affordable(
            self.state, menu_action
        )

    def _refresh_status_view(self) -> None:
        if self.state.is_dead:
            self.status_view.update(
                f"[red]Game Over[/]\n{self.state.last_action_message}\nPress r to start a new run."
            )
            return

        self.status_view.update(f"Last action: {self.state.last_action_message}")


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


def action_status_text(state: GameState, menu_action: MenuAction) -> str:
    if menu_action.cooldown_key is not None:
        cooldown = state.action_cooldowns.get(menu_action.cooldown_key, 0.0)
        if cooldown > 0:
            return f"Cooldown {format_cooldown(cooldown)}"

    if is_action_affordable(state, menu_action):
        return "Ready"
    return "Missing requirements"


def action_status_style(state: GameState, menu_action: MenuAction) -> str:
    if is_action_affordable(state, menu_action):
        return "green"
    if menu_action.cooldown_key is not None:
        cooldown = state.action_cooldowns.get(menu_action.cooldown_key, 0.0)
        if cooldown > 0:
            return "yellow"
    return "red"


def action_status_label(state: GameState, menu_action: MenuAction) -> str:
    status = action_status_text(state, menu_action)
    if status == "Ready":
        return "[green]Ready[/]"
    if status.startswith("Cooldown"):
        return f"[yellow]{status}[/]"
    return f"[red]{status}[/]"


def owned_text(state: GameState, column: int, row: int) -> str:
    if column == 0:
        return str(state.units[tuple(UnitType)[row]])
    if column == 1:
        return str(state.buildings[tuple(BuildingType)[row]])
    return ""


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
    unit_lines = [
        f"{action.label:<16} {state.units[unit_type]}"
        for action, unit_type in zip(UNIT_ACTIONS, UnitType, strict=True)
    ]
    building_lines = [
        f"{action.label:<16} {state.buildings[building_type]}"
        for action, building_type in zip(BUILDING_ACTIONS, BuildingType, strict=True)
    ]
    shop_lines = format_shop_columns(state, selected_action_index)

    return "\n".join(
        [
            "Rise of the Shellcromancer",
            "",
            "Resources Tab",
            *resource_lines,
            "",
            "Units",
            *unit_lines,
            "",
            "Buildings",
            *building_lines,
            "",
            "Shop Tab",
            *shop_lines,
            "",
            "Selected",
            f"{menu_action.label}: {readiness}",
            f"Cost: {menu_action.cost}",
            "",
            f"Last action: {state.last_action_message}",
        ]
    )


def format_shop_columns(state: GameState, selected_action_index: int) -> list[str]:
    rows = [SHOP_COLUMN_LABELS]
    max_rows = max(len(column) for column in MENU_COLUMNS)
    selected_column, selected_row = selected_position(selected_action_index)
    for row in range(max_rows):
        cells = []
        for column, menu_actions in enumerate(MENU_COLUMNS):
            if row >= len(menu_actions):
                cells.append("")
                continue

            menu_action = menu_actions[row]
            status = action_status_label(state, menu_action)
            owned = owned_text(state, column, row)
            marker = ">" if column == selected_column and row == selected_row else " "
            cells.append(f"{marker} {menu_action.label:<14} {owned:<5} {status}")
        rows.append(tuple(cells))

    return [
        f"{unit:<34} {building:<40} {action}"
        for unit, building, action in rows
    ]


def format_shop_text(state: GameState, selected_action_index: int) -> Text:
    selected_column, selected_row = selected_position(selected_action_index)
    widths = (34, 40, 40)
    text = Text()

    for label, width in zip(SHOP_COLUMN_LABELS, widths, strict=True):
        text.append(label.ljust(width), style="bold")
    text.append("\n")

    max_rows = max(len(column) for column in MENU_COLUMNS)
    for row in range(max_rows):
        for column, menu_actions in enumerate(MENU_COLUMNS):
            width = widths[column]
            if row >= len(menu_actions):
                text.append(" " * width)
                continue

            menu_action = menu_actions[row]
            marker = ">" if column == selected_column and row == selected_row else " "
            status = action_status_text(state, menu_action)
            cell = (
                f"{marker} {menu_action.label:<14} "
                f"{owned_text(state, column, row):<5} {status}"
            )
            style = action_status_style(state, menu_action)
            if column == selected_column and row == selected_row:
                style = f"reverse {style}"
            text.append(cell[:width].ljust(width), style=style)
        text.append("\n")

    return text


def render_game_over(state: GameState) -> str:
    resource_lines = []
    for resource in ALL_RESOURCES:
        value = state.resources[resource]
        delta = state.last_delta[resource]
        resource_lines.append(f"{resource.value:<6} {value:>6.1f}   ({delta:+.1f}/s)")

    return "\n".join(
        [
            "Rise of the Shellcromancer",
            "Game Over",
            "Food reached 0. The run has ended.",
            "",
            "Final Stores",
            *resource_lines,
            "",
            state.last_action_message,
            "",
            "Press r to start a new run. Press q to quit.",
        ]
    )


def main() -> None:
    ShellcromancerApp().run()


if __name__ == "__main__":
    main()
