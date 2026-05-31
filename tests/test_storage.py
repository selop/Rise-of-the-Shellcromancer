from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.storage import add_resource


def test_add_resource_returns_full_applied_positive_delta() -> None:
    state = GameState()

    applied = add_resource(state, ResourceType.FOOD, 7.0)

    assert applied == 7.0
    assert state.resources[ResourceType.FOOD] == 17.0


def test_add_resource_returns_capped_positive_delta() -> None:
    state = GameState()
    state.resources[ResourceType.FOOD] = 98.0

    applied = add_resource(state, ResourceType.FOOD, 7.0)

    assert applied == 2.0
    assert state.resources[ResourceType.FOOD] == 100.0


def test_add_resource_returns_negative_delta() -> None:
    state = GameState()

    applied = add_resource(state, ResourceType.FOOD, -4.0)

    assert applied == -4.0
    assert state.resources[ResourceType.FOOD] == 6.0
