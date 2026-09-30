import streamlit as st
import plotly.express as px
import pandas as pd
from app_data import (
    get_ordered_roles,
    get_ordered_tiers,
    load_latest_stats,
    translate_role_name,
)
from ui import (
    COLS_HALF,
    GAP,
    page_shell,
    section,
    resolve_tier,
    selected_role as selected_role_value,
    GLOBAL_ACCENT_COLOR,
    GLOBAL_CHART_HILITE_COLOR,
    GLOBAL_CHART_LABEL_COLOR,
    GLOBAL_MUTED_TEXT_COLOR,
    GLOBAL_RANK_COLORS,
    style_chart,
)

_shell = page_shell(
    page_key="pick_win",
    title="픽률 · 승률 · 밴률 분포",
    badge="Meta Map",
)
_shell.__enter__()




def extract_selected_hero(event_data):
    if not event_data:
        return None

    points = []
    if isinstance(event_data, dict):
        points = event_data.get("selection", {}).get("points", [])
    elif hasattr(event_data, "selection") and hasattr(event_data.selection, "points"):
        points = event_data.selection.points

    if not points:
        return None

    first = points[0]
    custom_data = first.get("customdata") if isinstance(first, dict) else None
    if isinstance(custom_data, (list, tuple)) and custom_data:
        return str(custom_data[0])

    if isinstance(first, dict) and first.get("hovertext"):
        return str(first.get("hovertext"))

    return None


raw_df = load_latest_stats()

# 티어/포지션은 사이드바 전역 필터를 그대로 쓴다(페이지 간 선택이 유지된다).
selected_tier = resolve_tier(get_ordered_tiers(raw_df))
selected_role = selected_role_value()
if selected_role not in get_ordered_roles(raw_df):
    selected_role = "All"

filtered_df = raw_df[(raw_df["data_tier"] == selected_tier) & (raw_df["map"] == "all-maps")].copy()

if selected_role != "All":
    filtered_df = filtered_df[filtered_df["role"] == selected_role].copy()

if filtered_df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

filtered_df["display_size"] = (filtered_df["total_score"] - filtered_df["total_score"].min() + 1) * 6
filtered_df["role_display"] = filtered_df["role"].map(translate_role_name)
filtered_df["meta_type"] = filtered_df.get("score_strength", "보통")
filtered_df["hero_label"] = filtered_df.apply(
    lambda r: f"{r['hero']} · {r['meta_type']}" if str(r.get("meta_type", "보통")) != "보통" else str(r["hero"]),
    axis=1,
)

# ban_rate 없으면 0으로 대체
if "ban_rate" not in filtered_df.columns:
    filtered_df["ban_rate"] = 0.0
filtered_df["ban_rate"] = filtered_df["ban_rate"].fillna(0.0)

# 랭크 색은 표/카드/차트가 같아야 해서 ui 의 단일 정의를 쓴다.
rank_color_map = GLOBAL_RANK_COLORS

# 지시서 STEP 3: 문장으로 나열하던 메타 유형을 클릭 가능한 칩으로.
META_TYPES = ["메타 지배", "과열 주의", "밴 압박", "저평가 픽", "전문가 픽", "비주류"]

# 칩에 색 점을 달지 않는다. 같은 화면에서 차트 점 색이 이미 랭크(S~D)를 뜻해서,
# 유형 색을 같이 쓰면 빨간 점을 "밴 압박"으로 오독한다.
_available = [t for t in META_TYPES if (filtered_df["meta_type"].astype(str) == t).any()]
selected_types = st.pills(
    "메타 유형으로 걸러보기",
    _available,
    selection_mode="multi",
    default=None,
    key="meta_filter",
) or []
if selected_types:
    filtered_df = filtered_df[filtered_df["meta_type"].astype(str).isin(selected_types)].copy()
    if filtered_df.empty:
        st.warning("선택한 메타 유형에 해당하는 영웅이 없습니다.")
        st.stop()

# 라벨 겹침: 중앙 밀집 구간에서 이름이 뭉개진다. 상위 8명만 텍스트를 남기고 나머지는
# hover 로 뺀다.
_label_heroes = set(
    filtered_df.sort_values("total_score", ascending=False).head(8)["hero"].astype(str)
)
filtered_df["plot_label"] = filtered_df["hero"].astype(str).where(
    filtered_df["hero"].astype(str).isin(_label_heroes), ""
)

fig_2d = px.scatter(
    filtered_df,
    x="pick_rate",
    y="win_rate",
    color="rank",
    size="ban_rate",
    hover_name="hero",
    text="plot_label",
    custom_data=["hero", "role_display", "rank", "meta_type", "ban_rate"],
    category_orders={"rank": ["S", "A", "B", "C", "D"]},
    color_discrete_map=rank_color_map,
    labels={
        "pick_rate": "픽률 (%)",
        "win_rate": "승률 (%)",
        "ban_rate": "밴률 (%)",
        "rank": "영웅 랭크",
    },
    size_max=24,
    opacity=0.86,
)
fig_2d.add_hline(y=50, line_dash="dash", line_color="rgba(148,163,184,0.55)")
fig_2d.update_traces(
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "포지션: %{customdata[1]}<br>"
        "랭크: %{customdata[2]}<br>"
        "유형: %{customdata[3]}<br>"
        "픽률: %{x:.2f}%<br>"
        "승률: %{y:.2f}%<br>"
        "밴률: %{customdata[4]:.2f}%<extra></extra>"
    ),
    textposition="top center",
    textfont=dict(size=10, color=GLOBAL_CHART_LABEL_COLOR),
    marker=dict(line=dict(width=1, color="rgba(226,232,240,0.55)")),
)
style_chart(fig_2d, height=460)
# 드래그 확대를 끈다. 폰에서는 차트 위 스와이프를 확대가 먹어 페이지가 안 내려갔고,
# PC 에서도 모드바를 숨겨 둬서 한 번 확대하면 되돌릴 버튼이 없었다. hover 는 그대로다.
# 범례는 위 한 줄로. 오른쪽 세로 범례는 폰 폭(358px)의 30% 를 먹었다.
# style_chart 가 범례·여백을 덮어쓰므로 그 뒤에 건다.
fig_2d.update_layout(dragmode=False, margin=dict(t=36),
                     legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom",
                                 title_text="", bgcolor="rgba(0,0,0,0)", borderwidth=0))

fig = px.scatter_3d(
    filtered_df,
    x="pick_rate",
    y="win_rate",
    z="ban_rate",
    color="rank",
    size="display_size",
    hover_name="hero",
    text="plot_label",
    custom_data=["hero", "role_display", "rank", "meta_type", "ban_rate"],
    category_orders={"rank": ["S", "A", "B", "C", "D"]},
    color_discrete_map=rank_color_map,
    labels={
        "pick_rate": "픽률 (%)",
        "win_rate": "승률 (%)",
        "ban_rate": "밴률 (%)",
        "rank": "영웅 랭크",
    },
    size_max=18,
    opacity=0.85,
)

fig.update_traces(
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "포지션: %{customdata[1]}<br>"
        "랭크: %{customdata[2]}<br>"
        "유형: %{customdata[3]}<br>"
        "픽률: %{x:.2f}%<br>"
        "승률: %{y:.2f}%<br>"
        "밴률: %{customdata[4]:.2f}%<extra></extra>"
    ),
    textfont=dict(size=10, color=GLOBAL_CHART_LABEL_COLOR),
)

for trace in fig.data:
    customdata = trace.customdata if hasattr(trace, "customdata") else []
    line_colors = []
    for cd in customdata:
        meta_type = str(cd[3]) if len(cd) > 3 else "보통"
        line_colors.append(GLOBAL_CHART_HILITE_COLOR if meta_type != "보통" else "rgba(148,163,184,0.25)")
    trace.marker.line = dict(width=1, color=line_colors)

style_chart(fig, height=460, scene=True)
# 축 제목과 3D 전용 상호작용 설정은 공통 테마 위에 덧씌운다.
# 2차 지시서 D-5: 3D 범례가 데이터를 가려서 끈다(2D 범례 하나만 남긴다).
# 축 라벨은 작게, tick 은 5개로 줄여 회전 시 읽기 쉽게.
_axis_title = dict(font=dict(size=11))
fig.update_layout(
    scene=dict(
        xaxis=dict(title=dict(text="픽률 (%)", font=dict(size=11)), nticks=5),
        yaxis=dict(title=dict(text="승률 (%)", font=dict(size=11)), nticks=5),
        zaxis=dict(title=dict(text="밴률 (%)", font=dict(size=11)), nticks=5),
        bgcolor="rgba(0,0,0,0)",
        aspectmode="cube",
        # 점 선택 모드에서 Streamlit 이 layout.dragmode 를 "pan" 으로 두고 scene 이 그걸 물려받는다.
        # 그러면 드래그가 회전이 아니라 이동이라 큐브가 화면 밖으로 밀려나고 돌아올 방법이 없었다.
        # turntable 은 중심을 고정하고 위아래 각도도 막혀 있어 어떻게 밀어도 틀 안에 남는다.
        dragmode="turntable",
    ),
    margin=dict(l=0, r=0, t=10, b=0),
    clickmode="event+select",
    hovermode="closest",
    showlegend=False,
    modebar=dict(bgcolor="rgba(0,0,0,0)", color=GLOBAL_MUTED_TEXT_COLOR, activecolor=GLOBAL_ACCENT_COLOR),
)

# 지시서 STEP 3: 2D 와 3D 를 세로로 쌓지 않고 나란히. 제목은 각 차트와 같은 칸에 둔다.
# 제목 줄과 차트 줄을 따로 만들면 좁은 화면에서 제목 둘이 먼저 쌓이고 차트 둘이 뒤에 와서
# "3D 보기" 아래에 2D 차트가 나왔다. 칩은 두 차트를 함께 거르는 필터라 그 위에 둔다.
_c2d, _c3d = st.columns(COLS_HALF, gap=GAP)
with _c2d:
    section("픽률 × 승률", "원 크기는 밴률, 점선은 승률 50%")
    st.plotly_chart(fig_2d, key="pick_win_scatter_2d",
                    config={"displayModeBar": False}, use_container_width=True)
with _c3d:
    section("3D 보기", "드래그로 회전, 오른쪽 위 버튼으로 시점 초기화, 점을 누르면 영웅 리포트로 이동")
    event = st.plotly_chart(
        fig,
        key="pick_win_scatter_3d",
        on_select="rerun",
        selection_mode="points",
        # 모드바에는 시점 초기화 버튼 하나만 둔다. 휠 확대는 끈다(페이지를 내리다 차트 위에서
        # 휠이 걸리면 큐브가 점으로 줄어들었다).
        config={"displayModeBar": True, "displaylogo": False, "scrollZoom": False,
                "modeBarButtons": [["resetCameraDefault3d"]]},
        use_container_width=True,
    )

st.caption("색상 = 랭크 · 점 크기 = 밴률 · 라벨은 상위 8명")

selected_hero = extract_selected_hero(event)
if selected_hero:
    st.session_state.detail_hero = str(selected_hero)
    st.session_state.detail_tier = selected_tier
    st.session_state.detail_source = "pick_win"
    if hasattr(st, "switch_page"):
        st.switch_page("pages/3_hero_detail.py")

_shell.__exit__(None, None, None)
