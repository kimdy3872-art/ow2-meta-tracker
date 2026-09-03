"""CSS 로더와 페이지 초기화.

CSS 는 assets/style.css 에 있다. 예전에는 f-string 안에 넣어 중괄호를 전부 이스케이프해야
했는데, 파일로 빼면서 그 제약이 사라졌다.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .tokens import *  # noqa: F401,F403  (기존 from ui import GLOBAL_* 호환)

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style.css"


@st.cache_data
def _load_css() -> str:
    try:
        return CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _token_vars() -> str:
    """ui/tokens.py 값을 CSS 변수로 한 번만 내보낸다.

    페이지들이 #12111f, #cbd5e1 같은 값을 직접 박고 있어서 토큰을 고쳐도 화면이
    따라오지 않았다. 이제 CSS 쪽 단일 출처가 여기다. style.css 뒤에 붙여 이긴다.
    """
    return (
        ":root{"
        f"--bg:{GLOBAL_BG_COLOR};"
        f"--surface:{GLOBAL_SURFACE_COLOR};"
        f"--surface-alt:{GLOBAL_SURFACE_ALT_COLOR};"
        f"--border:{GLOBAL_BORDER_COLOR};"
        f"--text:{GLOBAL_TEXT_COLOR};"
        f"--muted:{GLOBAL_MUTED_TEXT_COLOR};"
        f"--accent:{GLOBAL_ACCENT_COLOR};"
        f"--good:{GLOBAL_GOOD_COLOR};"
        f"--info:{GLOBAL_INFO_COLOR};"
        f"--danger:{GLOBAL_DANGER_COLOR};"
        f"--warn:{GLOBAL_WARN_COLOR};"
        f"--font:{GLOBAL_FONT_FAMILY};"
        f"--radius-sm:{GLOBAL_RADIUS_SM};"
        f"--radius-md:{GLOBAL_RADIUS_MD};"
        f"--radius-lg:{GLOBAL_RADIUS_LG};"
        "}"
    )


def inject_css() -> None:
    """모든 페이지 최상단에서 호출. 스타일시트를 주입한다."""
    css = _load_css()
    if css:
        st.markdown(f"<style>{css}{_token_vars()}</style>", unsafe_allow_html=True)


def apply_global_theme() -> None:
    """기존 이름 유지 (호출부가 많다). inject_css 의 별칭."""
    inject_css()
