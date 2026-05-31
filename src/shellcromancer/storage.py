from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState
from shellcromancer.resources import ALL_RESOURCES, ResourceType


BASE_RESOURCE_CAPACITY = 100.0
STORAGE_CAPACITY_BONUS = 100.0


def resource_capacity(state: GameState, resource: ResourceType) -> float:
    return BASE_RESOURCE_CAPACITY + (
        state.buildings[BuildingType.STORAGE] * STORAGE_CAPACITY_BONUS
    )


def add_resource(state: GameState, resource: ResourceType, amount: float) -> None:
    capacity = resource_capacity(state, resource)
    current = state.resources[resource]
    state.resources[resource] = max(0.0, min(current + amount, capacity))


def clamp_resource(state: GameState, resource: ResourceType) -> None:
    add_resource(state, resource, 0.0)


def clamp_all_resources(state: GameState) -> None:
    for resource in ALL_RESOURCES:
        clamp_resource(state, resource)


def is_resource_capped(state: GameState, resource: ResourceType) -> bool:
    return state.resources[resource] >= resource_capacity(state, resource)
