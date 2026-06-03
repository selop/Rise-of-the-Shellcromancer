from collections.abc import Callable
from dataclasses import dataclass, field

from shellcromancer import actions
from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.units import UnitType


@dataclass(frozen=True)
class MenuAction:
    label: str
    resource_costs: dict[ResourceType, float]
    unit_costs: dict[UnitType, int]
    run: Callable[[GameState], actions.ActionResult]
    cooldown_key: str | None = None
    building_costs: dict[BuildingType, int] = field(default_factory=dict)
    requires_active_threat: bool = False
    owned_unit: UnitType | None = None
    owned_building: BuildingType | None = None
    automation_key: str | None = None
    automation_enabler_units: dict[UnitType, int] = field(default_factory=dict)
    automation_enabler_buildings: dict[BuildingType, int] = field(
        default_factory=dict
    )
    automation_enable_requirement: str | None = None
    dynamic_resource_costs: (
        Callable[[GameState], dict[ResourceType, float]] | None
    ) = None
    dynamic_unit_costs: Callable[[GameState], dict[UnitType, int]] | None = None

    def effective_resource_costs(
        self, state: GameState
    ) -> dict[ResourceType, float]:
        if self.dynamic_resource_costs is not None:
            return self.dynamic_resource_costs(state)
        return self.resource_costs

    def effective_unit_costs(self, state: GameState) -> dict[UnitType, int]:
        if self.dynamic_unit_costs is not None:
            return self.dynamic_unit_costs(state)
        return self.unit_costs


def storage_unit_costs(state: GameState) -> dict[UnitType, int]:
    return {UnitType.WORKER: actions.storage_worker_cost(state)}


UNIT_ACTIONS = (
    MenuAction(
        label="Worker",
        resource_costs={ResourceType.SHELL: 10.0},
        unit_costs={},
        run=actions.create_worker,
        owned_unit=UnitType.WORKER,
    ),
    MenuAction(
        label="Soldier",
        resource_costs={
            ResourceType.IRON: 5.0,
            ResourceType.SHELL: 5.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.upgrade_worker_to_soldier,
        owned_unit=UnitType.SOLDIER,
    ),
    MenuAction(
        label="Lumberjack",
        resource_costs={
            ResourceType.WOOD: 5.0,
            ResourceType.SHELL: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.upgrade_worker_to_lumberjack,
        owned_unit=UnitType.LUMBERJACK,
    ),
    MenuAction(
        label="Ranger",
        resource_costs={ResourceType.GOLD: 5.0, ResourceType.SHELL: 10.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.upgrade_soldier_to_ranger,
        owned_unit=UnitType.RANGER,
    ),
    MenuAction(
        label="Captain",
        resource_costs={ResourceType.GOLD: 10.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.promote_worker_to_captain,
        owned_unit=UnitType.CAPTAIN,
    ),
    MenuAction(
        label="Watchpost",
        resource_costs={ResourceType.GOLD: 10.0, ResourceType.WOOD: 50.0},
        unit_costs={},
        run=actions.create_watchpost,
        owned_unit=UnitType.WATCHPOST,
    ),
    MenuAction(
        label="Sorcerer",
        resource_costs={ResourceType.SHELL: 50.0},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.upgrade_soldier_to_sorcerer,
        owned_unit=UnitType.SORCERER,
    ),
)


BUILDING_ACTIONS = (
    MenuAction(
        label="Farm",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_farm,
        owned_building=BuildingType.FARM,
    ),
    MenuAction(
        label="Mine",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_mine,
        owned_building=BuildingType.MINE,
    ),
    MenuAction(
        label="Quarry",
        resource_costs={
            ResourceType.WOOD: 10.0,
            ResourceType.STONE: 10.0,
            ResourceType.IRON: 2.0,
        },
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_quarry,
        owned_building=BuildingType.QUARRY,
    ),
    MenuAction(
        label="Arcane Tower",
        resource_costs={ResourceType.STONE: 250.0},
        unit_costs={UnitType.SORCERER: 1},
        run=actions.build_arcane_tower,
        owned_building=BuildingType.ARCANE_TOWER,
    ),
    MenuAction(
        label="Catapult",
        resource_costs={
            ResourceType.GOLD: 5.0,
            ResourceType.WOOD: 100.0,
            ResourceType.STONE: 200.0,
        },
        unit_costs={},
        run=actions.build_catapult,
        owned_building=BuildingType.CATAPULT,
    ),
    MenuAction(
        label="Storage",
        resource_costs={ResourceType.WOOD: 50.0, ResourceType.STONE: 25.0},
        unit_costs={UnitType.WORKER: 1},
        run=actions.build_storage,
        owned_building=BuildingType.STORAGE,
        dynamic_resource_costs=actions.storage_resource_costs,
        dynamic_unit_costs=storage_unit_costs,
    ),
)


ONE_TIME_ACTIONS = (
    MenuAction(
        label="Hunt",
        resource_costs={},
        unit_costs={UnitType.SOLDIER: 1},
        run=actions.hunt,
        cooldown_key=actions.HUNT_ACTION_KEY,
        automation_key=actions.HUNT_ACTION_KEY,
        automation_enabler_units={UnitType.RANGER: 1},
        automation_enable_requirement="Need a ranger to enable Auto Hunt.",
    ),
    MenuAction(
        label="Patrol",
        resource_costs={ResourceType.FOOD: 10.0},
        unit_costs={UnitType.SOLDIER: 3},
        run=actions.patrol,
        cooldown_key=actions.PATROL_ACTION_KEY,
        automation_key=actions.PATROL_ACTION_KEY,
        automation_enabler_units={UnitType.CAPTAIN: 1},
        automation_enable_requirement="Need a captain to enable Auto Patrol.",
    ),
    MenuAction(
        label="Expedition",
        resource_costs={ResourceType.FOOD: 25.0, ResourceType.GOLD: 5.0},
        unit_costs={UnitType.CAPTAIN: 1, UnitType.SOLDIER: 10},
        run=actions.expedition,
        cooldown_key=actions.EXPEDITION_ACTION_KEY,
    ),
    MenuAction(
        label="Kindle the Pyre",
        resource_costs={ResourceType.WOOD: 100.0},
        unit_costs={UnitType.SORCERER: 1},
        run=actions.kindle_the_pyre,
        cooldown_key=actions.KINDLE_PYRE_ACTION_KEY,
        building_costs={BuildingType.ARCANE_TOWER: 1},
    ),
    MenuAction(
        label="Defend",
        resource_costs={},
        unit_costs={},
        run=actions.defend,
        cooldown_key=actions.DEFEND_ACTION_KEY,
        building_costs={BuildingType.CATAPULT: 1},
        requires_active_threat=True,
        automation_key=actions.DEFEND_ACTION_KEY,
        automation_enabler_units={UnitType.WATCHPOST: 1},
        automation_enable_requirement="Need a watchpost to enable Auto Defend.",
    ),
)


MENU_COLUMNS = (UNIT_ACTIONS, BUILDING_ACTIONS, ONE_TIME_ACTIONS)
MENU_ACTIONS = tuple(action for column in MENU_COLUMNS for action in column)
SHOP_COLUMN_LABELS = ("Units", "Buildings", "Actions")

AUTOMATED_ACTIONS = {
    action.automation_key: action
    for action in MENU_ACTIONS
    if action.automation_key is not None
}
AUTOMATED_ACTION_LABELS = {
    action.label: action_key for action_key, action in AUTOMATED_ACTIONS.items()
}
AUTOMATED_ACTION_NAMES = {
    action_key: action.label for action_key, action in AUTOMATED_ACTIONS.items()
}
AUTOMATION_ENABLE_REQUIREMENTS = {
    action_key: action.automation_enable_requirement or ""
    for action_key, action in AUTOMATED_ACTIONS.items()
}


def owned_count(state: GameState, menu_action: MenuAction) -> int | None:
    if menu_action.owned_unit is not None:
        return state.units[menu_action.owned_unit]
    if menu_action.owned_building is not None:
        return state.buildings[menu_action.owned_building]
    return None
