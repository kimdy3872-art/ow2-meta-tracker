import streamlit as st
import plotly.express as px
import pandas as pd
from app_data import (
    get_initial_index,
    get_ordered_roles,
    get_ordered_tiers,
    load_latest_stats,
    translate_role_name,
    translate_tier_name,
)
from ui import (
    GLOBAL_BG_COLOR,
    GLOBAL_FONT_FAMILY,
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_DANGER_COLOR,
    GLOBAL_TEXT_COLOR,
    apply_global_theme,
    render_page_hero,
    render_top_navigation,
)

st.set_page_config(page_title="픽률/승률 분포", layout="wide")
apply_global_theme()


def get_selected_tier(df):
    tier_options = get_ordered_tiers(df)
    default_tier = "Gold" if "Gold" in tier_options else tier_options[0]
    return st.selectbox(
        "티어",
        tier_options,
        index=get_initial_index(tier_options, default_tier),
        format_func=translate_tier_name,
        placeholder="티어 선택",
    )


def get_selected_role(df):
    valid_roles = get_ordered_roles(df)
    return st.selectbox(
        "포지션",
        valid_roles,
        index=0,
        format_func=translate_role_name,
        placeholder="포지션 선택",
    )


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


render_page_hero(
    "픽률 · 승률 · 밴률 3D 분포",
    "영웅 메타 포지셔닝을 3차원으로 확인하고, 점 클릭으로 상세 분석으로 이동합니다.",
    badge="Meta Positioning 3D",
)
render_top_navigation("pick_win")
st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

raw_df = load_latest_stats()

st.markdown(
    """
    <div class="ow-control-band">
        <div class="ow-control-head">
            <div class="ow-control-title">분포 조건</div>
            <div class="ow-control-meta">2D는 빠른 판단용, 3D는 밴률까지 포함한 탐색용입니다.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
f1, f2 = st.columns([1.0, 1.0])
with f1:
    selected_tier = get_selected_tier(raw_df)
with f2:
    selected_role = get_selected_role(raw_df)

filtered_df = raw_df[(raw_df["data_tier"] == selected_tier) & (raw_df["map"] == "all-maps")].copy()

if selected_role != "All":
    filtered_df = filtered_df[filtered_df["role"] == selected_role].copy()

if filtered_df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

if "pick_rate_z" in filtered_df.columns and "win_rate_z" in filtered_df.columns:
    pick_z = pd.to_numeric(filtered_df["pick_rate_z"], errors="coerce")
    win_z = pd.to_numeric(filtered_df["win_rate_z"], errors="coerce")
    filtered_df["is_master"] = (pick_z <= -0.5) & (win_z >= 0.5)
else:
    filtered_df["is_master"] = False

filtered_df["display_size"] = (filtered_df["total_score"] - filtered_df["total_score"].min() + 1) * 6
filtered_df["role_display"] = filtered_df["role"].map(translate_role_name)
filtered_df["master_label"] = filtered_df["is_master"].map(lambda x: "장인" if x else "일반")
filtered_df["hero_label"] = filtered_df.apply(
    lambda r: f"★ {r['hero']}" if r["is_master"] else str(r["hero"]),
    axis=1,
)

# ban_rate 없으면 0으로 대체
if "ban_rate" not in filtered_df.columns:
    filtered_df["ban_rate"] = 0.0
filtered_df["ban_rate"] = filtered_df["ban_rate"].fillna(0.0)

rank_color_map = {
    "S": "#ef4444",
    "A": "#f59e0b",
    "B": "#22c55e",
    "C": "#60a5fa",
    "D": "#94a3b8",
}

fig_2d = px.scatter(
    filtered_df,
    x="pick_rate",
    y="win_rate",
    color="rank",
    size="ban_rate",
    hover_name="hero",
    text="hero_label",
    custom_data=["hero", "role_display", "rank", "master_label", "ban_rate"],
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
        "분류: %{customdata[3]}<br>"
        "픽률: %{x:.2f}%<br>"
        "승률: %{y:.2f}%<br>"
        "밴률: %{customdata[4]:.2f}%<extra></extra>"
    ),
    textposition="top center",
    textfont=dict(size=10, color="#e2e8f0"),
    marker=dict(line=dict(width=1, color="rgba(226,232,240,0.55)")),
)
fig_2d.update_layout(
    title=dict(
        text="판단용 2D 분포: 픽률 x 승률",
        font=dict(size=18, color=GLOBAL_TEXT_COLOR),
        x=0,
        xanchor="left",
    ),
    font=dict(family=GLOBAL_FONT_FAMILY, size=13, color=GLOBAL_TEXT_COLOR),
    paper_bgcolor=GLOBAL_BG_COLOR,
    plot_bgcolor=GLOBAL_BG_COLOR,
    margin=dict(l=10, r=10, t=42, b=10),
    legend=dict(bgcolor="rgba(17,24,39,0.8)", bordercolor="#374151", borderwidth=1),
    xaxis=dict(gridcolor="#1f2937", zerolinecolor="#374151", showline=True, linecolor="#334155"),
    yaxis=dict(gridcolor="#1f2937", zerolinecolor="#374151", showline=True, linecolor="#334155"),
    height=430,
)

st.caption(
    f"색상은 랭크, 점 크기는 밴률입니다. 초록({GLOBAL_GOOD_COLOR})은 성능, 파랑({GLOBAL_INFO_COLOR})은 정보, 빨강({GLOBAL_DANGER_COLOR})은 위험/밴 신호로 읽습니다."
)
st.plotly_chart(fig_2d, key="pick_win_scatter_2d", config={"displayModeBar": True}, use_container_width=True)
st.markdown("<div class='ow-soft-divider'></div>", unsafe_allow_html=True)

fig = px.scatter_3d(
    filtered_df,
    x="pick_rate",
    y="win_rate",
    z="ban_rate",
    color="rank",
    size="display_size",
    hover_name="hero",
    text="hero_label",
    custom_data=["hero", "role_display", "rank", "master_label", "is_master", "ban_rate"],
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
        "분류: %{customdata[3]}<br>"
        "픽률: %{x:.2f}%<br>"
        "승률: %{y:.2f}%<br>"
        "밴률: %{customdata[5]:.2f}%<extra></extra>"
    ),
    textfont=dict(size=10, color="#e2e8f0"),
)

for trace in fig.data:
    customdata = trace.customdata if hasattr(trace, "customdata") else []
    line_colors = []
    for cd in customdata:
        is_master = bool(cd[4]) if len(cd) > 4 else False
        line_colors.append("#f8fafc" if is_master else "rgba(148,163,184,0.25)")
    trace.marker.line = dict(width=1, color=line_colors)

fig.update_layout(
    font=dict(family=GLOBAL_FONT_FAMILY, size=13, color=GLOBAL_TEXT_COLOR),
    paper_bgcolor=GLOBAL_BG_COLOR,
    scene=dict(
        xaxis=dict(
            title="픽률 (%)",
            backgroundcolor=GLOBAL_BG_COLOR,
            gridcolor="#1f2937",
            showbackground=True,
            zerolinecolor="#374151",
        ),
        yaxis=dict(
            title="승률 (%)",
            backgroundcolor=GLOBAL_BG_COLOR,
            gridcolor="#1f2937",
            showbackground=True,
            zerolinecolor="#374151",
        ),
        zaxis=dict(
            title="밴률 (%)",
            backgroundcolor=GLOBAL_BG_COLOR,
            gridcolor="#1f2937",
            showbackground=True,
            zerolinecolor="#374151",
        ),
        bgcolor=GLOBAL_BG_COLOR,
    ),
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(
        bgcolor="rgba(17,24,39,0.8)",
        bordercolor="#374151",
        borderwidth=1,
    ),
    clickmode="event+select",
    hovermode="closest",
    height=560,
)

master_count = int(filtered_df["is_master"].sum())
st.caption(
    f"장인 기준: 픽률 Z <= -0.5 and 승률 Z >= 0.5 | 현재 {master_count}명"
)
st.caption("드래그로 회전, 스크롤로 줌. 점을 클릭하면 영웅 상세 페이지로 이동합니다.")

event = st.plotly_chart(
    fig,
    key="pick_win_scatter_3d",
    on_select="rerun",
    selection_mode="points",
    config={"displayModeBar": True},
)

selected_hero = extract_selected_hero(event)
if selected_hero:
    st.session_state.detail_hero = str(selected_hero)
    st.session_state.detail_tier = selected_tier
    st.session_state.detail_source = "pick_win"
    if hasattr(st, "switch_page"):
        st.switch_page("pages/3_hero_detail.py")
