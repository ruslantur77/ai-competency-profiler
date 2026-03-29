from enum import IntEnum


class CompetencyLevel(IntEnum):
    """Уровень владения компетенцией (0-5)."""

    NONE = 0
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5

    def __str__(self) -> str:
        return self.name.lower()
