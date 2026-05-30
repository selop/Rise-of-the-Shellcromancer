from collections.abc import Callable
from dataclasses import dataclass
from random import randint, random

from shellcromancer.buildings import BuildingType
from shellcromancer.game_state import GameState, record_action_message
from shellcromancer.resources import ResourceType
from shellcromancer.threats import (
    ActiveThreat,
    active_threat_name,
    create_random_threat,
)
from shellcromancer.units import UnitType

HUNT_ACTION_KEY = "hunt"
HUNT_COOLDOWN_SECONDS = 60.0
PATROL_ACTION_KEY = "patrol"
PATROL_COOLDOWN_SECONDS = 120.0
PATROL_SHELL_FAIRY_BONUS = 0.1
EXPEDITION_ACTION_KEY = "expedition"
EXPEDITION_COOLDOWN_SECONDS = 300.0
EXPEDITION_SHELL_FAIRY_BONUS = 0.2
KINDLE_PYRE_ACTION_KEY = "kindle_the_pyre"
KINDLE_PYRE_COOLDOWN_SECONDS = 600.0
KINDLE_PYRE_REWARD_BONUS_PER_POWER = 0.25
KINDLE_PYRE_MAX_REWARD_MULTIPLIER = 3.0
DEFEND_ACTION_KEY = "defend"
DEFEND_COOLDOWN_SECONDS = 300.0
DEFEND_BASE_SUCCESS_CHANCE = 0.25
DEFEND_DEFENDER_SUCCESS_BONUS = 0.10
DEFEND_MAX_SUCCESS_CHANCE = 0.75
DEFEND_CATAPULT_BREAK_CHANCE = 0.15


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str


ThreatFactory = Callable[[], ActiveThreat]


def _resource_name(resource: ResourceType) -> str:
    return resource.value


def _can_afford(
    state: GameState, costs: dict[ResourceType, float]
) -> tuple[bool, ResourceType | None]:
    for resource, amount in costs.items():
        if state.resources[resource] < amount:
            return False, resource
    return True, None


def _spend(state: GameState, costs: dict[ResourceType, float]) -> None:
    for resource, amount in costs.items():
        state.resources[resource] -= amount


def _finish(state: GameState, success: bool, message: str) -> ActionResult:
    record_action_message(state, message)
    return ActionResult(success=success, message=message)


def _add_action_threat(
    state: GameState, threat_factory: ThreatFactory | None = None
) -> str:
    active_threat = (
        create_random_threat(state) if threat_factory is None else threat_factory()
    )
    state.active_threats.append(active_threat)
    return active_threat_name(active_threat)


def kindle_pyre_reward_multiplier(state: GameState) -> float:
    pyre_power = (
        state.units[UnitType.SORCERER] + state.buildings[BuildingType.ARCANE_TOWER]
    )
    return min(
        KINDLE_PYRE_MAX_REWARD_MULTIPLIER,
        1.0 + KINDLE_PYRE_REWARD_BONUS_PER_POWER * max(0, pyre_power - 2),
    )


def scaled_kindle_pyre_reward(state: GameState, reward: int) -> int:
    return int(round(reward * kindle_pyre_reward_multiplier(state)))


def create_worker(state: GameState) -> ActionResult:
    costs = {ResourceType.SHELL: 10.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(state, False, f"Not enough {_resource_name(missing)} to create worker.")

    _spend(state, costs)
    state.units[UnitType.WORKER] += 1
    return _finish(state, True, "Created worker.")


def _build_structure(
    state: GameState, building_type: BuildingType, singular_name: str
) -> ActionResult:
    if state.units[UnitType.WORKER] < 1:
        return _finish(
            state, False, f"Need at least 1 worker to build a {singular_name}."
        )

    costs = {
        ResourceType.WOOD: 10.0,
        ResourceType.STONE: 10.0,
        ResourceType.IRON: 2.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state, False, f"Not enough {_resource_name(missing)} to build a {singular_name}."
        )

    _spend(state, costs)
    state.units[UnitType.WORKER] -= 1
    state.buildings[building_type] += 1
    return _finish(state, True, f"Built {singular_name}.")


def build_farm(state: GameState) -> ActionResult:
    return _build_structure(state, BuildingType.FARM, "farm")


def build_mine(state: GameState) -> ActionResult:
    return _build_structure(state, BuildingType.MINE, "mine")


def build_quarry(state: GameState) -> ActionResult:
    return _build_structure(state, BuildingType.QUARRY, "quarry")


def upgrade_worker_to_soldier(state: GameState) -> ActionResult:
    if state.units[UnitType.WORKER] < 1:
        return _finish(state, False, "Need at least 1 worker to upgrade soldier.")

    costs = {
        ResourceType.IRON: 5.0,
        ResourceType.SHELL: 5.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(state, False, f"Not enough {_resource_name(missing)} to upgrade soldier.")

    _spend(state, costs)
    state.units[UnitType.WORKER] -= 1
    state.units[UnitType.SOLDIER] += 1
    return _finish(state, True, "Upgraded worker to soldier.")


def upgrade_soldier_to_sorcerer(state: GameState) -> ActionResult:
    if state.units[UnitType.SOLDIER] < 1:
        return _finish(state, False, "Need at least 1 soldier to create sorcerer.")

    costs = {ResourceType.SHELL: 50.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(state, False, f"Not enough {_resource_name(missing)} to create sorcerer.")

    _spend(state, costs)
    state.units[UnitType.SOLDIER] -= 1
    state.units[UnitType.SORCERER] += 1
    return _finish(state, True, "Created sorcerer from soldier.")


def upgrade_worker_to_lumberjack(state: GameState) -> ActionResult:
    if state.units[UnitType.WORKER] < 1:
        return _finish(state, False, "Need at least 1 worker to upgrade lumberjack.")

    costs = {
        ResourceType.WOOD: 5.0,
        ResourceType.SHELL: 2.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(state, False, f"Not enough {_resource_name(missing)} to upgrade lumberjack.")

    _spend(state, costs)
    state.units[UnitType.WORKER] -= 1
    state.units[UnitType.LUMBERJACK] += 1
    return _finish(state, True, "Upgraded worker to lumberjack.")


def upgrade_soldier_to_ranger(state: GameState) -> ActionResult:
    if state.units[UnitType.SOLDIER] < 1:
        return _finish(state, False, "Need at least 1 soldier to create ranger.")

    costs = {
        ResourceType.GOLD: 5.0,
        ResourceType.SHELL: 10.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state, False, f"Not enough {_resource_name(missing)} to create ranger."
        )

    _spend(state, costs)
    state.units[UnitType.SOLDIER] -= 1
    state.units[UnitType.RANGER] += 1
    return _finish(
        state,
        True,
        "Created ranger from soldier. Hunts will now run whenever they are ready.",
    )


def promote_worker_to_captain(state: GameState) -> ActionResult:
    if state.units[UnitType.SOLDIER] < 1:
        return _finish(state, False, "Need at least 1 soldier to promote captain.")

    costs = {ResourceType.GOLD: 10.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state, False, f"Not enough {_resource_name(missing)} to promote captain."
        )

    _spend(state, costs)
    state.units[UnitType.SOLDIER] -= 1
    state.units[UnitType.CAPTAIN] += 1
    return _finish(
        state,
        True,
        "Promoted a soldier to captain. Patrols will now depart whenever they are ready.",
    )


def create_watchpost(state: GameState) -> ActionResult:
    costs = {
        ResourceType.GOLD: 10.0,
        ResourceType.WOOD: 50.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state, False, f"Not enough {_resource_name(missing)} to post a watchpost."
        )

    _spend(state, costs)
    state.units[UnitType.WATCHPOST] += 1
    return _finish(
        state,
        True,
        "Posted a watchpost. Defend will now run automatically when ready.",
    )


def build_arcane_tower(state: GameState) -> ActionResult:
    if state.units[UnitType.SORCERER] < 1:
        return _finish(
            state, False, "Need at least 1 sorcerer to build an arcane tower."
        )

    costs = {ResourceType.STONE: 250.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state,
            False,
            f"Not enough {_resource_name(missing)} to build an arcane tower.",
        )

    _spend(state, costs)
    state.units[UnitType.SORCERER] -= 1
    state.buildings[BuildingType.ARCANE_TOWER] += 1
    return _finish(state, True, "Built arcane tower.")


def build_catapult(state: GameState) -> ActionResult:
    costs = {
        ResourceType.GOLD: 5.0,
        ResourceType.WOOD: 100.0,
        ResourceType.STONE: 200.0,
    }
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state, False, f"Not enough {_resource_name(missing)} to build a catapult."
        )

    _spend(state, costs)
    state.buildings[BuildingType.CATAPULT] += 1
    return _finish(state, True, "Built catapult.")


def hunt(state: GameState, roll: float | None = None) -> ActionResult:
    cooldown = state.action_cooldowns.get(HUNT_ACTION_KEY, 0.0)
    if cooldown > 0:
        return _finish(state, False, f"Hunt is on cooldown for {cooldown:.0f} seconds.")

    if state.units[UnitType.SOLDIER] < 1:
        return _finish(state, False, "Need at least 1 soldier to hunt.")

    outcome_roll = random() if roll is None else roll
    state.action_cooldowns[HUNT_ACTION_KEY] = HUNT_COOLDOWN_SECONDS

    if outcome_roll < 0.15:
        state.units[UnitType.SOLDIER] -= 1
        return _finish(
            state,
            True,
            "Hunt result: The soldier did not return from the wilds. No resources were recovered.",
        )

    if outcome_roll < 0.80:
        state.resources[ResourceType.FOOD] += 5.0
        return _finish(
            state,
            True,
            "Hunt result: The soldier returned with fresh game, adding 5 food to the stores.",
        )

    state.resources[ResourceType.FOOD] += 5.0
    state.resources[ResourceType.SHELL] += 5.0
    return _finish(
        state,
        True,
        "Hunt result: The soldier found game beside a buried shell cache, gaining 5 food and 5 shell.",
    )


def patrol(
    state: GameState,
    roll: float | None = None,
    gold_reward: int | None = None,
    food_reward: int | None = None,
    iron_reward: int | None = None,
    threat_factory: ThreatFactory | None = None,
) -> ActionResult:
    cooldown = state.action_cooldowns.get(PATROL_ACTION_KEY, 0.0)
    if cooldown > 0:
        return _finish(
            state, False, f"Patrol is on cooldown for {cooldown:.0f} seconds."
        )

    if state.units[UnitType.SOLDIER] < 3:
        return _finish(state, False, "Need at least 3 soldiers to patrol.")

    costs = {ResourceType.FOOD: 10.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(state, False, f"Not enough {_resource_name(missing)} to patrol.")

    _spend(state, costs)
    outcome_roll = random() if roll is None else roll
    state.action_cooldowns[PATROL_ACTION_KEY] = PATROL_COOLDOWN_SECONDS

    if outcome_roll < 0.05:
        state.units[UnitType.SOLDIER] -= 3
        return _finish(
            state,
            True,
            "Patrol result: The patrol was wiped out beyond the thorn road; "
            "the sentries found only broken spears at dawn.",
        )

    if outcome_roll < 0.10:
        state.units[UnitType.SOLDIER] -= 2
        return _finish(
            state,
            True,
            "Patrol result: The patrol was ambushed in a black ravine. "
            "2 soldiers died before the survivors escaped.",
        )

    if outcome_roll < 0.20:
        state.units[UnitType.SOLDIER] -= 1
        return _finish(
            state,
            True,
            "Patrol result: The patrol fought through smoke and arrows. "
            "1 soldier died on the road.",
        )

    if outcome_roll < 0.40:
        return _finish(
            state,
            True,
            "Patrol result: The moonlit roads were quiet. "
            "The soldiers returned safely but found nothing useful.",
        )

    if outcome_roll < 0.50:
        reward = randint(1, 10) if gold_reward is None else gold_reward
        state.resources[ResourceType.GOLD] += reward
        return _finish(
            state,
            True,
            "Patrol result: The soldiers stormed a bandit hideout "
            f"under the pines and carried back {reward} gold.",
        )

    if outcome_roll < 0.60:
        state.shell_fairy_bonus += PATROL_SHELL_FAIRY_BONUS
        return _finish(
            state,
            True,
            "Patrol result: Caught a shell fairy in a lantern jar. "
            "Its glow now strengthens shell income by +0.1/s.",
        )

    if outcome_roll < 0.80:
        state.units[UnitType.WORKER] += 1
        return _finish(
            state,
            True,
            "Patrol result: The soldiers saved a stranded worker from a wolf attack "
            "near the old mile stones. Worker +1.",
        )

    if outcome_roll < 0.90:
        threat_name = _add_action_threat(state, threat_factory)
        return _finish(
            state,
            True,
            "Patrol result: The scouts pushed too far and stirred trouble "
            f"on the border. New threat: {threat_name}.",
        )

    food = randint(1, 10) if food_reward is None else food_reward
    iron = randint(1, 10) if iron_reward is None else iron_reward
    state.resources[ResourceType.FOOD] += food
    state.resources[ResourceType.IRON] += iron
    return _finish(
        state,
        True,
        "Patrol result: Found an abandoned merchant cart half-buried in the ditch. "
        f"The soldiers recovered {food} food and {iron} iron.",
    )


def expedition(
    state: GameState,
    roll: float | None = None,
    iron_reward: int | None = None,
    gold_reward: int | None = None,
    food_reward: int | None = None,
    wood_reward: int | None = None,
    shell_reward: int | None = None,
    stone_reward: int | None = None,
    threat_factory: ThreatFactory | None = None,
) -> ActionResult:
    cooldown = state.action_cooldowns.get(EXPEDITION_ACTION_KEY, 0.0)
    if cooldown > 0:
        return _finish(
            state, False, f"Expedition is on cooldown for {cooldown:.0f} seconds."
        )

    if state.units[UnitType.CAPTAIN] < 1:
        return _finish(
            state, False, "Need at least 1 captain to launch an expedition."
        )

    if state.units[UnitType.SOLDIER] < 10:
        return _finish(
            state, False, "Need at least 10 soldiers to launch an expedition."
        )

    costs = {ResourceType.FOOD: 25.0, ResourceType.GOLD: 5.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state,
            False,
            f"Not enough {_resource_name(missing)} to launch an expedition.",
        )

    _spend(state, costs)
    outcome_roll = random() if roll is None else roll
    state.action_cooldowns[EXPEDITION_ACTION_KEY] = EXPEDITION_COOLDOWN_SECONDS

    if outcome_roll < 0.05:
        state.units[UnitType.SOLDIER] -= 6
        return _finish(
            state,
            True,
            "Expedition result: The column vanished into a dead kingdom. "
            "6 soldiers returned only as names carved into shell.",
        )

    if outcome_roll < 0.12:
        state.units[UnitType.SOLDIER] -= 3
        iron = randint(10, 20) if iron_reward is None else iron_reward
        gold = randint(5, 12) if gold_reward is None else gold_reward
        state.resources[ResourceType.IRON] += iron
        state.resources[ResourceType.GOLD] += gold
        return _finish(
            state,
            True,
            "Expedition result: The survivors dragged home a battered cache "
            "through rain and ruin, "
            f"losing 3 soldiers but recovering {iron} iron and {gold} gold.",
        )

    if outcome_roll < 0.25:
        iron = randint(15, 30) if iron_reward is None else iron_reward
        gold = randint(10, 25) if gold_reward is None else gold_reward
        state.resources[ResourceType.IRON] += iron
        state.resources[ResourceType.GOLD] += gold
        return _finish(
            state,
            True,
            "Expedition result: An ancient armory opened under the captain's "
            f"seal, its racks still sharp with {iron} iron and {gold} gold.",
        )

    if outcome_roll < 0.40:
        food = randint(40, 80) if food_reward is None else food_reward
        wood = randint(20, 50) if wood_reward is None else wood_reward
        state.resources[ResourceType.FOOD] += food
        state.resources[ResourceType.WOOD] += wood
        return _finish(
            state,
            True,
            "Expedition result: A forgotten granary was found above old roots, "
            "its doors sealed against centuries of hunger, "
            f"adding {food} food and {wood} wood.",
        )

    if outcome_roll < 0.55:
        shell = randint(25, 60) if shell_reward is None else shell_reward
        state.resources[ResourceType.SHELL] += shell
        state.shell_fairy_bonus += EXPEDITION_SHELL_FAIRY_BONUS
        return _finish(
            state,
            True,
            "Expedition result: The soldiers mapped a shell shrine humming beneath "
            "cold blue moss, "
            f"gaining {shell} shell and +0.2/s shell income.",
        )

    if outcome_roll < 0.70:
        state.units[UnitType.WORKER] += 2
        return _finish(
            state,
            True,
            "Expedition result: The captain liberated a hidden settlement "
            "from its barricaded valley. "
            "Worker +2.",
        )

    if outcome_roll < 0.85:
        stone = randint(20, 50) if stone_reward is None else stone_reward
        iron = randint(20, 50) if iron_reward is None else iron_reward
        gold = randint(10, 25) if gold_reward is None else gold_reward
        state.resources[ResourceType.STONE] += stone
        state.resources[ResourceType.IRON] += iron
        state.resources[ResourceType.GOLD] += gold
        return _finish(
            state,
            True,
            "Expedition result: Battlefield salvage from a forgotten siege "
            "filled the wagons with "
            f"{stone} stone, {iron} iron, and {gold} gold.",
        )

    if outcome_roll < 0.97:
        threat_name = _add_action_threat(state, threat_factory)
        return _finish(
            state,
            True,
            "Expedition result: The column crossed a cursed marker and drew "
            f"hostile eyes homeward. New threat: {threat_name}.",
        )

    shell = randint(50, 100) if shell_reward is None else shell_reward
    state.units[UnitType.CAPTAIN] += 1
    state.resources[ResourceType.SHELL] += shell
    return _finish(
        state,
        True,
        "Expedition result: A rival warband bent the knee. "
        f"Captain +1 and {shell} shell.",
    )


def kindle_the_pyre(
    state: GameState,
    roll: float | None = None,
    shell_reward: int | None = None,
    gold_reward: int | None = None,
) -> ActionResult:
    cooldown = state.action_cooldowns.get(KINDLE_PYRE_ACTION_KEY, 0.0)
    if cooldown > 0:
        return _finish(
            state,
            False,
            f"Kindle the Pyre is on cooldown for {cooldown:.0f} seconds.",
        )

    if state.units[UnitType.SORCERER] < 1:
        return _finish(state, False, "Need at least 1 sorcerer to kindle the pyre.")

    if state.buildings[BuildingType.ARCANE_TOWER] < 1:
        return _finish(
            state, False, "Need at least 1 arcane tower to kindle the pyre."
        )

    costs = {ResourceType.WOOD: 100.0}
    can_afford, missing = _can_afford(state, costs)
    if not can_afford and missing is not None:
        return _finish(
            state,
            False,
            f"Not enough {_resource_name(missing)} to kindle the pyre.",
        )

    _spend(state, costs)
    outcome_roll = random() if roll is None else roll
    state.action_cooldowns[KINDLE_PYRE_ACTION_KEY] = KINDLE_PYRE_COOLDOWN_SECONDS

    if outcome_roll < 0.20:
        return _finish(
            state,
            True,
            "Kindle the Pyre result: The flames guttered out, leaving only ash behind.",
        )

    if outcome_roll < 0.60:
        base_reward = randint(10, 50) if shell_reward is None else shell_reward
        reward = scaled_kindle_pyre_reward(state, base_reward)
        state.resources[ResourceType.SHELL] += reward
        return _finish(
            state,
            True,
            "Kindle the Pyre result: Shell fragments cracked open in the heat, "
            f"yielding {reward} shell.",
        )

    base_reward = randint(5, 10) if gold_reward is None else gold_reward
    reward = scaled_kindle_pyre_reward(state, base_reward)
    state.resources[ResourceType.GOLD] += reward
    return _finish(
        state,
        True,
        "Kindle the Pyre result: A bright ember hardened into treasure, "
        f"yielding {reward} gold.",
    )


def defend_success_chance(state: GameState) -> float:
    defender_count = (
        state.buildings[BuildingType.CATAPULT] + state.units[UnitType.CAPTAIN]
    )
    return min(
        DEFEND_MAX_SUCCESS_CHANCE,
        DEFEND_BASE_SUCCESS_CHANCE
        + DEFEND_DEFENDER_SUCCESS_BONUS * defender_count,
    )


def defend(
    state: GameState,
    roll: float | None = None,
    break_roll: float | None = None,
) -> ActionResult:
    cooldown = state.action_cooldowns.get(DEFEND_ACTION_KEY, 0.0)
    if cooldown > 0:
        return _finish(
            state, False, f"Defend is on cooldown for {cooldown:.0f} seconds."
        )

    if state.buildings[BuildingType.CATAPULT] < 1:
        return _finish(state, False, "Need at least 1 catapult to defend.")

    if not state.active_threats:
        return _finish(state, False, "No active threats to defend against.")

    target_threat = state.active_threats[0]
    threat_name = active_threat_name(target_threat)
    chance = defend_success_chance(state)
    outcome_roll = random() if roll is None else roll
    catapult_break_roll = random() if break_roll is None else break_roll
    state.action_cooldowns[DEFEND_ACTION_KEY] = DEFEND_COOLDOWN_SECONDS
    catapult_broke = catapult_break_roll < DEFEND_CATAPULT_BREAK_CHANCE
    break_message = ""
    if catapult_broke:
        state.buildings[BuildingType.CATAPULT] -= 1
        break_message = " One catapult cracked apart in the recoil."

    if outcome_roll >= chance:
        return _finish(
            state,
            True,
            f"Defended against {threat_name}, but the defense failed "
            f"({chance:.0%} chance).{break_message}",
        )

    state.active_threats.pop(0)
    return _finish(
        state,
        True,
        f"Defended against {threat_name}. The threat has been stopped "
        f"({chance:.0%} chance).{break_message}",
    )
