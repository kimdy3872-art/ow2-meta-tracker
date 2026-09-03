import streamlit as st
import pandas as pd
import urllib.parse
import html
from app_data import (
    ROLE_ORDER,
    get_ordered_tiers,
    get_hero_banner_art,
    get_hero_color,
    get_map_image_url,
    load_score_deltas,
    normalize_meta_score,
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
    COLS_FILTER_WIDE,
    COLS_MAIN_SIDE,
    FILTER_DEFAULTS,
    GAP,
    page_shell,
    resolve_tier,
    section,
    selected_role as selected_role_value,
    rank_badge,
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_DANGER_COLOR,
    GLOBAL_RANK_COLORS,
    GLOBAL_TEXT_COLOR,
    render_rotating_card_groups,
    render_hero_showcase,
    render_map_cards,
    render_meta_score_card,
    render_rail_rows,
    render_rank_rail,
)

# -------------------------------------------------
# 1. 페이지 설정
# -------------------------------------------------
_shell = page_shell(
    page_key="main",
    title="오버워치 2 경쟁전 메타 센터",
    subtitle="",
    badge="Live Competitive Meta",
)
_shell.__enter__()


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

# 데이터 기준일 표시는 사이드바 하단(render_sidebar_navigation)으로 옮겼다.

# -------------------------------------------------
# 3. 메인 상단 필터
# -------------------------------------------------
roles = [role for role in ROLE_ORDER if role != "All"]
# TIER_ORDER 를 그대로 쓰면 아직 수집되지 않은 티어(에메랄드 등)가 빈 화면으로 뜬다.
# 데이터에 실제로 있는 티어만 노출하고, 수집이 시작되면 자동으로 목록에 들어온다.
tiers = get_ordered_tiers(df_raw)



def reset_filters():
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value

# 티어/포지션은 사이드바 전역 필터로 올라갔다(4개 페이지가 같은 선택을 공유한다).
# 본문에는 이 페이지 고유 필터인 검색만 남는다.
selected_tier = resolve_tier(tiers)
selected_role = selected_role_value()
_s_col, _ = st.columns(COLS_FILTER_WIDE, gap=GAP)
with _s_col:
    search_hero = st.text_input("영웅 검색", key="search_hero", placeholder="영웅 이름")

# 정렬은 드롭다운을 없애고 표 헤더 클릭으로 받는다(?sort= 쿼리 파라미터).
SORT_COLUMNS = {
    "total_score": "종합 점수",
    "win_rate": "승률",
    "pick_rate": "픽률",
    "ban_rate": "밴률",
}
if "sort_col" not in st.session_state:
    st.session_state.sort_col = "total_score"
if "sort_desc" not in st.session_state:
    st.session_state.sort_desc = True

_sort_q = st.query_params.get("sort")
if isinstance(_sort_q, list):
    _sort_q = _sort_q[0] if _sort_q else None
if _sort_q in SORT_COLUMNS:
    if st.session_state.sort_col == _sort_q:
        st.session_state.sort_desc = not st.session_state.sort_desc
    else:
        st.session_state.sort_col = _sort_q
        st.session_state.sort_desc = True
    st.query_params.clear()
    st.rerun()

sort_col = st.session_state.sort_col
sort_by = SORT_COLUMNS[sort_col]

# 패치노트는 순위표 아래 expander 로 내렸다(지시서: 상단은 시각적 임팩트 우선).

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

ICON_CARET = ("<svg class='sort-caret' viewBox='0 0 10 6' fill='currentColor' "
              "aria-hidden='true'><path d='M5 6 0 0h10z'/></svg>")


def _sort_header(key, label):
    """표 헤더를 정렬 링크로. 드롭다운을 없앤 자리를 대신한다."""
    active = st.session_state.get("sort_col") == key
    caret = ICON_CARET if active else ""
    cls = "sortable active" if active else "sortable"
    flip = " flip" if active and not st.session_state.get("sort_desc", True) else ""
    return (f"<th class='{cls}'><a href='?sort={key}' target='_self'>"
            f"{html.escape(label)}<span class='caret-wrap{flip}'>{caret}</span></a></th>")


def render_rank_table_html(df):
    rank_color_map = GLOBAL_RANK_COLORS

    styles = ""  # 표 스타일은 assets/style.css 에 있다
    rows = []
    for _, row in df.iterrows():
        hero_name = str(row["hero"])
        hero = html.escape(hero_name)
        hero_query = urllib.parse.quote(hero_name, safe="")
        hero_link = (
            f"<a href='?hero={hero_query}&tier={selected_tier}' target='_self' "
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
        hero_cell_html = hero_link  # 포지션/메타 라벨은 아래 부제 줄로 흡수한다
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
        img_html = (f'<img class="hero-cell-img" src="{hero_url}" alt=""/>' if hero_url
                    else '<div class="hero-cell-img"></div>')

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
            ban_html = "<div class='rate-text muted'>-</div>"
        low_html = f"<span class='cell-warn'>{html.escape(low_pick_warning)}</span>" if low_pick_warning else ""
        sub_bits = [role]
        if meta_type:
            sub_bits.append(meta_type)
        sub_text = " · ".join(b for b in sub_bits if b)

        def _bar(kind, value, text):
            if pd.isna(value):
                return "<div class='rate-text muted'>-</div>"
            w = min(max(float(value), 0), 100)
            return (
                f"<div class='rate-line'><div class='rate-bar'>"
                f"<div class='rate-fill {kind}' style='width:{w}%'></div></div>"
                f"<div class='rate-text'>{text}</div></div>"
            )

        rows.append(
            "<tr>"
            f"<td class='hero-cell'>{img_html}"
            f"<div class='hero-cell-text'>"
            f"<div class='hero-cell-name nowrap'>{hero_cell_html}{low_html}</div>"
            f"<div class='hero-cell-sub nowrap'>{html.escape(sub_text)}</div>"
            f"</div></td>"
            f"<td class='rate-cell'>{_bar('win', row['win_rate'], win_rate)}</td>"
            f"<td class='rate-cell'>{_bar('pick', row['pick_rate'], pick_rate)}</td>"
            f"<td class='rate-cell'>{_bar('ban', ban_rate_val, f'{ban_rate_val:.1f}%' if pd.notna(ban_rate_val) else '-')}</td>"
            f"<td class='score-cell nowrap'>{score_html}"
            f"{rank_badge(rank)}</td>"
            "</tr>"
        )
    table_html = (
        styles
        + "<div class='table-wrap'><table class='overwatch-table'><thead><tr>"
        + "<th>영웅</th>"
        + "".join(_sort_header(key, label) for key, label in
                 [("win_rate", "승률"), ("pick_rate", "픽률"),
                  ("ban_rate", "밴률"), ("total_score", "종합 점수")])
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
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


def _format_metric(metric_col, value):
    """종합 점수는 비율이 아니라 z-score 라 % 를 붙이면 안 된다."""
    if pd.isna(value):
        return "-"
    if metric_col == "total_score":
        return f"{float(value):+.2f}"
    return f"{float(value):.1f}%"


def _build_top_cards(metric_col, label, top_df, metric_color, limit=4):
    """상위 영웅을 아트 카드로. 배너와 같은 스플래시 아트 + 초점 좌표를 재사용한다."""
    rank_color_map = GLOBAL_RANK_COLORS
    cards = []
    for i in range(min(limit, len(top_df))):
        row = top_df.iloc[i]
        hero_name = str(row["hero"])
        value = row[metric_col]
        art = get_hero_banner_art(hero_name) or {}
        cards.append({
            "name": hero_name,
            # 카드가 세로형이라 초상화(정사각)보다 스플래시 아트가 덜 늘어난다.
            "art_url": art.get("splash_url") or get_hero_image_url(hero_name),
            "focal_x": art.get("focal_x", 0.6),
            "metric": _format_metric(metric_col, value),
            "metric_color": metric_color,
            "sub": f"{label} {i + 1}위 · {translate_role_name(str(row.get('role', '')))}",
            "rank": str(row.get("rank", "")),
            "rank_color": rank_color_map.get(str(row.get("rank", "")), GLOBAL_TEXT_COLOR),
            "href": f"?hero={urllib.parse.quote(hero_name, safe='')}&tier={selected_tier}",
        })
    return cards


def _rank_distribution_rows(df):
    rank_color_map = GLOBAL_RANK_COLORS
    counts = df["rank"].astype(str).value_counts()
    return [(key, int(counts.get(key, 0)), rank_color_map[key]) for key in ["S", "A", "B", "C", "D"]]


if "ban_rate" in df_filtered.columns:
    _ban_top4 = df_filtered[df_filtered["ban_rate"].notna()].sort_values("ban_rate", ascending=False).head(4)
else:
    _ban_top4 = pd.DataFrame(columns=["hero", "ban_rate"])

_win_top4 = df_filtered[df_filtered["win_rate"].notna()].sort_values("win_rate", ascending=False).head(4)
_pick_top4 = df_filtered[df_filtered["pick_rate"].notna()].sort_values("pick_rate", ascending=False).head(4)

# 2차 지시서 D-2: 전역 라디오를 없애고 이 카드 안에서만 전환되는 탭으로 흡수.
def _map_cards(hero_name, limit=4):
    """전장별 승률 상위 카드. 전장 데이터가 없으면 빈 리스트."""
    if "map" not in df_raw.columns:
        return []
    rows = df_raw[
        (df_raw["data_tier"] == selected_tier)
        & (df_raw["hero"].astype(str) == str(hero_name))
        & (df_raw["map"].astype(str) != "all-maps")
        & (df_raw["win_rate"].notna())
    ].sort_values("win_rate", ascending=False).head(limit)
    return [
        {
            "name": str(r.get("map_name") or r.get("map")),
            "metric": f"{float(r['win_rate']):.1f}%",
            "image": get_map_image_url(str(r["map"])),
        }
        for _, r in rows.iterrows()
    ]


# 밴률 컬럼이 있으면 포함
display_cols = ["hero", "role", "win_rate", "pick_rate", "ban_rate", "total_score", "score_strength", "pick_rate_warning", "rank"] if "ban_rate" in df_filtered.columns else ["hero", "role", "win_rate", "pick_rate", "total_score", "score_strength", "pick_rate_warning", "rank"]
display_df = df_filtered.sort_values(
    sort_col,
    ascending=not st.session_state.sort_desc,
)[display_cols]

if display_df.empty:
    st.info("선택한 조건에 해당하는 영웅이 없습니다.")
    st.stop()

# 지시서 STEP 2: 사이드바(메뉴) + 메인 + 우측 레일. 지시서의 left 컬럼은 사이드바와
# 역할이 겹쳐 두지 않는다.
_main_col, _rail_col2 = st.columns(COLS_MAIN_SIDE, gap=GAP)

with _main_col:
    _top = display_df.iloc[0]
    _top_hero = str(_top["hero"])

    def _pct(v):
        return "-" if pd.isna(v) else f"{float(v):.1f}<span class='unit'>%</span>"

    _watermark = _top.get(sort_col)
    if pd.isna(_watermark):
        _watermark_text = "-"
    elif sort_col == "total_score":
        _watermark_text = f"{float(_watermark):.1f}"
    else:
        _watermark_text = f"{float(_watermark):.1f}%"

    render_hero_showcase(
        hero_name=_top_hero,
        art=get_hero_banner_art(_top_hero),
        accent=get_hero_color(_top_hero),
        watermark=_watermark_text,
        eyebrow=f"{sort_by} 1위",
        meta=f"{translate_tier_name(selected_tier)} · "
             f"{translate_role_name(str(_top.get('role', '')))} · 랭크 {_top.get('rank', '-')}",
        stats=[
            ("승률", _pct(_top.get("win_rate"))),
            ("픽률", _pct(_top.get("pick_rate"))),
            ("밴률", _pct(_top.get("ban_rate"))),
            ("종합 점수", "-" if pd.isna(_top.get("total_score"))
                       else f"{float(_top['total_score']):+.2f}"),
        ],
    )

    # TOP Winrate / Pickrate / Banrate 를 자동 순환시킨다(제목도 함께 전환).
    render_rotating_card_groups([
        (f"TOP {label}", _build_top_cards(col, name, frame, color))
        for label, name, col, frame, color in [
            ("WINRATE", "승률", "win_rate", _win_top4, GLOBAL_GOOD_COLOR),
            ("PICKRATE", "픽률", "pick_rate", _pick_top4, GLOBAL_INFO_COLOR),
            ("BANRATE", "밴률", "ban_rate", _ban_top4, GLOBAL_DANGER_COLOR),
        ]
    ])

    _maps = _map_cards(_top_hero)
    if _maps:
        st.markdown("<div class='eyebrow'>Top Maps</div>", unsafe_allow_html=True)
        render_map_cards(_maps)

    section("영웅 랭크 순위표", "픽률·승률·밴률을 합친 종합 점수 순")
    st.caption("영웅 이름을 클릭하면 상세 페이지로 이동합니다. 헤더를 눌러 정렬합니다.")
    st.markdown(render_rank_table_html(display_df), unsafe_allow_html=True)

with _rail_col2:
    st.markdown("<div class='ow-rail-sticky'>", unsafe_allow_html=True)
    # 정규화 풀에 그 영웅이 1위로 들어있으면 항상 1000 이 나온다. 전 티어를 기준으로 펴서
    # "다른 티어까지 통틀어 어느 위치인가"를 보여준다.
    # 같은 영웅이 티어마다 행을 가지므로 hero 로 dict 를 만들면 값이 덮어써진다.
    # 기준 분포(전 티어)와 조회 값(현재 행)을 분리해서 환산한다.
    _pool = df_raw[df_raw["map"].astype(str) == "all-maps"]["total_score"]
    _meta_score = float(
        normalize_meta_score(pd.Series([_top.get("total_score")]), reference=_pool).iloc[0]
    )
    render_meta_score_card(
        _meta_score,
        _top.get("rank", "-"),
        _top_hero,
    )

    _deltas = load_score_deltas(selected_tier)
    _delta_rows = []
    if _deltas:
        _ranked = sorted(
            ((h, d) for h, d in _deltas.items()
             if h in set(display_df["hero"].astype(str))),
            key=lambda x: -abs(x[1]),
        )[:4]
        _delta_rows = [
            (get_hero_image_url(h), h, f"{d:+.2f}",
             GLOBAL_GOOD_COLOR if d >= 0 else GLOBAL_DANGER_COLOR)
            for h, d in _ranked
        ]
    render_rail_rows("최근 변동", _delta_rows,
                     empty_text="비교할 이전 스냅샷이 아직 없습니다.")

    if "ban_rate" in display_df.columns:
        _ban3 = display_df[display_df["ban_rate"].notna()].sort_values(
            "ban_rate", ascending=False).head(3)
        render_rail_rows(
            "밴률 TOP 3",
            [(get_hero_image_url(str(r["hero"])), str(r["hero"]),
              f"{float(r['ban_rate']):.1f}%", GLOBAL_DANGER_COLOR)
             for _, r in _ban3.iterrows()],
        )

    render_rank_rail(
        "랭크 분포",
        _rank_distribution_rows(display_df),
        footnote=f"{translate_tier_name(selected_tier)} · 총 {len(display_df)}명",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# 2차 지시서 PART C: 참조용 블록은 전부 최하단으로.
st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
with st.expander("최근 패치노트"):
    render_patch_intelligence_block()

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


# 즐겨찾기 토글: 하트 링크가 ?fav=<영웅> 으로 들어온다.
if "favorites" not in st.session_state:
    st.session_state.favorites = set()
fav_from_query = st.query_params.get("fav")
if isinstance(fav_from_query, list):
    fav_from_query = fav_from_query[0] if fav_from_query else None
if fav_from_query:
    fav_name = urllib.parse.unquote(str(fav_from_query))
    st.session_state.favorites ^= {fav_name}
    st.query_params.clear()
    st.rerun()

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

_shell.__exit__(None, None, None)
