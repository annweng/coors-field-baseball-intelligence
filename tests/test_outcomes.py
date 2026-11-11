import math

from data_pipeline.transform.outcomes import classify_event


def test_strikeout():
    assert classify_event("strikeout") == "strikeout"


def test_walk_intent():
    assert classify_event("intent_walk") == "walk"


def test_sac_fly_other_out():
    assert classify_event("sac_fly") == "other_out"


def test_unknown_empty():
    assert classify_event(None) == "unknown"
    assert classify_event("") == "unknown"
    assert classify_event(math.nan) == "unknown"
