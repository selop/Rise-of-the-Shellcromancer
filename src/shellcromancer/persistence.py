import json
import os
from pathlib import Path
from typing import TypeVar

from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import (
    ACTION_HISTORY_LIMIT,
    GameState,
    record_action_message,
)
from shellcromancer.resources import ResourceType
from shellcromancer.storage import clamp_all_resources
from shellcromancer.threats import THREAT_DEFINITIONS, THREAT_ROLL_SECONDS, ActiveThreat
from shellcromancer.units import UnitType


SAVE_VERSION = 1
SAVE_LOAD_FAILURE_MESSAGE = "Save file could not be loaded; started a new run."

EnumKey = TypeVar("EnumKey", ResourceType, UnitType, BuildingType)


def default_save_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    base_path = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base_path / "shellcromancer" / "save.json"


def state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "version": SAVE_VERSION,
        "resources": {
            resource.value: amount for resource, amount in state.resources.items()
        },
        "units": {unit.value: count for unit, count in state.units.items()},
        "buildings": {
            building.value: count for building, count in state.buildings.items()
        },
        "action_cooldowns": dict(state.action_cooldowns),
        "active_threats": [
            {
                "key": active_threat.key,
                "remaining_seconds": active_threat.remaining_seconds,
            }
            for active_threat in state.active_threats
        ],
        "threat_roll_cooldown": state.threat_roll_cooldown,
        "last_delta": {
            resource.value: amount for resource, amount in state.last_delta.items()
        },
        "last_action_message": state.last_action_message,
        "action_history": state.action_history[-ACTION_HISTORY_LIMIT:],
        "shell_fairy_bonus": state.shell_fairy_bonus,
        "is_dead": state.is_dead,
        "run_elapsed_seconds": state.run_elapsed_seconds,
    }


def state_from_dict(data: dict[str, object]) -> GameState:
    if not isinstance(data, dict):
        raise ValueError("Save data must be a JSON object.")

    default_state = GameState()
    state = GameState(
        resources=_enum_float_mapping(
            data.get("resources"), ResourceType, default_state.resources
        ),
        units=_enum_int_mapping(data.get("units"), UnitType, default_state.units),
        buildings=_enum_int_mapping(
            data.get("buildings"), BuildingType, default_state.buildings
        ),
        action_cooldowns=_string_float_mapping(
            data.get("action_cooldowns"), default_state.action_cooldowns
        ),
        active_threats=_active_threats(data.get("active_threats")),
        threat_roll_cooldown=_float_or_default(
            data.get("threat_roll_cooldown"), THREAT_ROLL_SECONDS
        ),
        last_delta=_enum_float_mapping(
            data.get("last_delta"), ResourceType, default_state.last_delta
        ),
    )

    raw_action_history = data.get("action_history")
    has_action_history = _is_string_list(raw_action_history) and bool(
        raw_action_history
    )
    if has_action_history:
        state.action_history = raw_action_history[-ACTION_HISTORY_LIMIT:]
        state.last_action_message = state.action_history[-1]

    last_action_message = data.get("last_action_message")
    if isinstance(last_action_message, str) and not has_action_history:
        state.last_action_message = last_action_message
        state.action_history = [last_action_message]

    state.shell_fairy_bonus = _float_or_default(
        data.get("shell_fairy_bonus"), default_state.shell_fairy_bonus
    )
    is_dead = data.get("is_dead", default_state.is_dead)
    state.is_dead = is_dead if isinstance(is_dead, bool) else default_state.is_dead
    state.run_elapsed_seconds = _float_or_default(
        data.get("run_elapsed_seconds"), default_state.run_elapsed_seconds
    )
    clamp_all_resources(state)
    return state


def load_state(path: Path | None = None) -> GameState:
    save_path = path or default_save_path()
    if not save_path.exists():
        return GameState()

    try:
        data = json.loads(save_path.read_text(encoding="utf-8"))
        return state_from_dict(data)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        state = GameState()
        record_action_message(state, SAVE_LOAD_FAILURE_MESSAGE)
        return state


def save_state(state: GameState, path: Path | None = None) -> None:
    save_path = path or default_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = save_path.with_suffix(f"{save_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(state_to_dict(state), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(save_path)


def _enum_float_mapping(
    raw_value: object, enum_type: type[EnumKey], defaults: dict[EnumKey, float]
) -> dict[EnumKey, float]:
    values = defaults.copy()
    if not isinstance(raw_value, dict):
        return values

    for key in enum_type:
        if key.value in raw_value:
            values[key] = _float_or_default(raw_value[key.value], values[key])
    return values


def _enum_int_mapping(
    raw_value: object, enum_type: type[EnumKey], defaults: dict[EnumKey, int]
) -> dict[EnumKey, int]:
    values = defaults.copy()
    if not isinstance(raw_value, dict):
        return values

    for key in enum_type:
        if key.value in raw_value:
            values[key] = _int_or_default(raw_value[key.value], values[key])
    return values


def _is_string_list(raw_value: object) -> bool:
    return isinstance(raw_value, list) and all(
        isinstance(item, str) for item in raw_value
    )


def _string_float_mapping(
    raw_value: object, defaults: dict[str, float]
) -> dict[str, float]:
    values = defaults.copy()
    if not isinstance(raw_value, dict):
        return values

    for key, value in raw_value.items():
        if isinstance(key, str):
            values[key] = _float_or_default(value, values.get(key, 0.0))
    return values


def _active_threats(raw_value: object) -> list[ActiveThreat]:
    if not isinstance(raw_value, list):
        return []

    active_threats = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue

        key = item.get("key")
        if not isinstance(key, str) or key not in THREAT_DEFINITIONS:
            continue

        active_threats.append(
            ActiveThreat(
                key=key,
                remaining_seconds=_float_or_default(
                    item.get("remaining_seconds"),
                    THREAT_DEFINITIONS[key].countdown_seconds,
                ),
            )
        )
    return active_threats


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
