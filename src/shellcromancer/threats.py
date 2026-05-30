from dataclasses import dataclass
from random import choice

from shellcromancer.buildings import BuildingType


THREAT_ROLL_SECONDS = 600.0


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
        description="A raiding party is moving toward the farms.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 2 farms when the countdown reaches zero.",
        target_building=BuildingType.FARM,
        damage_count=2,
    ),
    "mine_saboteurs": ThreatDefinition(
        key="mine_saboteurs",
        name="Mine Saboteurs",
        description="Sappers are searching for a weak point in the mines.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 mine when the countdown reaches zero.",
        target_building=BuildingType.MINE,
        damage_count=1,
    ),
    "quarry_raiders": ThreatDefinition(
        key="quarry_raiders",
        name="Quarry Raiders",
        description="Raiders are circling the stone works.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 quarry when the countdown reaches zero.",
        target_building=BuildingType.QUARRY,
        damage_count=1,
    ),
    "tower_arson": ThreatDefinition(
        key="tower_arson",
        name="Tower Arson",
        description="Fire-starters are creeping toward an arcane tower.",
        countdown_seconds=300.0,
        effect_text="Destroys up to 1 arcane tower when the countdown reaches zero.",
        target_building=BuildingType.ARCANE_TOWER,
        damage_count=1,
    ),
}


def create_random_threat() -> ActiveThreat:
    definition = choice(tuple(THREAT_DEFINITIONS.values()))
    return ActiveThreat(
        key=definition.key,
        remaining_seconds=definition.countdown_seconds,
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
        definition.damage_count,
        state.buildings[definition.target_building],
    )
    state.buildings[definition.target_building] -= destroyed
    target_name = definition.target_building.value.replace("_", " ")
    if destroyed == 0:
        return f"{definition.name} struck, but found no {target_name} to destroy."
    if destroyed == 1:
        return f"{definition.name} struck and destroyed 1 {target_name}."
    return f"{definition.name} struck and destroyed {destroyed} {target_name}s."
