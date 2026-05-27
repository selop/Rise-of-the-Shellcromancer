from enum import StrEnum


class ResourceType(StrEnum):
    WOOD = "wood"
    STONE = "stone"
    IRON = "iron"
    FOOD = "food"
    SHELL = "shell"
    GOLD = "gold"


ALL_RESOURCES = tuple(ResourceType)
