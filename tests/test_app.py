import asyncio
import json
from pathlib import Path

from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static, TabbedContent

from shellcromancer.actions import (
    DEFEND_ACTION_KEY,
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
    format_action_cost,
    format_action_requirements,
    format_shop_tooltip,
    is_action_affordable,
    render_state,
)
from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState, record_action_message
from shellcromancer.resources import ResourceType
from shellcromancer.threats import THREAT_ROLL_SECONDS, ActiveThreat
from shellcromancer.units import UnitType


def test_render_state_snapshot_only_shows_implemented_features() -> None:
    rendered = render_state(GameState())

    assert "Scribe Tab" in rendered
    assert "Run Time: 0:00" in rendered
    assert "Reign Tab" in rendered
    assert "Battle Tab" in rendered
    assert "Next threat roll: 10:00" in rendered
    assert "No active threats." in rendered
    assert "Logs Tab" in rendered
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
    assert "Ranger" in rendered
    assert "Captain" in rendered
    assert "Watchpost" in rendered
    assert "Sorcerer" in rendered
    assert "Arcane Tower" in rendered
    assert "Catapult" in rendered
    assert "Storage" in rendered
    assert "Kindle the Pyre" in rendered
    assert "Defend" in rendered


def test_menu_includes_new_units_buildings_and_actions() -> None:
    labels = {menu_action.label for menu_action in MENU_ACTIONS}

    assert "Mine" in labels
    assert "Quarry" in labels
    assert "Hunt" in labels
    assert "Patrol" in labels
    assert "Expedition" in labels
    assert "Ranger" in labels
    assert "Captain" in labels
    assert "Watchpost" in labels
    assert "Sorcerer" in labels
    assert "Arcane Tower" in labels
    assert "Catapult" in labels
    assert "Storage" in labels
    assert "Kindle the Pyre" in labels
    assert "Defend" in labels


def test_render_state_shows_gold_resource() -> None:
    rendered = render_state(GameState())

    assert "gold       0.0 / 100.0   (+0.0/s)" in rendered



def test_render_state_shows_resource_capacity_and_capped_status() -> None:
    state = GameState()
    state.resources[ResourceType.SHELL] = 100.0
    state.last_delta[ResourceType.SHELL] = 0.1

    rendered = render_state(state)

    assert "shell    100.0 / 100.0   (+0.1/s (capped))" in rendered


def test_render_state_storage_increases_resource_capacity() -> None:
    state = GameState()
    state.buildings[BuildingType.STORAGE] = 2

    rendered = render_state(state)

    assert "wood      10.0 / 300.0" in rendered

def test_render_state_shows_active_threats_and_encyclopedia() -> None:
    state = GameState()
    state.run_elapsed_seconds = 1200.0
    state.active_threats.append(ActiveThreat(key="goblin_raid", remaining_seconds=59.0))

    rendered = render_state(state)

    assert "Goblin Raid: 0:59" in rendered
    assert "Destroys up to 4 farms" in rendered
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
            unit_shop_table = app.query_one("#unit-shop-table", DataTable)
            building_shop_table = app.query_one("#building-shop-table", DataTable)
            action_shop_table = app.query_one("#action-shop-table", DataTable)
            battle_summary = app.query_one("#battle-summary", Static)
            encyclopedia_view = app.query_one("#encyclopedia-view", Static)

            assert tabs.active == "scribe-tab"
            assert resource_table.row_count == len(ResourceType)
            assert resource_table.get_row_at(0) == ["wood", "10.0 / 100.0", "+0.0/s"]
            assert unit_table.row_count == len(UnitType)
            assert building_table.row_count == len(BuildingType)
            assert unit_table.get_row_at(0) == ["Worker", "0"]
            assert building_table.get_row_at(0) == ["Farm", "0"]
            assert unit_shop_table.row_count == 7
            assert building_shop_table.row_count == 6
            assert action_shop_table.row_count == 5
            assert "Worker" in str(unit_shop_table.get_row_at(0)[0])
            assert "Farm" in str(building_shop_table.get_row_at(0)[0])
            assert "Hunt" in str(action_shop_table.get_row_at(0)[0])
            assert "Next threat roll: 10:00" in str(battle_summary.content)
            assert "No active threats." in str(battle_summary.content)
            assert "Resources" in str(encyclopedia_view.content)
            assert "Goblin Raid" in str(encyclopedia_view.content)

    asyncio.run(run_app())


def test_app_frames_major_panels() -> None:
    import shellcromancer.app as app_module

    css_path = Path(app_module.__file__).parent / ShellcromancerApp.CSS_PATH
    css = css_path.read_text(encoding="utf-8")

    assert "#resource-table, #unit-table, #building-table" in css
    assert "#unit-shop-table, #building-shop-table, #action-shop-table" in css
    assert "#battle-view" in css
    assert "#logs-view" in css
    assert "#encyclopedia-view" in css
    assert "#selected" in css
    assert "#status" in css
    assert "#execute" not in css
    assert "border: solid $surface-lighten-1;" in css
    assert "border: solid $accent;" in css
    assert "min-height: 6;" in css


def test_status_panel_shows_story_and_last_three_actions(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            record_action_message(app.state, "A patrol returned with gold.")
            record_action_message(app.state, "A ranger found a trail.")
            record_action_message(app.state, "A defense held.")
            app._refresh_view()

            status = app.query_one("#status", Static)
            assert "Run Time: 0:00" in str(status.content)
            content = str(status.content)
            assert "Story" in content
            assert "A patrol returned with gold." in content
            assert "A ranger found a trail." in content
            assert "A defense held." in content
            assert "Welcome, Shellcromancer." not in content

    asyncio.run(run_app())


def test_logs_tab_shows_last_twenty_five_actions(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            for index in range(30):
                record_action_message(app.state, f"Log entry {index}.")
            app._refresh_view()

            logs = app.query_one("#logs-view", Static)
            content = str(logs.content)
            assert "Logs" in content
            assert "Log entry 5." in content
            assert "Log entry 29." in content
            assert "Log entry 4." not in content

            status = app.query_one("#status", Static)
            story = str(status.content)
            assert "Log entry 27." in story
            assert "Log entry 29." in story
            assert "Log entry 26." not in story

    asyncio.run(run_app())


def test_status_panel_shows_game_over_story(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            app.state.is_dead = True
            record_action_message(app.state, "The stores are empty.")
            app._refresh_view()

            status = app.query_one("#status", Static)
            assert "Game Over" in str(status.content)
            assert "Run Time: 0:00" in str(status.content)
            assert "The stores are empty." in str(status.content)
            assert "Press n to start a new run." in str(status.content)

    asyncio.run(run_app())


def test_scribe_reign_battle_logs_and_encyclopedia_tab_shortcuts(tmp_path) -> None:
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

            await pilot.press("l")
            await pilot.pause()
            assert tabs.active == "logs-tab"

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
    captain_rendered = render_state(
        GameState(), selected_action_index=action_index(0, 4)
    )
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

    assert "Cost: 10 gold" in captain_rendered
    assert "Requirements: 1 soldier" in captain_rendered

    assert "Cost: 10 food" in patrol_rendered
    assert "Requirements: 3 soldiers, cooldown ready" in patrol_rendered

    assert "Cost: 25 food, 5 gold" in expedition_rendered
    assert (
        "Requirements: 1 captain, 10 soldiers, cooldown ready"
        in expedition_rendered
    )

    assert "Cost: -" in defend_rendered
    assert (
        "Requirements: 1 catapult, cooldown ready, active threat, "
        "25-75% success chance"
    ) in defend_rendered

    kindle_rendered = render_state(
        GameState(), selected_action_index=action_index(2, 3)
    )
    assert "Cost: 100 wood" in kindle_rendered
    assert (
        "Requirements: 1 sorcerer, 1 arcane tower, cooldown ready"
        in kindle_rendered
    )


def test_render_state_shows_scaled_storage_cost() -> None:
    state = GameState()
    state.buildings[BuildingType.STORAGE] = 1

    rendered = render_state(state, selected_action_index=action_index(1, 5))

    assert "Cost: 100 wood, 50 stone" in rendered
    assert "Requirements: 2 workers" in rendered


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


def test_render_state_marks_patrol_manual_with_captain_and_automation_off() -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1

    rendered = render_state(state, selected_action_index=action_index(2, 1))

    assert "Patrol (M)" in rendered


def test_render_state_marks_patrol_automated_with_captain_and_automation_on() -> None:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.automation_enabled[PATROL_ACTION_KEY] = True

    rendered = render_state(state, selected_action_index=action_index(2, 1))

    assert "Patrol (A)" in rendered


def test_render_state_marks_hunt_automated_with_ranger() -> None:
    state = GameState()
    state.units[UnitType.RANGER] = 1

    rendered = render_state(state, selected_action_index=action_index(2, 0))

    assert "Hunt (A)" in rendered


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


def test_render_state_shows_defend_cooldown_behind_action() -> None:
    state = GameState()
    state.action_cooldowns[DEFEND_ACTION_KEY] = 299.0

    rendered = render_state(state, selected_action_index=action_index(2, 4))

    assert "Defend" in rendered
    assert "4:59" in rendered
    assert "Cooldown 4:59" in rendered


def test_render_state_marks_defend_automated_with_watchpost() -> None:
    state = GameState()
    state.units[UnitType.WATCHPOST] = 1

    rendered = render_state(state, selected_action_index=action_index(2, 4))

    assert "Defend (A)" in rendered


def test_render_state_hides_automation_marker_until_enabler_exists() -> None:
    state = GameState()
    state.automation_enabled[PATROL_ACTION_KEY] = True

    rendered = render_state(state, selected_action_index=action_index(2, 1))

    assert "Hunt (A)" not in rendered
    assert "Patrol (A)" not in rendered
    assert "Patrol (M)" not in rendered
    assert "Defend (A)" not in rendered
    assert "Patrol" in rendered


def test_toggle_automation_flips_selected_action_and_logs(tmp_path) -> None:
    app = ShellcromancerApp(save_path=tmp_path / "save.json")
    app.state.units[UnitType.CAPTAIN] = 1
    app.selected_action_index = action_index(2, 1)

    app.action_toggle_automation()

    assert app.state.automation_enabled[PATROL_ACTION_KEY] is True
    assert app.state.last_action_message == "Auto Patrol enabled."

    app.action_toggle_automation()

    assert app.state.automation_enabled[PATROL_ACTION_KEY] is False
    assert app.state.last_action_message == "Auto Patrol disabled."


def test_toggle_automation_cannot_enable_before_enabler_exists(tmp_path) -> None:
    app = ShellcromancerApp(save_path=tmp_path / "save.json")
    app.selected_action_index = action_index(2, 1)

    app.action_toggle_automation()

    assert app.state.automation_enabled[PATROL_ACTION_KEY] is False
    assert app.state.last_action_message == "Need a captain to enable Auto Patrol."


def test_toggle_automation_can_disable_after_enabler_is_lost(tmp_path) -> None:
    app = ShellcromancerApp(save_path=tmp_path / "save.json")
    app.state.automation_enabled[PATROL_ACTION_KEY] = True
    app.state.units[UnitType.CAPTAIN] = 0
    app.selected_action_index = action_index(2, 1)

    app.action_toggle_automation()

    assert app.state.automation_enabled[PATROL_ACTION_KEY] is False
    assert app.state.last_action_message == "Auto Patrol disabled."


def test_toggle_automation_ignores_non_automated_action(tmp_path) -> None:
    app = ShellcromancerApp(save_path=tmp_path / "save.json")
    app.selected_action_index = action_index(2, 2)

    app.action_toggle_automation()

    assert app.state.last_action_message == "Welcome, Shellcromancer."
    assert app.state.action_history == ["Welcome, Shellcromancer."]


def test_render_state_shows_defend_success_chance_range() -> None:
    rendered = render_state(GameState(), selected_action_index=action_index(2, 4))

    assert "25-75% success chance" in rendered


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

    state.action_cooldowns[DEFEND_ACTION_KEY] = 1.0
    assert is_action_affordable(state, defend) is False


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


def test_storage_affordability_uses_scaled_cost() -> None:
    state = GameState()
    state.buildings[BuildingType.STORAGE] = 1
    state.resources[ResourceType.WOOD] = 100.0
    state.resources[ResourceType.STONE] = 50.0
    storage = next(action for action in MENU_ACTIONS if action.label == "Storage")

    state.units[UnitType.WORKER] = 1
    assert is_action_affordable(state, storage) is False

    state.units[UnitType.WORKER] = 2
    assert is_action_affordable(state, storage) is True

    state.resources[ResourceType.WOOD] = 99.9
    assert is_action_affordable(state, storage) is False


def test_storage_formatters_use_scaled_cost_when_state_is_given() -> None:
    state = GameState()
    state.buildings[BuildingType.STORAGE] = 2
    storage = next(action for action in MENU_ACTIONS if action.label == "Storage")

    assert format_action_cost(storage, state) == "150 wood, 75 stone"
    assert format_action_requirements(storage, state) == "3 workers"


def test_dead_state_renders_game_over_and_restart_key() -> None:
    state = GameState()
    state.is_dead = True
    state.run_elapsed_seconds = 125.0
    state.resources[ResourceType.FOOD] = 0.0
    record_action_message(state, "The stores are empty.")

    rendered = render_state(state)

    assert "Game Over" in rendered
    assert "Food reached 0" in rendered
    assert "Final Run Time: 2:05" in rendered
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
    app.state.automation_enabled[HUNT_ACTION_KEY] = False
    app.state.automation_enabled[PATROL_ACTION_KEY] = True
    app.state.automation_enabled[DEFEND_ACTION_KEY] = False

    app.action_reset()

    assert app.state.is_dead is False
    assert app.state.resources[ResourceType.FOOD] == 10.0
    assert app.state.automation_enabled[HUNT_ACTION_KEY] is True
    assert app.state.automation_enabled[PATROL_ACTION_KEY] is False
    assert app.state.automation_enabled[DEFEND_ACTION_KEY] is True
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


def test_format_shop_tooltip_includes_recipe_and_production() -> None:
    state = GameState()

    worker = next(action for action in MENU_ACTIONS if action.label == "Worker")
    worker_tip = format_shop_tooltip(state, worker)
    assert "Worker" in worker_tip
    assert "Status: Ready" in worker_tip
    assert "Cost: 10 shell" in worker_tip
    assert "Upkeep: +0.1 food/s" in worker_tip

    farm = next(action for action in MENU_ACTIONS if action.label == "Farm")
    farm_tip = format_shop_tooltip(state, farm)
    assert "Produces: +0.2 food/s" in farm_tip
    assert "Requires: 1 worker" in farm_tip

    storage = next(action for action in MENU_ACTIONS if action.label == "Storage")
    assert (
        "Effect: +100 capacity to every resource"
        in format_shop_tooltip(state, storage)
    )


def test_shop_table_hover_sets_recipe_tooltip(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            app.unit_shop_table.hover_coordinate = Coordinate(0, 1)
            await pilot.pause()
            assert app.unit_shop_table.tooltip is not None
            assert "Worker" in app.unit_shop_table.tooltip

            app.action_shop_table.hover_coordinate = Coordinate(2, 0)
            await pilot.pause()
            assert "Expedition" in app.action_shop_table.tooltip

            # Hovering the header row (no recipe) clears the tooltip.
            app.unit_shop_table.hover_coordinate = Coordinate(-1, 0)
            await pilot.pause()
            assert app.unit_shop_table.tooltip is None

    asyncio.run(run_app())


def test_battle_tab_mounts_and_removes_threat_bars(tmp_path) -> None:
    async def run_app() -> None:
        app = ShellcromancerApp(save_path=tmp_path / "save.json")
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app._threat_rows == []
            assert app.next_threat_bar.total == THREAT_ROLL_SECONDS
            assert app.next_threat_bar.progress == app.state.threat_roll_cooldown

            app.state.active_threats.append(
                ActiveThreat(key="goblin_raid", remaining_seconds=150.0)
            )
            app._refresh_view()
            await pilot.pause()

            assert len(app._threat_rows) == 1
            assert "Active threats: 1" in str(app.battle_summary.content)
            assert len(app.threats_container.query("ProgressBar")) == 1

            app.state.active_threats.clear()
            app._refresh_view()
            await pilot.pause()

            assert app._threat_rows == []
            assert "No active threats." in str(app.battle_summary.content)

    asyncio.run(run_app())
