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
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_DANGER_COLOR,
    GLOBAL_RANK_COLORS,
    apply_global_theme,
    render_page_hero,
    render_sidebar_navigation,
    style_chart,
)

st.set_page_config(page_title="픽률/승률 분포", layout="wide", initial_sidebar_state="expanded")
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
render_sidebar_navigation("pick_win")
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
# st.pills 라벨에는 HTML 을 넣을 수 없어서, 색 점은 컬러 이모지 원으로 낸다.
# nth-child CSS 로 칠하는 방법은 유형이 빠질 때 색이 밀려서 쓰지 않는다.
META_TYPE_DOTS = {
    "메타 지배": "🟡",
    "과열 주의": "🟠",
    "밴 압박": "🔴",
    "저평가 픽": "🟢",
    "전문가 픽": "🔵",
    "비주류": "⚪",
}
_available = [t for t in META_TYPES if (filtered_df["meta_type"].astype(str) == t).any()]
_chip_to_type = {f"{META_TYPE_DOTS[t]} {t}": t for t in _available}
_selected_chips = st.pills(
    "메타 유형",
    list(_chip_to_type),
    selection_mode="multi",
    default=None,
    key="meta_filter",
    label_visibility="collapsed",
)
selected_types = [_chip_to_type[c] for c in (_selected_chips or [])]
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
    textfont=dict(size=10, color="#e2e8f0"),
    marker=dict(line=dict(width=1, color="rgba(226,232,240,0.55)")),
)
style_chart(fig_2d, height=470)

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
    textfont=dict(size=10, color="#e2e8f0"),
)

for trace in fig.data:
    customdata = trace.customdata if hasattr(trace, "customdata") else []
    line_colors = []
    for cd in customdata:
        meta_type = str(cd[3]) if len(cd) > 3 else "보통"
        line_colors.append("#f8fafc" if meta_type != "보통" else "rgba(148,163,184,0.25)")
    trace.marker.line = dict(width=1, color=line_colors)

style_chart(fig, height=470, scene=True)
# 축 제목과 3D 전용 상호작용 설정은 공통 테마 위에 덧씌운다.
fig.update_layout(
    scene=dict(
        xaxis=dict(title="픽률 (%)"),
        yaxis=dict(title="승률 (%)"),
        zaxis=dict(title="밴률 (%)"),
        bgcolor="rgba(0,0,0,0)",
    ),
    margin=dict(l=0, r=0, t=10, b=0),
    clickmode="event+select",
    hovermode="closest",
)

# 지시서 STEP 3: 2D 와 3D 를 세로로 쌓지 않고 나란히.
_c2d, _c3d = st.columns([1, 1], gap="large")
with _c2d:
    st.markdown("<div class='eyebrow'>판단용 2D · 픽률 x 승률</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_2d, key="pick_win_scatter_2d",
                    config={"displayModeBar": False}, use_container_width=True)
with _c3d:
    st.markdown("<div class='eyebrow'>탐색용 3D · 픽률 x 승률 x 밴률</div>", unsafe_allow_html=True)
    event = st.plotly_chart(
        fig,
        key="pick_win_scatter_3d",
        on_select="rerun",
        selection_mode="points",
        config={"displayModeBar": False},
        use_container_width=True,
    )

st.caption(
    f"색상은 랭크, 점 크기는 밴률입니다. 초록({GLOBAL_GOOD_COLOR})은 성능, "
    f"파랑({GLOBAL_INFO_COLOR})은 정보, 빨강({GLOBAL_DANGER_COLOR})은 위험/밴 신호입니다. "
    "3D 는 드래그로 회전·스크롤로 줌, 점을 클릭하면 상세로 이동합니다. "
    "이름표는 종합 점수 상위 8명만 표시되고 나머지는 hover 로 확인합니다."
)

selected_hero = extract_selected_hero(event)
if selected_hero:
    st.session_state.detail_hero = str(selected_hero)
    st.session_state.detail_tier = selected_tier
    st.session_state.detail_source = "pick_win"
    if hasattr(st, "switch_page"):
        st.switch_page("pages/3_hero_detail.py")
