from models.evaluation.compare import better_than_baseline


def test_better_than_baseline_margin() -> None:
    assert better_than_baseline(2.0, 2.2)
    assert not better_than_baseline(2.195, 2.2)
    assert not better_than_baseline(2.25, 2.2)
