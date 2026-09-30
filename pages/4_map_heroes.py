import html
import urllib.parse

import pandas as pd
import streamlit as st

from app_data import (
    MAP_MODES,
    get_hero_image_url,
    get_map_image_url,
    get_ordered_tiers,
    load_latest_stats,
    top_heroes_by_map,
    translate_role_name,
)
from ui import filter_qs, page_shell, resolve_tier, section

# 포지션은 카드 안에 셋 다 나오므로 전역 필터는 티어만 쓴다.
_shell = page_shell(
    page_key="map_heroes",
    title="전장별 영웅",
    badge="Maps",
    filters=("tier",),
)
_shell.__enter__()

df_raw = load_latest_stats()
selected_tier = resolve_tier(get_ordered_tiers(df_raw))

# 카드의 영웅 링크(?hero=)는 전체 리로드로 이 페이지에 다시 들어온다. 메인과 같은 방식으로
# 영웅 상세에 넘긴다. 나머지를 그리기 전에 넘겨야 빈 화면이 잠깐 보이지 않는다.
_hero_from_query = st.query_params.get("hero")
if _hero_from_query:
    st.session_state.detail_hero = str(_hero_from_query)
    st.session_state.detail_tier = selected_tier
    st.switch_page("pages/3_hero_detail.py")

picks = top_heroes_by_map(df_raw, selected_tier)
if picks.empty:
    st.info("이 티어의 전장별 데이터가 없습니다.")
    st.stop()

_mode_of = {map_id: mode for mode, map_ids in MAP_MODES.items() for map_id in map_ids}
picks["mode"] = picks["map"].astype(str).map(_mode_of).fillna("기타")
_modes = [mode for mode in [*MAP_MODES, "기타"] if (picks["mode"] == mode).any()]

selected_modes = st.pills(
    "모드로 걸러보기",
    _modes,
    selection_mode="multi",
    default=None,
    key="map_mode_filter",
) or _modes

st.caption("포지션별 보정 승률 상위 2명 · 작은 숫자는 전체 전장 대비 %p")

ROLES = ["Tank", "Damage", "Support"]
_qs = filter_qs()


def _pick_html(row) -> str:
    hero = str(row["hero"])
    img = get_hero_image_url(hero)
    img_html = (f"<img class='rail-row-img' src='{html.escape(str(img), quote=True)}' alt='' loading='lazy'>"
                if img else "<div class='rail-row-img'></div>")
    lift_html = ""
    if pd.notna(row["lift"]):
        # 보이는 자릿수로 먼저 맞춘다. + 0.0 은 "-0.0" 이 찍히지 않게 음의 0 을 없앤다.
        lift = round(float(row["lift"]), 1) + 0.0
        tone = "up" if lift > 0 else "down" if lift < 0 else "flat"
        lift_html = f"<span class='mh-lift {tone}'>{lift:+.1f}</span>"
    return (
        f"<a class='mh-pick' target='_self' href='?hero={urllib.parse.quote(hero, safe='')}{_qs}'>"
        f"{img_html}"
        f"<div class='mh-pick-text'>"
        f"<div class='mh-hero'>{html.escape(hero)}</div>"
        f"<div class='mh-stat'>{float(row['shrunk_win_rate']):.1f}%{lift_html}</div>"
        f"</div></a>"
    )


def _card_html(map_rows) -> str:
    first = map_rows.iloc[0]
    map_id = str(first["map"])
    sample = first.get("sample_warning")
    sample = sample if isinstance(sample, str) else ""
    sample_html = f"<span class='sample-note'>{html.escape(sample)}</span>" if sample else ""
    rows_html = ""
    for role in ROLES:
        role_rows = map_rows[map_rows["role"] == role]
        if role_rows.empty:
            continue
        rows_html += (
            f"<div class='mh-row'><div class='mh-role'>{html.escape(translate_role_name(role))}</div>"
            + "".join(_pick_html(row) for _, row in role_rows.iterrows())
            + "</div>"
        )
    # 표본 부족 조합은 다른 전장 카드와 같은 방식으로 흐리게 둔다.
    cls = "mh-card dim" if sample == "표본 부족" else "mh-card"
    return (
        f"<div class='{cls}'>"
        f"<div class='mh-head'>"
        f"<img class='mh-art' src='{html.escape(get_map_image_url(map_id), quote=True)}' alt='' loading='lazy'>"
        f"<div class='mh-name'>{html.escape(str(first.get('map_name') or map_id))}{sample_html}</div>"
        f"</div>"
        f"<div class='mh-rows'>{rows_html}</div>"
        f"</div>"
    )


for mode in selected_modes:
    mode_rows = picks[picks["mode"] == mode]
    # 아는 전장을 빨리 찾을 수 있게 모드 안에서는 가나다순.
    cards = sorted(
        ((str(rows["map_name"].iloc[0]), _card_html(rows)) for _, rows in mode_rows.groupby("map", sort=False)),
        key=lambda item: item[0],
    )
    section(mode, f"{len(cards)}개 전장")
    st.markdown(f"<div class='mh-grid'>{''.join(card for _, card in cards)}</div>", unsafe_allow_html=True)

with st.expander("보정 승률은 뭔가요?"):
    st.markdown(
        """
        - 전장 하나로 좁히면 판수가 적어서 원래 승률이 0%나 100%처럼 튑니다. 보정 승률은 판수가 적을수록 그 영웅의 같은 티어 전체 전장 승률 쪽으로 당긴 값입니다.
        - 그래서 픽률이 낮은 영웅은 영웅 상세에 보이는 원래 승률과 숫자가 다를 수 있습니다.
        - 옆의 작은 숫자가 크면 "이 전장에서 특히 강한 영웅", 0에 가깝거나 음수면 "어느 전장에서나 강한 영웅"입니다.
        """
    )

_shell.__exit__(None, None, None)
