"""Feature and outcome constants for modeling."""

OUTCOME_CLASSES: tuple[str, ...] = (
    "strikeout",
    "walk",
    "hit_by_pitch",
    "single",
    "double",
    "triple",
    "home_run",
    "other_out",
)

# wOBA linear weights (approximate; outcome-only rolling wOBA).
WOBA_WEIGHTS: dict[str, float] = {
    "walk": 0.69,
    "hit_by_pitch": 0.72,
    "single": 0.88,
    "double": 1.24,
    "triple": 1.56,
    "home_run": 2.0,
    "strikeout": 0.0,
    "other_out": 0.0,
}

ROLLING_WINDOWS_DAYS: tuple[int, ...] = (7, 30, 60)

COORS_FIELD_STADIUM_IDS: frozenset[int] = frozenset({19, 3312})
