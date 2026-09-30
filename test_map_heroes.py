"""전장별 영웅 선정 셀프 체크. `python3 test_map_heroes.py` 또는 pytest 로 실행."""
import pandas as pd

from app_data import MAP_MODES, top_heroes_by_map


def _row(hero, role, map_id, win, shrunk, tier="Gold"):
    return {"hero": hero, "role": role, "data_tier": tier, "map": map_id,
            "win_rate": win, "shrunk_win_rate": shrunk}


def test_picks_top_two_per_role_by_shrunk_win_rate():
    df = pd.DataFrame([
        _row("A", "Tank", "all-maps", 50.0, 50.0),
        _row("B", "Tank", "all-maps", 55.0, 55.0),
        _row("C", "Tank", "all-maps", 48.0, 48.0),
        _row("D", "Support", "all-maps", 51.0, 51.0),
        # 부산: C 는 원래 승률이 100% 지만 보정하면 49% 라 뽑히면 안 된다
        _row("A", "Tank", "busan", 54.0, 53.0),
        _row("B", "Tank", "busan", 56.0, 56.0),
        _row("C", "Tank", "busan", 100.0, 49.0),
        _row("D", "Support", "busan", 52.0, 52.5),
        # 다른 티어 행은 섞이지 않는다
        _row("C", "Tank", "busan", 99.0, 99.0, tier="Master"),
    ])
    picks = top_heroes_by_map(df, "Gold")

    tank = picks[picks["role"] == "Tank"]
    assert list(tank["hero"]) == ["B", "A"]
    assert list(picks[picks["role"] == "Support"]["hero"]) == ["D"]
    assert "all-maps" not in set(picks["map"])
    # lift = 보정 승률 − 같은 티어 전체 전장 승률
    assert list(tank["lift"].round(1)) == [1.0, 3.0]


def test_every_mode_map_is_listed_once():
    ids = [map_id for maps in MAP_MODES.values() for map_id in maps]
    assert len(ids) == len(set(ids))


if __name__ == "__main__":
    test_picks_top_two_per_role_by_shrunk_win_rate()
    test_every_mode_map_is_listed_once()
    print("ok")
