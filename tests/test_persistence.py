import json

import pytest

from shellcromancer.actions import (
    DEFEND_ACTION_KEY,
    EXPEDITION_ACTION_KEY,
    HUNT_ACTION_KEY,
)
from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState, record_action_message
from shellcromancer.persistence import (
    SAVE_LOAD_FAILURE_MESSAGE,
    default_save_path,
    load_state,
    save_state,
    state_from_dict,
    state_to_dict,
)
from shellcromancer.resources import ResourceType
from shellcromancer.threats import ActiveThreat
from shellcromancer.units import UnitType


def test_save_and_load_state_round_trip(tmp_path) -> None:
    save_path = tmp_path / "save.json"
    state = GameState()
    state.resources[ResourceType.FOOD] = 4.5
    state.units[UnitType.SOLDIER] = 2
    state.buildings[BuildingType.FARM] = 3
    state.action_cooldowns[HUNT_ACTION_KEY] = 12.0
    state.last_delta[ResourceType.FOOD] = -0.4
    record_action_message(state, "First stored event.")
    record_action_message(state, "Second stored event.")
    record_action_message(state, "Stored state.")
    state.shell_fairy_bonus = 0.3
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=42.0))
    state.threat_roll_cooldown = 123.0
    state.is_dead = True
    state.run_elapsed_seconds = 456.0

    save_state(state, save_path)
    loaded = load_state(save_path)

    assert loaded.resources[ResourceType.FOOD] == pytest.approx(4.5)
    assert loaded.units[UnitType.SOLDIER] == 2
    assert loaded.buildings[BuildingType.FARM] == 3
    assert loaded.action_cooldowns[HUNT_ACTION_KEY] == pytest.approx(12.0)
    assert loaded.last_delta[ResourceType.FOOD] == pytest.approx(-0.4)
    assert loaded.last_action_message == "Stored state."
    assert loaded.action_history == [
        "Welcome, Shellcromancer.",
        "First stored event.",
        "Second stored event.",
        "Stored state.",
    ]
    assert loaded.shell_fairy_bonus == pytest.approx(0.3)
    assert loaded.active_threats == [
        ActiveThreat(key="goblin_raid", remaining_seconds=42.0)
    ]
    assert loaded.threat_roll_cooldown == pytest.approx(123.0)
    assert loaded.is_dead is True
    assert loaded.run_elapsed_seconds == pytest.approx(456.0)


def test_load_missing_save_returns_fresh_state(tmp_path) -> None:
    loaded = load_state(tmp_path / "missing.json")

    assert loaded.resources[ResourceType.FOOD] == pytest.approx(10.0)
    assert loaded.is_dead is False


def test_load_corrupt_save_falls_back_to_fresh_state(tmp_path) -> None:
    save_path = tmp_path / "save.json"
    save_path.write_text("{not json", encoding="utf-8")

    loaded = load_state(save_path)

    assert loaded.resources[ResourceType.FOOD] == pytest.approx(10.0)
    assert loaded.last_action_message == SAVE_LOAD_FAILURE_MESSAGE
    assert loaded.action_history[-1] == SAVE_LOAD_FAILURE_MESSAGE
    assert loaded.is_dead is False


def test_state_from_dict_fills_missing_fields_with_defaults() -> None:
    state = state_from_dict({"resources": {"food": 2.0}, "units": {"worker": 1}})

    assert state.resources[ResourceType.FOOD] == pytest.approx(2.0)
    assert state.resources[ResourceType.WOOD] == pytest.approx(10.0)
    assert state.units[UnitType.WORKER] == 1
    assert state.units[UnitType.SOLDIER] == 0
    assert state.units[UnitType.WATCHPOST] == 0
    assert state.action_cooldowns[HUNT_ACTION_KEY] == pytest.approx(0.0)
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == pytest.approx(0.0)
    assert state.action_cooldowns[DEFEND_ACTION_KEY] == pytest.approx(0.0)
    assert state.active_threats == []
    assert state.threat_roll_cooldown == pytest.approx(600.0)
    assert state.run_elapsed_seconds == pytest.approx(0.0)


def test_state_from_dict_loads_old_last_action_message_into_history() -> None:
    state = state_from_dict({"last_action_message": "Stored old save."})

    assert state.last_action_message == "Stored old save."
    assert state.action_history == ["Stored old save."]


def test_action_history_is_limited_to_twenty_five_entries() -> None:
    state = GameState()
    for index in range(30):
        record_action_message(state, f"Entry {index}")

    data = state_to_dict(state)
    loaded = state_from_dict(data)

    assert data["action_history"] == [f"Entry {index}" for index in range(5, 30)]
    assert loaded.action_history == [f"Entry {index}" for index in range(5, 30)]
    assert loaded.last_action_message == "Entry 29"


def test_state_from_dict_ignores_unknown_threats() -> None:
    state = state_from_dict(
        {
            "active_threats": [
                {"key": "goblin_raid", "remaining_seconds": 17.0},
                {"key": "unknown", "remaining_seconds": 99.0},
            ]
        }
    )

    assert state.active_threats == [
        ActiveThreat(key="goblin_raid", remaining_seconds=17.0)
    ]


def test_default_save_path_respects_xdg_data_home(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert default_save_path() == tmp_path / "shellcromancer" / "save.json"


def test_save_file_uses_enum_values_as_keys(tmp_path) -> None:
    save_path = tmp_path / "save.json"

    save_state(GameState(), save_path)
    data = json.loads(save_path.read_text(encoding="utf-8"))

    assert "food" in data["resources"]
    assert "worker" in data["units"]
    assert "watchpost" in data["units"]
    assert "ranger" in data["units"]
    assert "farm" in data["buildings"]
    assert "active_threats" in data
    assert "threat_roll_cooldown" in data
    assert "action_history" in data
