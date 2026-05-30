import pytest

from shellcromancer.buildings import BuildingType
from shellcromancer.actions import (
    DEFEND_ACTION_KEY,
    EXPEDITION_ACTION_KEY,
    HUNT_ACTION_KEY,
    PATROL_ACTION_KEY,
)
from shellcromancer.economy import (
    DEATH_MESSAGE,
    apply_delta,
    calculate_delta,
    reduce_cooldowns,
    tick,
)
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.threats import THREAT_ROLL_SECONDS, ActiveThreat
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


def test_tick_reduces_threat_roll_cooldown() -> None:
    state = GameState()

    tick(state)

    assert state.threat_roll_cooldown == pytest.approx(THREAT_ROLL_SECONDS - 1.0)


def test_tick_adds_threat_when_roll_timer_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.threat_roll_cooldown = 1.0

    def fake_create_random_threat() -> ActiveThreat:
        return ActiveThreat(key="goblin_raid", remaining_seconds=300.0)

    monkeypatch.setattr(
        "shellcromancer.economy.create_random_threat", fake_create_random_threat
    )

    tick(state)

    assert state.threat_roll_cooldown == pytest.approx(THREAT_ROLL_SECONDS)
    assert state.active_threats == [
        ActiveThreat(key="goblin_raid", remaining_seconds=300.0)
    ]
    assert state.last_action_message == "New threat: Goblin Raid."


def test_tick_reduces_active_threat_countdown() -> None:
    state = GameState()
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=2.0))

    tick(state)

    assert state.active_threats == [
        ActiveThreat(key="goblin_raid", remaining_seconds=1.0)
    ]


def test_expired_goblin_raid_destroys_up_to_two_farms() -> None:
    state = GameState()
    state.buildings[BuildingType.FARM] = 3
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=1.0))

    tick(state)

    assert state.buildings[BuildingType.FARM] == 1
    assert state.active_threats == []
    assert state.last_action_message == "Goblin Raid struck and destroyed 2 farms."


def test_expired_threat_without_target_does_not_crash() -> None:
    state = GameState()
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=1.0))

    tick(state)

    assert state.buildings[BuildingType.FARM] == 0
    assert state.active_threats == []
    assert state.last_action_message == (
        "Goblin Raid struck, but found no farm to destroy."
    )


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


def test_tick_does_not_auto_launch_expedition_when_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 10
    state.resources[ResourceType.FOOD] = 25.0
    state.resources[ResourceType.GOLD] = 5.0
    state.action_cooldowns[PATROL_ACTION_KEY] = 5.0
    calls = []

    def fake_patrol(patrol_state: GameState) -> None:
        calls.append(patrol_state)

    monkeypatch.setattr("shellcromancer.economy.patrol", fake_patrol)

    tick(state)

    assert calls == []
    assert state.resources[ResourceType.GOLD] == pytest.approx(5.0)
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == pytest.approx(0.0)


def test_tick_auto_defends_when_watchpost_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.WATCHPOST] = 1
    state.buildings[BuildingType.CATAPULT] = 1
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=60.0))
    calls = []

    def fake_defend(defend_state: GameState) -> None:
        calls.append(defend_state)

    monkeypatch.setattr("shellcromancer.economy.defend", fake_defend)

    tick(state)

    assert calls == [state]


def test_tick_does_not_auto_defend_without_watchpost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.buildings[BuildingType.CATAPULT] = 1
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=60.0))
    calls = []

    def fake_defend(defend_state: GameState) -> None:
        calls.append(defend_state)

    monkeypatch.setattr("shellcromancer.economy.defend", fake_defend)

    tick(state)

    assert calls == []


def test_tick_does_not_auto_defend_until_cooldown_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = GameState()
    state.units[UnitType.WATCHPOST] = 1
    state.buildings[BuildingType.CATAPULT] = 1
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=60.0))
    state.action_cooldowns[DEFEND_ACTION_KEY] = 2.0
    calls = []

    def fake_defend(defend_state: GameState) -> None:
        calls.append(defend_state)

    monkeypatch.setattr("shellcromancer.economy.defend", fake_defend)

    tick(state)

    assert calls == []
    assert state.action_cooldowns[DEFEND_ACTION_KEY] == pytest.approx(1.0)


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
