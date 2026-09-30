"""
OW2 메타 트래커 — 뱃지 생성 모듈
────────────────────────────────────────────────────────
섹션 1~2 는 인라인 HTML/SVG 를 문자열로 반환한다. 이미지 파일도, base64 인코딩도 필요 없다.
st.markdown(html, unsafe_allow_html=True) 안에 그대로 끼워 넣으면 된다.

    from ui.badges import rank_badge

    st.markdown(f'<div>{rank_badge("S")} 아나</div>', unsafe_allow_html=True)
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════
# 1. S / A / B / C / D 랭크 뱃지
# ═══════════════════════════════════════════════════════
# 오버워치에 이런 등급은 없다. 티어리스트 관용 표기이므로 구할 에셋 자체가 없고,
# 직접 만드는 것이 유일한 방법이자 저작권상 가장 안전한 방법이다.
# A 는 노랑 쪽으로 둔다. 액센트(오버워치 오렌지)와 붙어 보이면 등급이 UI 강조로 읽힌다.
RANK_COLORS: dict[str, str] = {
    "S": "#ff5c6a",
    "A": "#f2c14e",
    "B": "#3ecf8e",
    "C": "#4ea8ff",
    "D": "#7d8394",
}


def rank_badge(rank: str, size: int = 26) -> str:
    """랭크 글자 타일. 표 행·카드 공용. 색은 CSS(.rank-tag)가 --rank 로 받는다.

    예전 육각형 SVG 는 26px 에서 글자가 뭉개졌다. 텍스트 타일은 어느 크기에서나 선명하다.
    """
    c = RANK_COLORS.get(rank, RANK_COLORS["D"])
    return (
        f'<span class="rank-tag" style="--rank:{c};width:{size}px;height:{size}px;'
        f'font-size:{size * 0.52:.0f}px">{rank}</span>'
    )


# ═══════════════════════════════════════════════════════
# 2. 부속 — 델타 화살표, 즐겨찾기 하트
# ═══════════════════════════════════════════════════════
# 영웅 추이 페이지의 "▲ 4.7%" 텍스트 화살표와 HEROES 카드의 ♡ 이모지를 대체한다.

def delta_arrow(up: bool, size: int = 8) -> str:
    c = "#3ecf8e" if up else "#ff5c6a"
    pts = "5,1 9.5,8 0.5,8" if up else "5,9 9.5,2 0.5,2"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 10 10" '
        f'style="vertical-align:baseline;flex:none">'
        f'<polygon points="{pts}" fill="{c}"/></svg>'
    )


def heart_icon(filled: bool = False, size: int = 16) -> str:
    c = "#f99e1a" if filled else "rgba(255,255,255,.42)"
    fill = c if filled else "none"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{c}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:middle;flex:none">'
        f'<path d="M12 20.3 3.9 12.4a5 5 0 0 1 7.1-7.1l1 1 1-1a5 5 0 0 1 7.1 7.1z"/>'
        f"</svg>"
    )


# ── 3. 실제 게임 뱃지(assets/ranks) ───────────────────────────────────────────
#
# 섹션 1~2 는 손으로 그린 것이다. 아래는 Blizzard 가 실제로 쓰는 아트를 받아
# assets/ranks/ 에 커밋해 둔 것이다. 원본은 해시가 파일명에 박힌 CDN 경로라
# (Rank_EmeraldTier.d82e76cb....png) 재배포될 때마다 URL 이 죽는다. 실제로
# damage 역할 아이콘과 TierDivision_2 는 이미 403 이다. 그래서 런타임에 물지
# 않고 받아서 커밋했다. 표시 크기 22px 의 2배인 44px 로 줄여 12개 합쳐 21KB.

import base64
from functools import lru_cache
from pathlib import Path

_RANK_ART_DIR = Path(__file__).resolve().parent.parent / "assets" / "ranks"


@lru_cache(maxsize=None)
def rank_art_uri(name: str) -> str:
    """assets/ranks/<name> 을 data URI 로. 없으면 빈 문자열."""
    for ext, mime in (("webp", "image/webp"), ("svg", "image/svg+xml")):
        path = _RANK_ART_DIR / f"{name}.{ext}"
        if path.exists():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
    return ""


# 아이콘 정사각 박스와 그 왼쪽 여백. 닫힌 상태와 열린 목록이 같은 값을 써야
# 크기가 어긋나지 않는다. 티어 뱃지(세로로 긴 날개)와 포지션 아이콘(가로로 넓은
# 칼)은 종횡비가 달라서, 정사각 박스에 맞춰야 시각적 무게가 비슷해진다.
_ICON_BOX = 24
_ICON_PAD = 48


def _icon_rule(selector: str, uri: str, box: int = _ICON_BOX, pad: int = _ICON_PAD) -> str:
    """배경 이미지 + padding-left 로 아이콘을 넣는다.

    ::before 로 넣으면 값 컨테이너의 형제 플렉스 아이템이 되는데, 값 컨테이너가
    이미 자기 padding-left 를 갖고 있어서 아이콘 폭 + margin + 그 패딩이 전부
    더해져 글자가 멀리 밀렸다. 배경은 새 박스를 안 만들어서 중복이 없다.

    background 단축 속성을 쓰면 BaseWeb 이 건 background-color 가 지워진다.
    반드시 롱핸드로.

    background-* 에만 !important 를 단다. style.css 의
    `.stSelectbox [data-baseweb="select"] * { background: transparent !important }`
    가 단축 속성이라 background 롱핸드 전부를 initial-important 로 덮는다.
    특이도로는 못 이긴다. padding-left 는 그 규칙 밖이라 그냥 둔다.
    """
    if not uri:
        return ""
    return (
        f"{selector}{{"
        f"background-image:url('{uri}') !important;"
        f"background-repeat:no-repeat !important;"
        f"background-position:{(pad - box) // 2}px center !important;"
        f"background-size:{box}px {box}px !important;"
        f"padding-left:{pad}px;"
        f"}}"
    )


def option_list_icon_css(options: list[str]) -> str:
    """열린 드롭다운 목록에 실제 뱃지를 붙이는 CSS.

    옵션 li 는 셀렉트박스 밖 포털에 그려져서 위젯 단위로 스코프를 못 건다.
    대신 nth-child 와 nth-last-child 를 겹쳐 "N개짜리 목록의 i번째"를 집는다.
    티어(9개)와 포지션(4개)은 길이가 달라 서로를 침범하지 않는다.

    # ponytail: 길이가 같아지면 두 목록의 규칙이 겹쳐 아이콘이 섞인다. 포지션은
    # 항상 4개고 티어는 전체+수집된 티어라, 한 영웅이 딱 3개 티어에만 존재해야
    # 충돌한다. 현재 데이터는 모든 영웅이 9개 티어에 다 있어 도달 불가.
    # 실제로 겹치기 시작하면 열린 목록을 st.popover 로 직접 그리는 수밖에 없다.

    li 는 display:flex 라 자체 padding-left 를 갖는다. 그 값을 덮어써서 아이콘
    자리를 만든다.
    """
    total = len(options)
    css = ['li[role="option"]{align-items:center;}']
    for i, name in enumerate(options):
        # body 접두사는 특이도용이다. style.css 의 aria-selected 규칙이
        # `background: ... !important` 단축 속성이라 같은 특이도면 아이콘이
        # 지워진다(현재 선택된 항목만 뱃지가 사라졌다).
        selector = (
            f'body li[role="option"]:nth-child({i + 1}):nth-last-child({total - i})'
        )
        css.append(_icon_rule(selector, rank_art_uri(name)))
    return "".join(css)


def selected_value_icon_css(scope: str, name: str) -> str:
    """닫힌 셀렉트박스(선택된 값)에 뱃지를 붙이는 CSS.

    선택값 div 는 난독화된 st-* 클래스뿐이라 직접 못 잡는다. st.container(key=scope)
    가 내주는 .st-key-<scope> 로 우회한다. 값은 key 에 넣지 않는다 - 그러면 값이
    바뀔 때마다 셀렉트박스가 재마운트된다(ui/components.py:icon_selectbox 참고).
    셀렉터는 고정이고, 값에 따라 달라지는 건 규칙 안의 URI 뿐이다.
    """
    # control div 은 style.css 가 linear-gradient 배경을 이미 깔아둬서 여기에
    # background-image 를 걸면 그 그라디언트가 지워진다. 한 단계 안쪽 값
    # 컨테이너로 좁힌다. 원래 padding-left 12px 자리를 그대로 넘겨받는다.
    selector = (
        f'.st-key-{scope} [data-baseweb="select"] > div:first-child > div:first-child'
    )
    return _icon_rule(selector, rank_art_uri(name))
