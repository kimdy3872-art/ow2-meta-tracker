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


def inject_css() -> None:
    """모든 페이지 최상단에서 호출. 스타일시트를 주입한다."""
    css = _load_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def apply_global_theme() -> None:
    """기존 이름 유지 (호출부가 많다). inject_css 의 별칭."""
    inject_css()
