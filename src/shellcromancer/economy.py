from dataclasses import dataclass

from shellcromancer.buildings import BUILDING_DEFINITIONS, BuildingType
from shellcromancer.actions import (
    DEFEND_ACTION_KEY,
    HUNT_ACTION_KEY,
    PATROL_ACTION_KEY,
    defend,
    hunt,
    patrol,
)
from shellcromancer.game_state import GameState, empty_delta, record_action_message
from shellcromancer.resources import ResourceType
from shellcromancer.storage import add_resource
from shellcromancer.threats import (
    THREAT_ROLL_SECONDS,
    active_threat_name,
    create_random_threat,
    resolve_threat,
)
from shellcromancer.units import UNIT_DEFINITIONS, UnitType


BASE_RESOURCE_PER_SECOND = 0.1
BASE_RESOURCE_TYPES = (
    ResourceType.WOOD,
    ResourceType.STONE,
    ResourceType.IRON,
    ResourceType.FOOD,
    ResourceType.SHELL,
)
DEATH_MESSAGE = "The stores are empty. You starved, and the shellhost falls silent."


@dataclass(frozen=True)
class AutomatedAction:
    action_key: str
    unit_enablers: dict[UnitType, int]
    building_enablers: dict[BuildingType, int]
    unit_requirements: dict[UnitType, int]
    building_requirements: dict[BuildingType, int]
    resource_requirements: dict[ResourceType, float]
    requires_active_threat: bool = False


AUTOMATED_ACTIONS = {
    HUNT_ACTION_KEY: AutomatedAction(
        action_key=HUNT_ACTION_KEY,
        unit_enablers={UnitType.RANGER: 1},
        building_enablers={},
        unit_requirements={UnitType.SOLDIER: 1},
        building_requirements={},
        resource_requirements={},
    ),
    PATROL_ACTION_KEY: AutomatedAction(
        action_key=PATROL_ACTION_KEY,
        unit_enablers={UnitType.CAPTAIN: 1},
        building_enablers={},
        unit_requirements={UnitType.SOLDIER: 3},
        building_requirements={},
        resource_requirements={ResourceType.FOOD: 10.0},
    ),
    DEFEND_ACTION_KEY: AutomatedAction(
        action_key=DEFEND_ACTION_KEY,
        unit_enablers={UnitType.WATCHPOST: 1},
        building_enablers={},
        unit_requirements={},
        building_requirements={BuildingType.CATAPULT: 1},
        resource_requirements={},
        requires_active_threat=True,
    ),
}


def calculate_delta(state: GameState) -> dict[ResourceType, float]:
    delta = empty_delta()
    for resource in BASE_RESOURCE_TYPES:
        delta[resource] += BASE_RESOURCE_PER_SECOND
    delta[ResourceType.SHELL] += state.shell_fairy_bonus

    for unit_type, count in state.units.items():
        definition = UNIT_DEFINITIONS[unit_type]
        for resource, amount in definition.production.items():
            delta[resource] += amount * count
        for resource, amount in definition.upkeep.items():
            delta[resource] -= amount * count

    for building_type, count in state.buildings.items():
        definition = BUILDING_DEFINITIONS[building_type]
        for resource, amount in definition.production.items():
            delta[resource] += amount * count
        for resource, amount in definition.upkeep.items():
            delta[resource] -= amount * count

    return delta


def apply_delta(state: GameState, delta: dict[ResourceType, float]) -> None:
    for resource, amount in delta.items():
        add_resource(state, resource, amount)
    state.last_delta = delta.copy()
    mark_dead_if_food_depleted(state)


def mark_dead_if_food_depleted(state: GameState) -> None:
    if state.is_dead:
        return
    if state.resources[ResourceType.FOOD] > 0:
        return

    state.is_dead = True
    record_action_message(state, DEATH_MESSAGE)


def reduce_cooldowns(state: GameState, elapsed_seconds: float = 1.0) -> None:
    for action_key, remaining in state.action_cooldowns.items():
        state.action_cooldowns[action_key] = max(0.0, remaining - elapsed_seconds)


def has_automation_enabler(state: GameState, action_key: str) -> bool:
    automated_action = AUTOMATED_ACTIONS[action_key]
    return _has_units(state, automated_action.unit_enablers) and _has_buildings(
        state, automated_action.building_enablers
    )


def action_prerequisites_met(state: GameState, action_key: str) -> bool:
    automated_action = AUTOMATED_ACTIONS[action_key]
    if not _has_units(state, automated_action.unit_requirements):
        return False
    if not _has_buildings(state, automated_action.building_requirements):
        return False
    if not _has_resources(state, automated_action.resource_requirements):
        return False
    return not automated_action.requires_active_threat or bool(state.active_threats)


def should_run_automated_action(state: GameState, action_key: str) -> bool:
    return (
        not state.is_dead
        and state.automation_enabled.get(action_key, False)
        and has_automation_enabler(state, action_key)
        and state.action_cooldowns.get(action_key, 0.0) <= 0
        and action_prerequisites_met(state, action_key)
    )


def run_automatic_action(state: GameState, action_key: str) -> None:
    if should_run_automated_action(state, action_key):
        _run_automated_action(state, action_key)


def run_automatic_hunt(state: GameState) -> None:
    run_automatic_action(state, HUNT_ACTION_KEY)


def run_automatic_patrol(state: GameState) -> None:
    run_automatic_action(state, PATROL_ACTION_KEY)


def run_automatic_defend(state: GameState) -> None:
    run_automatic_action(state, DEFEND_ACTION_KEY)


def _has_units(state: GameState, requirements: dict[UnitType, int]) -> bool:
    return all(state.units[unit] >= amount for unit, amount in requirements.items())


def _has_buildings(
    state: GameState, requirements: dict[BuildingType, int]
) -> bool:
    return all(
        state.buildings[building] >= amount
        for building, amount in requirements.items()
    )


def _has_resources(
    state: GameState, requirements: dict[ResourceType, float]
) -> bool:
    return all(
        state.resources[resource] >= amount
        for resource, amount in requirements.items()
    )


def _run_automated_action(state: GameState, action_key: str) -> None:
    if action_key == HUNT_ACTION_KEY:
        hunt(state)
    elif action_key == PATROL_ACTION_KEY:
        patrol(state)
    elif action_key == DEFEND_ACTION_KEY:
        defend(state)


def update_threats(state: GameState, elapsed_seconds: float = 1.0) -> None:
    expired_messages = []
    remaining_threats = []
    for active_threat in state.active_threats:
        active_threat.remaining_seconds = max(
            0.0, active_threat.remaining_seconds - elapsed_seconds
        )
        if active_threat.remaining_seconds <= 0:
            expired_messages.append(resolve_threat(state, active_threat))
        else:
            remaining_threats.append(active_threat)
    state.active_threats = remaining_threats

    state.threat_roll_cooldown = max(
        0.0, state.threat_roll_cooldown - elapsed_seconds
    )
    new_threat_message = ""
    if state.threat_roll_cooldown <= 0:
        active_threat = create_random_threat(state)
        state.active_threats.append(active_threat)
        state.threat_roll_cooldown = THREAT_ROLL_SECONDS
        new_threat_message = f"New threat: {active_threat_name(active_threat)}."

    messages = [*expired_messages]
    if new_threat_message:
        messages.append(new_threat_message)
    if messages:
        record_action_message(state, " ".join(messages))


def tick(state: GameState) -> None:
    if state.is_dead:
        return

    state.run_elapsed_seconds += 1.0

    delta = calculate_delta(state)
    apply_delta(state, delta)
    if state.is_dead:
        return

    reduce_cooldowns(state)
    run_automatic_hunt(state)
    run_automatic_patrol(state)
    run_automatic_defend(state)
    update_threats(state)
