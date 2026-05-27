import json

from shellcromancer.actions import HUNT_ACTION_KEY, KINDLE_PYRE_ACTION_KEY, PATROL_ACTION_KEY
from shellcromancer.app import (
    MENU_ACTIONS,
    ShellcromancerApp,
    action_index,
    is_action_affordable,
    render_state,
)
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.units import UnitType
from shellcromancer.buildings import BuildingType


def test_render_state_shows_keybindings_and_only_implemented_features() -> None:
    rendered = render_state(GameState())

    assert "Keybindings" in rendered
    assert "enter" in rendered
    assert "Future PvE Targets" not in rendered
    assert "Village" not in rendered


def test_render_state_lists_creatures_and_buildings_in_overview() -> None:
    rendered = render_state(GameState())

    assert "Overview" in rendered
    assert "Creatures" in rendered
    assert "Buildings" in rendered
    assert "Actions" in rendered
    assert "Worker" in rendered
    assert "Farm" in rendered
    assert "Mine" in rendered
    assert "Quarry" in rendered
    assert "Hunt" in rendered
    assert "Patrol" in rendered
    assert "Captain" in rendered
    assert "Sorcerer" in rendered
    assert "Arcane Tower" in rendered
    assert "Catapult" in rendered
    assert "Kindle the Pyre" in rendered
    assert "Defend" in rendered


def test_menu_includes_new_units_buildings_and_actions() -> None:
    labels = {menu_action.label for menu_action in MENU_ACTIONS}

    assert "Mine" in labels
    assert "Quarry" in labels
    assert "Hunt" in labels
    assert "Patrol" in labels
    assert "Captain" in labels
    assert "Sorcerer" in labels
    assert "Arcane Tower" in labels
    assert "Catapult" in labels
    assert "Kindle the Pyre" in labels
    assert "Defend" in labels


def test_render_state_shows_gold_resource() -> None:
    rendered = render_state(GameState())

    assert "gold      0.0   (+0.0/s)" in rendered


def test_render_state_uses_bordered_panels() -> None:
    rendered = render_state(GameState())

    assert "+ Resources" in rendered
    assert "+ Overview" in rendered
    assert "+ Selected" in rendered


def test_render_state_only_shows_selected_cost_below_overview() -> None:
    rendered = render_state(GameState())

    assert "Selected" in rendered
    assert "Cost: 10 shell" in rendered
    assert rendered.count("Cost:") == 1


def test_render_state_marks_affordable_and_unaffordable_actions() -> None:
    state = GameState()

    worker_rendered = render_state(state)
    farm_rendered = render_state(state, selected_action_index=action_index(1, 0))

    assert "[green]Ready[/]" in worker_rendered
    assert "[red]Missing requirements[/]" in farm_rendered


def test_render_state_shows_hunt_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[HUNT_ACTION_KEY] = 59.0

    rendered = render_state(state, selected_action_index=action_index(2, 0))

    assert "Hunt" in rendered
    assert "0:59" in rendered
    assert "Cooldown 0:59" in rendered


def test_render_state_shows_patrol_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[PATROL_ACTION_KEY] = 119.0

    rendered = render_state(state, selected_action_index=action_index(2, 1))

    assert "Patrol" in rendered
    assert "1:59" in rendered
    assert "Cooldown 1:59" in rendered


def test_render_state_shows_kindle_the_pyre_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = 599.0

    rendered = render_state(state, selected_action_index=action_index(2, 2))

    assert "Kindle the Pyre" in rendered
    assert "9:59" in rendered
    assert "Cooldown 9:59" in rendered


def test_render_state_does_not_show_action_chances() -> None:
    for selected_index, _menu_action in enumerate(MENU_ACTIONS):
        rendered = render_state(GameState(), selected_action_index=selected_index)

        assert "%" not in rendered


def test_action_affordability_accounts_for_units_and_resources() -> None:
    state = GameState()
    build_farm = next(action for action in MENU_ACTIONS if action.label == "Farm")

    assert is_action_affordable(state, build_farm) is False

    state.units[UnitType.WORKER] = 1
    assert is_action_affordable(state, build_farm) is True

    state.resources[ResourceType.STONE] = 9.9
    assert is_action_affordable(state, build_farm) is False


def test_patrol_affordability_requires_soldiers_food_and_cooldown() -> None:
    state = GameState()
    patrol = next(action for action in MENU_ACTIONS if action.label == "Patrol")

    assert is_action_affordable(state, patrol) is False

    state.units[UnitType.SOLDIER] = 3
    assert is_action_affordable(state, patrol) is True

    state.resources[ResourceType.FOOD] = 9.9
    assert is_action_affordable(state, patrol) is False

    state.resources[ResourceType.FOOD] = 10.0
    state.action_cooldowns[PATROL_ACTION_KEY] = 1.0
    assert is_action_affordable(state, patrol) is False


def test_kindle_the_pyre_affordability_requires_wood_and_cooldown() -> None:
    state = GameState()
    kindle = next(action for action in MENU_ACTIONS if action.label == "Kindle the Pyre")

    assert is_action_affordable(state, kindle) is False

    state.resources[ResourceType.WOOD] = 100.0
    assert is_action_affordable(state, kindle) is False

    state.units[UnitType.SORCERER] = 1
    assert is_action_affordable(state, kindle) is True

    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = 1.0
    assert is_action_affordable(state, kindle) is False


def test_defend_affordability_requires_catapult() -> None:
    state = GameState()
    defend = next(action for action in MENU_ACTIONS if action.label == "Defend")

    assert is_action_affordable(state, defend) is False

    state.buildings[BuildingType.CATAPULT] = 1
    assert is_action_affordable(state, defend) is True


def test_arcane_tower_affordability_requires_sorcerer_and_stone() -> None:
    state = GameState()
    arcane_tower = next(
        action for action in MENU_ACTIONS if action.label == "Arcane Tower"
    )

    assert is_action_affordable(state, arcane_tower) is False

    state.units[UnitType.SORCERER] = 1
    state.resources[ResourceType.STONE] = 250.0
    assert is_action_affordable(state, arcane_tower) is True

    state.resources[ResourceType.STONE] = 249.9
    assert is_action_affordable(state, arcane_tower) is False


def test_dead_state_renders_game_over_and_restart_key() -> None:
    state = GameState()
    state.is_dead = True
    state.resources[ResourceType.FOOD] = 0.0
    state.last_action_message = "The stores are empty."

    rendered = render_state(state)

    assert "Game Over" in rendered
    assert "Food reached 0" in rendered
    assert "r                  Start a new run" in rendered
    assert "The stores are empty." in rendered


def test_dead_state_makes_actions_unaffordable() -> None:
    state = GameState()
    state.is_dead = True
    worker = next(action for action in MENU_ACTIONS if action.label == "Worker")

    assert is_action_affordable(state, worker) is False


def test_reset_starts_new_run_and_saves_state(tmp_path) -> None:
    save_path = tmp_path / "save.json"
    app = ShellcromancerApp(save_path=save_path)
    app.state.is_dead = True
    app.state.resources[ResourceType.FOOD] = 0.0

    app.action_reset()

    assert app.state.is_dead is False
    assert app.state.resources[ResourceType.FOOD] == 10.0
    assert save_path.exists()


def test_app_marks_loaded_zero_food_save_dead(tmp_path) -> None:
    save_path = tmp_path / "save.json"
    save_path.write_text(
        json.dumps({"resources": {"food": 0.0}, "is_dead": False}),
        encoding="utf-8",
    )

    app = ShellcromancerApp(save_path=save_path)

    assert app.state.is_dead is True
