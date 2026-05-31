from dataclasses import dataclass
from random import choice

from shellcromancer.buildings import BuildingType


THREAT_ROLL_SECONDS = 600.0
THREAT_SCALING_INTERVAL_SECONDS = 600.0
THREAT_DAMAGE_PER_TIER = 1
THREAT_MAX_DAMAGE_COUNT = 5
THREAT_COUNTDOWN_REDUCTION_PER_TIER = 30.0
THREAT_MIN_COUNTDOWN_SECONDS = 90.0


@dataclass(frozen=True)
class ThreatDefinition:
    key: str
    name: str
    description: str
    countdown_seconds: float
    effect_text: str
    target_building: BuildingType
    damage_count: int


@dataclass
class ActiveThreat:
    key: str
    remaining_seconds: float


THREAT_DEFINITIONS: dict[str, ThreatDefinition] = {
    "goblin_raid": ThreatDefinition(
        key="goblin_raid",
        name="Goblin Raid",
        description="A torchlit raiding party is moving down from the thorn hills.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 2 farms when the raiders arrive.",
        target_building=BuildingType.FARM,
        damage_count=2,
    ),
    "mine_saboteurs": ThreatDefinition(
        key="mine_saboteurs",
        name="Mine Saboteurs",
        description="Sappers with black powder are searching for weak mine braces.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 mine when their charges are set.",
        target_building=BuildingType.MINE,
        damage_count=1,
    ),
    "quarry_raiders": ThreatDefinition(
        key="quarry_raiders",
        name="Quarry Raiders",
        description="Hook-clawed raiders are circling the stone works at dusk.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 quarry when they break through.",
        target_building=BuildingType.QUARRY,
        damage_count=1,
    ),
    "tower_arson": ThreatDefinition(
        key="tower_arson",
        name="Tower Arson",
        description="Fire-starters are creeping toward an arcane tower with oil jars.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 arcane tower if the flames reach it.",
        target_building=BuildingType.ARCANE_TOWER,
        damage_count=1,
    ),
}


def threat_scaling_tier(state: object) -> int:
    elapsed_seconds = getattr(state, "run_elapsed_seconds", 0.0)
    return int(elapsed_seconds // THREAT_SCALING_INTERVAL_SECONDS)


def scaled_threat_damage(definition: ThreatDefinition, state: object) -> int:
    return min(
        THREAT_MAX_DAMAGE_COUNT,
        definition.damage_count
        + THREAT_DAMAGE_PER_TIER * threat_scaling_tier(state),
    )


def scaled_threat_countdown(definition: ThreatDefinition, state: object) -> float:
    return max(
        THREAT_MIN_COUNTDOWN_SECONDS,
        definition.countdown_seconds
        - THREAT_COUNTDOWN_REDUCTION_PER_TIER * threat_scaling_tier(state),
    )


def create_random_threat(state: object | None = None) -> ActiveThreat:
    definition = choice(tuple(THREAT_DEFINITIONS.values()))
    return ActiveThreat(
        key=definition.key,
        remaining_seconds=(
            definition.countdown_seconds
            if state is None
            else scaled_threat_countdown(definition, state)
        ),
    )


def active_threat_name(active_threat: ActiveThreat) -> str:
    definition = THREAT_DEFINITIONS.get(active_threat.key)
    if definition is None:
        return active_threat.key
    return definition.name


def resolve_threat(state: object, active_threat: ActiveThreat) -> str:
    definition = THREAT_DEFINITIONS.get(active_threat.key)
    if definition is None:
        return f"Unknown threat {active_threat.key} faded without effect."

    destroyed = min(
        scaled_threat_damage(definition, state),
        state.buildings[definition.target_building],
    )
    state.buildings[definition.target_building] -= destroyed

    from shellcromancer.storage import clamp_all_resources

    clamp_all_resources(state)
    target_name = definition.target_building.value.replace("_", " ")
    if destroyed == 0:
        return f"{definition.name} struck, but found no {target_name} to destroy."
    if destroyed == 1:
        return f"{definition.name} struck and destroyed 1 {target_name}."
    return f"{definition.name} struck and destroyed {destroyed} {target_name}s."
