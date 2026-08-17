"""HTML 카드 렌더 헬퍼.

시각적으로 하나인 카드는 위젯을 조합하지 않고 HTML 한 덩어리로 렌더한다.
"""

from __future__ import annotations

import html

import streamlit as st

from .tokens import *  # noqa: F401,F403


def render_page_hero(title: str, subtitle: str, badge: str = "Overwatch 2 Meta") -> None:
    st.markdown(
        f"""
        <section class="ow-hero-wrap">
            <div class="ow-hero-badge">{html.escape(badge)}</div>
            <h1 class="ow-hero-title">{html.escape(title)}</h1>
            <p class="ow-hero-sub">{html.escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_hero_banner(
    hero_name: str,
    art: dict | None,
    stats,
    headline: str = "",
    kicker: str = "Top Meta Hero",
    meta: str = "",
) -> None:
    """레퍼런스(Valorant 트래커) 스타일의 히어로 배너.

    art 는 app_data.get_hero_banner_art() 의 반환값. None 이면 아트 없이 렌더링한다.
    stats 는 [(라벨, 값), ...].
    """
    art = art or {}
    splash_url = art.get("splash_url")
    cutout_url = art.get("cutout_url")
    focal_x = art.get("focal_x") or 0.7

    bg_style = ""
    if splash_url:
        # 컷아웃이 없으면 캐릭터가 보이도록 초점 위치를 우측으로 당겨서 배치한다.
        pos = 50 if cutout_url else min(max(focal_x * 100, 55), 88)
        bg_style = (
            f"background-image:url('{html.escape(splash_url, quote=True)}');"
            f"background-position:{pos:.0f}% center;"
        )

    cutout_html = ""
    if cutout_url:
        # 컷아웃은 Streamlit 정적 서빙(/app/static/...)에서 온다. 배포 환경이 base URL
        # 경로를 붙이면 이 절대 경로가 어긋날 수 있어, 실패 시 깨진 이미지 아이콘 대신
        # 조용히 사라지게 한다(배경 아트만 남아 배너는 그대로 성립).
        cutout_html = (
            f"<img class='ow-hero-cutout' alt='' aria-hidden='true' "
            f"onerror=\"this.style.display='none'\" "
            f"src='{html.escape(cutout_url, quote=True)}'>"
        )

    headline_html = ""
    if headline:
        headline_html = f"<div class='ow-hero-banner-num'>{html.escape(headline)}</div>"

    meta_html = ""
    if meta:
        meta_html = f"<div class='ow-hero-banner-meta'>{html.escape(meta)}</div>"

    stats_html = "".join(
        "<div>"
        f"<div class='ow-hero-banner-stat-label'>{html.escape(str(label))}</div>"
        f"<div class='ow-hero-banner-stat-value'>{html.escape(str(value))}</div>"
        "</div>"
        for label, value in stats
    )

    st.markdown(
        f"""
        <section class="ow-hero-banner{' has-cutout' if cutout_url else ''}">
            <div class="ow-hero-banner-card">
                <div class="ow-hero-banner-bg" style="{bg_style}"></div>
                {headline_html}
                <div class="ow-hero-banner-body">
                    <div class="ow-hero-banner-kicker">{html.escape(kicker)}</div>
                    <div class="ow-hero-banner-name">{html.escape(hero_name)}</div>
                    {meta_html}
                    <div class="ow-hero-banner-stats">{stats_html}</div>
                </div>
            </div>
            {cutout_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_hero_card_grid(cards) -> None:
    """영웅 아트 카드 그리드.

    cards 는 dict 리스트: name, art_url, focal_x, metric, metric_color, sub, rank,
    rank_color, href. 첫 카드는 강조 처리한다.
    """
    items = []
    for index, card in enumerate(cards):
        art = ""
        if card.get("art_url"):
            # focal_x 는 fetch_hero_art.py 가 산출한 캐릭터 가로 위치. 세로형으로 crop 될 때
            # 인물이 잘리지 않게 이 지점을 기준으로 맞춘다.
            pos = min(max(float(card.get("focal_x") or 0.6) * 100, 25), 85)
            art = (
                f"<div class='ow-card-art' style=\"background-image:url('"
                f"{html.escape(str(card['art_url']), quote=True)}');"
                f"background-position:{pos:.0f}% 28%;\"></div>"
            )
        else:
            art = "<div class='ow-card-art' style='background:#1b1e2e;'></div>"

        rank_html = ""
        if card.get("rank"):
            rank_html = (
                f"<div class='ow-card-rank' style=\"color:{card.get('rank_color', '#fff')};\">"
                f"{html.escape(str(card['rank']))}</div>"
            )

        body = (
            f"<div class='ow-card-body'>"
            f"<div class='ow-card-metric' style=\"color:{card.get('metric_color', '#fff')};\">"
            f"{html.escape(str(card.get('metric', '-')))}</div>"
            f"<div class='ow-card-name'>{html.escape(str(card.get('name', '-')))}</div>"
            f"<div class='ow-card-sub'>{html.escape(str(card.get('sub', '')))}</div>"
            f"</div>"
        )

        classes = "ow-card featured" if index == 0 else "ow-card"
        href = card.get("href")
        if href:
            items.append(
                f"<a class='{classes}' target='_self' "
                f"href='{html.escape(str(href), quote=True)}'>{art}{rank_html}{body}</a>"
            )
        else:
            items.append(f"<div class='{classes}'>{art}{rank_html}{body}</div>")

    st.markdown(f"<div class='ow-card-grid'>{''.join(items)}</div>", unsafe_allow_html=True)


def render_rank_rail(title: str, rows, footnote: str = "") -> None:
    """우측 요약 패널. rows 는 (라벨, 개수, 색) 튜플 리스트."""
    total = max(sum(int(count) for _, count, _ in rows), 1)
    body = []
    for label, count, color in rows:
        width = int(count) / total * 100
        body.append(
            f"<div class='ow-rail-row'>"
            f"<div class='ow-rail-key' style=\"color:{color};\">{html.escape(str(label))}</div>"
            f"<div class='ow-rail-bar'><div class='ow-rail-fill' "
            f"style=\"width:{width:.1f}%;background:{color};\"></div></div>"
            f"<div class='ow-rail-count'>{int(count)}</div>"
            f"</div>"
        )
    foot = f"<div class='ow-rail-foot'>{html.escape(footnote)}</div>" if footnote else ""
    st.markdown(
        f"<div class='ow-rail'><div class='ow-rail-title'>{html.escape(title)}</div>"
        f"{''.join(body)}{foot}</div>",
        unsafe_allow_html=True,
    )


NAV_ITEMS = [
    ("main", "랭크 순위표", ":material/leaderboard:", "main.py"),
    ("pick_win", "3D 메타 분포", ":material/scatter_plot:", "pages/1_pick_win_distribution.py"),
    ("hero_trends", "시계열 분석", ":material/show_chart:", "pages/2_hero_trends.py"),
]


def _latest_data_date() -> str:
    """사이드바 하단에 표시할 데이터 기준일.

    페이지마다 따로 넘기면 어떤 페이지에서는 빠져 일관성이 깨지므로 여기서 직접 읽는다.
    load_latest_stats 는 캐시되어 있어 추가 비용이 없다. app_data 는 ui 를 임포트하지
    않지만, 임포트 순서에 얽히지 않도록 지연 임포트한다.
    """
    try:
        from app_data import load_latest_stats

        df = load_latest_stats()
        if "update_date" in df.columns and not df.empty:
            return str(df["update_date"].iloc[0])
    except Exception:
        pass
    return ""


def render_sidebar_navigation(current_page: str, data_date: str | None = None) -> None:
    """좌측 아이콘 네비게이션.

    Streamlit 기본 페이지 목록(stSidebarNav)은 숨기고 page_link 로 직접 구성한다.
    활성 항목 표시는 st.container(key=...) 가 붙여주는 st-key-* 클래스를 CSS 훅으로 쓴다.
    """
    if data_date is None:
        data_date = _latest_data_date()
    with st.sidebar:
        st.markdown(
            """
            <div class="ow-nav-brand">
                <div class="ow-nav-brand-mark">OW2</div>
                <div>
                    <div class="ow-nav-brand-title">META TRACKER</div>
                    <div class="ow-nav-brand-sub">경쟁전 메타 분석</div>
                </div>
            </div>
            <div class="ow-nav-section">Menu</div>
            """,
            unsafe_allow_html=True,
        )

        for page_key, label, icon, target in NAV_ITEMS:
            state = "active" if page_key == current_page else "idle"
            with st.container(key=f"ownav-{state}-{page_key}"):
                st.page_link(target, label=label, icon=icon)

        # 영웅 상세는 메뉴에 없고 표에서 진입하므로, 그 페이지에 있을 때만 현재 위치를 알린다.
        if current_page == "detail":
            st.markdown(
                '<div class="ow-nav-standalone">'
                '<span class="ow-nav-standalone-dot"></span>영웅 상세 리포트</div>',
                unsafe_allow_html=True,
            )

        if data_date:
            st.markdown(
                f'<div class="ow-nav-foot"><div class="ow-nav-section">Data</div>'
                f'<div class="ow-nav-foot-value">{html.escape(str(data_date))}</div></div>',
                unsafe_allow_html=True,
            )
