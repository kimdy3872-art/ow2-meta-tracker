from __future__ import annotations

import html

import streamlit as st

# 팔레트는 assets/style.css 의 :root 와 짝이다. 한쪽을 고치면 다른 쪽도 고친다.
# 배경은 보라 기운 없는 중성 다크, 액센트는 오버워치 오렌지 한 색만 쓴다.
# (예전 크림슨 #ff4655 는 발로란트 브랜드색이었다.)
GLOBAL_BG_COLOR = "#0b0c10"
GLOBAL_TEXT_COLOR = "#eceef3"
GLOBAL_SURFACE_COLOR = "#13151b"
GLOBAL_SURFACE_ALT_COLOR = "#1a1d25"
GLOBAL_BORDER_COLOR = "#262a34"
GLOBAL_MUTED_TEXT_COLOR = "#868c9c"
GLOBAL_ACCENT_COLOR = "#f99e1a"
GLOBAL_FONT_FAMILY = "'Pretendard Variable', Pretendard, 'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif"
# 폰트는 한 벌로 통일했다. 이름은 호출부 호환을 위해 남긴다.
GLOBAL_DISPLAY_FONT_FAMILY = GLOBAL_FONT_FAMILY
GLOBAL_RADIUS_SM = "6px"
GLOBAL_RADIUS_MD = "8px"
GLOBAL_RADIUS_LG = "12px"
GLOBAL_GOOD_COLOR = "#3ecf8e"
GLOBAL_INFO_COLOR = "#4ea8ff"
GLOBAL_DANGER_COLOR = "#ff5c6a"
GLOBAL_WARN_COLOR = "#f5b942"
# 특전 라인 구분색. Minor 는 정보 계열, Major 는 경고 계열(WARN)을 쓴다.
MINOR_PERK_COLOR = "#8fb8ff"

# 차트용 토큰. paper 는 투명으로 두고 플롯 영역만 아주 옅게 띄운다.
GLOBAL_CHART_LABEL_COLOR = "#d5d8e0"
GLOBAL_CHART_HILITE_COLOR = "#f5f6f8"
GLOBAL_CHART_PLOT_BG = "rgba(255, 255, 255, 0.015)"
GLOBAL_CHART_GRID_COLOR = "rgba(255, 255, 255, 0.06)"
GLOBAL_CHART_AXIS_COLOR = "rgba(255, 255, 255, 0.14)"
# zeroline 을 액센트 색으로 두면 3D 씬 축에 선이 그어져 경고처럼 읽힌다. 중립색 유지.
GLOBAL_CHART_ZERO_COLOR = "rgba(255, 255, 255, 0.18)"
# 표·카드·차트가 같은 색을 써야 한다. ui/badges.py 의 RANK_COLORS 가 단일 출처다.
from .badges import RANK_COLORS as GLOBAL_RANK_COLORS  # noqa: E402
