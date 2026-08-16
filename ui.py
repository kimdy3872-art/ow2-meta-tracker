from __future__ import annotations

import html

import streamlit as st

GLOBAL_BG_COLOR = "#0c0f1a"
GLOBAL_TEXT_COLOR = "#eceffc"
GLOBAL_SURFACE_COLOR = "#161a2b"
GLOBAL_SURFACE_ALT_COLOR = "#1d2236"
GLOBAL_BORDER_COLOR = "#2f3552"
GLOBAL_MUTED_TEXT_COLOR = "#9ba2c4"
# 브랜드 액센트. 시맨틱 색(위험 #f87171)과 겹치지 않도록 마젠타 쪽으로 기울인 크림슨.
GLOBAL_ACCENT_COLOR = "#ff4d6a"
GLOBAL_FONT_FAMILY = "'SUIT Variable', 'Pretendard Variable', 'Noto Sans KR', 'Apple SD Gothic Neo', 'Segoe UI', sans-serif"
# 디스플레이용 콘덴스드 폰트. Oswald 에는 한글이 없어서 한글은 자동으로 SUIT 로 폴백되고
# 라틴/숫자만 콘덴스드로 잡힌다 - 레퍼런스의 대문자 타이포 느낌을 한글 가독성 손해 없이 낸다.
GLOBAL_DISPLAY_FONT_FAMILY = "'Oswald', 'SUIT Variable', 'Pretendard Variable', 'Noto Sans KR', sans-serif"
GLOBAL_RADIUS_SM = "8px"
GLOBAL_RADIUS_MD = "10px"
GLOBAL_RADIUS_LG = "12px"
GLOBAL_GOOD_COLOR = "#34d399"
GLOBAL_INFO_COLOR = "#60a5fa"
GLOBAL_DANGER_COLOR = "#f87171"
GLOBAL_WARN_COLOR = "#fbbf24"

# 차트용 토큰. 앱 프레임이 그라데이션이라 차트 배경을 단색으로 칠하면 그 부분만 판때기처럼
# 떠 보인다. paper 는 투명으로 두고 플롯 영역만 아주 옅게 띄운다.
GLOBAL_CHART_PLOT_BG = "rgba(255, 255, 255, 0.022)"
GLOBAL_CHART_GRID_COLOR = "rgba(148, 150, 190, 0.15)"
GLOBAL_CHART_AXIS_COLOR = "rgba(148, 150, 190, 0.34)"
# zeroline 을 액센트 색으로 두면 3D 씬 축에 빨간 선이 그어져 경고처럼 읽힌다. 중립색 유지.
GLOBAL_CHART_ZERO_COLOR = "rgba(168, 170, 205, 0.32)"
GLOBAL_RANK_COLORS = {
    "S": "#ef4444",
    "A": "#f59e0b",
    "B": "#22c55e",
    "C": GLOBAL_INFO_COLOR,
    "D": "#94a3b8",
}


def apply_global_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/static/woff2/SUIT.css');
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap');

        :root,
        [data-theme="light"],
        [data-theme="dark"] {{
            color-scheme: dark !important;
            --app-bg: {GLOBAL_BG_COLOR};
            --app-surface: {GLOBAL_SURFACE_COLOR};
            --app-surface-alt: {GLOBAL_SURFACE_ALT_COLOR};
            --app-border: {GLOBAL_BORDER_COLOR};
            --app-text: {GLOBAL_TEXT_COLOR};
            --app-muted: {GLOBAL_MUTED_TEXT_COLOR};
            --app-accent: {GLOBAL_ACCENT_COLOR};
            --app-font: {GLOBAL_FONT_FAMILY};
            --app-display-font: {GLOBAL_DISPLAY_FONT_FAMILY};
            --app-radius-sm: {GLOBAL_RADIUS_SM};
            --app-radius-md: {GLOBAL_RADIUS_MD};
            --app-radius-lg: {GLOBAL_RADIUS_LG};
            --app-good: {GLOBAL_GOOD_COLOR};
            --app-info: {GLOBAL_INFO_COLOR};
            --app-danger: {GLOBAL_DANGER_COLOR};
            --app-warn: {GLOBAL_WARN_COLOR};
            --app-menu-bg: #12162a;
            --app-menu-surface: #191e35;
            --app-menu-hover: #242a49;
            --app-menu-selected: #4a2440;
            --app-menu-text: #f2f4ff;
            --app-menu-muted: #a9b0d0;
            --app-menu-border: #3d4468;
            --primary-color: {GLOBAL_ACCENT_COLOR};
            --background-color: {GLOBAL_BG_COLOR};
            --secondary-background-color: {GLOBAL_SURFACE_COLOR};
            --text-color: {GLOBAL_TEXT_COLOR};
            --font: {GLOBAL_FONT_FAMILY};
        }}

        /* 페이지 바닥은 라벤더 그라데이션. 그 위에 어두운 앱 프레임이 떠 있는 구조라
           레퍼런스처럼 "화면"이 아니라 "기기"처럼 읽힌다. */
        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(1300px 760px at 10% -14%, rgba(206, 192, 244, 0.85), transparent 58%),
                radial-gradient(1000px 620px at 96% 4%, rgba(150, 128, 208, 0.55), transparent 62%),
                linear-gradient(158deg, #a08fd2 0%, #8877c0 46%, #63549a 100%) !important;
            background-attachment: fixed !important;
            color: var(--app-text) !important;
            font-family: var(--app-font) !important;
        }}

        [data-testid="stMain"],
        section.main {{
            background: transparent !important;
        }}

        header[data-testid="stHeader"],
        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

        /* Streamlit 기본 페이지 목록만 숨긴다. 네비게이션은 render_sidebar_navigation 이 직접 그린다.
           접기 버튼은 남겨둔다 - 좁은 화면에서 사이드바가 본문을 덮는데 닫을 방법이 없으면 갇힌다. */
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        [data-testid="stSidebarCollapseButton"] button {{
            color: var(--app-muted) !important;
        }}

        /* 사이드바도 라벤더 위에 떠 있는 카드로. 메인 프레임과 같은 재질을 쓴다. */
        [data-testid="stSidebar"] {{
            background: transparent !important;
            width: 268px !important;
            min-width: 268px !important;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background:
                radial-gradient(420px 260px at 50% 0%, rgba(255, 77, 106, 0.12), transparent 68%),
                linear-gradient(180deg, #11141f 0%, #0a0d16 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 22px;
            margin: 1.5rem 0 2.6rem 1.2rem;
            box-shadow:
                0 2px 0 rgba(255, 255, 255, 0.06) inset,
                0 40px 80px rgba(28, 16, 56, 0.5);
        }}

        [data-testid="stSidebarUserContent"] {{
            padding: 20px 14px 18px !important;
        }}

        .ow-nav-brand {{
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 0 6px 16px;
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        }}

        .ow-nav-brand-mark {{
            display: grid;
            place-items: center;
            width: 38px;
            height: 38px;
            flex-shrink: 0;
            border-radius: 11px;
            background: linear-gradient(135deg, #a8123a, #ff4d6a);
            color: #fff;
            font-family: var(--app-display-font);
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            box-shadow: 0 6px 16px rgba(196, 24, 66, 0.45);
        }}

        .ow-nav-brand-title {{
            font-family: var(--app-display-font);
            color: #f6f7ff;
            font-size: 0.98rem;
            font-weight: 600;
            letter-spacing: 0.09em;
            line-height: 1.1;
        }}

        .ow-nav-brand-sub {{
            color: var(--app-muted);
            font-size: 0.72rem;
            font-weight: 600;
            margin-top: 2px;
        }}

        .ow-nav-section {{
            color: rgba(155, 162, 196, 0.72);
            font-family: var(--app-display-font);
            font-size: 0.68rem;
            font-weight: 500;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            padding: 0 8px;
            margin: 14px 0 4px;
        }}

        /* page_link 를 사이드바 항목처럼 재단장 */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {{
            display: flex;
            align-items: center;
            gap: 11px;
            position: relative;
            padding: 9px 10px 9px 13px !important;
            margin: 2px 0;
            border-radius: 10px;
            background: transparent;
            text-decoration: none !important;
            transition: background 0.16s ease, color 0.16s ease;
        }}

        [data-testid="stSidebar"] [data-testid="stPageLink"] a p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] a span {{
            color: var(--app-muted) !important;
            font-size: 0.9rem !important;
            font-weight: 650 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}

        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover span {{
            color: #e6e8f7 !important;
        }}

        /* 활성 항목: 좌측 크림슨 바 + 강조색 - 레퍼런스 사이드바와 같은 언어 */
        [class*="st-key-ownav-active"] [data-testid="stPageLink"] a {{
            background: linear-gradient(90deg, rgba(255, 77, 106, 0.18), rgba(255, 77, 106, 0.03));
        }}

        [class*="st-key-ownav-active"] [data-testid="stPageLink"] a::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 8px;
            bottom: 8px;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: linear-gradient(180deg, #ff4d6a, #ff7a54);
        }}

        [class*="st-key-ownav-active"] [data-testid="stPageLink"] a p,
        [class*="st-key-ownav-active"] [data-testid="stPageLink"] a span {{
            color: #ff8da0 !important;
            font-weight: 750 !important;
        }}

        .ow-nav-standalone {{
            display: flex;
            align-items: center;
            gap: 9px;
            padding: 9px 10px 9px 13px;
            margin: 2px 0;
            border-radius: 10px;
            color: #ff8da0;
            font-size: 0.9rem;
            font-weight: 700;
            background: linear-gradient(90deg, rgba(255, 77, 106, 0.18), rgba(255, 77, 106, 0.03));
        }}

        .ow-nav-standalone-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #ff4d6a;
            flex-shrink: 0;
        }}

        .ow-nav-foot {{
            margin-top: 18px;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
        }}

        .ow-nav-foot-value {{
            color: #e6e8f7;
            font-family: var(--app-display-font);
            font-size: 0.94rem;
            font-weight: 500;
            padding: 0 8px;
        }}

        /* 떠 있는 앱 프레임 */
        .block-container,
        [data-testid="stMainBlockContainer"] {{
            max-width: 1340px;
            margin: 1.5rem auto 2.6rem !important;
            /* 사이드바 카드와 사이 간격 */
            margin-left: 1.2rem !important;
            margin-right: 1.2rem !important;
            padding: 2.4rem 2.3rem 2.6rem !important;
            border-radius: 26px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            background:
                radial-gradient(900px 420px at 92% -6%, rgba(255, 77, 106, 0.10), transparent 62%),
                linear-gradient(180deg, #11141f 0%, #0a0d16 100%);
            box-shadow:
                0 2px 0 rgba(255, 255, 255, 0.06) inset,
                0 48px 90px rgba(28, 16, 56, 0.55),
                0 12px 28px rgba(28, 16, 56, 0.35);
        }}

        h1, h2, h3, h4, p, span, div, label, li, a, summary, input, select, button, table, th, td {{
            font-family: var(--app-font) !important;
        }}

        /* 디스플레이 타이포. 위 blanket 규칙보다 뒤에 와야 이긴다(동일 명시도, 나중 선언 승). */
        h1, h2, h3,
        .ow-hero-title,
        .ow-hero-badge,
        .ow-control-title,
        .ow-hero-banner-name,
        .ow-hero-banner-num,
        .ow-hero-banner-kicker,
        .ow-hero-banner-stat-value,
        .overwatch-table th,
        .rank-pill,
        [data-testid="stMetricValue"] {{
            font-family: var(--app-display-font) !important;
        }}

        h1, h2, h3 {{
            text-transform: uppercase;
            letter-spacing: 0.01em;
        }}

        .material-symbols-rounded,
        .material-symbols-outlined,
        .material-icons,
        [class*="material-symbols"],
        [class*="material-icons"],
        [data-testid="stIconMaterial"] {{
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
        }}

        h1 {{
            font-size: clamp(1.8rem, 1.2rem + 1.8vw, 2.7rem) !important;
            font-weight: 780 !important;
            letter-spacing: -0.02em;
        }}

        h2 {{
            font-size: clamp(1.2rem, 1rem + 0.8vw, 1.7rem) !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }}

        [data-testid="stMetric"] {{
            border: 1px solid var(--app-border);
            border-radius: var(--app-radius-lg);
            padding: 10px 12px;
            background: linear-gradient(180deg, rgba(30,28,50,0.9), rgba(14,13,24,0.94));
            box-shadow: 0 10px 20px rgba(2, 6, 23, 0.25);
        }}

        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"] {{
            color: var(--app-text) !important;
        }}

        .stButton > button,
        div[data-testid="stButton"] > button,
        button[data-testid^="stBaseButton-"] {{
            border-radius: 12px !important;
            border: 1px solid var(--app-border) !important;
            min-height: 44px !important;
            background: linear-gradient(180deg, rgba(30,28,50,0.95), rgba(18,17,30,0.95)) !important;
            color: var(--app-text) !important;
            font-size: 0.92rem !important;
            font-weight: 760 !important;
            letter-spacing: 0.01em !important;
            transition: all 0.18s ease;
        }}

        .stButton > button:hover,
        div[data-testid="stButton"] > button:hover {{
            border-color: rgba(255, 77, 106, 0.55) !important;
            transform: translateY(-1px);
        }}

        .stButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"] {{
            background: linear-gradient(135deg, #a8123a 0%, #e0284f 52%, #ff4d6a 100%) !important;
            border-color: rgba(255, 138, 140, 0.7) !important;
            color: #fff5f7 !important;
            box-shadow: 0 0 0 1px rgba(255, 122, 140, 0.28), 0 8px 20px rgba(196, 24, 66, 0.34) !important;
        }}

        [data-testid="stWidgetLabel"] {{
            margin-bottom: 0.36rem !important;
        }}

        [data-testid="stWidgetLabel"] p {{
            color: var(--app-muted) !important;
            font-size: 0.76rem !important;
            font-weight: 820 !important;
            letter-spacing: 0.06em !important;
            line-height: 1.15 !important;
        }}

        .stSelectbox,
        .stMultiSelect,
        .stTextInput,
        .stSlider {{
            margin-bottom: 0.35rem !important;
        }}

        .stSelectbox [data-baseweb="select"],
        .stMultiSelect [data-baseweb="select"] {{
            background: transparent !important;
        }}

        .stSelectbox [data-baseweb="select"] [data-baseweb="popover"],
        .stMultiSelect [data-baseweb="select"] [data-baseweb="popover"] {{
            color-scheme: dark !important;
        }}

        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div,
        [data-baseweb="input"],
        [data-testid="stTextInputRootElement"],
        [data-baseweb="input"] > div,
        .stTextArea textarea,
        .stNumberInput input {{
            border-radius: 12px !important;
            border: 1px solid rgba(100, 94, 140, 0.75) !important;
            min-height: 44px !important;
            background: linear-gradient(180deg, rgba(30,28,50,0.96), rgba(16,15,26,0.96)) !important;
            color: var(--app-text) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 18px rgba(2,6,23,0.16) !important;
            transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease !important;
        }}

        .stTextInput [data-baseweb="input"] > div,
        .stTextInput div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"] > div {{
            border: 1px solid rgba(100, 94, 140, 0.75) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            background: transparent !important;
        }}

        .stSelectbox [data-baseweb="select"] *,
        .stMultiSelect [data-baseweb="select"] *,
        .stTextInput input,
        .stTextInput input:focus,
        .stTextInput input:focus-visible {{
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
            color: var(--app-text) !important;
            -webkit-text-fill-color: var(--app-text) !important;
            font-size: 0.94rem !important;
            font-weight: 650 !important;
        }}

        .stTextInput input::placeholder,
        [data-baseweb="select"] input::placeholder {{
            color: rgba(143, 167, 204, 0.78) !important;
            -webkit-text-fill-color: rgba(143, 167, 204, 0.78) !important;
        }}

        .stSelectbox [data-baseweb="select"]:focus-within > div,
        .stMultiSelect [data-baseweb="select"]:focus-within > div,
        [data-baseweb="input"]:focus-within > div,
        [data-baseweb="input"]:focus-within,
        [data-testid="stTextInputRootElement"]:focus-within,
        [data-baseweb="input"] > div:focus-within,
        .stTextInput div[data-baseweb="input"]:focus-within > div {{
            border-color: var(--app-accent) !important;
            box-shadow: 0 0 0 1px rgba(255, 77, 106, 0.45), 0 10px 22px rgba(2,6,23,0.22) !important;
            outline: none !important;
        }}

        .stTextInput input:-webkit-autofill,
        .stTextInput input:-webkit-autofill:hover,
        .stTextInput input:-webkit-autofill:focus {{
            -webkit-text-fill-color: var(--app-text) !important;
            -webkit-box-shadow: 0 0 0 1000px rgba(13, 23, 42, 0.92) inset !important;
            transition: background-color 9999s ease-out 0s !important;
        }}

        .stSelectbox svg,
        .stMultiSelect svg,
        [data-baseweb="select"] svg {{
            color: var(--app-muted) !important;
            fill: var(--app-muted) !important;
        }}

        body [data-baseweb="popover"],
        body [data-baseweb="popover"] > div,
        body [data-baseweb="popover"] > div > div,
        body [data-baseweb="popover"] [data-baseweb],
        body [data-baseweb="popover"] [data-baseweb="menu"],
        body [data-baseweb="popover"] [data-baseweb="select-dropdown"],
        body [data-baseweb="popover"] [role="listbox"],
        body [data-baseweb="popover"] ul,
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        div[data-baseweb="popover"] [role="listbox"] {{
            background: var(--app-menu-bg) !important;
            background-color: var(--app-menu-bg) !important;
            color: var(--app-menu-text) !important;
            color-scheme: dark !important;
        }}

        body [data-baseweb="popover"],
        div[data-baseweb="popover"] {{
            border: 1px solid var(--app-menu-border) !important;
            border-radius: 12px !important;
            color: var(--app-menu-text) !important;
            box-shadow: 0 18px 38px rgba(2, 6, 23, 0.5) !important;
            overflow: hidden !important;
        }}

        body [data-baseweb="popover"] [role="option"],
        body [data-baseweb="popover"] [data-baseweb="menu"] li,
        body [data-baseweb="popover"] li,
        div[data-baseweb="popover"] [role="option"],
        div[data-baseweb="popover"] li {{
            background: var(--app-menu-bg) !important;
            background-color: var(--app-menu-bg) !important;
            color: var(--app-menu-text) !important;
            font-size: 0.92rem !important;
            font-weight: 620 !important;
        }}

        body [data-baseweb="popover"] [role="option"] *,
        body [data-baseweb="popover"] [data-baseweb="menu"] li *,
        body [data-baseweb="popover"] li *,
        div[data-baseweb="popover"] [role="option"] *,
        div[data-baseweb="popover"] li * {{
            color: var(--app-menu-text) !important;
            -webkit-text-fill-color: var(--app-menu-text) !important;
            background-color: transparent !important;
        }}

        body [data-baseweb="popover"] [role="option"]:hover,
        body [data-baseweb="popover"] [role="option"]:hover *,
        body [data-baseweb="popover"] [data-highlighted="true"],
        body [data-baseweb="popover"] [data-baseweb="menu"] li:hover,
        body [data-baseweb="popover"] li:hover,
        div[data-baseweb="popover"] [role="option"]:hover,
        div[data-baseweb="popover"] li:hover {{
            background: var(--app-menu-hover) !important;
            background-color: var(--app-menu-hover) !important;
        }}

        body [data-baseweb="popover"] [aria-selected="true"],
        body [data-baseweb="popover"] [role="option"][aria-selected="true"],
        div[data-baseweb="popover"] [aria-selected="true"],
        div[data-baseweb="popover"] [role="option"][aria-selected="true"] {{
            background: var(--app-menu-selected) !important;
            background-color: var(--app-menu-selected) !important;
            color: #ffffff !important;
        }}

        body [data-baseweb="popover"] [aria-selected="true"] *,
        div[data-baseweb="popover"] [aria-selected="true"] * {{
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }}

        body [data-baseweb="popover"] input,
        div[data-baseweb="popover"] input {{
            background: var(--app-menu-surface) !important;
            background-color: var(--app-menu-surface) !important;
            color: var(--app-menu-text) !important;
            -webkit-text-fill-color: var(--app-menu-text) !important;
        }}

        body [data-baseweb="popover"] input::placeholder,
        div[data-baseweb="popover"] input::placeholder {{
            color: var(--app-menu-muted) !important;
            -webkit-text-fill-color: var(--app-menu-muted) !important;
        }}

        body [data-baseweb="popover"] ::-webkit-scrollbar-thumb {{
            background: #5d7192 !important;
            border-radius: 999px !important;
        }}

        body [data-baseweb="popover"] ::-webkit-scrollbar-track {{
            background: var(--app-menu-surface) !important;
        }}

        .stMultiSelect [data-baseweb="tag"] {{
            border: 1px solid rgba(255, 122, 140, 0.42) !important;
            border-radius: 999px !important;
            background: rgba(255, 77, 106, 0.14) !important;
            color: #ffd9e0 !important;
        }}

        .stMultiSelect [data-baseweb="tag"] span {{
            color: #ffd9e0 !important;
            font-size: 0.82rem !important;
            font-weight: 760 !important;
        }}

        [data-testid="stSlider"] [role="slider"] {{
            background: var(--app-accent) !important;
            border: 2px solid #ffe3e8 !important;
            box-shadow: 0 0 0 5px rgba(255, 77, 106, 0.18) !important;
        }}

        .ow-filter-action-spacer {{
            height: 1.52rem;
        }}

        .ow-control-band {{
            border: 1px solid rgba(92, 86, 132, 0.7);
            border-radius: var(--app-radius-lg);
            background:
                linear-gradient(180deg, rgba(26, 24, 44, 0.84), rgba(14, 13, 24, 0.9));
            padding: 13px 14px 10px;
            margin: 0 0 12px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
        }}

        .ow-control-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 9px;
        }}

        .ow-control-title {{
            color: var(--app-text);
            font-size: 0.84rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}

        .ow-control-meta {{
            color: var(--app-muted);
            font-size: 0.78rem;
            font-weight: 680;
        }}

        .ow-soft-divider {{
            height: 1px;
            background: rgba(92, 86, 132, 0.42);
            margin: 10px 0 12px;
        }}

        .ow-panel-card {{
            border: 1px solid var(--app-border);
            border-radius: var(--app-radius-lg);
            background: linear-gradient(180deg, var(--app-surface) 0%, #13121f 100%);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        }}

        [data-testid="stExpander"] > details {{
            border: 1px solid var(--app-border) !important;
            border-radius: var(--app-radius-lg) !important;
            background: rgba(16, 15, 27, 0.86) !important;
        }}

        [data-testid="stExpander"] > details > summary,
        [data-testid="stExpander"] > details[open] > summary,
        [data-testid="stExpander"] > details > summary:hover,
        [data-testid="stExpander"] > details > summary:focus-visible {{
            background: transparent !important;
            color: var(--app-text) !important;
            -webkit-text-fill-color: var(--app-text) !important;
        }}

        [data-testid="stExpander"] > details > summary * {{
            color: var(--app-text) !important;
            -webkit-text-fill-color: var(--app-text) !important;
            background: transparent !important;
        }}

        [data-testid="stDivider"] {{
            border-color: rgba(92, 86, 132, 0.5) !important;
        }}

        .ow-hero-wrap {{
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 18px;
            padding: 20px 22px;
            overflow: hidden;
            background:
                radial-gradient(680px 300px at 100% 0%, rgba(255, 77, 106, 0.22), transparent 66%),
                linear-gradient(120deg, #1c1930 0%, #12111f 58%, #0c0d16 100%);
            box-shadow: 0 18px 30px rgba(10, 6, 24, 0.45);
            margin-bottom: 0.9rem;
        }}

        /* 좌측 액센트 바 - 레퍼런스 사이드바의 활성 표시와 같은 언어 */
        .ow-hero-wrap::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 16px;
            bottom: 16px;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: linear-gradient(180deg, #ff4d6a, #ff7a54);
        }}

        .ow-hero-badge {{
            display: inline-block;
            border-radius: 999px;
            border: 1px solid rgba(255, 122, 140, 0.5);
            background: rgba(255, 77, 106, 0.12);
            color: #ffb3c1;
            padding: 4px 11px;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 9px;
            font-weight: 600;
        }}

        .ow-hero-title {{
            font-size: clamp(1.6rem, 1.2rem + 1.6vw, 2.6rem);
            font-weight: 700;
            color: #f6f7ff;
            line-height: 1.1;
            letter-spacing: -0.01em;
            margin: 0 0 6px 0;
        }}

        .ow-hero-sub {{
            color: var(--app-muted);
            margin: 0;
            font-size: 0.95rem;
        }}

        /* --- 히어로 배너 -------------------------------------------------
           컷아웃이 카드 위쪽으로 넘쳐야 해서 래퍼에 상단 패딩을 주고
           카드는 그 안에서 overflow: visible 로 둔다. */
        .ow-hero-banner {{
            position: relative;
            padding-top: 46px;
            margin: 0 0 18px;
        }}

        /* 컷아웃이 없으면 위로 넘칠 것도 없으므로 여백을 남기지 않는다 */
        .ow-hero-banner:not(.has-cutout) {{
            padding-top: 0;
        }}

        .ow-hero-banner-card {{
            position: relative;
            border-radius: 22px;
            min-height: 236px;
            padding: 26px 30px 24px;
            overflow: hidden;
            isolation: isolate;
            box-shadow: 0 26px 48px rgba(2, 6, 23, 0.55);
        }}

        /* 배경: 스플래시 아트를 우측에 앉히고 좌->우 스크림으로 덮는다 */
        .ow-hero-banner-bg {{
            position: absolute;
            inset: 0;
            z-index: -2;
            background-size: cover;
            background-repeat: no-repeat;
            filter: saturate(1.05);
        }}

        /* 스크림. 우측 끝을 투명하게 두면 밝은 배경 아트가 그대로 드러나
           어두운 페이지 위에서 카드만 떠 보인다. 우측도 어둡게 닫아준다. */
        .ow-hero-banner-card::after {{
            content: "";
            position: absolute;
            inset: 0;
            z-index: -1;
            background: linear-gradient(
                100deg,
                rgba(146, 18, 66, 0.98) 0%,
                rgba(150, 22, 72, 0.92) 32%,
                rgba(110, 20, 68, 0.58) 58%,
                rgba(44, 12, 38, 0.62) 82%,
                rgba(18, 10, 26, 0.80) 100%
            );
        }}

        /* 컷아웃이 있을 때는 배경 아트를 강하게 블러 + 감광해 인물 중복을 피한다 */
        .ow-hero-banner.has-cutout .ow-hero-banner-bg {{
            filter: blur(26px) saturate(1.05) brightness(0.42);
            transform: scale(1.12);
        }}

        /* 컷아웃 bbox 에는 뻗은 무기까지 들어가 가로가 길다. contain 으로 두면 폭 제약에
           걸려 인물이 작아지므로 박스를 넉넉히 주고 우측 하단에 붙인다. 좌측으로 뻗는
           무기는 마스크로 부드럽게 날려 텍스트와 충돌하지 않게 한다. */
        .ow-hero-cutout {{
            position: absolute;
            right: -10px;
            top: 0;
            bottom: 0;
            height: 100%;
            width: auto;
            max-width: 66%;
            object-fit: contain;
            object-position: bottom right;
            pointer-events: none;
            filter: drop-shadow(0 16px 26px rgba(2, 6, 23, 0.5));
            -webkit-mask-image: linear-gradient(to right, transparent 0%, #000 22%);
            mask-image: linear-gradient(to right, transparent 0%, #000 22%);
        }}

        .ow-hero-banner-num {{
            position: absolute;
            right: 40%;
            top: -2px;
            font-size: clamp(6rem, 4rem + 9vw, 12rem);
            font-weight: 900;
            line-height: 1;
            letter-spacing: -0.03em;
            color: rgba(255, 255, 255, 0.15);
            pointer-events: none;
            user-select: none;
        }}

        .ow-hero-banner-body {{
            position: relative;
            max-width: 62%;
        }}

        .ow-hero-banner-kicker {{
            color: rgba(255, 214, 226, 0.94);
            font-size: 0.74rem;
            font-weight: 850;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }}

        .ow-hero-banner-name {{
            margin: 2px 0 4px;
            color: #ffffff;
            font-size: clamp(2rem, 1.3rem + 2.6vw, 3.4rem);
            font-weight: 900;
            line-height: 1.02;
            letter-spacing: -0.02em;
        }}

        .ow-hero-banner-meta {{
            color: rgba(255, 200, 216, 0.9);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}

        .ow-hero-banner-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 26px;
            margin-top: 20px;
        }}

        .ow-hero-banner-stat-label {{
            color: rgba(255, 190, 210, 0.88);
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.11em;
            text-transform: uppercase;
        }}

        .ow-hero-banner-stat-value {{
            color: #ffffff;
            font-size: 1.45rem;
            font-weight: 880;
            line-height: 1.2;
        }}

        /* --- 영웅 카드 그리드 -------------------------------------------
           레퍼런스의 AGENTS 카드와 같은 언어: 세로형 아트 카드 + 하단 스크림 + 이름. */
        .ow-card-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 11px;
            margin: 2px 0 4px;
        }}

        .ow-card {{
            position: relative;
            display: block;
            height: 188px;
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: #12141f;
            text-decoration: none !important;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }}

        .ow-card:hover {{
            transform: translateY(-3px);
            border-color: rgba(255, 122, 140, 0.5);
            box-shadow: 0 16px 30px rgba(10, 6, 24, 0.55);
        }}

        /* 1위 카드는 레퍼런스의 강조 카드처럼 액센트 글로우를 준다 */
        .ow-card.featured {{
            border-color: rgba(255, 77, 106, 0.62);
            box-shadow: 0 0 0 1px rgba(255, 77, 106, 0.28), 0 16px 34px rgba(120, 10, 40, 0.42);
        }}

        .ow-card-art {{
            position: absolute;
            inset: 0;
            background-size: cover;
            background-repeat: no-repeat;
            transition: transform 0.35s ease;
        }}

        .ow-card:hover .ow-card-art {{
            transform: scale(1.06);
        }}

        .ow-card-art::after {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(
                180deg,
                rgba(10, 8, 20, 0.10) 0%,
                rgba(10, 8, 20, 0.30) 42%,
                rgba(9, 7, 17, 0.86) 78%,
                rgba(8, 6, 15, 0.96) 100%
            );
        }}

        .ow-card-rank {{
            position: absolute;
            top: 9px;
            right: 9px;
            min-width: 26px;
            height: 26px;
            display: grid;
            place-items: center;
            padding: 0 6px;
            border-radius: 8px;
            font-family: var(--app-display-font);
            font-size: 0.9rem;
            font-weight: 600;
            color: #fff;
            background: rgba(10, 8, 20, 0.62);
            border: 1px solid currentColor;
            backdrop-filter: blur(3px);
        }}

        .ow-card-body {{
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            padding: 11px 12px 12px;
        }}

        .ow-card-metric {{
            font-family: var(--app-display-font);
            font-size: 1.5rem;
            font-weight: 600;
            line-height: 1;
            letter-spacing: -0.01em;
        }}

        .ow-card-name {{
            color: #ffffff;
            font-size: 0.98rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 3px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .ow-card-sub {{
            color: rgba(226, 228, 245, 0.66);
            font-size: 0.74rem;
            font-weight: 650;
            margin-top: 1px;
        }}

        /* --- 우측 요약 패널 ---------------------------------------------- */
        .ow-rail {{
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 15px;
            background: linear-gradient(180deg, #171a28 0%, #101320 100%);
            padding: 14px 15px 15px;
            height: 188px;
            display: flex;
            flex-direction: column;
        }}

        .ow-rail-title {{
            font-family: var(--app-display-font);
            color: rgba(155, 162, 196, 0.86);
            font-size: 0.68rem;
            font-weight: 500;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}

        .ow-rail-row {{
            display: flex;
            align-items: center;
            gap: 9px;
            margin-bottom: 7px;
        }}

        .ow-rail-key {{
            font-family: var(--app-display-font);
            font-size: 0.92rem;
            font-weight: 600;
            width: 15px;
            flex-shrink: 0;
        }}

        .ow-rail-bar {{
            flex: 1;
            height: 7px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.07);
            overflow: hidden;
        }}

        .ow-rail-fill {{
            height: 100%;
            border-radius: 999px;
        }}

        .ow-rail-count {{
            color: #e2e4f5;
            font-family: var(--app-display-font);
            font-size: 0.88rem;
            font-weight: 500;
            width: 22px;
            text-align: right;
            flex-shrink: 0;
        }}

        .ow-rail-foot {{
            margin-top: auto;
            padding-top: 9px;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
            color: var(--app-muted);
            font-size: 0.74rem;
            font-weight: 650;
        }}

        @media (max-width: 1100px) {{
            .ow-card-grid {{grid-template-columns: repeat(2, minmax(0, 1fr));}}
        }}

        @media (max-width: 560px) {{
            .ow-card-grid {{grid-template-columns: 1fr;}}
            .ow-card, .ow-rail {{height: 160px;}}
        }}

        @media (max-width: 900px) {{
            .ow-hero-banner {{ padding-top: 0; }}
            .ow-hero-banner-body {{ max-width: 100%; }}
            .ow-hero-cutout {{ display: none; }}
            .ow-hero-banner-num {{ right: 6%; opacity: 0.7; }}
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-top: 1.2rem !important;
            }}
            .ow-control-head {{
                display: block;
            }}
            .ow-control-meta {{
                margin-top: 3px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        cutout_html = (
            f"<img class='ow-hero-cutout' alt='' aria-hidden='true' "
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


def _axis_theme(**overrides):
    axis = dict(
        gridcolor=GLOBAL_CHART_GRID_COLOR,
        zerolinecolor=GLOBAL_CHART_ZERO_COLOR,
        linecolor=GLOBAL_CHART_AXIS_COLOR,
        tickcolor=GLOBAL_CHART_AXIS_COLOR,
        tickfont=dict(family=GLOBAL_DISPLAY_FONT_FAMILY, size=12,
                      color=GLOBAL_MUTED_TEXT_COLOR),
        title=dict(font=dict(family=GLOBAL_FONT_FAMILY, size=12,
                             color=GLOBAL_MUTED_TEXT_COLOR)),
    )
    axis.update(overrides)
    return axis


def style_chart(fig, title: str = "", height: int | None = None, scene: bool = False):
    """모든 Plotly 차트에 같은 테마를 입힌다.

    페이지마다 배경·그리드 색을 따로 적으면 팔레트를 바꿀 때마다 어긋나므로 여기로 모은다.
    scene=True 는 3D(scatter_3d)용. 3D 는 xaxis/yaxis 대신 scene 하위에 축이 있다.
    """
    layout = dict(
        font=dict(family=GLOBAL_FONT_FAMILY, size=13, color=GLOBAL_TEXT_COLOR),
        # 앱 프레임의 그라데이션이 비쳐 보이도록 종이 배경은 칠하지 않는다.
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=44 if title else 12, b=10),
        legend=dict(
            bgcolor="rgba(18, 20, 33, 0.82)",
            bordercolor="rgba(148, 150, 190, 0.22)",
            borderwidth=1,
            font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
        ),
        hoverlabel=dict(
            bgcolor="#161a2b",
            bordercolor=GLOBAL_ACCENT_COLOR,
            font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
        ),
    )
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(family=GLOBAL_DISPLAY_FONT_FAMILY, size=19, color=GLOBAL_TEXT_COLOR),
            x=0,
            xanchor="left",
        )
    if height:
        layout["height"] = height

    if scene:
        layout["scene"] = dict(
            xaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
            yaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
            zaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
        )
    else:
        layout["plot_bgcolor"] = GLOBAL_CHART_PLOT_BG
        layout["xaxis"] = _axis_theme(showline=True)
        layout["yaxis"] = _axis_theme(showline=True)

    fig.update_layout(**layout)
    return fig


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
