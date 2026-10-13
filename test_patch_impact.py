"""밸런스 패치 전후 비교 셀프 체크. `python3 test_patch_impact.py` 또는 pytest 로 실행."""
import pandas as pd

from app_data import patch_impact


def _row(date, hero, role, win, pick, ban, rank, tier="All"):
    return {"update_date": date, "hero": hero, "role": role, "data_tier": tier, "map": "all-maps",
            "win_rate": win, "pick_rate": pick, "ban_rate": ban, "total_score": 0.0, "rank": rank}


PRE = [_row("2026-10-06", "솜브라", "Damage", 48.6, 4.2, 37.9, "C"),
       _row("2026-10-06", "겐지", "Damage", 52.9, 15.9, 1.9, "A")]
# 패치 다음 날: 넥슨은 평소처럼 일부만 조금 갱신했다(새 집계 아님)
DRIFT = [_row("2026-10-07", "솜브라", "Support", 48.6, 4.2, 37.9, "C"),
         _row("2026-10-07", "겐지", "Damage", 52.9, 16.0, 1.9, "A")]
# 넥슨이 집계를 새로 시작한 날: 모든 영웅이 한꺼번에 바뀐다
RESET = [_row("2026-10-09", "솜브라", "Support", 56.7, 19.0, 50.4, "S"),
         _row("2026-10-09", "겐지", "Damage", 55.7, 20.7, 2.9, "S"),
         _row("2026-10-09", "독트린", "Support", 56.4, 32.5, 29.8, "S")]
HEROES = ["겐지", "솜브라", "독트린"]


def run(rows, latest, patch_date="2026-10-06", heroes=HEROES, tier="All"):
    return patch_impact(pd.DataFrame(rows), pd.DataFrame(latest), patch_date, heroes, tier)


def test_compares_pre_patch_snapshot_after_aggregate_reset():
    rows, before, state = run(PRE + DRIFT + RESET, RESET)
    assert (before, state) == ("2026-10-06", "ok"), (before, state)
    assert [r["hero"] for r in rows] == ["솜브라", "겐지"], rows  # 변화 합이 큰 순, 새 영웅(독트린)은 뺀다
    som = rows[0]
    assert som["win_rate_before"] == 48.6 and som["win_rate"] == 56.7, som
    assert som["rank_before"] == "C" and som["rank"] == "S", som
    assert som["role_change"] and rows[1]["role_change"] == "", rows


def test_daily_drift_after_patch_is_not_the_patch_effect():
    assert run(PRE + DRIFT, DRIFT) == ([], "2026-10-06", "pending")
    late = [dict(r, update_date="2026-10-15") for r in DRIFT]  # 일주일이 지나도 새 집계가 없다(핫픽스)
    assert run(PRE + DRIFT + late, late) == ([], "2026-10-06", "no_reset")


def test_nothing_to_compare():
    assert run(PRE + RESET, RESET, patch_date="2026-09-01") == ([], None, None)  # 직전 기록 없음
    assert run(PRE + RESET, RESET, tier="Gold") == ([], None, None)
    assert run(PRE + RESET, RESET, heroes=["독트린"]) == ([], None, None)  # 비교할 영웅이 없다


if __name__ == "__main__":
    test_compares_pre_patch_snapshot_after_aggregate_reset()
    test_daily_drift_after_patch_is_not_the_patch_effect()
    test_nothing_to_compare()
    print("ok")
