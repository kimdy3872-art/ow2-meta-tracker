"""
OW2 메타 트래커 — 뱃지 생성 모듈
────────────────────────────────────────────────────────
전부 인라인 SVG를 문자열로 반환한다. 이미지 파일도, base64 인코딩도 필요 없다.
st.markdown(html, unsafe_allow_html=True) 안에 그대로 끼워 넣으면 된다.

    from badges import tier_pip, tier_badge, role_icon, rank_badge

    st.markdown(f'<div>{tier_badge("골드", 3)} 골드 3</div>', unsafe_allow_html=True)

주의: SVG <defs> 안의 gradient id가 한 페이지에서 중복되면 브라우저가 첫 번째 것만
적용한다. 아래 함수들은 모두 id에 고유 접미사를 붙여 이 문제를 피한다.
"""

from __future__ import annotations
import itertools

_uid = itertools.count()


def _nid(prefix: str) -> str:
    """페이지 내 고유 id 생성."""
    return f"{prefix}{next(_uid)}"


# ═══════════════════════════════════════════════════════
# 1. 티어 뱃지 (브론즈 ~ 챔피언)
# ═══════════════════════════════════════════════════════
# (진한 색, 밝은 색) — 인게임 뱃지의 금속 톤을 참조한 자체 팔레트.
# 공식 에셋을 쓰지 않으므로 저작권 문제가 없다.
TIER_COLORS: dict[str, tuple[str, str]] = {
    "브론즈":       ("#a4652f", "#d89a63"),
    "실버":         ("#8f9aa6", "#cfd8e2"),
    "골드":         ("#d69c1f", "#f5d271"),
    "플래티넘":     ("#6f9dae", "#b3d8e4"),
    "에메랄드":     ("#249b6d", "#6ad6a6"),
    "다이아몬드":   ("#5d85f2", "#a5c0ff"),
    "마스터":       ("#dc7f2c", "#f7b96b"),
    "그랜드마스터": ("#b9c1d0", "#edf1f7"),
    "챔피언":       ("#a63fce", "#dd9cf2"),
}

# 티어 순서. 에메랄드는 2026-08-12 신설.
TIER_ORDER = list(TIER_COLORS.keys())


def tier_pip(tier: str, size: int = 10) -> str:
    """
    작은 원형 표식. 세그먼트 컨트롤·표 셀처럼 20px 이하 공간에 쓴다.
    이 크기에서 방패 형태는 뭉개지므로 색 신호만 남긴다.
    """
    dark, light = TIER_COLORS.get(tier, ("#6b7280", "#9ca3af"))
    gid = _nid("tp")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 10 10" '
        f'style="vertical-align:middle;flex:none">'
        f'<defs><radialGradient id="{gid}" cx=".35" cy=".3" r=".8">'
        f'<stop stop-color="{light}"/><stop offset="1" stop-color="{dark}"/>'
        f"</radialGradient></defs>"
        f'<circle cx="5" cy="5" r="4.2" fill="url(#{gid})"/>'
        f"</svg>"
    )


def tier_badge(tier: str, division: int | None = None, size: int = 28) -> str:
    """
    방패형 티어 뱃지. 사이드바·HERO 카드·상세 페이지 헤더용 (24px 이상).

    division: 1~5. None이면 숫자 없이 방패만 (필터 UI에 적합).
              앱이 티어를 필터로만 쓰면 division은 대체로 불필요하다.
    """
    dark, light = TIER_COLORS.get(tier, ("#6b7280", "#9ca3af"))
    gid, sid = _nid("tg"), _nid("ts")

    numeral = ""
    if division is not None:
        numeral = (
            f'<text x="16" y="21" text-anchor="middle" '
            f'font-family="Bebas Neue, sans-serif" font-size="13" '
            f'font-weight="700" fill="#0a0c12">{division}</text>'
        )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
        f'style="vertical-align:middle;flex:none">'
        f"<defs>"
        f'<linearGradient id="{gid}" x1="16" y1="2" x2="16" y2="30" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{light}"/><stop offset="1" stop-color="{dark}"/>'
        f"</linearGradient>"
        f'<linearGradient id="{sid}" x1="6" y1="4" x2="26" y2="14" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="#fff" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        f"</linearGradient>"
        f"</defs>"
        # 방패 본체
        f'<path d="M16 2.5 27 7v9c0 6.3-4.8 10.7-11 13.5C9.8 26.7 5 22.3 5 16V7z" '
        f'fill="url(#{gid})"/>'
        # 상단 광택
        f'<path d="M16 2.5 27 7v4.5C22.6 8.8 19.4 7.6 16 7.6S9.4 8.8 5 11.5V7z" '
        f'fill="url(#{sid})"/>'
        # 테두리
        f'<path d="M16 2.5 27 7v9c0 6.3-4.8 10.7-11 13.5C9.8 26.7 5 22.3 5 16V7z" '
        f'fill="none" stroke="{light}" stroke-width="1" stroke-opacity=".55"/>'
        f"{numeral}"
        f"</svg>"
    )


# ═══════════════════════════════════════════════════════
# 2. 포지션(역할) 아이콘 — 돌격 / 공격 / 지원
# ═══════════════════════════════════════════════════════
# 블리자드 공식 아이콘을 복제하지 않고, 같은 의미가 읽히는 기하 도형으로 새로 그렸다.
# 방패=탱킹, 조준선=딜, 십자=힐 은 장르 전반의 관용 기호라 학습 없이 이해된다.
ROLE_COLORS: dict[str, str] = {
    "돌격": "#60a5fa",   # 정보/방어 = 파랑
    "공격": "#f87171",   # 위험/화력 = 빨강
    "지원": "#34d399",   # 성능/회복 = 초록
}


def role_icon(role: str, size: int = 18, color: str | None = None) -> str:
    """
    role: "돌격" | "공격" | "지원" | "전체"
    color: None이면 역할별 기본색. 세그먼트 컨트롤에서는
           "currentColor"를 넘겨 활성/비활성 색을 CSS로 제어하는 편이 낫다.
    """
    c = color or ROLE_COLORS.get(role, "#9ca3af")
    head = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{c}" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:middle;flex:none">'
    )

    if role == "돌격":
        # 방패
        body = (
            '<path d="M12 3 4.5 6v6c0 5 3.1 8.3 7.5 10 4.4-1.7 7.5-5 7.5-10V6z"/>'
            '<path d="M12 8.5v7" stroke-opacity=".55"/>'
        )
    elif role == "공격":
        # 조준선
        body = (
            '<circle cx="12" cy="12" r="7"/>'
            '<path d="M12 2.5v3.2M12 18.3v3.2M2.5 12h3.2M18.3 12h3.2"/>'
            f'<circle cx="12" cy="12" r="1.6" fill="{c}" stroke="none"/>'
        )
    elif role == "지원":
        # 십자
        body = '<path d="M12 4.5v15M4.5 12h15"/>'
    else:
        # 전체 — 세 역할을 삼각 배치한 중립 기호
        body = (
            '<circle cx="12" cy="6.5" r="2.6"/>'
            '<circle cx="6.5" cy="16.5" r="2.6"/>'
            '<circle cx="17.5" cy="16.5" r="2.6"/>'
        )

    return head + body + "</svg>"


# ═══════════════════════════════════════════════════════
# 3. S / A / B / C / D 랭크 뱃지
# ═══════════════════════════════════════════════════════
# 오버워치에 이런 등급은 없다. 티어리스트 관용 표기이므로 구할 에셋 자체가 없고,
# 직접 만드는 것이 유일한 방법이자 저작권상 가장 안전한 방법이다.
RANK_COLORS: dict[str, str] = {
    "S": "#ff4655",
    "A": "#f59e0b",
    "B": "#34d399",
    "C": "#60a5fa",
    "D": "#8b93a7",
}


def rank_badge(rank: str, size: int = 26) -> str:
    """육각형 랭크 뱃지. 표 행·HERO 카드 공용."""
    c = RANK_COLORS.get(rank, RANK_COLORS["D"])
    gid = _nid("rg")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
        f'style="vertical-align:middle;flex:none">'
        f"<defs>"
        f'<linearGradient id="{gid}" x1="16" y1="2" x2="16" y2="30" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="{c}" stop-opacity=".34"/>'
        f'<stop offset="1" stop-color="{c}" stop-opacity=".08"/>'
        f"</linearGradient></defs>"
        f'<path d="M16 1.8 28 8.6v14.8L16 30.2 4 23.4V8.6z" '
        f'fill="url(#{gid})" stroke="{c}" stroke-width="1.4"/>'
        f'<text x="16" y="21.4" text-anchor="middle" '
        f'font-family="Bebas Neue, sans-serif" font-size="15" '
        f'font-weight="700" fill="{c}">{rank}</text>'
        f"</svg>"
    )


# ═══════════════════════════════════════════════════════
# 4. 부속 — 델타 화살표, 즐겨찾기 하트
# ═══════════════════════════════════════════════════════
# 시계열 페이지의 "▲ 4.7%" 텍스트 화살표와 HEROES 카드의 ♡ 이모지를 대체한다.

def delta_arrow(up: bool, size: int = 8) -> str:
    c = "#34d399" if up else "#f87171"
    pts = "5,1 9.5,8 0.5,8" if up else "5,9 9.5,2 0.5,2"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 10 10" '
        f'style="vertical-align:baseline;flex:none">'
        f'<polygon points="{pts}" fill="{c}"/></svg>'
    )


def heart_icon(filled: bool = False, size: int = 16) -> str:
    c = "#ff4655" if filled else "rgba(255,255,255,.42)"
    fill = c if filled else "none"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{c}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:middle;flex:none">'
        f'<path d="M12 20.3 3.9 12.4a5 5 0 0 1 7.1-7.1l1 1 1-1a5 5 0 0 1 7.1 7.1z"/>'
        f"</svg>"
    )


# ═══════════════════════════════════════════════════════
# 5. 앱 연결 어댑터
# ═══════════════════════════════════════════════════════
# 이 모듈은 한글 티어/역할명을 키로 쓰고, 앱 내부는 영문 키("Gold", "Tank")를 쓴다.
# 호출부가 매번 변환하지 않도록 여기서 흡수한다.
#
# 원래 파일에 있던 tier_option_label / role_option_label(섹션 5)은 제거했다.
# st.selectbox / st.segmented_control 의 옵션은 평문만 받아서 SVG 가 그대로
# 문자열로 노출된다(브라우저에서 확인). 위젯 라벨에는 쓸 수 없다.

_TIER_KO = {
    "All": "전체", "Bronze": "브론즈", "Silver": "실버", "Gold": "골드",
    "Platinum": "플래티넘", "Emerald": "에메랄드", "Diamond": "다이아몬드",
    "Master": "마스터", "Grandmaster": "그랜드마스터", "Champion": "챔피언",
}
_ROLE_KO = {"All": "전체", "Tank": "돌격", "Damage": "공격", "Support": "지원"}


def tier_badge_for(tier_key: str, **kwargs) -> str:
    """영문 티어 키로 방패 뱃지를 얻는다."""
    return tier_badge(_TIER_KO.get(tier_key, tier_key), **kwargs)


def tier_pip_for(tier_key: str, **kwargs) -> str:
    return tier_pip(_TIER_KO.get(tier_key, tier_key), **kwargs)


def role_icon_for(role_key: str, **kwargs) -> str:
    return role_icon(_ROLE_KO.get(role_key, role_key), **kwargs)
