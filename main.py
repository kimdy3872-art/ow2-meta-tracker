import streamlit as st
import pandas as pd
import urllib.parse
import html
from app_data import (
    ROLE_ORDER,
    TIER_ORDER,
    get_hero_image_url,
    load_latest_balance_patch_note,
    load_latest_patch_ai_analysis,
    load_latest_patch_note,
    load_latest_stats,
    clean_patch_note_content,
    translate_role_name,
    translate_tier_name,
)
from ui import (
    GLOBAL_BG_COLOR,
    GLOBAL_BORDER_COLOR,
    GLOBAL_FONT_FAMILY,
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_DANGER_COLOR,
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


def _as_list(value):
    return value if isinstance(value, list) else []


def _clip_text(value, limit=220):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def render_patch_intelligence_block():
    patch_note = load_latest_patch_note()
    if not patch_note:
        return

    balance_patch_note = load_latest_balance_patch_note()
    analysis = load_latest_patch_ai_analysis(
        balance_patch_note.get("id") if balance_patch_note else patch_note.get("id")
    )
    affected_heroes = _as_list(patch_note.get("affected_heroes"))
    summary_items = _as_list(patch_note.get("summary_items"))
    source_url = str(patch_note.get("source_url") or "")
    title = str(patch_note.get("title") or "최근 패치노트")
    patch_date = str(patch_note.get("patch_date") or "-")
    summary_text = str(patch_note.get("summary") or "")
    if not summary_text and summary_items:
        summary_text = " · ".join(str(item) for item in summary_items[:3])

    hero_badges = "".join(
        f"<span class='patch-hero-badge'>{html.escape(str(hero_name))}</span>"
        for hero_name in affected_heroes[:8]
    )
    if not hero_badges:
        hero_badges = "<span class='patch-hero-badge muted'>일반 패치</span>"

    source_link = ""
    if source_url:
        safe_url = html.escape(source_url, quote=True)
        source_link = (
            f"<a class='patch-link' href='{safe_url}' target='_blank' "
            "rel='noopener noreferrer'>공식 원문</a>"
        )

    if analysis:
        direct_impacts = _as_list(analysis.get("direct_hero_impacts"))
        indirect_impacts = _as_list(analysis.get("indirect_hero_impacts"))
        hero_impacts = direct_impacts or _as_list(analysis.get("hero_impacts"))
        impact_items = []
        for row in hero_impacts[:3]:
            if not isinstance(row, dict):
                continue
            sentence = row.get("display_sentence") or row.get("reason") or ""
            if sentence:
                impact_items.append(f"<li>{html.escape(str(sentence))}</li>")
        impact_html = ""
        if impact_items:
            impact_html = f"<ul class='patch-ai-list'>{''.join(impact_items)}</ul>"
        balance_title = html.escape(str((balance_patch_note or {}).get("title") or "최근 밸런스 패치"))
        balance_date = html.escape(str((balance_patch_note or {}).get("patch_date") or "-"))
        phase = html.escape(str(analysis.get("analysis_phase") or "관찰 단계"))
        ai_panel_html = f"""
<div class="patch-ai-box">
    <div class="patch-ai-title">최근 밸런스 패치 분석</div>
    <div class="patch-ai-sub">기준 패치: {balance_title} · {balance_date} · {phase}</div>
    <div class="patch-ai-summary">{html.escape(_clip_text(analysis.get("summary"), 320))}</div>
    {impact_html}
</div>
"""
    else:
        ai_panel_html = """
<div class="patch-ai-box">
    <div class="patch-ai-title">최근 밸런스 패치 분석</div>
    <div class="patch-ai-summary">아직 영웅 밸런스 패치와 연결된 AI 분석이 생성되지 않았습니다.</div>
</div>
"""

    card_html = "\n".join(line.lstrip() for line in f"""
        <style>
        .patch-intel-wrap {{
            border: 1px solid {GLOBAL_BORDER_COLOR};
            border-radius: 8px;
            background: linear-gradient(180deg, {GLOBAL_SURFACE_COLOR} 0%, #101a2d 100%);
            padding: 16px 18px;
            margin: 4px 0 14px;
        }}
        .patch-intel-top {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
        }}
        .patch-kicker {{
            color: #93c5fd;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .patch-title {{
            color: {GLOBAL_TEXT_COLOR};
            font-size: 1.04rem;
            font-weight: 850;
            line-height: 1.35;
            margin-bottom: 6px;
        }}
        .patch-summary {{
            color: #cbd5e1;
            font-size: 0.92rem;
            line-height: 1.55;
        }}
        .patch-meta {{
            color: #94a3b8;
            font-size: 0.82rem;
            white-space: nowrap;
            text-align: right;
        }}
        .patch-link {{
            display: inline-block;
            margin-top: 8px;
            color: #bfdbfe;
            font-weight: 800;
            text-decoration: none;
            border-bottom: 1px solid rgba(191, 219, 254, 0.55);
        }}
        .patch-hero-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 12px;
        }}
        .patch-hero-badge {{
            color: #e0f2fe;
            background: rgba(14, 165, 233, 0.12);
            border: 1px solid rgba(125, 211, 252, 0.25);
            border-radius: 999px;
            padding: 3px 9px;
            font-size: 0.76rem;
            font-weight: 750;
        }}
        .patch-hero-badge.muted {{
            color: #cbd5e1;
            background: rgba(148, 163, 184, 0.1);
            border-color: rgba(148, 163, 184, 0.22);
        }}
        .patch-ai-box {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(66, 88, 126, 0.6);
        }}
        .patch-ai-title {{
            color: #f8fafc;
            font-size: 0.9rem;
            font-weight: 850;
            margin-bottom: 5px;
        }}
        .patch-ai-sub {{
            color: #94a3b8;
            font-size: 0.78rem;
            line-height: 1.45;
            margin-bottom: 6px;
        }}
        .patch-ai-summary {{
            color: #dbeafe;
            font-size: 0.92rem;
            line-height: 1.55;
        }}
        .patch-ai-list {{
            color: #cbd5e1;
            font-size: 0.88rem;
            line-height: 1.55;
            margin: 8px 0 0 18px;
            padding: 0;
        }}
        .patch-ai-list li {{
            margin: 3px 0;
        }}
        @media (max-width: 760px) {{
            .patch-intel-top {{display: block;}}
            .patch-meta {{text-align: left; margin-top: 8px; white-space: normal;}}
        }}
        </style>
        <section class="patch-intel-wrap">
            <div class="patch-intel-top">
                <div>
                    <div class="patch-kicker">Latest Patch Notes</div>
                    <div class="patch-title">{html.escape(title)}</div>
                    <div class="patch-summary">{html.escape(_clip_text(summary_text, 260))}</div>
                </div>
                <div class="patch-meta">
                    <div>{html.escape(patch_date)}</div>
                    {source_link}
                </div>
            </div>
            <div class="patch-hero-row">{hero_badges}</div>
{ai_panel_html}
        </section>
        """.splitlines())
    st.markdown(card_html, unsafe_allow_html=True)

    with st.expander("패치노트 자세히 보기"):
        if summary_items:
            st.markdown("**핵심 요약**")
            for item in summary_items[:8]:
                st.markdown(f"- {item}")
        st.markdown("**상세 내용**")
        detail_content = clean_patch_note_content(
            patch_note.get("parsed_content") or patch_note.get("raw_content")
        )
        st.markdown(detail_content or "상세 내용이 없습니다.")

    if analysis:
        with st.expander("AI 분석 자세히 보기"):
            st.markdown(str(analysis.get("meta_analysis") or analysis.get("summary") or "상세 분석이 없습니다."))
            direct_impacts = _as_list(analysis.get("direct_hero_impacts"))
            indirect_impacts = _as_list(analysis.get("indirect_hero_impacts"))
            if direct_impacts:
                st.markdown("**직접 변경 영웅**")
                for row in direct_impacts:
                    if not isinstance(row, dict):
                        continue
                    hero_name = row.get("hero", "-")
                    sentence = row.get("display_sentence") or row.get("reason", "")
                    st.markdown(f"- **{hero_name}**: {sentence}")
            if indirect_impacts:
                st.markdown("**간접 영향 가능 영웅**")
                for row in indirect_impacts:
                    if not isinstance(row, dict):
                        continue
                    hero_name = row.get("hero", "-")
                    sentence = row.get("display_sentence") or row.get("reason", "")
                    st.markdown(f"- **{hero_name}**: {sentence}")

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
        border-radius: 12px;
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

st.markdown(
    f"""
    <div class="ow-control-band">
        <div class="ow-control-head">
            <div class="ow-control-title">분석 조건</div>
            <div class="ow-control-meta">티어, 포지션, 정렬 기준을 먼저 고르면 아래 랭킹과 요약이 즉시 갱신됩니다.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
            ["종합 점수", "승률", "픽률", "밴률"],
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
    "<div class='ow-soft-divider'></div>",
    unsafe_allow_html=True,
)

render_patch_intelligence_block()

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

# -------------------------------------------------
# 5. 데이터 준비
# -------------------------------------------------
if not df_filtered.empty:
    df_filtered["rank"] = pd.Categorical(
        df_filtered["rank"],
        categories=["D", "C", "B", "A", "S"],
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
        "D": "#94a3b8",
    }

    styles = """
    <style>
    .overwatch-table {border-collapse: separate; border-spacing: 0; width: 100%; font-family: __GLOBAL_FONT_FAMILY__; overflow: hidden; border: 1px solid __GLOBAL_BORDER_COLOR__; border-radius: 12px; background-color: __GLOBAL_BG_COLOR__;}
    .overwatch-table th, .overwatch-table td {border-bottom: 1px solid __GLOBAL_BORDER_COLOR__; padding: 9px 12px; vertical-align: middle; color: __GLOBAL_TEXT_COLOR__; font-size: 0.9rem;}
    .overwatch-table th:not(:last-child), .overwatch-table td:not(:last-child) {border-right: 1px solid rgba(43, 63, 99, 0.72);}
    .overwatch-table tbody tr:last-child td {border-bottom: 0;}
    .overwatch-table th {background-color: __GLOBAL_SURFACE_COLOR__; color: #f8fafc; font-weight: 700; font-size: 0.9rem; letter-spacing: 0.03em; text-transform: uppercase;}
    .overwatch-table tbody tr:hover {background-color: #111827;}
    .overwatch-table .portrait-cell {width: 76px; text-align: center;}
    .overwatch-table .portrait-cell img {border-radius: 10px; width: 54px; height: 54px; object-fit: cover;}
    .overwatch-table .hero-cell {text-align: left; font-weight: 700; color: __GLOBAL_TEXT_COLOR__;}
    .overwatch-table .role-cell {text-align: center; color: __GLOBAL_TEXT_COLOR__;}
    .overwatch-table .rate-cell {text-align: left; min-width: 152px;}
    .overwatch-table .score-cell {text-align: center; font-weight: 800; min-width: 92px; color: #fbbf24;}
    .overwatch-table .rank-cell {text-align: center; padding: 4px 8px;}
    .rank-pill {display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:30px;border-radius:999px;font-weight:900;font-size:1.05rem;border:1px solid currentColor;background:rgba(255,255,255,0.05);}
    .meta-type-badge {display: inline-block; margin-left: 8px; padding: 2px 7px; border-radius: 999px; font-size: 0.68rem; font-weight: 850; letter-spacing: 0.02em; vertical-align: middle;}
    .meta-dominant {background: rgba(250, 204, 21, 0.14); color: #fde68a; border: 1px solid rgba(250, 204, 21, 0.36);}
    .meta-overheated {background: rgba(249, 115, 22, 0.14); color: #fdba74; border: 1px solid rgba(251, 146, 60, 0.42);}
    .meta-ban-pressure {background: rgba(248, 113, 113, 0.14); color: #fecaca; border: 1px solid rgba(248, 113, 113, 0.42);}
    .meta-underrated {background: rgba(16, 185, 129, 0.14); color: #86efac; border: 1px solid rgba(52, 211, 153, 0.42);}
    .meta-expert {background: rgba(20, 184, 166, 0.13); color: #99f6e4; border: 1px solid rgba(45, 212, 191, 0.38);}
    .meta-niche {background: rgba(148, 163, 184, 0.10); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.28);}
    .low-pick-badge {display: inline-block; margin-left: 6px; padding: 2px 7px; border-radius: 999px; font-size: 0.68rem; font-weight: 800; vertical-align: middle; color: #fed7aa; background: rgba(249, 115, 22, 0.12); border: 1px solid rgba(251, 146, 60, 0.35);}
    .rate-line {display:flex;align-items:center;gap:9px;}
    .rate-bar {flex:1;background: #1f2937; border-radius: 999px; height: 8px; overflow: hidden;}
    .rate-fill {height: 100%; border-radius: 999px;}
    .rate-fill.pick {background: #60a5fa;}
    .rate-fill.win {background: #34d399;}
    .rate-fill.ban {background: #f87171;}
    .rate-text {width:48px;text-align:right;font-size: 0.84rem; color: __GLOBAL_TEXT_COLOR__; font-weight:700;}
    .header-note {font-size: 0.9rem; color: #cbd5e1; margin-bottom: 8px;}
    @media (max-width: 860px) {
        .overwatch-table {border: 0; background: transparent;}
        .overwatch-table thead {display:none;}
        .overwatch-table, .overwatch-table tbody, .overwatch-table tr, .overwatch-table td {display:block;width:100%;}
        .overwatch-table tr {border:1px solid __GLOBAL_BORDER_COLOR__;border-radius:12px;margin-bottom:10px;background:rgba(15,23,42,0.82);overflow:hidden;}
        .overwatch-table td {border-right:0!important;padding:8px 12px;}
        .overwatch-table td[data-label]::before {content:attr(data-label);display:block;color:#8fa7cc;font-size:0.72rem;font-weight:850;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:5px;}
        .overwatch-table .portrait-cell {width:100%;text-align:left;}
        .overwatch-table .role-cell,.overwatch-table .score-cell,.overwatch-table .rank-cell {text-align:left;}
        .overwatch-table .rate-cell {min-width:0;}
        .overwatch-table .rate-cell::before {display:inline-flex!important;align-items:center;gap:6px;margin-bottom:7px;}
        .overwatch-table .rate-cell.win::before {content:"승률";}
        .overwatch-table .rate-cell.pick::before {content:"픽률";}
        .overwatch-table .rate-cell.ban::before {content:"밴률";}
    }
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
        meta_type_raw = str(row.get("score_strength", "") or "보통")
        meta_type = html.escape(meta_type_raw)
        meta_type_class = {
            "메타 지배": "meta-dominant",
            "과열 주의": "meta-overheated",
            "과열주의": "meta-overheated",
            "밴 압박": "meta-ban-pressure",
            "밴압박": "meta-ban-pressure",
            "저평가 픽": "meta-underrated",
            "저평가픽": "meta-underrated",
            "전문가 픽": "meta-expert",
            "전문가픽": "meta-expert",
            "비주류": "meta-niche",
        }.get(meta_type_raw)
        badge_html = (
            f"<span class='meta-type-badge {meta_type_class}'>{meta_type}</span>"
            if meta_type_class
            else ""
        )
        low_pick_warning = str(row.get("pick_rate_warning", "") or "").strip()
        low_pick_html = ""
        if low_pick_warning:
            low_pick_html = f"<span class='low-pick-badge'>{html.escape(low_pick_warning)}</span>"
        hero_cell_html = f"{hero_link}{badge_html}{low_pick_html}"
        role = html.escape(translate_role_name(str(row["role"])))
        win_rate = f"{row['win_rate']:.1f}%"
        pick_rate = f"{row['pick_rate']:.1f}%"
        ban_rate_val = pd.to_numeric(row.get("ban_rate", None), errors="coerce")
        score_val = pd.to_numeric(row.get("total_score", None), errors="coerce")
        score = f"{score_val:+.2f}" if pd.notna(score_val) else "-"
        score_html = score
        rank = html.escape(str(row["rank"]))
        rank_color = rank_color_map.get(str(row["rank"]), GLOBAL_TEXT_COLOR)
        hero_url = get_hero_image_url(row["hero"])
        img_html = f'<img src="{hero_url}"/>' if hero_url else "-"

        pick_html = (
            f"<div class='rate-line'><div class='rate-bar'><div class='rate-fill pick' style='width:{min(max(row['pick_rate'],0),100)}%'></div></div>"
            f"<div class='rate-text'>{pick_rate}</div></div>"
        )
        win_html = (
            f"<div class='rate-line'><div class='rate-bar'><div class='rate-fill win' style='width:{min(max(row['win_rate'],0),100)}%'></div></div>"
            f"<div class='rate-text'>{win_rate}</div></div>"
        )
        if pd.notna(ban_rate_val):
            ban_rate_str = f"{ban_rate_val:.1f}%"
            ban_html = (
                f"<div class='rate-line'><div class='rate-bar'><div class='rate-fill ban' style='width:{min(max(ban_rate_val,0),100)}%'></div></div>"
                f"<div class='rate-text'>{ban_rate_str}</div></div>"
            )
        else:
            ban_html = "<div class='rate-text' style='color:#6b7280;'>-</div>"
        rows.append(
            f"<tr><td class='portrait-cell' data-label='초상화'>{img_html}</td><td class='hero-cell' data-label='영웅'>{hero_cell_html}</td><td class='role-cell' data-label='포지션'>{role}</td><td class='rate-cell win'>{win_html}</td><td class='rate-cell pick'>{pick_html}</td><td class='rate-cell ban'>{ban_html}</td><td class='score-cell' data-label='종합 점수'>{score_html}</td><td class='rank-cell' data-label='랭크'><span class='rank-pill' style='color:{rank_color};'>{rank}</span></td></tr>"
        )
    table_html = (
        styles
        + "<table class='overwatch-table'><thead><tr>"
        + "<th>Portrait</th><th>영웅</th><th>포지션</th><th>승률</th><th>픽률</th><th>밴률</th><th>종합 점수</th><th>랭크</th>"
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
# 9. 상단 요약 지표 — 밴률/승률/픽률 TOP 4
# -------------------------------------------------


def _build_top4_grid(metric_col, label, top4_df, metric_color):
    _rank_colors = {1: "#ef4444", 2: "#f59e0b", 3: "#22c55e", 4: GLOBAL_INFO_COLOR}
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
            f'<img src="{html.escape(img_url)}" style="width:46px;height:46px;border-radius:8px;object-fit:cover;flex-shrink:0;">'
            if img_url
            else '<div style="width:46px;height:46px;border-radius:8px;background:#1f2937;flex-shrink:0;"></div>'
        )
        safe = html.escape(hero_name)
        cards.append(
            f'<div class="top4-card" style="border-left:3px solid {accent};">'
            f'{img_part}'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:inline-block;padding:2px 7px;border-radius:999px;'
            f'background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.28);'
            f'color:#bfdbfe;font-size:0.68rem;font-weight:760;margin-bottom:3px;">{label} {rank}위</div>'
            f'<div style="color:{GLOBAL_TEXT_COLOR};font-size:0.95rem;font-weight:760;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{safe}</div>'
            f'</div>'
            f'<div style="color:{metric_color};font-size:1.25rem;font-weight:850;flex-shrink:0;">{value_str}</div>'
            f'</div>'
        )
    return "".join(cards)


if "ban_rate" in df_filtered.columns:
    _ban_top4 = df_filtered[df_filtered["ban_rate"].notna()].sort_values("ban_rate", ascending=False).head(4)
else:
    _ban_top4 = pd.DataFrame(columns=["hero", "ban_rate"])

_win_top4 = df_filtered[df_filtered["win_rate"].notna()].sort_values("win_rate", ascending=False).head(4)
_pick_top4 = df_filtered[df_filtered["pick_rate"].notna()].sort_values("pick_rate", ascending=False).head(4)

_top4_options = {
    "밴률": ("ban_rate", _ban_top4, GLOBAL_DANGER_COLOR),
    "승률": ("win_rate", _win_top4, GLOBAL_GOOD_COLOR),
    "픽률": ("pick_rate", _pick_top4, GLOBAL_INFO_COLOR),
}
selected_top4 = st.radio(
    "TOP 4 지표",
    list(_top4_options.keys()),
    horizontal=True,
    label_visibility="collapsed",
    key="main_top4_metric",
)
top4_col, top4_df, top4_color = _top4_options[selected_top4]
st.markdown(
    f"""
    <style>
    .top4-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin: 4px 0 12px;
    }}
    .top4-card {{
        background: linear-gradient(135deg, {GLOBAL_SURFACE_COLOR} 0%, #0f1b31 100%);
        border: 1px solid {GLOBAL_BORDER_COLOR};
        border-radius: 12px;
        padding: 8px 12px;
        display: flex;
        align-items: center;
        gap: 11px;
        min-width: 0;
    }}
    @media (max-width: 960px) {{
        .top4-grid {{grid-template-columns: repeat(2, minmax(0, 1fr));}}
    }}
    @media (max-width: 560px) {{
        .top4-grid {{grid-template-columns: 1fr;}}
    }}
    </style>
    <div style="color:#94a3b8;font-size:0.76rem;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">
        {selected_top4} TOP 4
    </div>
    <div class="top4-grid">{_build_top4_grid(top4_col, selected_top4, top4_df, top4_color)}</div>
    <div class="ow-soft-divider"></div>
    """,
    unsafe_allow_html=True,
)

st.subheader("🏆 영웅 랭크 순위표")
st.caption("영웅 이름을 클릭하면 상세 페이지로 이동합니다.")

with st.expander("랭크는 어떻게 산정되나요?"):
    st.markdown(
        """
        - 랭크는 같은 티어/포지션/전장(all-maps) 안에서 산정됩니다.
        - 랭크는 "메타 지배력"을 측정합니다: 존재감(픽률+밴률) 65% + 성능 검증(수축 승률) 35%.
        - 존재감은 픽률과 밴률의 합으로 계산합니다. 밴률이 높은 영웅은 픽이 눌려 있으므로, 둘의 합이 드래프트에서 차지하는 실제 지분을 나타냅니다.
        - 성능은 픽률로 가중 수축한 승률입니다. 픽률이 낮을수록 승률을 비교군 평균 쪽으로 끌어당겨, 저픽률 고승률 영웅의 과대평가를 줄입니다.
        - 영웅 이름 옆 메타 유형 라벨은 두 축의 조합입니다: `메타 지배`, `과열 주의`, `저평가 픽`, `전문가 픽`, `비주류`.
        - 랭크는 분위수 강제 배분이 아니라 절대 점수 기준 `S/A/B/C/D`로 산정됩니다.
        - 기준은 `S >= 1.25`, `A >= 0.50`, `B -0.50~0.50`, `C <= -0.50`, `D <= -1.00`입니다.
        - 픽률 1.0% 미만 영웅은 저픽률 경고를 함께 표시합니다.
        - 종합 점수는 같은 비교군 평균 대비 상대 점수라서 0보다 높으면 평균 이상, 낮으면 평균 이하로 해석할 수 있습니다.
        - 표의 정렬 기준(종합 점수/승률/픽률/밴률)을 바꾸면 같은 집합 내 우선순위가 달라집니다.
        - 데이터는 최신 수집일 기준으로만 비교됩니다.
        """
    )

with st.expander("메타 유형 라벨은 뭔가요?"):
    st.markdown(
        """
        - `메타 지배`: 존재감이 높고 성능도 평균 이상인 핵심 메타 영웅입니다.
        - `과열 주의`: 픽률이 매우 높지만 성능 검증은 낮은 영웅입니다.
        - `밴 압박`: 픽률은 낮지만 밴률이 매우 높아 강하게 의식되는 영웅입니다.
        - `저평가 픽`: 존재감은 아직 낮지만 수축 승률 기준 성능이 매우 뚜렷한 영웅입니다.
        - `전문가 픽`: 낮은 픽률 대비 승률이 매우 좋은 숙련자형 후보입니다.
        - `비주류`: 존재감이 매우 낮고 성능 신호도 약한 영웅입니다.
        - 라벨이 없으면 뚜렷한 유형 신호가 없는 `보통` 구간입니다.
        """
    )

sort_col = {
    "종합 점수": "total_score",
    "승률": "win_rate",
    "픽률": "pick_rate",
    "밴률": "ban_rate",
}.get(sort_by, "total_score")

# 밴률 컬럼이 있으면 포함
display_cols = ["hero", "role", "win_rate", "pick_rate", "ban_rate", "total_score", "score_strength", "pick_rate_warning", "rank"] if "ban_rate" in df_filtered.columns else ["hero", "role", "win_rate", "pick_rate", "total_score", "score_strength", "pick_rate_warning", "rank"]
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
