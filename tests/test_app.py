import asyncio
import json

from textual.widgets import DataTable, Static, TabbedContent

from shellcromancer.actions import (
    EXPEDITION_ACTION_KEY,
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
from shellcromancer.threats import ActiveThreat
from shellcromancer.units import UnitType


def test_render_state_snapshot_only_shows_implemented_features() -> None:
    rendered = render_state(GameState())

    assert "Scribe Tab" in rendered
    assert "Reign Tab" in rendered
    assert "Battle Tab" in rendered
    assert "Next threat roll: 10:00" in rendered
    assert "No active threats." in rendered
    assert "Encyclopedia Tab" in rendered
    assert "Resources Tab" not in rendered
    assert "Shop Tab" not in rendered
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
    assert "Expedition" in rendered
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
    assert "Expedition" in labels
    assert "Captain" in labels
    assert "Sorcerer" in labels
    assert "Arcane Tower" in labels
    assert "Catapult" in labels
    assert "Kindle the Pyre" in labels
    assert "Defend" in labels


def test_render_state_shows_gold_resource() -> None:
    rendered = render_state(GameState())

    assert "gold      0.0   (+0.0/s)" in rendered


def test_render_state_shows_active_threats_and_encyclopedia() -> None:
    state = GameState()
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=59.0))

    rendered = render_state(state)

    assert "Goblin Raid: 0:59" in rendered
    assert "Destroys up to 2 farms" in rendered
    assert "Resources" in rendered
    assert "Threats" in rendered
    assert "Mine Saboteurs" in rendered


def test_app_uses_scribe_reign_and_battle_tabs(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            tabs = app.query_one(TabbedContent)
            resource_table = app.query_one("#resource-table", DataTable)
            unit_table = app.query_one("#unit-table", DataTable)
            building_table = app.query_one("#building-table", DataTable)
            shop_view = app.query_one("#shop-view", Static)
            battle_view = app.query_one("#battle-view", Static)
            encyclopedia_view = app.query_one("#encyclopedia-view", Static)

            assert tabs.active == "scribe-tab"
            assert resource_table.row_count == len(ResourceType)
            assert unit_table.row_count == len(UnitType)
            assert building_table.row_count == len(BuildingType)
            assert unit_table.get_row_at(0) == ["Worker", "0"]
            assert building_table.get_row_at(0) == ["Farm", "0"]
            assert str(shop_view.content).startswith("Units")
            assert "Next threat roll: 10:00" in str(battle_view.content)
            assert "No active threats." in str(battle_view.content)
            assert "Resources" in str(encyclopedia_view.content)
            assert "Goblin Raid" in str(encyclopedia_view.content)

    asyncio.run(run_app())


def test_app_frames_major_panels() -> None:
    css = ShellcromancerApp.CSS

    assert "#resource-table, #unit-table, #building-table" in css
    assert "#shop-view" in css
    assert "#battle-view" in css
    assert "#encyclopedia-view" in css
    assert "#selected" in css
    assert "#status" in css
    assert "#execute" not in css
    assert "border: solid $surface-lighten-1;" in css
    assert "border: solid $accent;" in css
    assert "min-height: 6;" in css


def test_status_panel_shows_story_and_last_action(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            app.state.last_action_message = "A patrol returned with gold."
            app._refresh_view()

            status = app.query_one("#status", Static)
            assert "Story" in str(status.content)
            assert "Last action: A patrol returned with gold." in str(status.content)

    asyncio.run(run_app())


def test_status_panel_shows_game_over_story(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            app.state.is_dead = True
            app.state.last_action_message = "The stores are empty."
            app._refresh_view()

            status = app.query_one("#status", Static)
            assert "Game Over" in str(status.content)
            assert "The stores are empty." in str(status.content)
            assert "Press n to start a new run." in str(status.content)

    asyncio.run(run_app())


def test_scribe_reign_and_battle_tab_shortcuts(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            tabs = app.query_one(TabbedContent)
            await pilot.press("r")
            await pilot.pause()
            assert tabs.active == "reign-tab"

            await pilot.press("b")
            await pilot.pause()
            assert tabs.active == "battle-tab"

            await pilot.press("e")
            await pilot.pause()
            assert tabs.active == "encyclopedia-tab"

            await pilot.press("s")
            await pilot.pause()
            assert tabs.active == "scribe-tab"

    asyncio.run(run_app())


def test_reign_tab_keeps_initial_selection_buyable_and_enter_executes(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            tabs = app.query_one(TabbedContent)
            tabs.active = "reign-tab"
            await pilot.pause()

            assert app.selected_action_index == action_index(0, 0)
            await pilot.press("e")
            await pilot.pause()
            assert app.state.units[UnitType.WORKER] == 0

            await pilot.press("enter")
            await pilot.pause()
            assert app.state.units[UnitType.WORKER] == 1

    asyncio.run(run_app())


def test_render_state_only_shows_selected_recipe() -> None:
    rendered = render_state(GameState())

    assert "Selected" in rendered
    assert "Cost: 10 shell" in rendered
    assert "Requirements: -" in rendered
    assert rendered.count("Cost:") == 1
    assert rendered.count("Requirements:") == 1
    assert "1 worker, 5 iron, 5 shell" not in rendered


def test_render_state_splits_resource_costs_from_requirements() -> None:
    farm_rendered = render_state(GameState(), selected_action_index=action_index(1, 0))
    patrol_rendered = render_state(
        GameState(), selected_action_index=action_index(2, 1)
    )
    expedition_rendered = render_state(
        GameState(), selected_action_index=action_index(2, 2)
    )
    defend_rendered = render_state(
        GameState(), selected_action_index=action_index(2, 4)
    )

    assert "Cost: 10 wood, 10 stone, 2 iron" in farm_rendered
    assert "Requirements: 1 worker" in farm_rendered
    assert "Cost: 10 wood, 10 stone, 2 iron, 1 worker" not in farm_rendered

    assert "Cost: 10 food" in patrol_rendered
    assert "Requirements: 3 soldiers, cooldown ready" in patrol_rendered

    assert "Cost: 25 food, 5 gold" in expedition_rendered
    assert (
        "Requirements: 1 captain, 10 soldiers, cooldown ready"
        in expedition_rendered
    )

    assert "Cost: -" in defend_rendered
    assert "Requirements: 1 catapult, active threat" in defend_rendered

    kindle_rendered = render_state(
        GameState(), selected_action_index=action_index(2, 3)
    )
    assert "Cost: 100 wood" in kindle_rendered
    assert (
        "Requirements: 1 sorcerer, 1 arcane tower, cooldown ready"
        in kindle_rendered
    )


def test_selected_panel_splits_costs_and_requirements(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            app.selected_action_index = action_index(1, 0)
            app._refresh_view()

            selected = app.query_one("#selected", Static)
            content = str(selected.content)
            assert "Farm: [red]Missing requirements[/]" in content
            assert "Cost: 10 wood, 10 stone, 2 iron" in content
            assert "Requirements: 1 worker" in content

    asyncio.run(run_app())


def test_render_state_marks_affordable_and_unaffordable_actions() -> None:
    state = GameState()

    worker_rendered = render_state(state)
    farm_rendered = render_state(state, selected_action_index=action_index(1, 0))

    assert "[green]Ready[/]" in worker_rendered
    assert "[red]Missing requirements[/]" in farm_rendered
    assert farm_rendered.count("[red]Missing requirements[/]") == 1


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


def test_render_state_shows_expedition_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[EXPEDITION_ACTION_KEY] = 299.0

    rendered = render_state(state, selected_action_index=action_index(2, 2))

    assert "Expedition" in rendered
    assert "4:59" in rendered
    assert "Cooldown 4:59" in rendered


def test_render_state_shows_kindle_the_pyre_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = 599.0

    rendered = render_state(state, selected_action_index=action_index(2, 3))

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


def test_expedition_affordability_requires_requirements() -> None:
    state = GameState()
    expedition = next(
        action for action in MENU_ACTIONS if action.label == "Expedition"
    )

    assert is_action_affordable(state, expedition) is False

    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 10
    state.resources[ResourceType.FOOD] = 25.0
    state.resources[ResourceType.GOLD] = 5.0
    assert is_action_affordable(state, expedition) is True

    state.resources[ResourceType.GOLD] = 4.9
    assert is_action_affordable(state, expedition) is False

    state.resources[ResourceType.GOLD] = 5.0
    state.action_cooldowns[EXPEDITION_ACTION_KEY] = 1.0
    assert is_action_affordable(state, expedition) is False


def test_kindle_the_pyre_affordability_requires_wood_tower_and_cooldown() -> None:
    state = GameState()
    kindle = next(action for action in MENU_ACTIONS if action.label == "Kindle the Pyre")

    assert is_action_affordable(state, kindle) is False

    state.resources[ResourceType.WOOD] = 100.0
    assert is_action_affordable(state, kindle) is False

    state.units[UnitType.SORCERER] = 1
    assert is_action_affordable(state, kindle) is False

    state.buildings[BuildingType.ARCANE_TOWER] = 1
    assert is_action_affordable(state, kindle) is True

    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = 1.0
    assert is_action_affordable(state, kindle) is False


def test_defend_affordability_requires_catapult() -> None:
    state = GameState()
    defend = next(action for action in MENU_ACTIONS if action.label == "Defend")

    assert is_action_affordable(state, defend) is False

    state.buildings[BuildingType.CATAPULT] = 1
    assert is_action_affordable(state, defend) is False

    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=60.0))
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
    assert "Press n to start a new run" in rendered
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


def test_new_game_shortcut_starts_new_run_after_death(tmp_path) -> None:
    async def run_app() -> None:
        save_path = tmp_path / "save.json"
        app = ShellcromancerApp(save_path=save_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.state.is_dead = True
            app.state.resources[ResourceType.FOOD] = 0.0
            app._refresh_view()

            await pilot.press("n")
            await pilot.pause()

            assert app.state.is_dead is False
            assert app.state.resources[ResourceType.FOOD] == 10.0
            assert save_path.exists()

    asyncio.run(run_app())


def test_resource_shortcut_does_not_restart_after_death(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()
            app.state.is_dead = True
            app.state.resources[ResourceType.FOOD] = 0.0
            app._refresh_view()

            await pilot.press("r")
            await pilot.pause()

            assert app.state.is_dead is True
            assert app.state.resources[ResourceType.FOOD] == 0.0

    asyncio.run(run_app())


def test_app_marks_loaded_zero_food_save_dead(tmp_path) -> None:
    save_path = tmp_path / "save.json"
    save_path.write_text(
        json.dumps({"resources": {"food": 0.0}, "is_dead": False}),
        encoding="utf-8",
    )

    app = ShellcromancerApp(save_path=save_path)

    assert app.state.is_dead is True
