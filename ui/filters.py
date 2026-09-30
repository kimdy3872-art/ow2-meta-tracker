"""전역 필터.

티어·역할은 페이지마다 다시 고르는 게 아니라 하나의 session_state 를 공유한다.
예전에는 main.py 만 key= 로 묶여 있고 나머지 세 페이지는 index= 로 잡아서, 골드로
보다가 영웅 상세로 넘어가면 선택이 초기화됐다.

옵션 목록은 latest 스냅샷에서 한 번만 뽑는다. 페이지별 df 로 뽑으면 페이지마다
목록이 달라져서 같은 key 를 공유하는 의미가 없어진다.
"""

from __future__ import annotations

import streamlit as st

# 전역 필터가 쓰는 session_state 키와 기본값.
FILTER_DEFAULTS = {
    "selected_tier": "Gold",
    "selected_role": "All",
    "search_hero": "",
    "sort_col": "total_score",
    "sort_desc": True,
}


# 위젯 키와 짝을 이루는 보관용 키의 접미사.
_STORE = "__keep"


def init_filter_state() -> None:
    """전역 필터 값을 페이지 이동 너머로 살려 둔다.

    Streamlit 은 페이지를 옮기면 이전 페이지에서 만들어진 위젯의 상태를 버린다.
    사이드바 필터는 모든 페이지에 렌더되는데도, st.page_link 로 넘어가면
    selected_tier 값이 사라지거나 옵션 0번(전체 티어)으로 되돌아갔다.
    브라우저는 리로드되지 않으므로(JS 전역 변수가 살아남는 것으로 확인) 순수하게
    파이썬 쪽 위젯 상태 문제다.

    그래서 위젯에 key= 를 주지 않는다. 정본은 위젯이 건드리지 않는 평범한
    session_state 키에 두고, 매 실행 index= 로 위젯을 초기화한 뒤 반환값을
    다시 정본에 쓴다. 위젯 상태가 버려져도 정본은 남는다.
    보관용 키는 그 정본이 혹시 사라져도 되살릴 수 있는 2차 안전망이다.
    """
    # 보관소가 아직 없으면 이번이 이 브라우저 세션의 첫 실행이다.
    fresh = ("selected_tier" + _STORE) not in st.session_state

    for key, value in FILTER_DEFAULTS.items():
        store = key + _STORE
        st.session_state.setdefault(store, value)
        if key in st.session_state:
            st.session_state[store] = st.session_state[key]
        else:
            st.session_state[key] = st.session_state[store]

    # 마크다운 링크(?hero=)는 전체 리로드라 세션이 새로 뜬다. 그때만 URL 의
    # 티어·포지션을 받아들인다. 이후 실행에서도 계속 받으면 사용자가 바꾼 값을 덮어쓴다.
    if fresh:
        for param, key in (("tier", "selected_tier"), ("role", "selected_role")):
            incoming = st.query_params.get(param)
            if isinstance(incoming, list):
                incoming = incoming[0] if incoming else None
            if incoming:
                st.session_state[key] = str(incoming)
                st.session_state[key + _STORE] = str(incoming)


def filter_qs() -> str:
    """마크다운 링크에 붙일 &tier=&role=. 링크 클릭은 전체 리로드라 URL 로 넘기지
    않으면 전역 필터가 기본값(골드·전체)으로 돌아간다."""
    from urllib.parse import quote

    init_filter_state()
    return (f"&tier={quote(st.session_state['selected_tier'], safe='')}"
            f"&role={quote(st.session_state['selected_role'], safe='')}")


def _options():
    """(티어, 역할) 선택지. latest 스냅샷 기준의 단일 출처."""
    from app_data import get_ordered_roles, get_ordered_tiers, load_latest_stats

    try:
        df = load_latest_stats()
    except Exception:
        return ["All"], ["All"]
    return get_ordered_tiers(df), get_ordered_roles(df)


def render_global_filters(which=("tier", "role")) -> None:
    """사이드바 전역 필터. 모든 페이지가 같은 key 로 바인딩한다."""
    from app_data import role_option_label, tier_option_label

    from .components import icon_selectbox

    if not which:
        return

    init_filter_state()
    tiers, roles = _options()
    if len(tiers) <= 1:
        # 데이터를 못 읽었다. 저장된 선택을 덮어쓰지 않는다.
        return

    # 수집이 끊긴 티어가 저장돼 있으면 위젯이 예외를 낸다. 목록 안으로 되돌린다.
    if st.session_state["selected_tier"] not in tiers:
        st.session_state["selected_tier"] = "Gold" if "Gold" in tiers else tiers[0]
    if st.session_state["selected_role"] not in roles:
        st.session_state["selected_role"] = roles[0]

    st.markdown('<div class="ow-nav-section">Filter</div>', unsafe_allow_html=True)
    if "tier" in which:
        st.session_state["selected_tier"] = icon_selectbox(
            "티어", tiers, "tiersel",
            index=tiers.index(st.session_state["selected_tier"]),
            format_func=tier_option_label,
        )
    if "role" in which:
        st.session_state["selected_role"] = icon_selectbox(
            "포지션", roles, "rolesel",
            index=roles.index(st.session_state["selected_role"]),
            format_func=role_option_label,
        )

    for key in ("selected_tier", "selected_role"):
        st.session_state[key + _STORE] = st.session_state[key]


def _sync_from(widget_key: str, canon: str) -> None:
    st.session_state[canon] = st.session_state[widget_key]
    st.session_state[canon + _STORE] = st.session_state[widget_key]


def render_inline_filters(which=("tier", "role")) -> None:
    """사이드바가 접혔을 때(폰·접은 태블릿) 본문 위에 보이는 필터 사본.

    사이드바 필터와 같은 정본(selected_*)을 쓴다. 사본은 key 가 있어서 매 실행 정본
    값으로 다시 채우고, 사용자가 바꾸면 on_change 콜백이 스크립트보다 먼저 정본을 고친다.
    그래서 사이드바 쪽(render_global_filters, 이보다 먼저 렌더)도 같은 실행에서 새 값을 본다.
    """
    from app_data import role_option_label, tier_option_label

    from .components import icon_selectbox

    if not which:
        return
    tiers, roles = _options()
    if len(tiers) <= 1:
        return
    specs = [("tier", "티어", tiers, "selected_tier", tier_option_label),
             ("role", "포지션", roles, "selected_role", role_option_label)]
    with st.container(horizontal=True, gap="small", key="mfilters"):
        for name, label, options, canon, fmt in specs:
            if name not in which or st.session_state[canon] not in options:
                continue
            widget_key = f"m_{name}"
            st.session_state[widget_key] = st.session_state[canon]
            icon_selectbox(label, options, f"m{name}sel", key=widget_key, format_func=fmt,
                           label_visibility="collapsed",
                           on_change=_sync_from, args=(widget_key, canon))


def selected_tier() -> str:
    init_filter_state()
    return st.session_state["selected_tier"]


def selected_role() -> str:
    init_filter_state()
    return st.session_state["selected_role"]


def resolve_tier(available) -> str:
    """전역 티어를 이 페이지가 가진 티어 목록에 맞춰 해석한다.

    영웅별 지표 추이처럼 데이터가 부분적인 화면에서 전역 선택이 비어 있을 수 있다.
    그때 빈 화면을 내는 대신 있는 티어로 떨어뜨린다.
    """
    available = list(available)
    if not available:
        return selected_tier()
    current = selected_tier()
    if current in available:
        return current
    return "Gold" if "Gold" in available else available[0]
