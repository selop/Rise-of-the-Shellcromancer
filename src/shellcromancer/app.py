from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
)

from shellcromancer import actions
from shellcromancer.buildings import BUILDING_DEFINITIONS, BuildingType
from shellcromancer.economy import mark_dead_if_food_depleted, tick
from shellcromancer.game_state import GameState
from shellcromancer.persistence import default_save_path, load_state, save_state
from shellcromancer.resources import ALL_RESOURCES, ResourceType
from shellcromancer.threats import (
    THREAT_DEFINITIONS,
    ThreatDefinition,
    scaled_threat_countdown,
    scaled_threat_damage,
)
from shellcromancer.units import UNIT_DEFINITIONS, UnitType


@dataclass(frozen=True)
class MenuAction:
    label: str
    cost: str
    resource_costs: dict[ResourceType, float]
    unit_costs: dict[UnitType, int]
    run: Callable[[GameState], actions.ActionResult]
    cooldown_key: str | None = None
    building_costs: dict[BuildingType, int] | None = None
    requires_active_threat: bool = False


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
        label="Ranger",
        cost="1 soldier, 5 gold, 10 shell",
        resource_costs={ResourceType.GOLD: 5.0, ResourceType.SHELL: 10.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.upgrade_soldier_to_ranger,
    ),
    MenuAction(
        label="Captain",
        cost="1 soldier, 10 gold",
        resource_costs={ResourceType.GOLD: 10.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.promote_worker_to_captain,
    ),
    MenuAction(
        label="Watchpost",
        cost="10 gold, 50 wood",
        resource_costs={ResourceType.GOLD: 10.0, ResourceType.WOOD: 50.0},
        unit_costs={},
        run=actions.create_watchpost,
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
        label="Expedition",
        cost=(
            "1 captain, 10 soldiers, 25 food, 5 gold. High-risk trek with "
            "major resource, worker, captain, and shell income rewards."
        ),
        resource_costs={ResourceType.FOOD: 25.0, ResourceType.GOLD: 5.0},
        unit_costs={UnitType.CAPTAIN: 1, UnitType.SOLDIER: 10},
        run=actions.expedition,
        cooldown_key=actions.EXPEDITION_ACTION_KEY,
    ),
    MenuAction(
        label="Kindle the Pyre",
        cost="1 sorcerer, 1 arcane tower, 100 wood. Burn offerings for shell or gold.",
        resource_costs={ResourceType.WOOD: 100.0},
        unit_costs={UnitType.SORCERER: 1},
        run=actions.kindle_the_pyre,
        cooldown_key=actions.KINDLE_PYRE_ACTION_KEY,
        building_costs={BuildingType.ARCANE_TOWER: 1},
    ),
    MenuAction(
        label="Defend",
        cost=(
            "Requires 1 catapult and an active threat. 25-75% chance based on "
            "catapults and captains, with a 5 minute cooldown."
        ),
        resource_costs={},
        unit_costs={},
        run=actions.defend,
        cooldown_key=actions.DEFEND_ACTION_KEY,
        building_costs={BuildingType.CATAPULT: 1},
        requires_active_threat=True,
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

    #resource-table, #unit-table, #building-table {
        border: solid $surface-lighten-1;
        margin: 0 1 1 1;
    }

    .overview-assets {
        height: auto;
    }

    .overview-column {
        width: 1fr;
        height: auto;
    }

    #shop-view, #battle-view, #logs-view, #encyclopedia-view {
        padding: 1;
        height: auto;
        border: solid $surface-lighten-1;
        margin: 0 1 1 1;
    }

    #status {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 1;
        border: solid $accent;
        background: $surface;
    }

    .section-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    #selected {
        padding: 1 1;
        min-height: 4;
        border: solid $surface-lighten-1;
        margin: 0 1 1 1;
    }

    """

    BINDINGS = [
        Binding("up,k", "select_previous", "Previous row", priority=True),
        Binding("down,j", "select_next", "Next row", priority=True),
        Binding("left,h", "select_left", "Previous column", priority=True),
        Binding("right", "select_right", "Next column", priority=True),
        Binding("enter", "execute_selected", "Use selected", priority=True),
        Binding("s", "show_scribe", "Scribe"),
        Binding("r", "show_reign", "Reign"),
        Binding("b", "show_battle", "Battle"),
        Binding("l", "show_logs", "Logs"),
        Binding("e", "show_encyclopedia", "Encyclopedia"),
        Binding("n", "reset", "New game after death"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, save_path: Path | None = None) -> None:
        super().__init__()
        self.save_path = save_path or default_save_path()
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
        self.battle_view = Static(id="battle-view")
        self.logs_view = Static(id="logs-view")
        self.encyclopedia_view = Static(id="encyclopedia-view")
        self.status_view = Static(id="status")
        self.tables_ready = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="scribe-tab"):
            with TabPane("Scribe", id="scribe-tab"):
                yield Static("Scribe", classes="section-title")
                yield self.resource_table
                with Horizontal(classes="overview-assets"):
                    with Vertical(classes="overview-column"):
                        yield Static("Units", classes="section-title")
                        yield self.unit_table
                    with Vertical(classes="overview-column"):
                        yield Static("Buildings", classes="section-title")
                        yield self.building_table
            with TabPane("Reign", id="reign-tab"):
                yield self.shop_view
                yield self.selected_view
            with TabPane("Battle", id="battle-tab"):
                yield self.battle_view
            with TabPane("Logs", id="logs-tab"):
                yield self.logs_view
            with TabPane("Encyclopedia", id="encyclopedia-tab"):
                yield self.encyclopedia_view
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

    def action_show_scribe(self) -> None:
        self.query_one(TabbedContent).active = "scribe-tab"

    def action_show_reign(self) -> None:
        self.query_one(TabbedContent).active = "reign-tab"

    def action_show_battle(self) -> None:
        self.query_one(TabbedContent).active = "battle-tab"

    def action_show_logs(self) -> None:
        self.query_one(TabbedContent).active = "logs-tab"

    def action_show_encyclopedia(self) -> None:
        self.query_one(TabbedContent).active = "encyclopedia-tab"

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
        self._refresh_battle_view()
        self._refresh_logs_view()
        self._refresh_encyclopedia_view()
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
            f"{action_display_label(self.state, menu_action)}: {readiness}\n"
            f"Cost: {format_action_cost(menu_action)}\n"
            f"Requirements: {format_action_requirements(menu_action)}"
        )

    def _refresh_battle_view(self) -> None:
        self.battle_view.update(format_battle_text(self.state))

    def _refresh_logs_view(self) -> None:
        self.logs_view.update(format_logs_text(self.state))

    def _refresh_encyclopedia_view(self) -> None:
        self.encyclopedia_view.update(format_encyclopedia_text(self.state))

    def _refresh_status_view(self) -> None:
        if self.state.is_dead:
            self.status_view.update(
                "[red bold]Game Over[/]\n"
                f"Run Time: {format_duration(self.state.run_elapsed_seconds)}\n"
                f"Save: {self.save_path}\n"
                + "\n".join(format_story_lines(self.state))
                + "\nPress n to start a new run."
            )
            return

        self.status_view.update(
            f"Run Time: {format_duration(self.state.run_elapsed_seconds)}\n"
            f"Save: {self.save_path}\n"
            "[bold]Story[/]\n"
            + "\n".join(format_story_lines(self.state))
        )


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
    threat_ready = not menu_action.requires_active_threat or bool(state.active_threats)
    return (
        has_resources
        and has_units
        and has_buildings
        and cooldown_ready
        and threat_ready
    )


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


def action_display_label(state: GameState, menu_action: MenuAction) -> str:
    if menu_action.label == "Hunt" and state.units[UnitType.RANGER] >= 1:
        return "Hunt (A)"
    if menu_action.label == "Patrol" and state.units[UnitType.CAPTAIN] >= 1:
        return "Patrol (A)"
    if menu_action.label == "Defend" and state.units[UnitType.WATCHPOST] >= 1:
        return "Defend (A)"
    return menu_action.label


def format_quantity(amount: float | int) -> str:
    if isinstance(amount, float) and amount.is_integer():
        return str(int(amount))
    return str(amount)


def format_action_cost(menu_action: MenuAction) -> str:
    if not menu_action.resource_costs:
        return "-"

    return ", ".join(
        f"{format_quantity(amount)} {resource.value}"
        for resource, amount in menu_action.resource_costs.items()
    )


def format_counted_name(amount: int, singular_name: str) -> str:
    name = singular_name.lower()
    if amount == 1:
        return f"{amount} {name}"
    return f"{amount} {name}s"


def format_action_requirements(menu_action: MenuAction) -> str:
    requirements = [
        format_counted_name(amount, UNIT_DEFINITIONS[unit].name)
        for unit, amount in menu_action.unit_costs.items()
    ]
    requirements.extend(
        format_counted_name(amount, BUILDING_DEFINITIONS[building].name)
        for building, amount in (menu_action.building_costs or {}).items()
    )
    if menu_action.cooldown_key is not None:
        requirements.append("cooldown ready")
    if menu_action.requires_active_threat:
        requirements.append("active threat")
    if menu_action.label == "Defend":
        requirements.append("25-75% success chance")

    if not requirements:
        return "-"
    return ", ".join(requirements)


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


def format_duration(seconds: float) -> str:
    remaining = max(0, int(seconds))
    hours, remainder = divmod(remaining, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_story_lines(state: GameState) -> list[str]:
    return [f"- {message}" for message in state.action_history[-3:]]


def format_log_lines(state: GameState) -> list[str]:
    return [f"- {message}" for message in state.action_history[-25:]]


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
            f"Run Time: {format_duration(state.run_elapsed_seconds)}",
            "",
            "Scribe Tab",
            *resource_lines,
            "",
            "Units",
            *unit_lines,
            "",
            "Buildings",
            *building_lines,
            "",
            "Reign Tab",
            *shop_lines,
            "",
            "Selected",
            f"{action_display_label(state, menu_action)}: {readiness}",
            f"Cost: {format_action_cost(menu_action)}",
            f"Requirements: {format_action_requirements(menu_action)}",
            "",
            "Battle Tab",
            *format_battle_lines(state),
            "",
            "Logs Tab",
            *format_log_lines(state),
            "",
            "Encyclopedia Tab",
            *format_encyclopedia_lines(state),
            "",
            "Story",
            *format_story_lines(state),
        ]
    )


def format_battle_text(state: GameState) -> str:
    return "\n".join(format_battle_lines(state))


def format_logs_text(state: GameState) -> str:
    return "[bold]Logs[/]\n" + "\n".join(format_log_lines(state))


def format_battle_lines(state: GameState) -> list[str]:
    lines = [
        f"Next threat roll: {format_cooldown(state.threat_roll_cooldown)}",
        "",
        "Current Threats",
    ]
    if not state.active_threats:
        lines.append("No active threats.")
        return lines

    for active_threat in state.active_threats:
        definition = THREAT_DEFINITIONS.get(active_threat.key)
        if definition is None:
            lines.append(
                f"- {active_threat.key}: {format_cooldown(active_threat.remaining_seconds)}"
            )
            continue

        lines.append(
            f"- {definition.name}: {format_cooldown(active_threat.remaining_seconds)}"
        )
        lines.append(f"  {definition.description}")
        lines.append(f"  Effect: {format_threat_effect(definition, state)}")
    return lines


def format_encyclopedia_text(state: GameState | None = None) -> str:
    return "\n".join(format_encyclopedia_lines(state))


def format_encyclopedia_lines(state: GameState | None = None) -> list[str]:
    lines = ["Resources"]
    for resource in ALL_RESOURCES:
        lines.append(f"- {resource.value.title()}: Stored resource used by the realm.")

    lines.extend(["", "Units"])
    for unit_type in UnitType:
        definition = UNIT_DEFINITIONS[unit_type]
        lines.append(
            f"- {definition.name}: production {format_rate_map(definition.production)}; "
            f"upkeep {format_rate_map(definition.upkeep)}."
        )

    lines.extend(["", "Buildings"])
    for building_type in BuildingType:
        definition = BUILDING_DEFINITIONS[building_type]
        lines.append(
            f"- {definition.name}: production {format_rate_map(definition.production)}; "
            f"upkeep {format_rate_map(definition.upkeep)}."
        )

    lines.extend(["", "Actions"])
    for menu_action in MENU_ACTIONS:
        label = menu_action.label
        if state is not None:
            label = action_display_label(state, menu_action)
        lines.append(
            f"- {label}: cost {format_action_cost(menu_action)}; "
            f"requirements {format_action_requirements(menu_action)}."
        )

    lines.extend(["", "Threats"])
    for definition in THREAT_DEFINITIONS.values():
        countdown = definition.countdown_seconds
        effect = definition.effect_text
        if state is not None:
            countdown = scaled_threat_countdown(definition, state)
            effect = format_threat_effect(definition, state)
        lines.append(
            f"- {definition.name}: {definition.description} "
            f"Countdown {format_cooldown(countdown)}. "
            f"{effect}"
        )
    return lines


def format_threat_effect(definition: ThreatDefinition, state: GameState) -> str:
    damage = scaled_threat_damage(definition, state)
    target_name = definition.target_building.value.replace("_", " ")
    target_label = target_name if damage == 1 else f"{target_name}s"
    return f"Destroys up to {damage} {target_label} when it resolves."


def format_rate_map(values: dict[ResourceType, float]) -> str:
    if not values:
        return "none"
    return ", ".join(
        f"{amount:+.1f} {resource.value}/s" for resource, amount in values.items()
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
            label = action_display_label(state, menu_action)
            owned = owned_text(state, column, row)
            marker = ">" if column == selected_column and row == selected_row else " "
            cells.append(f"{marker} {label:<14} {owned:<5}")
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
            label = action_display_label(state, menu_action)
            marker = ">" if column == selected_column and row == selected_row else " "
            cell = f"{marker} {label:<14} {owned_text(state, column, row):<5}"
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
            f"Final Run Time: {format_duration(state.run_elapsed_seconds)}",
            "",
            "Final Stores",
            *resource_lines,
            "",
            "Story",
            *format_story_lines(state),
            "",
            "Press n to start a new run. Press q to quit.",
        ]
    )


def main() -> None:
    ShellcromancerApp().run()


if __name__ == "__main__":
    main()
