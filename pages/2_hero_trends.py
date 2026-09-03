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
    translate_tier_name,
)
from ui import (
    COLS_ART_KPI,
    COLS_HALF,
    GAP,
    page_shell,
    resolve_tier,
    selected_role as selected_role_value,
    GLOBAL_CHART_LABEL_COLOR,
    GLOBAL_DANGER_COLOR,
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_RANK_COLORS,
    GLOBAL_WARN_COLOR,
    GLOBAL_TEXT_COLOR,
    render_hero_portrait_card,
    render_kpi_row,
    style_chart,
)

_shell = page_shell(
    page_key="hero_trends",
    title="영웅별 시계열",
    badge="Hero Trend Watch",
)
_shell.__enter__()

METRIC_CONFIG = {
    "win_rate": {"label": "승률", "color": GLOBAL_GOOD_COLOR, "suffix": "%"},
    "pick_rate": {"label": "픽률", "color": GLOBAL_INFO_COLOR, "suffix": "%"},
    "ban_rate": {"label": "밴률", "color": GLOBAL_DANGER_COLOR, "suffix": "%"},
    "total_score": {"label": "종합 점수", "color": GLOBAL_WARN_COLOR, "suffix": ""},
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
    return GLOBAL_RANK_COLORS.get(str(rank), GLOBAL_TEXT_COLOR)


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

history_df = load_history_data()

if history_df.empty:
    st.warning("시계열로 표시할 데이터가 없습니다.")
    st.stop()

# 티어/포지션은 사이드바 전역 필터. 본문에는 이 페이지 고유 필터(영웅·전장)만
# 한 줄로 둔다. 전장 목록이 영웅·티어에 의존해서, 열만 먼저 잡고 나중에 채운다.
_controls = st.columns(COLS_HALF, gap=GAP)
role_options = get_ordered_roles(history_df)
selected_role = selected_role_value()
if selected_role not in role_options:
    selected_role = "All"

role_df = history_df.copy()
if selected_role != "All":
    role_df = role_df[role_df["role"] == selected_role].copy()

hero_options = sorted(role_df["hero"].dropna().astype(str).unique().tolist())
if not hero_options:
    st.warning("선택한 포지션에 해당하는 영웅 데이터가 없습니다.")
    st.stop()

# 기본 선택이 알파벳 순 1번이라 신규 영웅(D.MON 등)이 잡히고, 그 영웅은 스냅샷이 1개뿐이라
# 처음 들어온 사람은 매번 빈 차트를 본다. 히스토리가 가장 많은 영웅을 기본값으로 둔다.
_date_col = "period_date" if "period_date" in role_df.columns else "update_date"
_snapshot_counts = (
    role_df.groupby(role_df["hero"].astype(str))[_date_col].nunique()
    if _date_col in role_df.columns else None
)
_richest_hero = (
    str(_snapshot_counts.idxmax()) if _snapshot_counts is not None and not _snapshot_counts.empty
    else hero_options[0]
)
preferred_hero = st.session_state.get("detail_hero") or _richest_hero
with _controls[0]:
    selected_hero = st.selectbox(
        "영웅",
        hero_options,
        index=get_initial_index(hero_options, preferred_hero),
        placeholder="영웅 선택",
    )

hero_df = role_df[role_df["hero"].astype(str) == selected_hero].copy()

selected_tier = resolve_tier(get_ordered_tiers(hero_df))

tier_df = hero_df[hero_df["data_tier"].astype(str) == selected_tier].copy()

map_options = sorted(tier_df["map"].dropna().astype(str).unique().tolist())
if "all-maps" in map_options:
    map_options = ["all-maps"] + [m for m in map_options if m != "all-maps"]
with _controls[1]:
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
_art_col, _kpi_col = st.columns(COLS_ART_KPI, gap=GAP)

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
            marker=dict(size=9, line=dict(width=1, color=GLOBAL_CHART_LABEL_COLOR)),
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

_shell.__exit__(None, None, None)
