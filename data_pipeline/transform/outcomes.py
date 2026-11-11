"""Map Statcast terminal events to training outcome classes."""

from __future__ import annotations

VALID_OUTCOMES = frozenset(
    {
        "strikeout",
        "walk",
        "hit_by_pitch",
        "single",
        "double",
        "triple",
        "home_run",
        "other_out",
        "unknown",
    }
)

_EVENT_TO_OUTCOME: dict[str, str] = {
    "strikeout": "strikeout",
    "strikeout_double_play": "strikeout",
    "walk": "walk",
    "intent_walk": "walk",
    "hit_by_pitch": "hit_by_pitch",
    "single": "single",
    "double": "double",
    "triple": "triple",
    "home_run": "home_run",
    "field_out": "other_out",
    "force_out": "other_out",
    "grounded_into_double_play": "other_out",
    "fielders_choice": "other_out",
    "fielders_choice_out": "other_out",
    "double_play": "other_out",
    "triple_play": "other_out",
    "sac_fly": "other_out",
    "sac_bunt": "other_out",
    "sac_fly_double_play": "other_out",
    "sac_bunt_double_play": "other_out",
    "catcher_interf": "other_out",
    "other_out": "other_out",
    "field_error": "other_out",
    "truncated_pa": "unknown",
}


def classify_event(event: str | None) -> str:
    """Return multiclass outcome label for a Statcast ``events`` value."""
    if event is None or (isinstance(event, float)):  # pandas NaN
        return "unknown"
    key = str(event).strip().lower()
    if not key:
        return "unknown"
    return _EVENT_TO_OUTCOME.get(key, "other_out")
