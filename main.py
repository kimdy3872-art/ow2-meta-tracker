import streamlit as st
import pandas as pd
import urllib.parse
import html
from app_data import (
    ROLE_ORDER,
    TIER_ORDER,
    get_hero_image_url,
    load_latest_stats,
    translate_role_name,
    translate_tier_name,
)
from ui import (
    GLOBAL_BG_COLOR,
    GLOBAL_BORDER_COLOR,
    GLOBAL_FONT_FAMILY,
    GLOBAL_SURFACE_COLOR,
    GLOBAL_TEXT_COLOR,
    apply_global_theme,
    render_page_hero,
    render_top_navigation,
)

# -------------------------------------------------
# 1. 페이지 설정
# -------------------------------------------------
st.set_page_config(
    page_title="오버워치 2 경쟁전 메타 분석기",
    layout="wide"
)
apply_global_theme()
render_page_hero(
    "오버워치 2 경쟁전 메타 센터",
    "티어와 포지션별 지표를 대시보드 형식으로 확인할 수 있습니다.",
    badge="Live Competitive Meta",
)
render_top_navigation("main")
st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

# -------------------------------------------------
# 2. 데이터 로드
# -------------------------------------------------
df_raw = load_latest_stats()

if "update_date" in df_raw.columns and not df_raw.empty:
    base_date = str(df_raw["update_date"].iloc[0])
else:
    base_date = "-"

st.caption(f"데이터 기준일: {base_date}")

# -------------------------------------------------
# 3. 메인 상단 필터
# -------------------------------------------------
roles = [role for role in ROLE_ORDER if role != "All"]
tiers = TIER_ORDER


def render_metric_card(title, value, accent_color="#0b69ff"):
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    return f"""
    <div style="
        background: linear-gradient(180deg, {GLOBAL_SURFACE_COLOR} 0%, #0f1b31 100%);
        border: 1px solid {GLOBAL_BORDER_COLOR};
        border-radius: 16px;
        padding: 16px 18px;
        min-height: 122px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    ">
        <div style="
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #bfdbfe;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-bottom: 12px;
        ">{safe_title}</div>
        <div style="
            color: {accent_color};
            font-size: 1.62rem;
            font-weight: 800;
            line-height: 1.2;
            word-break: keep-all;
        ">{safe_value}</div>
    </div>
    """

if "selected_tier" not in st.session_state:
    st.session_state.selected_tier = "Gold"
if "selected_role" not in st.session_state:
    st.session_state.selected_role = "All"
if "sort_by" not in st.session_state:
    st.session_state.sort_by = "종합 점수"
if "search_hero" not in st.session_state:
    st.session_state.search_hero = ""


def reset_filters():
    st.session_state.selected_tier = "Gold"
    st.session_state.selected_role = "All"
    st.session_state.sort_by = "종합 점수"
    st.session_state.search_hero = ""

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.05, 1.0, 0.95, 1.65, 0.55])

    with c1:
        selected_tier = st.selectbox(
            "티어",
            tiers,
            key="selected_tier",
            format_func=translate_tier_name,
            placeholder="티어",
        )
    with c2:
        selected_role = st.selectbox(
            "포지션",
            ["All"] + roles,
            key="selected_role",
            format_func=translate_role_name,
            placeholder="포지션",
        )
    with c3:
        sort_by = st.selectbox(
            "정렬",
            ["종합 점수", "승률", "픽률"],
            key="sort_by",
            placeholder="정렬",
        )
    with c4:
        search_hero = st.text_input(
            "영웅 검색",
            key="search_hero",
            placeholder="영웅 검색",
        )
    with c5:
        st.markdown("<div class='ow-filter-action-spacer'></div>", unsafe_allow_html=True)
        st.button("초기화", width="stretch", on_click=reset_filters)

st.markdown(
    f"""
    <style>
    .ow-top4-divider {{
        height: 1px;
        background: rgba(66, 88, 126, 0.55);
        margin: 8px 0 10px;
    }}
    .ow-top4-divider.after {{
        margin: 8px 0 12px;
    }}
    </style>
    <div class="ow-top4-divider"></div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# 4. 데이터 필터링
# -------------------------------------------------
if selected_role == "All":
    selected_roles = roles
else:
    selected_roles = [selected_role]

df_filtered = df_raw[
    (df_raw["data_tier"] == selected_tier) &
    (df_raw["role"].isin(selected_roles)) &
    (df_raw["map"] == "all-maps")
].copy()

if search_hero:
    df_filtered = df_filtered[
        df_filtered["hero"].str.contains(search_hero, case=False, na=False)
    ].copy()

if "pick_rate_z" in df_filtered.columns and "win_rate_z" in df_filtered.columns:
    pick_z = pd.to_numeric(df_filtered["pick_rate_z"], errors="coerce")
    win_z = pd.to_numeric(df_filtered["win_rate_z"], errors="coerce")
    df_filtered["is_master"] = (pick_z <= -0.5) & (win_z >= 0.5)
else:
    df_filtered["is_master"] = False

# -------------------------------------------------
# 5. 데이터 준비
# -------------------------------------------------
if not df_filtered.empty:
    df_filtered["rank"] = pd.Categorical(
        df_filtered["rank"],
        categories=["C", "B", "A", "S"],
        ordered=True
    )

    # 시각화 크기 보정
    if "total_score" in df_filtered.columns:
        df_filtered["display_size"] = (
            df_filtered["total_score"]
            - df_filtered["total_score"].min()
            + 1
        )
    else:
        df_filtered["display_size"] = 1

def render_rank_table_html(df):
    rank_color_map = {
        "S": "#ef4444",
        "A": "#f59e0b",
        "B": "#22c55e",
        "C": "#60a5fa",
    }

    styles = """
    <style>
    .overwatch-table {border-collapse: collapse; width: 100%; font-family: __GLOBAL_FONT_FAMILY__;}
    .overwatch-table th, .overwatch-table td {border: 1px solid __GLOBAL_BORDER_COLOR__; padding: 11px 13px; vertical-align: middle; color: __GLOBAL_TEXT_COLOR__; font-size: 0.92rem;}
    .overwatch-table {background-color: __GLOBAL_BG_COLOR__;}
    .overwatch-table th {background-color: __GLOBAL_SURFACE_COLOR__; color: #f8fafc; font-weight: 700; font-size: 0.9rem; letter-spacing: 0.03em; text-transform: uppercase;}
    .overwatch-table tbody tr:hover {background-color: #111827;}
    .overwatch-table .portrait-cell {width: 98px; text-align: center;}
    .overwatch-table .portrait-cell img {border-radius: 16px; width: 68px; height: 68px; object-fit: cover;}
    .overwatch-table .hero-cell {text-align: left; font-weight: 700; color: __GLOBAL_TEXT_COLOR__;}
    .overwatch-table .role-cell {text-align: center; color: __GLOBAL_TEXT_COLOR__;}
    .overwatch-table .rate-cell {text-align: left; min-width: 180px;}
    .overwatch-table .rank-cell {text-align: center; font-weight: 900; font-size: 1.38rem; line-height: 1; letter-spacing: 0.01em; padding: 4px 8px; color: __GLOBAL_TEXT_COLOR__;}
    .artisan-badge {display: inline-block; margin-left: 8px; padding: 2px 7px; border-radius: 999px; font-size: 0.68rem; font-weight: 800; letter-spacing: 0.02em; vertical-align: middle;}
    .artisan-strong {background: rgba(250, 204, 21, 0.14); color: #fde68a; border: 1px solid rgba(250, 204, 21, 0.36);}
    .rate-bar {background: #1f2937; border-radius: 999px; height: 10px; overflow: hidden; margin-top: 6px;}
    .rate-fill {height: 100%; border-radius: 999px;}
    .rate-fill.pick {background: #60a5fa;}
    .rate-fill.win {background: #34d399;}
    .rate-fill.ban {background: #f87171;}
    .rate-text {font-size: 0.85rem; color: __GLOBAL_TEXT_COLOR__; margin-top: 6px;}
    .header-note {font-size: 0.9rem; color: #cbd5e1; margin-bottom: 8px;}
    </style>
    """
    styles = styles.replace("__GLOBAL_BG_COLOR__", GLOBAL_BG_COLOR)
    styles = styles.replace("__GLOBAL_TEXT_COLOR__", GLOBAL_TEXT_COLOR)
    styles = styles.replace("__GLOBAL_BORDER_COLOR__", GLOBAL_BORDER_COLOR)
    styles = styles.replace("__GLOBAL_SURFACE_COLOR__", GLOBAL_SURFACE_COLOR)
    styles = styles.replace("__GLOBAL_FONT_FAMILY__", GLOBAL_FONT_FAMILY)
    rows = []
    for _, row in df.iterrows():
        hero_name = str(row["hero"])
        hero = html.escape(hero_name)
        hero_query = urllib.parse.quote(hero_name, safe="")
        hero_link = (
            f"<a href='?hero={hero_query}' target='_self' "
            f"style='color:{GLOBAL_TEXT_COLOR}; text-decoration: underline; text-underline-offset: 3px;'>"
            f"{hero}</a>"
        )
        is_master = bool(row.get("is_master", False))
        badge_html = ""
        if is_master:
            badge_html = "<span class='artisan-badge artisan-strong'>장인</span>"
        hero_cell_html = f"{hero_link}{badge_html}"
        role = html.escape(translate_role_name(str(row["role"])))
        win_rate = f"{row['win_rate']:.1f}%"
        pick_rate = f"{row['pick_rate']:.1f}%"
        ban_rate_val = pd.to_numeric(row.get("ban_rate", None), errors="coerce")
        rank = html.escape(str(row["rank"]))
        rank_color = rank_color_map.get(str(row["rank"]), GLOBAL_TEXT_COLOR)
        hero_url = get_hero_image_url(row["hero"])
        img_html = f'<img src="{hero_url}"/>' if hero_url else "-"

        pick_html = (
            f"<div class='rate-bar'><div class='rate-fill pick' style='width:{min(max(row['pick_rate'],0),100)}%'></div></div>"
            f"<div class='rate-text'>{pick_rate}</div>"
        )
        win_html = (
            f"<div class='rate-bar'><div class='rate-fill win' style='width:{min(max(row['win_rate'],0),100)}%'></div></div>"
            f"<div class='rate-text'>{win_rate}</div>"
        )
        if pd.notna(ban_rate_val):
            ban_rate_str = f"{ban_rate_val:.1f}%"
            ban_html = (
                f"<div class='rate-bar'><div class='rate-fill ban' style='width:{min(max(ban_rate_val,0),100)}%'></div></div>"
                f"<div class='rate-text'>{ban_rate_str}</div>"
            )
        else:
            ban_html = "<div class='rate-text' style='color:#6b7280;'>-</div>"
        rows.append(
            f"<tr><td class='portrait-cell'>{img_html}</td><td class='hero-cell'>{hero_cell_html}</td><td class='role-cell'>{role}</td><td class='rate-cell'>{win_html}</td><td class='rate-cell'>{pick_html}</td><td class='rate-cell'>{ban_html}</td><td class='rank-cell' style='color:{rank_color};'>{rank}</td></tr>"
        )
    table_html = (
        styles
        + "<table class='overwatch-table'><thead><tr>"
        + "<th>Portrait</th><th>영웅</th><th>포지션</th><th>승률</th><th>픽률</th><th>밴률</th><th>랭크</th>"
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return table_html

# -------------------------------------------------
# 9. 데이터 없는 경우 처리
# -------------------------------------------------
if df_filtered.empty:

    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# -------------------------------------------------
# 9. 상단 요약 지표 — 밴률/승률/픽률 TOP 4 순환
# -------------------------------------------------
import streamlit.components.v1 as _ow_components


def _build_top4_slide(metric_col, label, top4_df):
    _rank_colors = {1: "#ef4444", 2: "#f59e0b", 3: "#22c55e", 4: "#60a5fa"}
    is_pick_slide = label == "픽률"
    title_font_size = "0.82rem" if is_pick_slide else "0.72rem"
    badge_font_size = "0.72rem" if is_pick_slide else "0.68rem"
    hero_font_size = "0.98rem" if is_pick_slide else "0.93rem"
    value_font_size = "1.42rem" if is_pick_slide else "1.3rem"
    cards = []
    for i in range(4):
        rank = i + 1
        accent = _rank_colors[rank]
        if i < len(top4_df):
            row = top4_df.iloc[i]
            hero_name = str(row["hero"])
            val = row[metric_col]
            val = float(val) if pd.notna(val) else 0.0
            value_str = f"{val:.1f}%"
            img_url = get_hero_image_url(hero_name)
        else:
            hero_name = "-"
            value_str = "-"
            img_url = None
        img_part = (
            f'<img src="{html.escape(img_url)}" style="width:48px;height:48px;border-radius:10px;object-fit:cover;flex-shrink:0;">'
            if img_url
            else '<div style="width:48px;height:48px;border-radius:10px;background:#1f2937;flex-shrink:0;"></div>'
        )
        safe = html.escape(hero_name)
        cards.append(
            f'<div style="background:linear-gradient(135deg,{GLOBAL_SURFACE_COLOR} 0%,#0f1b31 100%);'
            f'border:1px solid {GLOBAL_BORDER_COLOR};border-radius:14px;padding:8px 14px;'
            f'display:flex;align-items:center;gap:12px;">'
            f'{img_part}'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:inline-block;padding:2px 7px;border-radius:999px;'
            f'background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.3);'
            f'color:#bfdbfe;font-size:{badge_font_size};font-weight:700;margin-bottom:3px;">{label} {rank}위</div>'
            f'<div style="color:{GLOBAL_TEXT_COLOR};font-size:{hero_font_size};font-weight:700;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{safe}</div>'
            f'</div>'
            f'<div style="color:{accent};font-size:{value_font_size};font-weight:800;flex-shrink:0;">{value_str}</div>'
            f'</div>'
        )
    grid = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">'
        + "".join(cards)
        + "</div>"
    )
    return (
        f'<div style="color:#94a3b8;font-size:{title_font_size};font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;margin-bottom:5px;">{label} TOP 4</div>'
        + grid
    )


if "ban_rate" in df_filtered.columns:
    _ban_top4 = df_filtered[df_filtered["ban_rate"].notna()].sort_values("ban_rate", ascending=False).head(4)
else:
    _ban_top4 = pd.DataFrame(columns=["hero", "ban_rate"])

_win_top4 = df_filtered[df_filtered["win_rate"].notna()].sort_values("win_rate", ascending=False).head(4)
_pick_top4 = df_filtered[df_filtered["pick_rate"].notna()].sort_values("pick_rate", ascending=False).head(4)

_slides = [
    _build_top4_slide("ban_rate", "밴률", _ban_top4),
    _build_top4_slide("win_rate", "승률", _win_top4),
    _build_top4_slide("pick_rate", "픽률", _pick_top4),
]

_slides_markup = ""
for _i, _s in enumerate(_slides):
    _cls = "ow-slide ow-active" if _i == 0 else "ow-slide"
    _slides_markup += f'<div class="{_cls}" id="owSlide{_i}">{_s}</div>'

_dots_markup = ""
for _i in range(3):
    _cls = "ow-dot ow-dot-active" if _i == 0 else "ow-dot"
    _dots_markup += f'<div class="{_cls}" onclick="owGoTo({_i})"></div>'

_ow_components.html(f"""
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:{GLOBAL_FONT_FAMILY};}}
@keyframes owFade{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes owProg{{from{{width:0%}}to{{width:100%}}}}
.ow-slide{{display:none}}.ow-slide.ow-active{{display:block;animation:owFade .55s ease}}
.ow-dot{{width:8px;height:8px;border-radius:50%;background:#374151;cursor:pointer;display:inline-block;transition:background .3s,transform .2s}}
.ow-dot:hover{{background:#60a5fa;transform:scale(1.3)}}.ow-dot-active{{background:#60a5fa!important;transform:scale(1.2)}}
</style>
<div>
  {_slides_markup}
  <div style="height:2px;background:#1f2937;border-radius:1px;overflow:hidden;margin-top:7px;">
    <div id="owFill" style="height:100%;background:#3b82f6;border-radius:1px;animation:owProg 10s linear infinite;width:0;"></div>
  </div>
  <div style="display:flex;justify-content:center;gap:8px;margin-top:7px;">{_dots_markup}</div>
</div>
<script>
var owC=0,owN=3;
var owS=document.querySelectorAll('.ow-slide');
var owD=document.querySelectorAll('.ow-dot');
var owF=document.getElementById('owFill');
function owGoTo(i){{
  owS[owC].classList.remove('ow-active');owD[owC].classList.remove('ow-dot-active');
  owC=i;owS[owC].classList.add('ow-active');owD[owC].classList.add('ow-dot-active');
  owF.style.animation='none';void owF.offsetWidth;owF.style.animation='owProg 10s linear infinite';
}}
setInterval(function(){{owGoTo((owC+1)%owN)}},10000);
</script>
""", height=112, scrolling=False)

st.markdown('<div class="ow-top4-divider after"></div>', unsafe_allow_html=True)

st.subheader("🏆 영웅 랭크 순위표")
st.caption("영웅 이름을 클릭하면 상세 페이지로 이동합니다.")

with st.expander("랭크는 어떻게 산정되나요?"):
    st.markdown(
        """
        - 랭크는 티어/포지션/전장(all-maps) 필터 기준의 종합 지표로 산정됩니다.
        - 기본적으로 승률과 픽률, 밴률 기반 점수를 함께 반영해 `S > A > B > C`로 구간화합니다.
        - 표의 정렬 기준(종합 점수/승률/픽률)을 바꾸면 같은 집합 내 우선순위가 달라집니다.
        - 데이터는 최신 수집일 기준으로만 비교됩니다.
        """
    )

with st.expander("장인챔프는 뭔가요?"):
    st.markdown(
        """
        - 장인챔프는 **낮은 픽률 대비 높은 승률**을 보이는 영웅입니다.
        - 현재 기준: `pick_rate_z <= -0.5` and `win_rate_z >= 0.5`
        - 즉, 평균보다 덜 선택되지만 성과가 높은 영웅을 뜻합니다.
        """
    )

sort_col = {
    "종합 점수": "total_score",
    "승률": "win_rate",
    "픽률": "pick_rate"
}.get(sort_by, "total_score")

# 밴률 컬럼이 있으면 포함
display_cols = ["hero", "role", "win_rate", "pick_rate", "ban_rate", "rank", "is_master"] if "ban_rate" in df_filtered.columns else ["hero", "role", "win_rate", "pick_rate", "rank", "is_master"]
display_df = df_filtered.sort_values(
    sort_col,
    ascending=False
)[display_cols]

if not display_df.empty:
    st.markdown(render_rank_table_html(display_df), unsafe_allow_html=True)
else:
    st.info("선택한 조건에 해당하는 영웅이 없습니다.")

hero_from_query = st.query_params.get("hero")
if isinstance(hero_from_query, list):
    hero_from_query = hero_from_query[0] if hero_from_query else None

if hero_from_query:
    hero_from_query = urllib.parse.unquote(str(hero_from_query))
    hero_row = display_df[display_df["hero"].astype(str) == hero_from_query]
    if not hero_row.empty:
        st.session_state.detail_hero = hero_from_query
        st.session_state.detail_tier = selected_tier
        st.session_state.detail_source = "main"
        if hasattr(st, "switch_page"):
            st.switch_page("pages/3_hero_detail.py")
