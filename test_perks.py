"""특전 수집(OverFast 응답 → 행) 셀프 체크. `python3 test_perks.py` 또는 pytest 로 실행."""
from update import build_perk_rows, role_dict


def perk(name, description="설명"):
    return {"name": name, "description": description, "icon": f"https://cdn/{name}.png"}


def fake_overfast(extra=None):
    """통계 영웅 전부 + 통계에 없는 영웅 하나. OverFast 표기(D.Va)도 섞는다."""
    names = ["D.Va" if h == "D.VA" else h for h in role_dict] + ["새영웅"]
    heroes = [{"key": f"k{i}", "name": n} for i, n in enumerate(names)]
    details = {
        h["key"]: {"perks": {"minor": [perk(f"{h['name']}-m1"), perk(f"{h['name']}-m2")],
                             "major": [perk(f"{h['name']}-M1"), perk(f"{h['name']}-M2")]}}
        for h in heroes
    }
    for key, value in (extra or {}).items():
        details[key]["perks"] = value
    return heroes, details


def test_rows_keep_official_order_and_names():
    heroes, details = fake_overfast()
    rows = build_perk_rows(heroes, details, "2026-10-12")
    assert len(rows) == len(role_dict) * 4  # 통계에 없는 영웅은 건너뛴다
    dva = [r for r in rows if r["hero"] == "D.VA"]
    assert [r["perk_name"] for r in dva] == ["D.Va-m1", "D.Va-m2", "D.Va-M1", "D.Va-M2"], dva
    assert dva[0]["role"] == "Tank" and dva[0]["perk_type"] == "minor" and dva[0]["icon_url"]


def test_key_icon_gap_is_filled():
    illari = next(h["key"] for h in fake_overfast()[0] if h["name"] == "일리아리")
    gap = "치유 광선을 사용하는 동안  키를 누르면 치유합니다."
    heroes, details = fake_overfast({illari: {"minor": [perk("a"), perk("b")],
                                              "major": [perk("태양의 섬광", gap), perk("c")]}})
    row = next(r for r in build_perk_rows(heroes, details, "d") if r["perk_name"] == "태양의 섬광")
    assert row["perk_description"] == "치유 광선을 사용하는 동안 [기본 발사] 키를 누르면 치유합니다.", row


def raises(heroes, details):
    try:
        build_perk_rows(heroes, details, "d")
    except ValueError:
        return True
    return False


def test_incomplete_data_is_rejected():
    heroes, details = fake_overfast()
    ana = next(h["key"] for h in heroes if h["name"] == "아나")
    short = dict(details, **{ana: {"perks": {"minor": [perk("a")], "major": [perk("b"), perk("c")]}}})
    assert raises(heroes, short)  # 특전이 2+2 가 아니다
    assert raises([h for h in heroes if h["name"] != "아나"], details)  # 통계 영웅이 빠졌다
    assert raises(heroes + [{"key": "dup", "name": "아나"}], dict(details, dup=details[ana]))  # 이름이 겹친다


if __name__ == "__main__":
    test_rows_keep_official_order_and_names()
    test_key_icon_gap_is_filled()
    test_incomplete_data_is_rejected()
    print("ok")
