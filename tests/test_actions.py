from shellcromancer.actions import (
    EXPEDITION_ACTION_KEY,
    EXPEDITION_COOLDOWN_SECONDS,
    HUNT_ACTION_KEY,
    HUNT_COOLDOWN_SECONDS,
    KINDLE_PYRE_ACTION_KEY,
    KINDLE_PYRE_COOLDOWN_SECONDS,
    PATROL_ACTION_KEY,
    PATROL_COOLDOWN_SECONDS,
    build_arcane_tower,
    build_catapult,
    build_farm,
    build_mine,
    build_quarry,
    create_worker,
    defend,
    expedition,
    hunt,
    kindle_the_pyre,
    patrol,
    promote_worker_to_captain,
    upgrade_worker_to_lumberjack,
    upgrade_worker_to_soldier,
    upgrade_soldier_to_sorcerer,
)
from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState
from shellcromancer.resources import ResourceType
from shellcromancer.threats import ActiveThreat
from shellcromancer.units import UnitType


def patrol_ready_state() -> GameState:
    state = GameState()
    state.units[UnitType.SOLDIER] = 3
    return state


def expedition_ready_state() -> GameState:
    state = GameState()
    state.units[UnitType.CAPTAIN] = 1
    state.units[UnitType.SOLDIER] = 10
    state.resources[ResourceType.FOOD] = 25.0
    state.resources[ResourceType.GOLD] = 5.0
    return state


def test_create_worker_consumes_shell() -> None:
    state = GameState()

    result = create_worker(state)

    assert result.success is True
    assert state.resources[ResourceType.SHELL] == 0.0
    assert state.units[UnitType.WORKER] == 1


def test_cannot_create_worker_without_enough_shell() -> None:
    state = GameState()
    state.resources[ResourceType.SHELL] = 9.9

    result = create_worker(state)

    assert result.success is False
    assert result.message == "Not enough shell to create worker."
    assert state.resources[ResourceType.SHELL] == 9.9
    assert state.units[UnitType.WORKER] == 0


def test_build_farm_consumes_resources_and_worker() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    result = build_farm(state)

    assert result.success is True
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.STONE] == 0.0
    assert state.resources[ResourceType.IRON] == 8.0
    assert state.units[UnitType.WORKER] == 0
    assert state.buildings[BuildingType.FARM] == 1


def test_cannot_build_farm_without_worker() -> None:
    state = GameState()

    result = build_farm(state)

    assert result.success is False
    assert result.message == "Need at least 1 worker to build a farm."
    assert state.buildings[BuildingType.FARM] == 0


def test_build_mine_consumes_resources_and_worker() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    result = build_mine(state)

    assert result.success is True
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.STONE] == 0.0
    assert state.resources[ResourceType.IRON] == 8.0
    assert state.units[UnitType.WORKER] == 0
    assert state.buildings[BuildingType.MINE] == 1


def test_build_quarry_consumes_resources_and_worker() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    result = build_quarry(state)

    assert result.success is True
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.STONE] == 0.0
    assert state.resources[ResourceType.IRON] == 8.0
    assert state.units[UnitType.WORKER] == 0
    assert state.buildings[BuildingType.QUARRY] == 1


def test_upgrade_worker_to_soldier_consumes_worker_iron_and_shell() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    result = upgrade_worker_to_soldier(state)

    assert result.success is True
    assert state.units[UnitType.WORKER] == 0
    assert state.units[UnitType.SOLDIER] == 1
    assert state.resources[ResourceType.IRON] == 5.0
    assert state.resources[ResourceType.SHELL] == 5.0


def test_upgrade_soldier_to_sorcerer_consumes_soldier_and_shell() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1
    state.resources[ResourceType.SHELL] = 50.0

    result = upgrade_soldier_to_sorcerer(state)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 0
    assert state.units[UnitType.SORCERER] == 1
    assert state.resources[ResourceType.SHELL] == 0.0


def test_cannot_create_sorcerer_without_soldier() -> None:
    state = GameState()
    state.resources[ResourceType.SHELL] = 50.0

    result = upgrade_soldier_to_sorcerer(state)

    assert result.success is False
    assert result.message == "Need at least 1 soldier to create sorcerer."
    assert state.units[UnitType.SORCERER] == 0


def test_cannot_create_sorcerer_without_shell() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1
    state.resources[ResourceType.SHELL] = 49.9

    result = upgrade_soldier_to_sorcerer(state)

    assert result.success is False
    assert result.message == "Not enough shell to create sorcerer."
    assert state.units[UnitType.SOLDIER] == 1
    assert state.units[UnitType.SORCERER] == 0


def test_upgrade_worker_to_lumberjack_consumes_worker_wood_and_shell() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1

    result = upgrade_worker_to_lumberjack(state)

    assert result.success is True
    assert state.units[UnitType.WORKER] == 0
    assert state.units[UnitType.LUMBERJACK] == 1
    assert state.resources[ResourceType.WOOD] == 5.0
    assert state.resources[ResourceType.SHELL] == 8.0


def test_promote_worker_to_captain_consumes_worker_and_gold() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1
    state.resources[ResourceType.GOLD] = 10.0

    result = promote_worker_to_captain(state)

    assert result.success is True
    assert state.units[UnitType.WORKER] == 0
    assert state.units[UnitType.CAPTAIN] == 1
    assert state.resources[ResourceType.GOLD] == 0.0
    assert "Patrols will now depart" in result.message


def test_cannot_promote_captain_without_worker() -> None:
    state = GameState()
    state.resources[ResourceType.GOLD] = 10.0

    result = promote_worker_to_captain(state)

    assert result.success is False
    assert result.message == "Need at least 1 worker to promote captain."
    assert state.units[UnitType.CAPTAIN] == 0


def test_cannot_promote_captain_without_gold() -> None:
    state = GameState()
    state.units[UnitType.WORKER] = 1
    state.resources[ResourceType.GOLD] = 9.9

    result = promote_worker_to_captain(state)

    assert result.success is False
    assert result.message == "Not enough gold to promote captain."
    assert state.units[UnitType.WORKER] == 1
    assert state.units[UnitType.CAPTAIN] == 0


def test_build_arcane_tower_consumes_sorcerer_and_stone() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.resources[ResourceType.STONE] = 250.0

    result = build_arcane_tower(state)

    assert result.success is True
    assert state.units[UnitType.SORCERER] == 0
    assert state.resources[ResourceType.STONE] == 0.0
    assert state.buildings[BuildingType.ARCANE_TOWER] == 1


def test_cannot_build_arcane_tower_without_sorcerer() -> None:
    state = GameState()
    state.resources[ResourceType.STONE] = 250.0

    result = build_arcane_tower(state)

    assert result.success is False
    assert result.message == "Need at least 1 sorcerer to build an arcane tower."
    assert state.buildings[BuildingType.ARCANE_TOWER] == 0


def test_cannot_build_arcane_tower_without_stone() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.resources[ResourceType.STONE] = 249.9

    result = build_arcane_tower(state)

    assert result.success is False
    assert result.message == "Not enough stone to build an arcane tower."
    assert state.units[UnitType.SORCERER] == 1
    assert state.buildings[BuildingType.ARCANE_TOWER] == 0


def test_build_catapult_consumes_resources() -> None:
    state = GameState()
    state.resources[ResourceType.GOLD] = 5.0
    state.resources[ResourceType.WOOD] = 100.0
    state.resources[ResourceType.STONE] = 200.0

    result = build_catapult(state)

    assert result.success is True
    assert state.resources[ResourceType.GOLD] == 0.0
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.STONE] == 0.0
    assert state.buildings[BuildingType.CATAPULT] == 1


def test_cannot_build_catapult_without_resources() -> None:
    state = GameState()
    state.resources[ResourceType.GOLD] = 4.9
    state.resources[ResourceType.WOOD] = 100.0
    state.resources[ResourceType.STONE] = 200.0

    result = build_catapult(state)

    assert result.success is False
    assert result.message == "Not enough gold to build a catapult."
    assert state.buildings[BuildingType.CATAPULT] == 0


def test_hunt_requires_soldier() -> None:
    state = GameState()

    result = hunt(state, roll=0.5)

    assert result.success is False
    assert result.message == "Need at least 1 soldier to hunt."
    assert state.action_cooldowns[HUNT_ACTION_KEY] == 0.0


def test_hunt_can_kill_soldier_and_starts_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1

    result = hunt(state, roll=0.14)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 0
    assert state.action_cooldowns[HUNT_ACTION_KEY] == HUNT_COOLDOWN_SECONDS
    assert "did not return" in result.message
    assert "%" not in result.message


def test_hunt_can_gain_food_and_starts_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1

    result = hunt(state, roll=0.5)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 1
    assert state.resources[ResourceType.FOOD] == 15.0
    assert state.action_cooldowns[HUNT_ACTION_KEY] == HUNT_COOLDOWN_SECONDS
    assert "fresh game" in result.message
    assert "%" not in result.message


def test_hunt_can_gain_food_and_shell_and_starts_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1

    result = hunt(state, roll=0.9)

    assert result.success is True
    assert state.resources[ResourceType.FOOD] == 15.0
    assert state.resources[ResourceType.SHELL] == 15.0
    assert state.action_cooldowns[HUNT_ACTION_KEY] == HUNT_COOLDOWN_SECONDS
    assert "buried shell cache" in result.message
    assert "%" not in result.message


def test_hunt_cannot_run_while_on_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 1
    state.action_cooldowns[HUNT_ACTION_KEY] = 12.0

    result = hunt(state, roll=0.5)

    assert result.success is False
    assert result.message == "Hunt is on cooldown for 12 seconds."
    assert state.resources[ResourceType.FOOD] == 10.0


def test_patrol_requires_three_soldiers() -> None:
    state = GameState()
    state.units[UnitType.SOLDIER] = 2

    result = patrol(state, roll=0.3)

    assert result.success is False
    assert result.message == "Need at least 3 soldiers to patrol."
    assert state.action_cooldowns[PATROL_ACTION_KEY] == 0.0


def test_patrol_requires_food() -> None:
    state = patrol_ready_state()
    state.resources[ResourceType.FOOD] = 9.9

    result = patrol(state, roll=0.3)

    assert result.success is False
    assert result.message == "Not enough food to patrol."
    assert state.action_cooldowns[PATROL_ACTION_KEY] == 0.0


def test_patrol_all_soldiers_die_and_starts_cooldown() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.04)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 0
    assert state.resources[ResourceType.FOOD] == 0.0
    assert state.action_cooldowns[PATROL_ACTION_KEY] == PATROL_COOLDOWN_SECONDS
    assert "wiped out" in result.message
    assert "%" not in result.message


def test_patrol_two_soldiers_die() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.09)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 1
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "2 soldiers died" in result.message


def test_patrol_one_soldier_dies() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.19)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 2
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "1 soldier died" in result.message


def test_patrol_can_be_peaceful() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.3)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 3
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "roads were quiet" in result.message
    assert "%" not in result.message


def test_patrol_can_gain_gold() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.45, gold_reward=7)

    assert result.success is True
    assert state.resources[ResourceType.GOLD] == 7.0
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "carried back 7 gold" in result.message
    assert "%" not in result.message


def test_patrol_can_catch_shell_fairy() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.55)

    assert result.success is True
    assert state.shell_fairy_bonus == 0.1
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "shell income by +0.1/s" in result.message
    assert "%" not in result.message


def test_patrol_shell_fairy_bonus_stacks() -> None:
    state = patrol_ready_state()
    state.shell_fairy_bonus = 0.1

    result = patrol(state, roll=0.55)

    assert result.success is True
    assert state.shell_fairy_bonus == 0.2


def test_patrol_can_gain_worker() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.7)

    assert result.success is True
    assert state.units[UnitType.WORKER] == 1
    assert state.resources[ResourceType.FOOD] == 0.0
    assert "Worker +1" in result.message
    assert "%" not in result.message


def test_patrol_can_find_merchant_cart() -> None:
    state = patrol_ready_state()

    result = patrol(state, roll=0.9, food_reward=4, iron_reward=6)

    assert result.success is True
    assert state.resources[ResourceType.FOOD] == 4.0
    assert state.resources[ResourceType.IRON] == 16.0
    assert "recovered 4 food and 6 iron" in result.message
    assert "%" not in result.message


def test_patrol_cannot_run_while_on_cooldown() -> None:
    state = patrol_ready_state()
    state.action_cooldowns[PATROL_ACTION_KEY] = 12.0

    result = patrol(state, roll=0.3)

    assert result.success is False
    assert result.message == "Patrol is on cooldown for 12 seconds."
    assert state.resources[ResourceType.FOOD] == 10.0


def test_expedition_requires_captain() -> None:
    state = expedition_ready_state()
    state.units[UnitType.CAPTAIN] = 0

    result = expedition(state, roll=0.3)

    assert result.success is False
    assert result.message == "Need at least 1 captain to launch an expedition."
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == 0.0


def test_expedition_requires_ten_soldiers() -> None:
    state = expedition_ready_state()
    state.units[UnitType.SOLDIER] = 9

    result = expedition(state, roll=0.3)

    assert result.success is False
    assert result.message == "Need at least 10 soldiers to launch an expedition."
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == 0.0


def test_expedition_requires_food() -> None:
    state = expedition_ready_state()
    state.resources[ResourceType.FOOD] = 24.9

    result = expedition(state, roll=0.3)

    assert result.success is False
    assert result.message == "Not enough food to launch an expedition."
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == 0.0


def test_expedition_requires_gold() -> None:
    state = expedition_ready_state()
    state.resources[ResourceType.GOLD] = 4.9

    result = expedition(state, roll=0.3)

    assert result.success is False
    assert result.message == "Not enough gold to launch an expedition."
    assert state.action_cooldowns[EXPEDITION_ACTION_KEY] == 0.0


def test_expedition_disaster_loses_soldiers_and_starts_cooldown() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.04)

    assert result.success is True
    assert state.units[UnitType.CAPTAIN] == 1
    assert state.units[UnitType.SOLDIER] == 4
    assert state.resources[ResourceType.FOOD] == 0.0
    assert state.resources[ResourceType.GOLD] == 0.0
    assert (
        state.action_cooldowns[EXPEDITION_ACTION_KEY]
        == EXPEDITION_COOLDOWN_SECONDS
    )
    assert "6 soldiers" in result.message
    assert "%" not in result.message


def test_expedition_harsh_return_loses_soldiers_and_gains_cache() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.10, iron_reward=14, gold_reward=6)

    assert result.success is True
    assert state.units[UnitType.SOLDIER] == 7
    assert state.resources[ResourceType.IRON] == 24.0
    assert state.resources[ResourceType.GOLD] == 6.0
    assert "3 soldiers" in result.message
    assert "14 iron and 6 gold" in result.message
    assert "%" not in result.message


def test_expedition_can_find_ancient_armory() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.20, iron_reward=21, gold_reward=17)

    assert result.success is True
    assert state.resources[ResourceType.IRON] == 31.0
    assert state.resources[ResourceType.GOLD] == 17.0
    assert "ancient armory" in result.message
    assert "%" not in result.message


def test_expedition_can_find_forgotten_granary() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.30, food_reward=44, wood_reward=22)

    assert result.success is True
    assert state.resources[ResourceType.FOOD] == 44.0
    assert state.resources[ResourceType.WOOD] == 32.0
    assert "44 food and 22 wood" in result.message
    assert "%" not in result.message


def test_expedition_can_map_shell_shrine() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.50, shell_reward=33)

    assert result.success is True
    assert state.resources[ResourceType.SHELL] == 43.0
    assert state.shell_fairy_bonus == 0.2
    assert "+0.2/s shell income" in result.message
    assert "%" not in result.message


def test_expedition_can_liberate_workers() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.60)

    assert result.success is True
    assert state.units[UnitType.WORKER] == 2
    assert "Worker +2" in result.message
    assert "%" not in result.message


def test_expedition_can_salvage_battlefield() -> None:
    state = expedition_ready_state()

    result = expedition(
        state,
        roll=0.80,
        stone_reward=24,
        iron_reward=26,
        gold_reward=12,
    )

    assert result.success is True
    assert state.resources[ResourceType.STONE] == 34.0
    assert state.resources[ResourceType.IRON] == 36.0
    assert state.resources[ResourceType.GOLD] == 12.0
    assert "24 stone, 26 iron, and 12 gold" in result.message
    assert "%" not in result.message


def test_expedition_can_recruit_captain() -> None:
    state = expedition_ready_state()

    result = expedition(state, roll=0.90, shell_reward=71)

    assert result.success is True
    assert state.units[UnitType.CAPTAIN] == 2
    assert state.resources[ResourceType.SHELL] == 81.0
    assert "Captain +1 and 71 shell" in result.message
    assert "%" not in result.message


def test_expedition_cannot_run_while_on_cooldown() -> None:
    state = expedition_ready_state()
    state.action_cooldowns[EXPEDITION_ACTION_KEY] = 12.0

    result = expedition(state, roll=0.3)

    assert result.success is False
    assert result.message == "Expedition is on cooldown for 12 seconds."
    assert state.resources[ResourceType.FOOD] == 25.0
    assert state.resources[ResourceType.GOLD] == 5.0


def test_kindle_the_pyre_requires_wood() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.buildings[BuildingType.ARCANE_TOWER] = 1
    state.resources[ResourceType.WOOD] = 99.9

    result = kindle_the_pyre(state, roll=0.5)

    assert result.success is False
    assert result.message == "Not enough wood to kindle the pyre."
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == 0.0


def test_kindle_the_pyre_requires_sorcerer() -> None:
    state = GameState()
    state.resources[ResourceType.WOOD] = 100.0

    result = kindle_the_pyre(state, roll=0.5)

    assert result.success is False
    assert result.message == "Need at least 1 sorcerer to kindle the pyre."
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == 0.0


def test_kindle_the_pyre_requires_arcane_tower() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.resources[ResourceType.WOOD] = 100.0

    result = kindle_the_pyre(state, roll=0.5)

    assert result.success is False
    assert result.message == "Need at least 1 arcane tower to kindle the pyre."
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == 0.0


def test_kindle_the_pyre_can_leave_only_ash_and_starts_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.buildings[BuildingType.ARCANE_TOWER] = 1
    state.resources[ResourceType.WOOD] = 100.0

    result = kindle_the_pyre(state, roll=0.19)

    assert result.success is True
    assert state.units[UnitType.SORCERER] == 1
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.SHELL] == 10.0
    assert state.resources[ResourceType.GOLD] == 0.0
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == KINDLE_PYRE_COOLDOWN_SECONDS
    assert "ash" in result.message
    assert "%" not in result.message


def test_kindle_the_pyre_can_gain_shell() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.buildings[BuildingType.ARCANE_TOWER] = 1
    state.resources[ResourceType.WOOD] = 100.0

    result = kindle_the_pyre(state, roll=0.5, shell_reward=37)

    assert result.success is True
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.SHELL] == 47.0
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == KINDLE_PYRE_COOLDOWN_SECONDS
    assert "yielding 37 shell" in result.message
    assert "%" not in result.message


def test_kindle_the_pyre_can_gain_gold() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.buildings[BuildingType.ARCANE_TOWER] = 1
    state.resources[ResourceType.WOOD] = 100.0

    result = kindle_the_pyre(state, roll=0.8, gold_reward=6)

    assert result.success is True
    assert state.resources[ResourceType.WOOD] == 0.0
    assert state.resources[ResourceType.GOLD] == 6.0
    assert state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] == KINDLE_PYRE_COOLDOWN_SECONDS
    assert "yielding 6 gold" in result.message
    assert "%" not in result.message


def test_kindle_the_pyre_cannot_run_while_on_cooldown() -> None:
    state = GameState()
    state.units[UnitType.SORCERER] = 1
    state.resources[ResourceType.WOOD] = 100.0
    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = 12.0

    result = kindle_the_pyre(state, roll=0.5)

    assert result.success is False
    assert result.message == "Kindle the Pyre is on cooldown for 12 seconds."
    assert state.resources[ResourceType.WOOD] == 100.0


def test_defend_requires_catapult() -> None:
    state = GameState()

    result = defend(state)

    assert result.success is False
    assert result.message == "Need at least 1 catapult to defend."


def test_defend_requires_active_threat() -> None:
    state = GameState()
    state.buildings[BuildingType.CATAPULT] = 1

    result = defend(state)

    assert result.success is False
    assert result.message == "No active threats to defend against."


def test_defend_stops_oldest_threat_and_keeps_catapult() -> None:
    state = GameState()
    state.buildings[BuildingType.CATAPULT] = 1
    state.active_threats = [
        ActiveThreat(key="goblin_raid", remaining_seconds=12.0),
        ActiveThreat(key="mine_saboteurs", remaining_seconds=30.0),
    ]

    result = defend(state)

    assert result.success is True
    assert result.message == "Defended against Goblin Raid. The threat has been stopped."
    assert state.buildings[BuildingType.CATAPULT] == 1
    assert [active_threat.key for active_threat in state.active_threats] == [
        "mine_saboteurs"
    ]
