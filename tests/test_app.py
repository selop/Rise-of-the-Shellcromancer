import asyncio
import json

from textual.widgets import DataTable, Static, TabbedContent

from shellcromancer.actions import (
    HUNT_ACTION_KEY,
    KINDLE_PYRE_ACTION_KEY,
    PATROL_ACTION_KEY,
)
from shellcromancer.app import (
    MENU_ACTIONS,
    ShellcromancerApp,
    action_status_style,
    action_index,
    is_action_affordable,
    render_state,
)
from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.units import UnitType


def test_render_state_snapshot_only_shows_implemented_features() -> None:
    rendered = render_state(GameState())

    assert "Resources Tab" in rendered
    assert "Shop Tab" in rendered
    assert "Future PvE Targets" not in rendered
    assert "Village" not in rendered


def test_render_state_lists_units_buildings_and_actions() -> None:
    rendered = render_state(GameState())

    assert "Units" in rendered
    assert "Buildings" in rendered
    assert "Actions" in rendered
    assert "Creature" not in rendered
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


def test_app_uses_resource_and_shop_tabs(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            tabs = app.query_one(TabbedContent)
            resource_table = app.query_one("#resource-table", DataTable)
            unit_table = app.query_one("#unit-table", DataTable)
            building_table = app.query_one("#building-table", DataTable)
            shop_view = app.query_one("#shop-view", Static)

            assert tabs.active == "resources-tab"
            assert resource_table.row_count == len(ResourceType)
            assert unit_table.row_count == len(UnitType)
            assert building_table.row_count == len(BuildingType)
            assert unit_table.get_row_at(0) == ["Worker", "0"]
            assert building_table.get_row_at(0) == ["Farm", "0"]
            assert str(shop_view.content).startswith("Units")

    asyncio.run(run_app())


def test_shop_tab_keeps_initial_selection_buyable(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            tabs = app.query_one(TabbedContent)
            tabs.active = "shop-tab"
            await pilot.pause()

            assert app.selected_action_index == action_index(0, 0)
            await pilot.press("e")
            await pilot.pause()

            assert app.state.units[UnitType.WORKER] == 1

    asyncio.run(run_app())


def test_render_state_only_shows_selected_recipe() -> None:
    rendered = render_state(GameState())

    assert "Selected" in rendered
    assert "Cost: 10 shell" in rendered
    assert rendered.count("Cost:") == 1
    assert "1 worker, 5 iron, 5 shell" not in rendered


def test_render_state_marks_affordable_and_unaffordable_actions() -> None:
    state = GameState()

    worker_rendered = render_state(state)
    farm_rendered = render_state(state, selected_action_index=action_index(1, 0))

    assert "[green]Ready[/]" in worker_rendered
    assert "[red]Missing requirements[/]" in farm_rendered


def test_action_status_style_marks_buyable_and_blocked_items() -> None:
    state = GameState()
    worker = next(action for action in MENU_ACTIONS if action.label == "Worker")
    farm = next(action for action in MENU_ACTIONS if action.label == "Farm")

    assert action_status_style(state, worker) == "green"
    assert action_status_style(state, farm) == "red"


def test_shop_keyboard_navigation_moves_inside_columns(tmp_path) -> None:
    app = ShellcromancerApp(save_path=tmp_path / "save.json")
    app.selected_action_index = action_index(1, 0)

    app.action_select_next()
    assert app.selected_action_index == action_index(1, 1)

    app.action_select_right()
    assert app.selected_action_index == action_index(2, 1)

    app.action_select_previous()
    assert app.selected_action_index == action_index(2, 0)


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
    assert "Press r to start a new run" in rendered
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
