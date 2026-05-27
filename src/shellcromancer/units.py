from dataclasses import dataclass, field
from enum import StrEnum

from shellcromancer.resources import ResourceType


class UnitType(StrEnum):
    WORKER = "worker"
    SOLDIER = "soldier"
    LUMBERJACK = "lumberjack"
    CAPTAIN = "captain"
    SORCERER = "sorcerer"


@dataclass(frozen=True)
class UnitDefinition:
    name: str
    upkeep: dict[ResourceType, float] = field(default_factory=dict)
    production: dict[ResourceType, float] = field(default_factory=dict)


UNIT_DEFINITIONS: dict[UnitType, UnitDefinition] = {
    UnitType.WORKER: UnitDefinition(
        name="Worker",
        upkeep={ResourceType.FOOD: 0.1},
    ),
    UnitType.SOLDIER: UnitDefinition(
        name="Soldier",
        upkeep={ResourceType.FOOD: 0.2},
    ),
    UnitType.LUMBERJACK: UnitDefinition(
        name="Lumberjack",
        upkeep={ResourceType.FOOD: 0.1},
        production={ResourceType.WOOD: 0.2},
    ),
    UnitType.CAPTAIN: UnitDefinition(
        name="Captain",
    ),
    UnitType.SORCERER: UnitDefinition(
        name="Sorcerer",
    ),
}


ALL_UNITS = tuple(UnitType)
