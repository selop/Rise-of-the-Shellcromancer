from shellcromancer.buildings import BUILDING_DEFINITIONS
from shellcromancer.actions import PATROL_ACTION_KEY, patrol
from shellcromancer.game_state import GameState, empty_delta
from shellcromancer.resources import ResourceType
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
        state.resources[resource] = max(0.0, state.resources[resource] + amount)
    state.last_delta = delta.copy()
    mark_dead_if_food_depleted(state)


def mark_dead_if_food_depleted(state: GameState) -> None:
    if state.is_dead:
        return
    if state.resources[ResourceType.FOOD] > 0:
        return

    state.is_dead = True
    state.last_action_message = DEATH_MESSAGE


def reduce_cooldowns(state: GameState, elapsed_seconds: float = 1.0) -> None:
    for action_key, remaining in state.action_cooldowns.items():
        state.action_cooldowns[action_key] = max(0.0, remaining - elapsed_seconds)


def run_automatic_patrol(state: GameState) -> None:
    if state.units[UnitType.CAPTAIN] < 1:
        return
    if state.action_cooldowns.get(PATROL_ACTION_KEY, 0.0) > 0:
        return
    if state.units[UnitType.SOLDIER] < 3:
        return
    if state.resources[ResourceType.FOOD] < 10.0:
        return

    patrol(state)


def tick(state: GameState) -> None:
    if state.is_dead:
        return

    delta = calculate_delta(state)
    apply_delta(state, delta)
    if state.is_dead:
        return

    reduce_cooldowns(state)
    run_automatic_patrol(state)
