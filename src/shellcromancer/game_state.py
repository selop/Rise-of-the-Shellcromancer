from dataclasses import dataclass, field

from shellcromancer.buildings import ALL_BUILDINGS, BuildingType
from shellcromancer.resources import ALL_RESOURCES, ResourceType
from shellcromancer.threats import THREAT_ROLL_SECONDS, ActiveThreat
from shellcromancer.units import ALL_UNITS, UnitType


def initial_resources() -> dict[ResourceType, float]:
    return {
        resource: 0.0 if resource is ResourceType.GOLD else 10.0
        for resource in ALL_RESOURCES
    }


def empty_delta() -> dict[ResourceType, float]:
    return {resource: 0.0 for resource in ALL_RESOURCES}


def empty_units() -> dict[UnitType, int]:
    return {unit: 0 for unit in ALL_UNITS}


def empty_buildings() -> dict[BuildingType, int]:
    return {building: 0 for building in ALL_BUILDINGS}


def empty_action_cooldowns() -> dict[str, float]:
    return {
        "hunt": 0.0,
        "patrol": 0.0,
        "expedition": 0.0,
        "kindle_the_pyre": 0.0,
    }


@dataclass
class GameState:
    resources: dict[ResourceType, float] = field(default_factory=initial_resources)
    units: dict[UnitType, int] = field(default_factory=empty_units)
    buildings: dict[BuildingType, int] = field(default_factory=empty_buildings)
    action_cooldowns: dict[str, float] = field(default_factory=empty_action_cooldowns)
    active_threats: list[ActiveThreat] = field(default_factory=list)
    threat_roll_cooldown: float = THREAT_ROLL_SECONDS
    last_delta: dict[ResourceType, float] = field(default_factory=empty_delta)
    last_action_message: str = "Welcome, Shellcromancer."
    shell_fairy_bonus: float = 0.0
    is_dead: bool = False
