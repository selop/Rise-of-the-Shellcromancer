from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    name: str
    difficulty: int
    description: str


TARGETS = (
    Target(
        name="Village",
        difficulty=1,
        description="A lightly defended settlement with food and wood.",
    ),
    Target(
        name="Orc Cave",
        difficulty=2,
        description="A crude cavern full of hostile raiders and stolen iron.",
    ),
    Target(
        name="Burg",
        difficulty=3,
        description="A fortified market town with stronger defenses.",
    ),
    Target(
        name="Abandoned Mine",
        difficulty=3,
        description="A ruined mine that may contain iron and shell fragments.",
    ),
    Target(
        name="Castle",
        difficulty=5,
        description="A heavily defended noble stronghold.",
    ),
    Target(
        name="Ancient Shell Shrine",
        difficulty=6,
        description="A forgotten place of shell power, guarded by unknown forces.",
    ),
)
