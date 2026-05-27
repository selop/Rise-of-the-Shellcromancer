from dataclasses import dataclass, field
from enum import StrEnum

from shellcromancer.resources import ResourceType


class BuildingType(StrEnum):
    FARM = "farm"
    MINE = "mine"
    QUARRY = "quarry"
    ARCANE_TOWER = "arcane_tower"
    CATAPULT = "catapult"


@dataclass(frozen=True)
class BuildingDefinition:
    name: str
    production: dict[ResourceType, float] = field(default_factory=dict)
    upkeep: dict[ResourceType, float] = field(default_factory=dict)


BUILDING_DEFINITIONS: dict[BuildingType, BuildingDefinition] = {
    BuildingType.FARM: BuildingDefinition(
        name="Farm",
        production={ResourceType.FOOD: 0.2},
    ),
    BuildingType.MINE: BuildingDefinition(
        name="Mine",
        production={ResourceType.IRON: 0.2},
    ),
    BuildingType.QUARRY: BuildingDefinition(
        name="Quarry",
        production={ResourceType.STONE: 0.2},
    ),
    BuildingType.ARCANE_TOWER: BuildingDefinition(
        name="Arcane Tower",
        production={ResourceType.SHELL: 0.1},
    ),
    BuildingType.CATAPULT: BuildingDefinition(
        name="Catapult",
    ),
}


ALL_BUILDINGS = tuple(BuildingType)
