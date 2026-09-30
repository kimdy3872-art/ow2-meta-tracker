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


def _filter_qs() -> str:
    """영웅 링크에 붙일 &tier=&role=. 링크 클릭은 전체 리로드라 세션이 새로 뜬다."""
    try:
        from .filters import filter_qs

        return filter_qs()
    except Exception:
        return ""


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
    """페이지 머리. 박스·글로우 배너 대신 제목 한 줄 + 상태 줄로 둔다."""
    live = (f"<span class='live-dot' title='마지막 갱신'><i></i>"
            f"{html.escape(live_label)} 업데이트</span>"
            f"<span class='ow-page-src'>한국 서버 · 경쟁전</span>") if live_label else ""
    sub = f"<p class='ow-page-sub'>{html.escape(subtitle)}</p>" if subtitle else ""
    # 조각이 비면 빈 줄이 생기고 뒤따르는 들여쓴 줄이 코드 블록으로 파싱된다. 한 줄로 낸다.
    st.markdown(
        f"<header class='ow-page-head'>"
        f"<div><div class='ow-page-kicker'>{html.escape(badge)}</div>"
        f"<h1 class='ow-page-title'>{html.escape(title)}</h1>{sub}</div>"
        f"<div class='ow-page-status'>{live}</div>"
        f"</header>",
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
        art = "<div class='ow-card-art' style='background:#1a1d25;'></div>"

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


def rank_rail_html(title: str, rows, footnote: str = "") -> str:
    """랭크 분포 카드. rows 는 (라벨, 개수, 색) 튜플 리스트."""
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
    return (f"<div class='ow-rail'><div class='ow-rail-title'>{html.escape(title)}</div>"
            f"{''.join(body)}{foot}</div>")


def render_rank_rail(title: str, rows, footnote: str = "") -> None:
    st.markdown(rank_rail_html(title, rows, footnote), unsafe_allow_html=True)


# 영웅 아트는 Overwatch Wiki(Fandom, CC BY-NC-SA)에서 받아 저장소에 미러링한 것이고
# 원화 저작권은 블리자드에 있다. 비공식 사이트임을 밝혀 둔다.
LEGAL_HTML = ('Blizzard Entertainment와 무관한 비공식 사이트입니다.<br>'
              'Overwatch®는 Blizzard Entertainment, Inc.의 상표입니다.<br>'
              '영웅 아트 출처: Overwatch Wiki (CC BY-NC-SA).')

NAV_ITEMS = [
    ("main", "영웅 순위", ":material/leaderboard:", "main.py"),
    ("map_heroes", "전장별 영웅", ":material/map:", "pages/4_map_heroes.py"),
    ("hero_trends", "영웅 추이", ":material/show_chart:", "pages/2_hero_trends.py"),
    ("pick_win", "메타 분포", ":material/scatter_plot:", "pages/1_pick_win_distribution.py"),
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


def render_sidebar_navigation(current_page: str, data_date: str | None = None,
                              filters=("tier", "role")) -> None:
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
                <div class="ow-nav-brand-mark"><svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M5 19V11M12 19V5M19 19v-5" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/></svg></div>
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
                '<span class="ow-nav-standalone-dot"></span>영웅 상세</div>',
                unsafe_allow_html=True,
            )

        # 전역 필터는 메뉴와 DATA 사이에 온다. 페이지가 바뀌어도 같은 자리다.
        from .filters import render_global_filters
        render_global_filters(filters)

        if data_date:
            st.markdown(
                f'<div class="ow-nav-foot"><div class="ow-nav-section">Data</div>'
                f'<div class="ow-nav-foot-value">{html.escape(str(data_date))}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f'<div class="ow-nav-legal">{LEGAL_HTML}</div>', unsafe_allow_html=True)


def render_inline_nav(current_page: str, filters=("tier", "role")) -> None:
    """사이드바가 접혀 있을 때(폰·접은 태블릿·접은 PC) 본문 맨 위에 보이는 메뉴·필터 줄.

    폰에서는 사이드바가 화면 밖에 접혀 있고 여는 버튼은 설명 없는 아이콘뿐이라, 다른
    페이지가 있다는 것도, 지금 어떤 티어를 보고 있는지도 드러나지 않았다. 표시 여부는
    CSS 가 사이드바의 aria-expanded 로 정한다(펼쳐져 있으면 숨긴다).
    """
    with st.container(key="mbar"):
        with st.container(horizontal=True, gap="small", key="mnav"):
            for page_key, label, _icon, target in NAV_ITEMS:
                state = "active" if page_key == current_page else "idle"
                with st.container(key=f"mnav-{state}-{page_key}"):
                    st.page_link(target, label=label)
        from .filters import render_inline_filters
        render_inline_filters(filters)


def render_page_footer() -> None:
    """사이드바가 접혔을 때만 보이는 하단 고지. 펼쳐져 있으면 사이드바에 같은 문구가 있다."""
    st.markdown(f'<footer class="ow-page-foot">{LEGAL_HTML}</footer>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 지시서 STEP 2 - 랭크 순위표 페이지 컴포넌트
# ---------------------------------------------------------------------------

def render_hero_showcase(
    hero_name: str,
    art: dict | None,
    accent: str,
    stats,
    eyebrow: str = "TOP HERO",
    meta: str = "",
    rank: str = "",
    href: str = "",
) -> None:
    """페이지 시그니처 HERO 카드.

    위젯을 조합하지 않고 HTML 한 덩어리로 렌더한다. 카드는 overflow:hidden 이고
    아트는 그 안쪽 레이어라 밖으로 새지 않는다. href 가 있으면 카드 전체가 링크다.
    """
    art = art or {}
    cutout = art.get("cutout_url")
    splash = art.get("splash_url")
    focal = art.get("focal_x") or 0.66

    # 아트가 없어도 영웅색 글로우만으로 카드가 성립해야 한다(검은 빈 칸 금지).
    # 보라 그라디언트 대신 중성 바탕 위에 영웅색을 인물 뒤쪽에만 번지게 한다.
    base = (f"radial-gradient(60% 95% at 76% 55%, {_glow(accent, 0.30)}, transparent 70%),"
            "linear-gradient(180deg, #16181f 0%, #0f1015 100%)")
    scrim = ("linear-gradient(90deg, rgba(11,12,16,0.94) 0%, "
             "rgba(11,12,16,0.7) 38%, transparent 70%)")
    bg_style = f"background-image:{scrim},{base};background-size:cover,cover,cover;"
    art_html = ""

    if cutout:
        # 아트는 카드 배경 레이어가 아니라 독립 <img> 다. drop-shadow 림라이트가
        # 실루엣을 따라가려면 알파를 가진 자기 박스가 필요하고, 카드 배경으로 두면
        # 필터가 카드 전체에 걸려 텍스트까지 번진다.
        #
        # D-4("아트를 <img> 로 카드 밖에 띄우지 않는다")의 우려는 카드 밖 삐져나옴
        # 이었다. 이 <img> 는 카드 *안쪽* absolute 이고 카드가 overflow:hidden 이라
        # 그 우려는 발생하지 않는다.
        art_html = (
            f"<img class='hero-showcase-art' alt='' aria-hidden='true' "
            f"style=\"--hero-glow:{_glow(accent)}\" "
            f"onerror=\"this.style.display='none'\" "
            f"src='{html.escape(str(cutout), quote=True)}'>"
        )
    elif splash:
        # 컷아웃이 없는 영웅만 스플래시로 대체한다. 이때는 인물 위치를 모르므로
        # focal_x 로 초점을 우측으로 당긴다.
        safe = html.escape(str(splash), quote=True)
        pos = f"{min(max(focal * 100, 55), 88):.0f}% 26%"
        bg_style = (f"background-image:{scrim},url('{safe}'),{base};"
                    f"background-position:center,{pos},center,center;"
                    "background-size:cover,cover,cover,cover;"
                    "background-repeat:no-repeat;")

    stat_html = "".join(
        "<div class='hero-showcase-stat'>"
        f"<div class='hero-showcase-stat-label'>{html.escape(str(label))}</div>"
        f"<div class='hero-showcase-stat-value nowrap'>{value}</div>"
        "</div>"
        for label, value in stats
    )
    meta_html = (
        f"<div class='hero-showcase-meta nowrap'>{html.escape(meta)}</div>" if meta else ""
    )
    rank_html = rank_badge(rank, size=34) if rank else ""
    tag, link_attrs, cta = "div", "", ""
    if href:
        tag = "a"
        link_attrs = f" href='{html.escape(href, quote=True)}' target='_self'"
        cta = ("<span class='hero-showcase-cta'>상세 보기"
               "<svg viewBox='0 0 16 16' width='14' height='14' aria-hidden='true'>"
               "<path d='M6 3.5 10.5 8 6 12.5' fill='none' stroke='currentColor' "
               "stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg></span>")

    st.markdown(
        _one_line(f"""
        <section class="hero-showcase">
            <{tag} class="hero-showcase-card"{link_attrs} style="{bg_style}">
                {art_html}
                <div class="hero-showcase-left">
                    <span class="hero-showcase-eyebrow">{html.escape(eyebrow)}</span>
                    <div class="hero-showcase-title">
                        <h2 class="hero-showcase-name">{html.escape(hero_name)}</h2>{rank_html}
                    </div>
                    {meta_html}
                    <div class="hero-showcase-stats">{stat_html}</div>
                    {cta}
                </div>
            </{tag}>
        </section>
        """),
        unsafe_allow_html=True,
    )


def render_map_cards(cards, title: str = "") -> None:
    """전장 카드. 표본 부족 조합은 흐리게 그린다. title 은 그리드 바로 위 라벨."""
    items = []
    for index, card in enumerate(cards):
        cls = "map-card featured" if index == 0 else "map-card"
        sample = str(card.get("sample") or "")
        if sample == "표본 부족":
            cls += " dim"
        sample_html = f"<span class='sample-note'>{html.escape(sample)}</span>" if sample else ""
        img = html.escape(str(card.get("image") or ""), quote=True)
        items.append(
            f"<div class='{cls}'>"
            f"<div class='map-card-art' style=\"background-image:url('{img}');\"></div>"
            f"<div class='map-card-body'>"
            f"<div class='map-card-name nowrap'>{html.escape(str(card.get('name', '-')))}</div>"
            f"<div class='map-card-metric nowrap'>{html.escape(str(card.get('metric', '-')))}{sample_html}</div>"
            f"</div></div>"
        )
    head = f"<div class='eyebrow'>{html.escape(title)}</div>" if title else ""
    st.markdown(f"<div class='map-wrap'>{head}<div class='map-grid'>{''.join(items)}</div></div>",
                unsafe_allow_html=True)


def meta_score_html(score, rank, hero_name) -> str:
    """META SCORE 카드. 종합 점수를 0~1000 으로 편 표시용 값."""
    return _one_line(f"""
        <div class="rail-card meta-score-card">
            <div class="eyebrow">Meta Score</div>
            <div class="meta-score-value nowrap">{int(round(score))}<span class="unit">/1000</span></div>
            <div class="meta-meter"><i style="width:{min(max(score / 10, 0), 100):.1f}%"></i></div>
            <div class="meta-score-sub nowrap">{html.escape(str(hero_name))} · 랭크 {html.escape(str(rank))}</div>
        </div>
        """)


def render_meta_score_card(score, rank, hero_name) -> None:
    st.markdown(meta_score_html(score, rank, hero_name), unsafe_allow_html=True)


def rail_rows_html(title: str, rows, empty_text: str = "") -> str:
    """우측 레일 공통 행 목록. rows: (초상화 url, 이름, 값 텍스트, 값 색)."""
    if not rows:
        body = f"<div class='rail-empty'>{html.escape(empty_text)}</div>" if empty_text else ""
    else:
        body = "".join(
            f"<a class='rail-row' target='_self' "
            f"href='?hero={urllib.parse.quote(str(name), safe='')}{_filter_qs()}'>"
            + (f"<img class='rail-row-img' src='{html.escape(str(img), quote=True)}' alt=''>"
               if img else "<div class='rail-row-img'></div>")
            + f"<div class='rail-row-name nowrap'>{html.escape(str(name))}</div>"
            f"<div class='rail-row-value nowrap' style=\"color:{color};\">{html.escape(str(value))}</div>"
            "</a>"
            for img, name, value, color in rows
        )
    return f"<div class='rail-card'><div class='eyebrow'>{html.escape(title)}</div>{body}</div>"


def render_rail_rows(title: str, rows, empty_text: str = "") -> None:
    st.markdown(rail_rows_html(title, rows, empty_text), unsafe_allow_html=True)


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
    st.markdown(f"<div class='kpi-wrap'><div class='kpi-row'>{''.join(cells)}</div></div>",
                unsafe_allow_html=True)


def render_hero_portrait_card(hero_name: str, art: dict | None, accent: str, caption: str = "") -> None:
    """영웅 추이 페이지 상단 좌측의 영웅 세로 카드."""
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
    hover 가 없는 터치 기기에서는 멈출 방법이 없어서, CSS 가 자동 순환을 끄고 좌우
    스와이프 캐러셀로 바꾼다(묶음마다 .rot-slide-title 이 그때 제목 역할을 한다).

    groups: [(제목, [카드 dict, ...]), ...]
    """
    if not groups:
        return
    # ponytail: style.css 의 rot-* 키프레임 구간(33.33%)이 3묶음 기준이다. 묶음 수가
    # 바뀌면 키프레임 퍼센트도 1/N 로 바꿔야 한다.
    count = len(groups)
    total = interval * count
    tabs, slides = [], []
    for index, (title, cards) in enumerate(groups):
        # 양수 지연: 0번이 먼저 들어오고, 앞 묶음이 빠지는 순간 다음 묶음이 들어온다.
        timing = f"--rot-total:{total}s;--rot-delay:{interval * index}s;"
        items = "".join(_hero_card_markup(c, featured=(i == 0))
                        for i, c in enumerate(cards))
        tabs.append(f"<span class='rot-tab' style='{timing}'>{html.escape(str(title))}</span>")
        slides.append(f"<div class='rot-slide' style='{timing}'>"
                      f"<div class='rot-slide-title'>{html.escape(str(title))}"
                      f"<span>{index + 1} / {count}</span></div>"
                      f"<div class='ow-card-grid'>{items}</div></div>")
    st.markdown(
        f"<div class='rot-wrap'><div class='rot-tabs'>{''.join(tabs)}</div>"
        f"<div class='rot-stage'>{''.join(slides)}</div></div>",
        unsafe_allow_html=True,
    )


def icon_selectbox(label, options, scope, **kwargs):
    """실제 게임 뱃지를 붙인 selectbox.

    st.selectbox 의 옵션은 평문만 받아서 마크업을 넣을 수 없다. 그래서 라벨은
    평문 그대로 두고 그림은 CSS 로 얹는다. 열린 목록과 닫힌 상태는 DOM 상
    전혀 다른 곳에 그려져서 규칙도 따로 만들어야 한다(ui/badges.py 참고).

    scope 는 닫힌 상태를 잡을 때 쓰는 컨테이너 key 접두사다. 값은 절대 key 에
    넣지 않는다. key 가 바뀌면 리액트가 셀렉트박스를 통째로 다시 마운트해서,
    클릭 커밋이 재마운트에 먹히고 검색 입력에 포커스가 잡혀 엔터를 한 번 더
    눌러야 값이 반영된다. 셀렉터는 고정하고 규칙 안의 URI 만 바꾼다.

    <style> 는 셀렉트박스 뒤에 낸다. 앞에 내면 아직 갱신 전인 session_state 로
    뱃지를 그려 값보다 한 박자 늦는다. CSS 는 위치와 무관하게 전역이다.
    """
    with st.container(key=scope):
        value = st.selectbox(label, options, **kwargs)
    st.markdown(
        f"<style>{option_list_icon_css(list(options))}"
        f"{selected_value_icon_css(scope, str(value))}</style>",
        unsafe_allow_html=True,
    )
    return value
