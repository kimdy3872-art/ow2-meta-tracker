import html

import streamlit as st

GLOBAL_BG_COLOR = "#070b14"
GLOBAL_TEXT_COLOR = "#ecf2ff"
GLOBAL_SURFACE_COLOR = "#0f1728"
GLOBAL_SURFACE_ALT_COLOR = "#121f36"
GLOBAL_BORDER_COLOR = "#2b3f63"
GLOBAL_MUTED_TEXT_COLOR = "#8fa7cc"
GLOBAL_ACCENT_COLOR = "#37d0ff"
GLOBAL_FONT_FAMILY = "'SUIT Variable', 'Pretendard Variable', 'Noto Sans KR', 'Apple SD Gothic Neo', 'Segoe UI', sans-serif"


def apply_global_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/sunn-us/SUIT/fonts/static/woff2/SUIT.css');

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
            --app-menu-bg: #08111f;
            --app-menu-surface: #0d1a2e;
            --app-menu-hover: #172d4d;
            --app-menu-selected: #1d426f;
            --app-menu-text: #f2f7ff;
            --app-menu-muted: #a9bddc;
            --app-menu-border: #3b5f92;
            --primary-color: {GLOBAL_ACCENT_COLOR};
            --background-color: {GLOBAL_BG_COLOR};
            --secondary-background-color: {GLOBAL_SURFACE_COLOR};
            --text-color: {GLOBAL_TEXT_COLOR};
            --font: {GLOBAL_FONT_FAMILY};
        }}

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(1000px 360px at 8% -5%, rgba(48, 95, 255, 0.22), transparent 60%),
                radial-gradient(900px 320px at 90% 0%, rgba(55, 208, 255, 0.16), transparent 64%),
                linear-gradient(180deg, #050912 0%, #070b14 100%) !important;
            color: var(--app-text) !important;
            font-family: var(--app-font) !important;
        }}

        header[data-testid="stHeader"],
        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

        [data-testid="stSidebarNav"],
        [data-testid="stSidebar"],
        [aria-label="Sidebar"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarToggleButton"],
        button[aria-label="Open sidebar"],
        button[aria-label="Close sidebar"] {{
            display: none !important;
        }}

        .block-container {{
            max-width: 1320px;
            padding-top: 2.2rem !important;
            padding-bottom: 2rem !important;
        }}

        h1, h2, h3, h4, p, span, div, label, li, a, summary, input, select, button, table, th, td {{
            font-family: var(--app-font) !important;
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
            border-radius: 16px;
            padding: 10px 12px;
            background: linear-gradient(180deg, rgba(18,31,54,0.88), rgba(9,15,28,0.92));
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
            background: linear-gradient(180deg, rgba(18,31,54,0.95), rgba(13,23,42,0.95)) !important;
            color: var(--app-text) !important;
            font-size: 0.92rem !important;
            font-weight: 760 !important;
            letter-spacing: 0.01em !important;
            transition: all 0.18s ease;
        }}

        .stButton > button:hover,
        div[data-testid="stButton"] > button:hover {{
            border-color: #4f77b5 !important;
            transform: translateY(-1px);
        }}

        .stButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"] {{
            background: linear-gradient(135deg, #1f6dff, #10b8ff) !important;
            border-color: #56d8ff !important;
            color: #f8fbff !important;
            box-shadow: 0 0 0 1px rgba(86, 216, 255, 0.25), 0 8px 20px rgba(16, 184, 255, 0.28) !important;
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
            border: 1px solid rgba(79, 119, 181, 0.72) !important;
            min-height: 44px !important;
            background: linear-gradient(180deg, rgba(18,31,54,0.96), rgba(10,18,33,0.96)) !important;
            color: var(--app-text) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 18px rgba(2,6,23,0.16) !important;
            transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease !important;
        }}

        .stTextInput [data-baseweb="input"] > div,
        .stTextInput div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"] > div {{
            border: 1px solid rgba(79, 119, 181, 0.72) !important;
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
            box-shadow: 0 0 0 1px rgba(55, 208, 255, 0.42), 0 10px 22px rgba(2,6,23,0.22) !important;
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
            border: 1px solid rgba(86, 216, 255, 0.4) !important;
            border-radius: 999px !important;
            background: rgba(55, 208, 255, 0.12) !important;
            color: #dff8ff !important;
        }}

        .stMultiSelect [data-baseweb="tag"] span {{
            color: #dff8ff !important;
            font-size: 0.82rem !important;
            font-weight: 760 !important;
        }}

        [data-testid="stSlider"] [role="slider"] {{
            background: var(--app-accent) !important;
            border: 2px solid #dff8ff !important;
            box-shadow: 0 0 0 5px rgba(55, 208, 255, 0.16) !important;
        }}

        .ow-filter-action-spacer {{
            height: 1.52rem;
        }}

        [data-testid="stExpander"] > details {{
            border: 1px solid var(--app-border) !important;
            border-radius: 12px !important;
            background: rgba(8, 14, 26, 0.86) !important;
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
            border-color: rgba(66, 88, 126, 0.55) !important;
        }}

        .ow-hero-wrap {{
            border: 1px solid var(--app-border);
            border-radius: 18px;
            padding: 18px 20px;
            background:
                linear-gradient(120deg, rgba(23, 38, 68, 0.92), rgba(10, 16, 30, 0.94));
            box-shadow: 0 18px 28px rgba(2, 8, 22, 0.42);
            margin-bottom: 0.8rem;
        }}

        .ow-hero-badge {{
            display: inline-block;
            border-radius: 999px;
            border: 1px solid rgba(86, 216, 255, 0.45);
            color: #a6f0ff;
            padding: 4px 10px;
            font-size: 0.72rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 700;
        }}

        .ow-hero-title {{
            font-size: clamp(1.45rem, 1.2rem + 1.2vw, 2.2rem);
            font-weight: 800;
            color: #f3f8ff;
            line-height: 1.15;
            margin: 0 0 6px 0;
        }}

        .ow-hero-sub {{
            color: var(--app-muted);
            margin: 0;
            font-size: 0.95rem;
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-top: 1.2rem !important;
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


def render_top_navigation(current_page: str) -> None:
    nav_items = [
        ("main", "메인", "main.py"),
        ("pick_win", "픽률·승률", "pages/1_pick_win_distribution.py"),
        ("hero_trends", "영웅 시계열", "pages/2_hero_trends.py"),
    ]

    cols = st.columns(len(nav_items))
    for col, (page_key, label, target) in zip(cols, nav_items):
        with col:
            is_current = page_key == current_page
            clicked = st.button(
                label,
                key=f"nav_{current_page}_{page_key}",
                width="stretch",
                type="primary" if is_current else "secondary",
                disabled=is_current,
            )
            if clicked and hasattr(st, "switch_page"):
                st.switch_page(target)
