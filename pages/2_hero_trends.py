import html
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_data import (
    DATA_CACHE_TTL,
    get_hero_banner_art,
    get_hero_color,
    get_hero_image_url,
    get_initial_index,
    get_ordered_roles,
    get_ordered_tiers,
    list_data_files,
    read_data_parquet,
    translate_role_name,
    translate_tier_name,
)
from ui import (
    GLOBAL_BORDER_COLOR,
    GLOBAL_MUTED_TEXT_COLOR,
    GLOBAL_SURFACE_COLOR,
    GLOBAL_TEXT_COLOR,
    apply_global_theme,
    render_hero_portrait_card,
    render_kpi_row,
    render_page_hero,
    render_sidebar_navigation,
    style_chart,
)

st.set_page_config(page_title="영웅 시계열", layout="wide", initial_sidebar_state="expanded")
apply_global_theme()

METRIC_CONFIG = {
    "win_rate": {"label": "승률", "color": "#34d399", "suffix": "%"},
    "pick_rate": {"label": "픽률", "color": "#60a5fa", "suffix": "%"},
    "ban_rate": {"label": "밴률", "color": "#f87171", "suffix": "%"},
    "total_score": {"label": "종합 점수", "color": "#fbbf24", "suffix": ""},
}


def format_delta(value, suffix):
    if value is None or pd.isna(value):
        return None

    if suffix == "%":
        return f"{value:+.1f}%p"
    return f"{value:+.2f}"


def format_metric_value(value, suffix):
    if pd.isna(value):
        return "-"

    if suffix == "%":
        return f"{value:.1f}%"
    return f"{value:.2f}"


def rank_color(rank):
    return {
        "S": "#ef4444",
        "A": "#f59e0b",
        "B": "#22c55e",
        "C": "#60a5fa",
        "D": "#94a3b8",
    }.get(str(rank), GLOBAL_TEXT_COLOR)


@st.cache_data(ttl=DATA_CACHE_TTL)
def load_history_data():
    frames = []
    weekly_paths = list_data_files(os.path.join("data", "history", "weekly"), suffix=".parquet")
    sources = [(path, 1) for path in weekly_paths]
    sources.append((os.path.join("data", "latest", "latest_tier.parquet"), 2))
    seen_paths = set()

    for path, priority in sources:
        if path in seen_paths:
            continue

        seen_paths.add(path)
        frame = read_data_parquet(path)
        if frame is None or frame.empty:
            continue

        frame = frame.copy()
        frame["_source_priority"] = priority
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)

    if "snapshot_date" in df.columns:
        df["period_date"] = df["snapshot_date"]
        if "update_date" in df.columns:
            df["period_date"] = df["period_date"].fillna(df["update_date"])
    elif "update_date" in df.columns:
        df["period_date"] = df["update_date"]
    else:
        return pd.DataFrame()

    df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
    df = df[df["period_date"].notna()].copy()

    if "map" not in df.columns:
        df["map"] = "all-maps"
    if "map_name" not in df.columns:
        df["map_name"] = df["map"]
    if "role" not in df.columns:
        df["role"] = "Unknown"
    if "rank" not in df.columns:
        df["rank"] = "-"

    for col in METRIC_CONFIG:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    dedupe_cols = ["period_date", "hero", "data_tier", "map"]
    df = (
        df.sort_values(dedupe_cols + ["_source_priority"])
        .drop_duplicates(dedupe_cols, keep="last")
        .sort_values(["period_date", "hero", "data_tier", "map"])
        .reset_index(drop=True)
    )
    df["period_label"] = df["period_date"].dt.strftime("%Y-%m-%d")
    return df

def format_map_option(map_id, df):
    rows = df[df["map"].astype(str) == str(map_id)]["map_name"].dropna().astype(str)
    label = rows.iloc[0] if not rows.empty else str(map_id)
    if str(map_id) == "all-maps":
        return label
    return f"{label} ({map_id})"

render_page_hero(
    "영웅별 시계열", "",
    badge="Hero Trend Watch",
)
render_sidebar_navigation("hero_trends")
st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

history_df = load_history_data()

if history_df.empty:
    st.warning("시계열로 표시할 데이터가 없습니다.")
    st.stop()

st.markdown(
    f"""
    <style>
    .trend-context {{
        border: 1px solid {GLOBAL_BORDER_COLOR};
        border-radius: 12px;
        background: linear-gradient(135deg, {GLOBAL_SURFACE_COLOR} 0%, #0f1b31 100%);
        padding: 10px 14px;
        color: {GLOBAL_MUTED_TEXT_COLOR};
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 12px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }}
    .trend-context img,
    .trend-context .portrait-fallback {{
        width: 54px;
        height: 54px;
        border-radius: 10px;
        object-fit: cover;
        flex-shrink: 0;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: #1f2937;
    }}
    .trend-context-main {{
        flex: 1;
        min-width: 220px;
    }}
    .trend-context-badge {{
        display: inline-block;
        padding: 2px 7px;
        border-radius: 999px;
        background: rgba(59,130,246,0.12);
        border: 1px solid rgba(59,130,246,0.3);
        color: #bfdbfe;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .trend-context-title {{
        color: {GLOBAL_TEXT_COLOR};
        font-size: 1.06rem;
        font-weight: 800;
        line-height: 1.25;
    }}
    .trend-context-sub {{
        color: {GLOBAL_MUTED_TEXT_COLOR};
        font-size: 0.86rem;
        margin-top: 2px;
    }}
    .trend-context-rank {{
        color: {GLOBAL_MUTED_TEXT_COLOR};
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        text-align: right;
        flex-shrink: 0;
    }}
    .trend-context-rank strong {{
        display: block;
        color: {GLOBAL_TEXT_COLOR};
        font-size: 1.7rem;
        line-height: 1;
        margin-top: 3px;
    }}
    @media (max-width: 700px) {{
        .trend-context {{
            align-items: flex-start;
        }}
        .trend-context-rank {{
            width: 100%;
            text-align: left;
            padding-left: 68px;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

controls_1 = st.columns([1.0, 1.0, 1.4])
with controls_1[0]:
    role_options = get_ordered_roles(history_df)
    selected_role = st.selectbox(
        "포지션",
        role_options,
        index=get_initial_index(role_options, "All"),
        format_func=translate_role_name,
        placeholder="포지션 선택",
    )

role_df = history_df.copy()
if selected_role != "All":
    role_df = role_df[role_df["role"] == selected_role].copy()

hero_options = sorted(role_df["hero"].dropna().astype(str).unique().tolist())
if not hero_options:
    st.warning("선택한 포지션에 해당하는 영웅 데이터가 없습니다.")
    st.stop()

preferred_hero = st.session_state.get("detail_hero")
with controls_1[1]:
    selected_hero = st.selectbox(
        "영웅",
        hero_options,
        index=get_initial_index(hero_options, preferred_hero),
        placeholder="영웅 선택",
    )

hero_df = role_df[role_df["hero"].astype(str) == selected_hero].copy()

with controls_1[2]:
    tier_options = get_ordered_tiers(hero_df)
    preferred_tier = st.session_state.get("detail_tier", "Gold")
    selected_tier = st.selectbox(
        "티어",
        tier_options,
        index=get_initial_index(tier_options, preferred_tier),
        format_func=translate_tier_name,
        placeholder="티어 선택",
    )

tier_df = hero_df[hero_df["data_tier"].astype(str) == selected_tier].copy()

map_options = sorted(tier_df["map"].dropna().astype(str).unique().tolist())
if "all-maps" in map_options:
    map_options = ["all-maps"] + [m for m in map_options if m != "all-maps"]
selected_map = st.selectbox(
    "전장",
    map_options,
    index=0,
    format_func=lambda value: format_map_option(value, tier_df),
    placeholder="전장 선택",
)

map_df = tier_df[tier_df["map"].astype(str) == selected_map].copy()
available_metrics = [
    metric for metric in METRIC_CONFIG
    if metric in map_df.columns and map_df[metric].notna().any()
]
chart_metrics = [
    metric for metric in ["win_rate", "pick_rate", "ban_rate"]
    if metric in available_metrics
]

if map_df.empty:
    st.warning("선택한 조건에 해당하는 시계열 데이터가 없습니다.")
    st.stop()

map_df = map_df.sort_values("period_date").copy()
unique_dates = sorted(map_df["period_date"].drop_duplicates().tolist())

if len(unique_dates) > 1:
    start_date, end_date = st.select_slider(
        "기간",
        options=unique_dates,
        value=(unique_dates[0], unique_dates[-1]),
        format_func=lambda value: value.strftime("%Y-%m-%d"),
    )
    map_df = map_df[
        (map_df["period_date"] >= pd.Timestamp(start_date)) &
        (map_df["period_date"] <= pd.Timestamp(end_date))
    ].copy()
else:
    st.info("현재 저장된 스냅샷이 1개입니다. 날짜 선택 바는 수집된 날짜만 표시됩니다.")

latest_row = map_df.sort_values("period_date").iloc[-1]
previous_row = map_df.sort_values("period_date").iloc[-2] if len(map_df) > 1 else None
date_min = map_df["period_label"].min()
date_max = map_df["period_label"].max()
date_text = date_min if date_min == date_max else f"{date_min} ~ {date_max}"
latest_rank = str(latest_row.get("rank", "-"))
portrait_url = get_hero_image_url(selected_hero)
portrait_html = (
    f'<img src="{html.escape(portrait_url)}" alt="{html.escape(selected_hero)} 초상화">'
    if portrait_url
    else '<div class="portrait-fallback"></div>'
)
context_title = (
    f"{html.escape(selected_hero)} · "
    f"{html.escape(translate_tier_name(selected_tier))} · "
    f"{html.escape(format_map_option(selected_map, tier_df))}"
)

st.markdown(
    f"""
    <div class="trend-context">
        {portrait_html}
        <div class="trend-context-main">
            <div class="trend-context-badge">Hero Trend</div>
            <div class="trend-context-title">{context_title}</div>
            <div class="trend-context-sub">표시 기간: {html.escape(date_text)}</div>
        </div>
        <div class="trend-context-rank">
            현재 랭크
            <strong style="color:{rank_color(latest_rank)};">{html.escape(latest_rank)}</strong>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 지시서 STEP 4: st.metric 은 숫자 크기 제어가 어려워 커스텀 HTML 로 간다.
_art_col, _kpi_col = st.columns([1, 2.6], gap="large")

with _art_col:
    render_hero_portrait_card(
        selected_hero,
        get_hero_banner_art(selected_hero),
        get_hero_color(selected_hero),
        caption=f"{translate_tier_name(selected_tier)} · 랭크 {latest_rank}",
    )

with _kpi_col:
    _kpis = []
    for metric in ["win_rate", "pick_rate", "ban_rate"]:
        cfg = METRIC_CONFIG[metric]
        if metric not in map_df.columns:
            _kpis.append((cfg["label"], "-", "", None, True))
            continue
        latest_value = latest_row.get(metric)
        previous_value = previous_row.get(metric) if previous_row is not None else None
        delta = (
            latest_value - previous_value
            if previous_value is not None and pd.notna(previous_value) and pd.notna(latest_value)
            else None
        )
        value_text = "-" if pd.isna(latest_value) else f"{float(latest_value):.1f}"
        _kpis.append((
            cfg["label"],
            value_text,
            cfg["suffix"],
            None if delta is None else f"{abs(delta):.1f}{cfg['suffix']}",
            bool(delta is not None and delta >= 0),
        ))
    render_kpi_row(_kpis)

if not chart_metrics:
    st.warning("차트에 표시할 지표가 없습니다.")
    st.stop()


def render_metric_chart(metric, chart_df):
    cfg = METRIC_CONFIG[metric]
    suffix = cfg["suffix"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["period_date"],
            y=chart_df[metric],
            mode="lines+markers",
            name=cfg["label"],
            customdata=chart_df[["rank", "period_label"]],
            line=dict(color=cfg["color"], width=3),
            marker=dict(size=9, line=dict(width=1, color="#e2e8f0")),
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                f"{cfg['label']}: %{{y:.2f}}{suffix}<br>"
                "랭크: %{customdata[0]}<extra></extra>"
            ),
        )
    )

    if suffix == "%" and chart_df[metric].notna().any():
        y_min = float(chart_df[metric].min())
        y_max = float(chart_df[metric].max())
        padding = max((y_max - y_min) * 0.18, 1.0)
        y_range = [max(0, y_min - padding), min(100, y_max + padding)]
    else:
        y_range = None

    style_chart(fig, height=260)
    fig.update_layout(
        margin=dict(l=10, r=10, t=12, b=10),
        hovermode="x unified",
        showlegend=False,
        xaxis=dict(title="스냅샷 날짜"),
        yaxis=dict(
            title=f"{cfg['label']} ({suffix})" if suffix else cfg["label"],
            range=y_range,
        ),
    )

    st.plotly_chart(fig, config={"displayModeBar": True})


# 지시서 STEP 4: 3개를 세로로 쌓지 않고 탭으로 전환.
_tabs = st.tabs([METRIC_CONFIG[m]["label"] for m in chart_metrics])
for _tab, _metric in zip(_tabs, chart_metrics):
    with _tab:
        render_metric_chart(_metric, map_df)

table_cols = ["period_label", "win_rate", "pick_rate", "ban_rate", "rank"]
table_cols = [col for col in table_cols if col in map_df.columns]
history_table = (
    map_df[table_cols]
    .rename(
        columns={
            "period_label": "날짜",
            "win_rate": "승률",
            "pick_rate": "픽률",
            "ban_rate": "밴률",
            "rank": "랭크",
        }
    )
    .sort_values("날짜", ascending=False)
)

with st.expander("스냅샷 원본 표"):
    st.dataframe(
        history_table,
        hide_index=True,
        width="stretch",
        column_config={
            "승률": st.column_config.NumberColumn(format="%.1f%%"),
            "픽률": st.column_config.NumberColumn(format="%.1f%%"),
            "밴률": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
