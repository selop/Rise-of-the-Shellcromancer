import pytest

from shellcromancer.buildings import BuildingType
from shellcromancer.actions import HUNT_ACTION_KEY, PATROL_ACTION_KEY
from shellcromancer.economy import (
    DEATH_MESSAGE,
    apply_delta,
    calculate_delta,
    reduce_cooldowns,
    tick,
)
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.units import UnitType


def test_initial_base_resource_gain() -> None:
    state = GameState()

    delta = calculate_delta(state)

    for resource in ResourceType:
        expected = 0.0 if resource is ResourceType.GOLD else 0.1
        assert delta[resource] == pytest.approx(expected)


def test_gold_starts_at_zero() -> None:
    state = GameState()

    assert state.resources[ResourceType.GOLD] == pytest.approx(0.0)


def test_shell_fairy_bonus_stacks_with_base_shell_gain() -> None:
    state = GameState()
    state.shell_fairy_bonus = 0.2

    delta = calculate_delta(state)

    assert delta[ResourceType.SHELL] == pytest.approx(0.3)


def test_worker_food_upkeep() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.FOOD] == pytest.approx(0.0)
    assert delta[ResourceType.SHELL] == pytest.approx(0.1)


def test_lumberjack_wood_production_and_food_upkeep() -> None:
    state = GameState()
    state.units[UnitType.LUMBERJACK] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.WOOD] == pytest.approx(0.3)
    assert delta[ResourceType.FOOD] == pytest.approx(0.0)


def test_farm_food_production() -> None:
    state = GameState()
    state.buildings[BuildingType.FARM] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.FOOD] == pytest.approx(0.3)


def test_mine_iron_production() -> None:
    state = GameState()
    state.buildings[BuildingType.MINE] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.IRON] == pytest.approx(0.3)


def test_quarry_stone_production() -> None:
    state = GameState()
    state.buildings[BuildingType.QUARRY] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.STONE] == pytest.approx(0.3)


def test_arcane_tower_shell_production() -> None:
    state = GameState()
    state.buildings[BuildingType.ARCANE_TOWER] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.SHELL] == pytest.approx(0.2)


def test_combined_net_delta() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 2
    state.units[UnitType.LUMBERJACK] = 1
    state.buildings[BuildingType.FARM] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.WOOD] == pytest.approx(0.3)
    assert delta[ResourceType.FOOD] == pytest.approx(0.0)
    assert delta[ResourceType.SHELL] == pytest.approx(0.1)


def test_worker_and_farm_net_positive_food() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1
    state.buildings[BuildingType.FARM] = 1

    delta = calculate_delta(state)

    assert delta[ResourceType.FOOD] == pytest.approx(0.2)
    assert delta[ResourceType.SHELL] == pytest.approx(0.1)


def test_apply_delta_clamps_resources_but_keeps_visible_deficit() -> None:
    state = GameState()
    state.resources[ResourceType.FOOD] = 0.0
    delta = {resource: 0.0 for resource in ResourceType}
    delta[ResourceType.FOOD] = -0.5

    apply_delta(state, delta)

    assert state.resources[ResourceType.FOOD] == pytest.approx(0.0)
    assert state.last_delta[ResourceType.FOOD] == pytest.approx(-0.5)
    assert state.is_dead is True
    assert state.last_action_message == DEATH_MESSAGE


def test_reduce_cooldowns_decrements_without_going_below_zero() -> None:
    state = GameState()
    state.action_cooldowns[HUNT_ACTION_KEY] = 2.0

    reduce_cooldowns(state)
    assert state.action_cooldowns[HUNT_ACTION_KEY] == pytest.approx(1.0)

    reduce_cooldowns(state, elapsed_seconds=5.0)
    assert state.action_cooldowns[HUNT_ACTION_KEY] == pytest.approx(0.0)


def test_tick_runs_automatic_patrol_when_captain_and_requirements_are_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 3
    state.resources[ResourceType.FOOD] = 10.5
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)
        patrol_state.last_action_message = "Automatic patrol ran."

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert calls == [state]
    assert state.last_action_message == "Automatic patrol ran."


def test_tick_does_not_auto_patrol_without_captain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 3
    state.resources[ResourceType.FOOD] = 10.5
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert calls == []


def test_tick_does_not_auto_patrol_until_cooldown_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 3
    state.resources[ResourceType.FOOD] = 10.5
    state.action_cooldowns[PATROL_ACTION_KEY] = 2.0
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert calls == []
    assert state.action_cooldowns[PATROL_ACTION_KEY] == pytest.approx(1.0)


def test_tick_does_not_auto_patrol_without_patrol_prerequisites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 2
    state.resources[ResourceType.FOOD] = 0.0
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert calls == []
    assert state.is_dead is True
    assert state.last_action_message == DEATH_MESSAGE


def test_tick_marks_state_dead_when_food_reaches_zero() -> None:
    state = GameState()
    state.resources[ResourceType.FOOD] = 0.1
    state.units[UnitType.SOLDIER] = 1

    tick(state)

    assert state.resources[ResourceType.FOOD] == pytest.approx(0.0)
    assert state.is_dead is True
    assert state.last_action_message == DEATH_MESSAGE


def test_tick_does_not_update_dead_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.is_dead = True
    state.resources[ResourceType.WOOD] = 10.0
    state.action_cooldowns[HUNT_ACTION_KEY] = 2.0
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert state.resources[ResourceType.WOOD] == pytest.approx(10.0)
    assert state.action_cooldowns[HUNT_ACTION_KEY] == pytest.approx(2.0)
    assert calls == []
