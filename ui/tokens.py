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
# 특전 라인 구분색. Minor 는 액센트 계열, Major 는 경고 계열(WARN)을 쓴다.
MINOR_PERK_COLOR = "#ff9db0"

# 차트용 토큰. 앱 프레임이 그라데이션이라 차트 배경을 단색으로 칠하면 그 부분만 판때기처럼
# 떠 보인다. paper 는 투명으로 두고 플롯 영역만 아주 옅게 띄운다.
# 차트 위 텍스트/마커. 본문 텍스트보다 한 단계 밝게 둬야 플롯 배경에서 읽힌다.
GLOBAL_CHART_LABEL_COLOR = "#e2e8f0"
GLOBAL_CHART_HILITE_COLOR = "#f8fafc"
GLOBAL_CHART_PLOT_BG = "rgba(255, 255, 255, 0.022)"
GLOBAL_CHART_GRID_COLOR = "rgba(148, 150, 190, 0.15)"
GLOBAL_CHART_AXIS_COLOR = "rgba(148, 150, 190, 0.34)"
# zeroline 을 액센트 색으로 두면 3D 씬 축에 빨간 선이 그어져 경고처럼 읽힌다. 중립색 유지.
GLOBAL_CHART_ZERO_COLOR = "rgba(168, 170, 205, 0.32)"
# 표·카드·차트가 같은 색을 써야 한다. ui/badges.py 의 RANK_COLORS 가 단일 출처다.
from .badges import RANK_COLORS as GLOBAL_RANK_COLORS  # noqa: E402
