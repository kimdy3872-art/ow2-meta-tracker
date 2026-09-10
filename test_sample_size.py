"""표본 크기 추정·보정 셀프 체크. `python3 test_sample_size.py` 또는 pytest 로 실행."""
import pandas as pd

from update import add_sample_columns


def test_noisy_combo_is_flagged_and_pulled_to_parent():
    heroes = [f"h{i}" for i in range(10)]
    parent = pd.DataFrame({
        "hero": heroes, "data_tier": "Gold", "map": "all-maps", "role": "Damage",
        "win_rate": 50.0, "pick_rate": 20.0,
    })
    clean = parent.assign(map="busan", win_rate=[50.0 + (i % 3 - 1) for i in range(10)])
    noisy = parent.assign(map="oasis", win_rate=[0.0, 100.0] * 5)
    df = add_sample_columns(pd.concat([parent, clean, noisy], ignore_index=True), ["data_tier", "map", "role"])

    by_map = df.groupby("map")
    assert (by_map.get_group("all-maps")["sample_warning"] == "").all()
    assert (by_map.get_group("busan")["sample_warning"] == "").all()
    assert (by_map.get_group("oasis")["sample_warning"] == "표본 부족").all()
    # 표본이 충분하면 원래 승률에 가깝고, 부족하면 부모(50%) 쪽으로 당겨진다.
    busan = by_map.get_group("busan")
    assert ((busan["shrunk_win_rate"] - busan["win_rate"]).abs() < 0.1).all()
    assert ((by_map.get_group("oasis")["shrunk_win_rate"] - 50).abs() < 1).all()
    # 부모 행은 기존 값(여기선 없으므로 원래 승률)을 유지한다.
    assert (by_map.get_group("all-maps")["shrunk_win_rate"] == 50.0).all()


def test_noisy_tier_parent_is_pulled_to_all_tier_first():
    # 그마처럼 티어 전체 전장 값 자체가 튀면, 전장별 행이 그 튄 값으로 끌려가면 안 된다.
    heroes = [f"h{i}" for i in range(10)]
    top = pd.DataFrame({
        "hero": heroes, "data_tier": "All", "map": "all-maps", "role": "Damage",
        "win_rate": 50.0, "pick_rate": 20.0,
    })
    gm_parent = top.assign(data_tier="Grandmaster", win_rate=[0.0, 100.0] * 5)
    gm_map = gm_parent.assign(map="oasis", win_rate=[100.0, 0.0] * 5)
    df = add_sample_columns(pd.concat([top, gm_parent, gm_map], ignore_index=True), ["data_tier", "map", "role"])

    oasis = df[df["map"] == "oasis"]
    assert ((oasis["shrunk_win_rate"] - 50).abs() < 2).all(), oasis["shrunk_win_rate"].tolist()
    # 전체 전장 행의 점수용 승률은 건드리지 않는다(메인 순위표 산식 유지).
    gm_all = df[(df["data_tier"] == "Grandmaster") & (df["map"] == "all-maps")]
    assert (gm_all["shrunk_win_rate"] == gm_all["win_rate"]).all()


if __name__ == "__main__":
    test_noisy_combo_is_flagged_and_pulled_to_parent()
    test_noisy_tier_parent_is_pulled_to_all_tier_first()
    print("ok")
