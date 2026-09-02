"""페이지 셸과 격자 상수.

페이지 4개가 제각각 set_page_config -> 테마 -> (데이터 로딩) -> 헤더 순으로
시작하고 있었다. main.py 만 헤더를 즉시 그리고 나머지 셋은 로딩 뒤에 그려서,
로딩 중에는 헤더 없는 빈 화면이 뜨고 예외가 나면 트레이스백만 남았다.
page_shell 은 그 순서를 하나로 고정한다.
"""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

from .components import _latest_data_date, render_page_hero, render_sidebar_navigation
from .theme import apply_global_theme

# st.columns 비율. 페이지마다 다른 값을 쓰던 것을 여기로 모은다.
COLS_HALF = [1, 1]              # 나란한 필터/차트 2개
COLS_THIRDS = [1, 1, 1.4]       # 필터 2개 + 넓은 입력
COLS_MAIN_SIDE = [3.4, 1.5]     # 본문 + 우측 레일
COLS_ART_KPI = [1, 2.5]         # 영웅 아트 + 지표
COLS_FILTER_WIDE = [1.25, 3.75]  # 단일 필터 + 나머지 여백
GAP = "large"


@contextmanager
def page_shell(*, page_key: str, title: str, subtitle: str = "",
               badge: str = "Overwatch 2 Meta", filters=("tier", "role")):
    """모든 페이지의 공통 시작부.

    헤더는 어떤 데이터 로딩보다 먼저 그린다. 그래야 로딩 중에도 화면이 서 있고,
    본문에서 예외가 나도 헤더가 남는다.
    """
    st.set_page_config(page_title=title, layout="wide",
                       initial_sidebar_state="expanded")
    apply_global_theme()
    render_page_hero(title, subtitle, badge, live_label=_latest_data_date())
    render_sidebar_navigation(page_key, filters=filters)
    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)
    try:
        yield
    except Exception:
        st.error("데이터를 불러오지 못했습니다.")
        raise


def section(title: str, sub: str = "") -> None:
    """섹션 제목. 제목+부제 쌍으로 통일한다.

    예전에는 <h3 class='section-title'> / st.subheader() / <h2> 세 방식이 섞여
    있어서 폰트와 여백이 페이지마다 달랐다.
    """
    import html as _html

    sub_html = (f"<p class='ow-section-sub'>{_html.escape(sub)}</p>") if sub else ""
    st.markdown(
        f"<div class='ow-section'>"
        f"<h3 class='ow-section-title'>{_html.escape(title)}</h3>{sub_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
