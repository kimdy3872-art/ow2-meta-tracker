"""과열 감시(성능을 섞은 기준선 비교) 셀프 체크. `python3 test_overheat.py` 또는 pytest 로 실행."""
import numpy as np
import pandas as pd

from update import build_overheat_monitor


def frame(presence, perf, tier="Gold", rank="B"):
    return pd.DataFrame({
        "hero": [f"h{i}" for i in range(len(presence))], "data_tier": tier, "map": "all-maps",
        "role": "Damage", "rank": rank, "presence_score": presence, "performance_score": perf,
    })


PRESENCE = np.linspace(-2, 2, 20)


def test_validated_ranks_stay_below_baseline():
    # 성능이 존재감과 같이 움직이면 S/A 에 성능 평균 이하가 없다. 표본 부족(-) 행은 세지 않는다.
    df = pd.concat([frame(PRESENCE, PRESENCE), frame([3.0], [-3.0], rank="-")], ignore_index=True)
    out = build_overheat_monitor(df, shuffles=200)
    assert out["s_a_perf_negative_share"] == 0
    assert out["shuffled_baseline_share"] > 0.1 and not out["alert"], out


def test_presence_only_ranks_alert():
    # 성능이 존재감과 반대로 움직이면 S/A 가 전부 성능 평균 이하라 경고가 켜진다.
    out = build_overheat_monitor(frame(PRESENCE, -PRESENCE), shuffles=200)
    assert out["s_a_perf_negative_share"] == 1 and out["alert"], out


def test_shuffle_stays_inside_group():
    # 비교군 안에서만 섞으면, 비교군마다 성능이 한 값뿐일 때 기준선이 실제와 같아야 한다.
    df = pd.concat([frame(PRESENCE, np.full(20, 1.0)), frame(PRESENCE, np.full(20, -1.0), tier="Silver")],
                   ignore_index=True)
    out = build_overheat_monitor(df, shuffles=50)
    assert out["shuffled_baseline_share"] == out["s_a_perf_negative_share"], out


if __name__ == "__main__":
    test_validated_ranks_stay_below_baseline()
    test_presence_only_ranks_alert()
    test_shuffle_stays_inside_group()
    print("ok")
