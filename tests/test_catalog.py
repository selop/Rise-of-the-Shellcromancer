from shellcromancer.actions import DEFEND_ACTION_KEY
from shellcromancer.buildings import BuildingType
from shellcromancer.catalog import (
    AUTOMATED_ACTIONS,
    BUILDING_ACTIONS,
    MENU_ACTIONS,
    MenuAction,
    owned_count,
)
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.units import UnitType


def test_owned_count_uses_explicit_action_target() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 7
    state.buildings[BuildingType.ARCANE_TOWER] = 3

    unit_action = MenuAction(
        label="Out of Order Unit",
        resource_costs={},
        unit_costs={},
        run=MENU_ACTIONS[0].run,
        owned_unit=UnitType.SORCERER,
    )
    building_action = MenuAction(
        label="Out of Order Building",
        resource_costs={},
        unit_costs={},
        run=MENU_ACTIONS[0].run,
        owned_building=BuildingType.ARCANE_TOWER,
    )

    assert owned_count(state, unit_action) == 7
    assert owned_count(state, building_action) == 3


def test_storage_menu_action_provides_scaled_effective_costs() -> None:
    state = GameState()
    state.buildings[BuildingType.STORAGE] = 2
    storage_action = next(
        action
        for action in BUILDING_ACTIONS
        if action.owned_building is BuildingType.STORAGE
    )

    assert storage_action.effective_unit_costs(state) == {UnitType.WORKER: 3}
    assert storage_action.effective_resource_costs(state) == {
        ResourceType.WOOD: 150.0,
        ResourceType.STONE: 75.0,
    }


def test_defend_automation_metadata_keeps_enabler_and_requirements_separate() -> None:
    defend_action = AUTOMATED_ACTIONS[DEFEND_ACTION_KEY]

    assert defend_action.automation_enabler_units == {UnitType.WATCHPOST: 1}
    assert defend_action.building_costs == {BuildingType.CATAPULT: 1}
    assert defend_action.requires_active_threat is True
