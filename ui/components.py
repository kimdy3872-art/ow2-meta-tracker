"""HTML 카드 렌더 헬퍼.

시각적으로 하나인 카드는 위젯을 조합하지 않고 HTML 한 덩어리로 렌더한다.
"""

from __future__ import annotations

import colorsys
import html
import urllib.parse

import streamlit as st

from .badges import (  # noqa: F401
    delta_arrow,
    heart_icon,
    option_list_icon_css,
    rank_badge,
    selected_value_icon_css,
)
from .tokens import *  # noqa: F401,F403

# 인라인 SVG 아이콘. 참고 목업의 이모지 개수는 0개다.
def _one_line(markup: str) -> str:
    """여러 줄 HTML 을 한 줄로 만든다.

    f-string 조각이 비면 빈 줄이 생기고, 그 뒤 들여쓴 줄을 Streamlit 마크다운이 코드
    블록으로 파싱해 HTML 이 화면에 그대로 노출된다. 이 함수를 거치면 그 경우가 사라진다.
    """
    return "".join(line.strip() for line in markup.splitlines())


def _glow(accent: str, alpha: float = 0.45) -> str:
    """영웅 색을 림라이트용 rgba 로. 아트를 어두운 배너 위로 띄우는 데 쓴다.

    hero_colors.json 의 대표색은 그대로 쓰면 안 된다. 아나(#473727)나 리퍼처럼
    어두운 영웅은 대표색도 어두워서, 어두운 배너 위에 깔면 빛나지 않고 그냥
    사라진다. 색상은 유지한 채 명도와 채도만 끌어올린다.
    """
    raw = str(accent or "").lstrip("#")
    if len(raw) != 6:
        return f"rgba(255, 122, 140, {alpha})"
    try:
        r, g, b = (int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return f"rgba(255, 122, 140, {alpha})"
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, max(s, 0.55), max(v, 0.92))
    return f"rgba({round(r * 255)}, {round(g * 255)}, {round(b * 255)}, {alpha})"




def render_page_hero(title: str, subtitle: str, badge: str = "Overwatch 2 Meta",
                     live_label: str = "") -> None:
    live = (f"<span class='live-dot' title='마지막 갱신'><i></i>"
            f"{html.escape(live_label)}</span>") if live_label else ""
    sub = f"<p class='ow-hero-sub'>{html.escape(subtitle)}</p>" if subtitle else ""
    # 조각이 비면 빈 줄이 생기고 뒤따르는 들여쓴 줄이 코드 블록으로 파싱된다. 한 줄로 낸다.
    st.markdown(
        f"<section class='ow-hero-wrap'>"
        f"<div class='ow-hero-badge'>{html.escape(badge)}</div>{live}"
        f"<h1 class='ow-hero-title'>{html.escape(title)}</h1>{sub}"
        f"</section>",
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
        _one_line(f"""
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
        """),
        unsafe_allow_html=True,
    )


def _hero_card_markup(card, featured: bool = False) -> str:
    """카드 하나의 HTML. 그리드와 자동 순환이 같은 마크업을 쓴다."""
    if card.get("art_url"):
        pos = min(max(float(card.get("focal_x") or 0.6) * 100, 25), 85)
        art = (f"<div class='ow-card-art' style=\"background-image:url('"
               f"{html.escape(str(card['art_url']), quote=True)}');"
               f"background-position:{pos:.0f}% 28%;\"></div>")
    else:
        art = "<div class='ow-card-art' style='background:#1b1e2e;'></div>"

    rank_html = ""
    if card.get("rank"):
        rank_html = (f"<div class='ow-card-rank'>"
                     f"{rank_badge(card['rank'])}</div>")

    body = (
        f"<div class='ow-card-body'>"
        f"<div class='ow-card-metric nowrap' style=\"color:{card.get('metric_color', '#fff')};\">"
        f"{html.escape(str(card.get('metric', '-')))}</div>"
        f"<div class='ow-card-name nowrap'>{html.escape(str(card.get('name', '-')))}</div>"
        f"<div class='ow-card-sub nowrap'>{html.escape(str(card.get('sub', '')))}</div>"
        f"</div>"
    )
    classes = "ow-card featured" if featured else "ow-card"
    href = card.get("href")
    if href:
        return (f"<a class='{classes}' target='_self' "
                f"href='{html.escape(str(href), quote=True)}'>{art}{rank_html}{body}</a>")
    return f"<div class='{classes}'>{art}{rank_html}{body}</div>"


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

        # 영웅 아트는 Overwatch Wiki(Fandom, CC BY-NC-SA)에서 받아 저장소에 미러링한 것이고
        # 원화 저작권은 블리자드에 있다. 비공식 사이트임을 밝혀 둔다.
        st.markdown(
            '<div class="ow-nav-legal">'
            'Blizzard Entertainment와 무관한 비공식 사이트입니다.<br>'
            'Overwatch®는 Blizzard Entertainment, Inc.의 상표입니다.<br>'
            '영웅 아트 출처: Overwatch Wiki (CC BY-NC-SA).'
            '</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# 지시서 STEP 2 - 랭크 순위표 페이지 컴포넌트
# ---------------------------------------------------------------------------

def render_hero_showcase(
    hero_name: str,
    art: dict | None,
    accent: str,
    watermark: str,
    stats,
    eyebrow: str = "TOP HERO",
    meta: str = "",
) -> None:
    """페이지 시그니처 HERO 카드.

    위젯을 조합하지 않고 HTML 한 덩어리로 렌더한다. 아트가 카드 위로 삐져나와야 해서
    래퍼에 여백을 주고 카드만 overflow: hidden 으로 둔다.
    """
    art = art or {}
    cutout = art.get("cutout_url")
    splash = art.get("splash_url")
    focal = art.get("focal_x") or 0.66

    # 2차 지시서 D-4: 아트를 <img> 로 카드 밖에 띄우지 않는다. 카드는 overflow:hidden
    # 이고 아트는 그 안쪽 레이어라 밖으로 새지 않는다. 아트가 없어도 그라디언트 +
    # 워터마크만으로 성립해야 한다(검은 빈 칸 금지).
    base = f"linear-gradient(115deg, {accent} 0%, #2a1440 58%, #140d24 100%)"
    scrim = ("linear-gradient(100deg, rgba(10,12,18,0.96) 0%, "
             "rgba(10,12,18,0.75) 42%, transparent 78%)")
    bg_style = f"background-image:{scrim},{base};background-size:cover,cover;"
    art_html = ""

    if cutout:
        # 전신 렌더는 카드 배경이 아니라 별도 레이어로 깐다. drop-shadow 림라이트가
        # 실루엣을 따라가려면 알파를 가진 자기 박스가 있어야 하는데, 배경 이미지로
        # 넣으면 필터가 카드 전체에 걸려서 텍스트까지 번진다.
        art_html = (
            f"<div class='hero-showcase-art' style=\"background-image:url('"
            f"{html.escape(str(cutout), quote=True)}');--hero-glow:{_glow(accent)};\"></div>"
        )
    elif splash:
        # 컷아웃이 없는 영웅만 스플래시로 대체한다. 이때는 인물 위치를 모르므로
        # focal_x 로 초점을 우측으로 당긴다.
        safe = html.escape(str(splash), quote=True)
        pos = f"{min(max(focal * 100, 55), 88):.0f}% 26%"
        bg_style = (f"background-image:{scrim},url('{safe}'),{base};"
                    f"background-position:center,{pos},center;"
                    "background-size:cover,cover,cover;"
                    "background-repeat:no-repeat,no-repeat,no-repeat;")

    stat_html = "".join(
        "<div class='hero-showcase-stat'>"
        f"<div class='eyebrow'>{html.escape(str(label))}</div>"
        f"<div class='hero-showcase-stat-value nowrap'>{value}</div>"
        "</div>"
        for label, value in stats
    )
    meta_html = (
        f"<div class='hero-showcase-meta nowrap'>{html.escape(meta)}</div>" if meta else ""
    )

    st.markdown(
        _one_line(f"""
        <section class="hero-showcase">
            <div class="hero-showcase-card" style="{bg_style}">
                {art_html}
                <div class="hero-showcase-num">{html.escape(watermark)}</div>
                <div class="hero-showcase-left">
                    <span class="eyebrow">{html.escape(eyebrow)}</span>
                    <h2 class="hero-showcase-name display">{html.escape(hero_name)}</h2>
                    {meta_html}
                    <div class="hero-showcase-stats">{stat_html}</div>
                </div>
            </div>
        </section>
        """),
        unsafe_allow_html=True,
    )


def render_hero_scroller(cards, favorites=None) -> None:
    """상위 영웅 세로 카드 가로 스크롤. 우상단 하트로 즐겨찾기 토글."""
    favorites = favorites or set()
    items = []
    for card in cards:
        name = str(card.get("name", "-"))
        art_url = card.get("art_url")
        pos = min(max(float(card.get("focal_x") or 0.62) * 100, 25), 85)
        art = (
            f"<div class='hero-tile-art' style=\"background-image:url('"
            f"{html.escape(str(art_url), quote=True)}');background-position:{pos:.0f}% 24%;\"></div>"
            if art_url else "<div class='hero-tile-art' style='background:#1b1e2e;'></div>"
        )
        is_fav = name in favorites
        heart = (
            f"<a class='hero-tile-fav{' on' if is_fav else ''}' target='_self' "
            f"href='?fav={urllib.parse.quote(name, safe='')}' "
            f"title='즐겨찾기' aria-label='즐겨찾기'>"
            f"{heart_icon(is_fav)}</a>"
        )
        items.append(
            f"<div class='hero-tile'>"
            f"<a class='hero-tile-link' target='_self' "
            f"href='?hero={urllib.parse.quote(name, safe='')}'>{art}"
            f"<div class='hero-tile-body'>"
            f"<div class='hero-tile-metric nowrap' style=\"color:{card.get('metric_color', '#fff')};\">"
            f"{html.escape(str(card.get('metric', '-')))}</div>"
            f"<div class='hero-tile-name nowrap'>{html.escape(name)}</div>"
            f"</div></a>{heart}</div>"
        )
    st.markdown(f"<div class='hero-scroller'>{''.join(items)}</div>", unsafe_allow_html=True)


def render_map_cards(cards) -> None:
    """전장 카드. 첫 카드(승률 1위)만 위로 띄운다."""
    items = []
    for index, card in enumerate(cards):
        cls = "map-card featured" if index == 0 else "map-card"
        img = html.escape(str(card.get("image") or ""), quote=True)
        items.append(
            f"<div class='{cls}'>"
            f"<div class='map-card-art' style=\"background-image:url('{img}');\"></div>"
            f"<div class='map-card-body'>"
            f"<div class='map-card-name nowrap'>{html.escape(str(card.get('name', '-')))}</div>"
            f"<div class='map-card-metric nowrap'>{html.escape(str(card.get('metric', '-')))}</div>"
            f"</div></div>"
        )
    st.markdown(f"<div class='map-grid'>{''.join(items)}</div>", unsafe_allow_html=True)


def render_meta_score_card(score, rank, hero_name) -> None:
    """META SCORE 카드. 종합 점수를 0~1000 으로 편 표시용 값."""
    st.markdown(
        _one_line(f"""
        <div class="rail-card meta-score-card">
            <div class="eyebrow">Meta Score</div>
            <div class="meta-score-value nowrap">{int(round(score))}<span class="unit">/1000</span></div>
            <div class="meta-score-sub nowrap">{html.escape(str(hero_name))} · 랭크 {html.escape(str(rank))}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def render_rail_rows(title: str, rows, empty_text: str = "") -> None:
    """우측 레일 공통 행 목록. rows: (초상화 url, 이름, 값 텍스트, 값 색)."""
    if not rows:
        body = f"<div class='rail-empty'>{html.escape(empty_text)}</div>" if empty_text else ""
    else:
        body = "".join(
            f"<a class='rail-row' target='_self' "
            f"href='?hero={urllib.parse.quote(str(name), safe='')}'>"
            + (f"<img class='rail-row-img' src='{html.escape(str(img), quote=True)}' alt=''>"
               if img else "<div class='rail-row-img'></div>")
            + f"<div class='rail-row-name nowrap'>{html.escape(str(name))}</div>"
            f"<div class='rail-row-value nowrap' style=\"color:{color};\">{html.escape(str(value))}</div>"
            "</a>"
            for img, name, value, color in rows
        )
    st.markdown(
        f"<div class='rail-card'><div class='eyebrow'>{html.escape(title)}</div>{body}</div>",
        unsafe_allow_html=True,
    )


def render_kpi_row(items) -> None:
    """KPI 카드 행. st.metric 은 숫자 크기를 못 키워서 직접 그린다.

    items: (라벨, 값, 단위, 델타 텍스트 또는 None, 델타 양수 여부) 리스트.
    """
    cells = []
    for label, value, unit, delta_text, delta_up in items:
        delta_html = ""
        if delta_text:
            cls = "up" if delta_up else "down"
            arrow = delta_arrow(delta_up)
            delta_html = (
                f"<span class='kpi-delta {cls} nowrap'>{arrow}"
                f"<span>{html.escape(str(delta_text))}</span></span>"
            )
        unit_html = f"<span class='unit'>{html.escape(str(unit))}</span>" if unit else ""
        cells.append(
            "<div class='kpi-card'>"
            f"<div class='eyebrow'>{html.escape(str(label))}</div>"
            f"<div class='kpi-value nowrap'>{html.escape(str(value))}{unit_html}</div>"
            f"{delta_html}</div>"
        )
    st.markdown(f"<div class='kpi-row'>{''.join(cells)}</div>", unsafe_allow_html=True)


def render_hero_portrait_card(hero_name: str, art: dict | None, accent: str, caption: str = "") -> None:
    """시계열 상단 좌측의 영웅 세로 카드."""
    art = art or {}
    inner = ""
    if art.get("cutout_url"):
        inner = (
            f"<img class='portrait-card-art' alt='' aria-hidden='true' "
            f"style='--hero-glow:{_glow(accent)}' "
            f"onerror=\"this.style.display='none'\" "
            f"src='{html.escape(art['cutout_url'], quote=True)}'>"
        )
    elif art.get("splash_url"):
        pos = min(max(float(art.get("focal_x") or 0.66) * 100, 55), 88)
        inner = (
            f"<div class='portrait-card-art bg' style=\"background-image:url('"
            f"{html.escape(art['splash_url'], quote=True)}');background-position:{pos:.0f}% 26%;\"></div>"
        )
    cap = f"<div class='portrait-card-cap nowrap'>{html.escape(caption)}</div>" if caption else ""
    # 한 줄로 낸다. 조각이 비면 빈 줄이 생기고, 그 뒤 들여쓴 줄을 Streamlit 이 코드 블록으로
    # 파싱해 HTML 이 그대로 노출된다.
    st.markdown(
        f"<div class='portrait-card' style='--pc-accent:{accent};'>{inner}"
        f"<div class='portrait-card-body'>"
        f"<div class='portrait-card-name nowrap'>{html.escape(hero_name)}</div>"
        f"{cap}</div></div>",
        unsafe_allow_html=True,
    )


def render_rotating_card_groups(groups, interval: int = 6) -> None:
    """제목 + 카드 4장을 한 묶음으로 자동 순환시킨다.

    Streamlit 에서 타이머 재실행을 걸면 매 주기마다 전체 스크립트가 다시 돌아 비싸고
    상호작용도 끊긴다. 그래서 세 묶음을 모두 렌더해 두고 CSS 키프레임으로만 전환한다.
    (rerun 0회, 사용자가 필터를 만지는 동안에도 끊기지 않는다.)

    groups: [(제목, [카드 dict, ...]), ...]
    """
    if not groups:
        return
    count = len(groups)
    total = interval * count
    blocks = []
    for index, (title, cards) in enumerate(groups):
        delay = -interval * (count - index) % total
        items = "".join(_hero_card_markup(c, featured=(i == 0))
                        for i, c in enumerate(cards))
        blocks.append(
            f"<div class='rot-slide' style='animation-duration:{total}s;"
            f"animation-delay:{-interval * index}s;'>"
            f"<div class='eyebrow rot-title'>{html.escape(str(title))}</div>"
            f"<div class='ow-card-grid'>{items}</div>"
            f"</div>"
        )
    dots = "".join(
        f"<i style='animation-duration:{total}s;animation-delay:{-interval * i}s;'></i>"
        for i in range(count)
    )
    st.markdown(
        f"<div class='rot-wrap' style='--rot-total:{total}s;'>{''.join(blocks)}"
        f"<div class='rot-dots'>{dots}</div></div>",
        unsafe_allow_html=True,
    )


def icon_selectbox(label, options, scope, **kwargs):
    """실제 게임 뱃지를 붙인 selectbox.

    st.selectbox 의 옵션은 평문만 받아서 마크업을 넣을 수 없다. 그래서 라벨은
    평문 그대로 두고 그림은 CSS 로 얹는다. 열린 목록과 닫힌 상태는 DOM 상
    전혀 다른 곳에 그려져서 규칙도 따로 만들어야 한다(ui/badges.py 참고).

    scope 는 닫힌 상태를 잡을 때 쓰는 컨테이너 key 접두사다.
    """
    if "key" in kwargs and kwargs["key"] in st.session_state:
        current = st.session_state[kwargs["key"]]
    else:
        current = options[kwargs.get("index", 0)] if options else ""

    st.markdown(
        f"<style>{option_list_icon_css(list(options))}"
        f"{selected_value_icon_css(scope, str(current))}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key=f"{scope}-{current}"):
        return st.selectbox(label, options, **kwargs)
