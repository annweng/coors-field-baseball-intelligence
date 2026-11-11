import pandas as pd

from data_pipeline.transform.plate_appearances import pitches_to_plate_appearances


def test_terminal_pitch_selected():
    pitches = pd.DataFrame(
        [
            {"game_pk": 1, "at_bat_number": 1, "pitch_number": 1, "batter": 10, "pitcher": 20,
             "game_date": "2024-04-01", "home_team": "COL", "away_team": "LAD", "events": None,
             "stand": "R", "p_throws": "R", "player_name": "Test Batter"},
            {"game_pk": 1, "at_bat_number": 1, "pitch_number": 2, "batter": 10, "pitcher": 20,
             "game_date": "2024-04-01", "home_team": "COL", "away_team": "LAD", "events": "single",
             "stand": "R", "p_throws": "R", "player_name": "Test Batter"},
        ]
    )
    pa = pitches_to_plate_appearances(pitches)
    assert len(pa) == 1
    assert pa.iloc[0]["outcome"] == "single"
    assert pa.iloc[0]["pitches_in_pa"] == 2
