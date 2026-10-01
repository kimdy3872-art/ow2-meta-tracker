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
    filter_qs,
    meta_score_html,
    rail_rows_html,
    rank_rail_html,
)

# -------------------------------------------------
# 1. 페이지 설정
# -------------------------------------------------
_shell = page_shell(
    page_key="main",
    title="영웅 순위",
    subtitle="",
    badge="Ranking",
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
search_hero = st.text_input("영웅 검색", key="search_hero", placeholder="영웅 이름으로 검색",
                            label_visibility="collapsed")

# 정렬은 표 위의 칩(위젯)으로 받는다. 예전에는 표 머리글 링크(?sort=)였는데, 링크는 전체
# 리로드라 스크롤이 맨 위로 돌아가고, 세션이 새로 떠서 정렬 상태가 기본값으로 돌아간 뒤에
# 클릭이 처리됐다(같은 열을 다시 눌러도 방향이 안 바뀌고, 종합 점수는 낮은 순으로만 갔다).
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


def _on_sort_change():
    """정렬 칩 콜백. 스크립트보다 먼저 돌아서, 표보다 위에 있는 HERO 카드도 새 정렬을 본다."""
    picked = st.session_state.sort_pills
    if picked is None:
        # 켜져 있는 칩을 다시 눌러 선택이 풀렸다. 방향만 뒤집는다.
        st.session_state.sort_desc = not st.session_state.sort_desc
    else:
        st.session_state.sort_col = picked
        st.session_state.sort_desc = True


sort_col = st.session_state.sort_col
sort_by = SORT_COLUMNS[sort_col]


def _sort_label(key):
    if key != sort_col:
        return SORT_COLUMNS[key]
    arrow = "arrow_downward" if st.session_state.sort_desc else "arrow_upward"
    return f"{SORT_COLUMNS[key]} :material/{arrow}:"

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


def _sort_head(key, label):
    """표 머리글 칸. 지금 정렬 열에만 액센트 색과 방향 화살표를 단다(조작은 표 위 칩에서)."""
    if sort_col != key:
        return f"<th>{html.escape(label)}</th>"
    flip = "" if st.session_state.sort_desc else " flip"
    return (f"<th class='active'><span class='th-sort'>{html.escape(label)}"
            f"<span class='caret-wrap{flip}'>{ICON_CARET}</span></span></th>")


def _rate_bar(kind, value, text):
    if pd.isna(value):
        return "<div class='rate-text muted'>-</div>"
    w = min(max(float(value), 0), 100)
    return (f"<div class='rate-line'><div class='rate-bar'>"
            f"<div class='rate-fill {kind}' style='width:{w}%'></div></div>"
            f"<div class='rate-text'>{text}</div></div>")


def render_rank_table_html(df):
    """순위표. 넓으면 5열 표, 좁으면(표 폭 기준, CSS 컨테이너 쿼리) 한 줄 요약 목록.

    영웅 링크는 ::after 로 행(목록 모드) 또는 영웅 칸(표 모드) 전체를 덮는다.
    """
    qs = filter_qs()
    rows = []
    for row_no, (_, row) in enumerate(df.iterrows(), start=1):
        hero_name = str(row["hero"])
        hero_link = (f"<a class='hero-link' target='_self' "
                     f"href='?hero={urllib.parse.quote(hero_name, safe='')}{qs}'>"
                     f"{html.escape(hero_name)}</a>")
        meta_type = str(row.get("score_strength", "") or "보통")
        sub_text = " · ".join(b for b in [translate_role_name(str(row["role"])), meta_type] if b)
        low_pick_warning = str(row.get("pick_rate_warning", "") or "").strip()
        low_html = (f"<span class='cell-warn'>{html.escape(low_pick_warning)}</span>"
                    if low_pick_warning else "")
        ban_val = pd.to_numeric(row.get("ban_rate", None), errors="coerce")
        score_val = pd.to_numeric(row.get("total_score", None), errors="coerce")
        hero_url = get_hero_image_url(row["hero"])
        img_html = (f'<img class="hero-cell-img" src="{hero_url}" alt=""/>' if hero_url
                    else '<div class="hero-cell-img"></div>')
        win_text = f"{row['win_rate']:.1f}%"
        pick_text = f"{row['pick_rate']:.1f}%"
        ban_text = f"{ban_val:.1f}%" if pd.notna(ban_val) else "-"
        score_text = f"{score_val:+.2f}" if pd.notna(score_val) else "-"
        rows.append(
            f"<tr style='--i:{min(row_no, 16)}'>"
            f"<td class='hero-cell'><span class='row-num'>{row_no}</span>{img_html}"
            f"<div class='hero-cell-text'>"
            f"<div class='hero-cell-name nowrap'>{hero_link}{low_html}</div>"
            f"<div class='hero-cell-sub nowrap'>{html.escape(sub_text)}</div>"
            f"</div></td>"
            f"<td class='rate-cell win'>{_rate_bar('win', row['win_rate'], win_text)}</td>"
            f"<td class='rate-cell pick'>{_rate_bar('pick', row['pick_rate'], pick_text)}</td>"
            f"<td class='rate-cell ban'>{_rate_bar('ban', ban_val, ban_text)}</td>"
            f"<td class='score-cell nowrap'>{score_text}"
            f"{rank_badge(html.escape(str(row['rank'])))}</td>"
            "</tr>"
        )
    header = "<th>영웅</th>" + "".join(
        _sort_head(key, SORT_COLUMNS[key]) for key in ("win_rate", "pick_rate", "ban_rate", "total_score"))
    return (f"<div class='rank-board'>"
            f"<div class='table-wrap'><table class='overwatch-table'><thead><tr>{header}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></div>")

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
            "href": f"?hero={urllib.parse.quote(hero_name, safe='')}{filter_qs()}",
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
    """전장별 승률 상위 카드. 전장 데이터가 없으면 빈 리스트.

    순서는 표본 보정 승률로 정한다. 원래 승률로 줄 세우면 표본 부족 조합의 0%/100% 가 맨 위로 온다.
    """
    if "map" not in df_raw.columns:
        return []
    order_col = "shrunk_win_rate" if "shrunk_win_rate" in df_raw.columns else "win_rate"
    rows = df_raw[
        (df_raw["data_tier"] == selected_tier)
        & (df_raw["hero"].astype(str) == str(hero_name))
        & (df_raw["map"].astype(str) != "all-maps")
        & (df_raw["win_rate"].notna())
    ].sort_values(order_col, ascending=False).head(limit)
    return [
        {
            "name": str(r.get("map_name") or r.get("map")),
            "metric": f"{float(r['win_rate']):.1f}%",
            "image": get_map_image_url(str(r["map"])),
            "sample": r.get("sample_warning") if isinstance(r.get("sample_warning"), str) else "",
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
    # 표를 낮은 순으로 뒤집어도 카드는 그 지표의 실제 1위를 보인다("승률 1위"에 꼴찌가 나오면 안 된다).
    _top = display_df.sort_values(sort_col, ascending=False).iloc[0]
    _top_hero = str(_top["hero"])

    def _pct(v):
        return "-" if pd.isna(v) else f"{float(v):.1f}<span class='unit'>%</span>"

    render_hero_showcase(
        hero_name=_top_hero,
        art=get_hero_banner_art(_top_hero),
        accent=get_hero_color(_top_hero),
        eyebrow=f"{sort_by} 1위",
        meta=f"{translate_tier_name(selected_tier)} · "
             f"{translate_role_name(str(_top.get('role', '')))}",
        rank=str(_top.get("rank", "")),
        href=f"?hero={urllib.parse.quote(_top_hero, safe='')}{filter_qs()}",
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
        (f"{name} TOP 4", _build_top_cards(col, name, frame, color))
        for name, col, frame, color in [
            ("승률", "win_rate", _win_top4, GLOBAL_GOOD_COLOR),
            ("픽률", "pick_rate", _pick_top4, GLOBAL_INFO_COLOR),
            ("밴률", "ban_rate", _ban_top4, GLOBAL_DANGER_COLOR),
        ]
    ])

    _maps = _map_cards(_top_hero)
    if _maps:
        render_map_cards(_maps, title=f"{_top_hero} · 승률 높은 전장")

    # 좁은 화면에서는 우측 레일이 53명 표 뒤(열 몇 화면 아래)로 밀려나 사실상 안 보였다.
    # 같은 카드를 표 위에 가로 스와이프 줄로 한 번 더 낸다. 레일 계산(최근 변동 로드)이
    # 표보다 늦게 끝나도 표가 먼저 그려지도록 자리만 잡아 두고 아래에서 채운다.
    _rail_strip = st.empty()
    _order = "높은" if st.session_state.sort_desc else "낮은"
    section("전체 순위", f"{sort_by} {_order} 순 · {len(display_df)}명")
    # 칩 값은 매 실행 정본(sort_col)으로 다시 채운다. 켜진 칩을 다시 누르면 위젯은 선택이
    # 풀리는데(None), 그건 방향 뒤집기로 쓰고 칩은 계속 켜 둔다.
    st.session_state.sort_pills = sort_col
    st.pills("정렬", list(SORT_COLUMNS), key="sort_pills", selection_mode="single",
             format_func=_sort_label, on_change=_on_sort_change, label_visibility="collapsed")
    st.markdown(render_rank_table_html(display_df), unsafe_allow_html=True)

# 정규화 풀에 그 영웅이 1위로 들어있으면 항상 1000 이 나온다. 전 티어를 기준으로 펴서
# "다른 티어까지 통틀어 어느 위치인가"를 보여준다.
# 같은 영웅이 티어마다 행을 가지므로 hero 로 dict 를 만들면 값이 덮어써진다.
# 기준 분포(전 티어)와 조회 값(현재 행)을 분리해서 환산한다.
_pool = df_raw[df_raw["map"].astype(str) == "all-maps"]["total_score"]
_meta_score = float(
    normalize_meta_score(pd.Series([_top.get("total_score")]), reference=_pool).iloc[0]
)
_rail_cards = [meta_score_html(_meta_score, _top.get("rank", "-"), _top_hero)]

_deltas, _delta_since = load_score_deltas(selected_tier)
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
# 넥슨 원본은 며칠에 한 번 갱신되므로, 원본이 달랐던 마지막 날짜를 기준으로 비교한다.
_delta_title = (f"최근 변동 · {_delta_since[5:].replace('-', '/')} 대비"
                if _delta_since else "최근 변동")
_rail_cards.append(rail_rows_html(_delta_title, _delta_rows,
                                  empty_text="비교할 이전 스냅샷이 아직 없습니다."))

if "ban_rate" in display_df.columns:
    _ban3 = display_df[display_df["ban_rate"].notna()].sort_values(
        "ban_rate", ascending=False).head(3)
    _rail_cards.append(rail_rows_html(
        "밴률 TOP 3",
        [(get_hero_image_url(str(r["hero"])), str(r["hero"]),
          f"{float(r['ban_rate']):.1f}%", GLOBAL_DANGER_COLOR)
         for _, r in _ban3.iterrows()],
    ))

_rail_cards.append(rank_rail_html(
    "랭크 분포",
    _rank_distribution_rows(display_df),
    footnote=f"{translate_tier_name(selected_tier)} · 총 {len(display_df)}명",
))

with _rail_col2:
    st.markdown(f"<div class='rail-side'>{''.join(_rail_cards)}</div>", unsafe_allow_html=True)
_rail_strip.markdown(f"<div class='rail-strip'>{''.join(_rail_cards)}</div>",
                     unsafe_allow_html=True)

# 2차 지시서 PART C: 참조용 블록은 전부 최하단으로.
st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
with st.expander("최근 패치노트"):
    render_patch_intelligence_block()

with st.expander("랭크는 어떻게 산정되나요?"):
    st.markdown(
        """
        **강한 영웅 순위가 아니라 메타 지배력 순위입니다.** 판에 얼마나 자주 나오는가(존재감)를 주축으로, 나왔을 때 실제로 이기는가(성능)로 검증합니다. 그래서 많이 쓰이지만 승률은 평범한 영웅도 상위에 올 수 있습니다. 이길 확률만 보려면 표를 승률로 정렬하세요.

        **점수**
        - 같은 티어·포지션 안에서 전체 전장 통계로 비교합니다.
        - 종합 점수 = 존재감 × 0.65 + 성능 × 0.35. 두 축 모두 비교군 안의 z-점수(평균 0, 표준편차 1)라 0이 평균입니다.
        - 존재감 = 픽률 + 밴률. 밴된 영웅은 그 판에서 양 팀 모두 고를 수 없어 픽과 밴은 겹치지 않고, 둘의 합은 "밴됐거나 우리 팀이 고른 판의 비율"이 됩니다. 몇몇 영웅에 몰리는 분포라 로그를 씌운 뒤 z-점수로 바꿉니다.
        - 성능 = 수축 승률. 픽률이 낮을수록 승률을 비교군 평균 쪽으로 끌어당겨, 적게 쓰인 영웅의 승률이 튀어 상위로 오르는 것을 막습니다.
        - 가중치 0.65는 존재감을 주축으로 삼는다는 정의에서 정한 값입니다. 0.55~0.75 사이로 바꾸면 영웅 열에 하나 남짓이 한 칸 움직이고, 두 칸 이상 움직이는 영웅은 없습니다.

        **등급**
        - 분위수로 나눠 주지 않고 점수의 절대 기준으로 매깁니다. 비교군 안의 격차가 작으면 S나 D가 없을 수 있습니다.
        - S 1.25 이상 · A 0.50 이상 1.25 미만 · B -0.50 초과 0.50 미만 · C -1.00 초과 -0.50 이하 · D -1.00 이하
        - D 경계만 -1.25가 아니라 -1.00인 이유: 픽률·밴률은 0% 아래로 내려갈 수 없어 존재감 점수가 아래쪽으로 덜 퍼집니다.

        **데이터와 한계**
        - 넥슨 한국 서버 통계입니다. 넥슨은 현재 패치 동안의 경기를 누적 집계해 며칠 간격으로 갱신하고, 여기서는 그 최신본을 씁니다. 하루치 경기만 보는 것이 아닙니다.
        - 전장별 승률은 추정 게임 수가 적을수록 같은 티어 전체 전장 승률 쪽으로 끌어당깁니다. 표본이 부족한 전장 조합은 흐리게 표시하고 랭크를 매기지 않습니다(`-`).
        - 픽률 1.0% 미만 영웅은 저픽률 경고를 함께 표시합니다.
        - 승률에는 영웅의 강함만이 아니라 그 영웅을 고른 사람(숙련도, 상황에 맞춘 픽)의 결과도 섞여 있습니다. 경기별 기록이 없는 집계 데이터라 이 편향은 보정하지 못합니다.
        """
    )

with st.expander("메타 유형 라벨은 뭔가요?"):
    st.markdown(
        """
        랭크와 별개로, 두 축이 한쪽으로 크게 치우친 영웅에만 붙습니다. 기준은 비교군 안의 z-점수입니다.

        - `메타 지배` (존재감 1.25 이상, 성능 0.75 이상): 많이 픽·밴되고 실제로도 잘 이기는 핵심 메타 영웅입니다.
        - `과열 주의` (픽률 1.25 이상, 성능 -0.25 이하): 많이 픽되지만 승률로는 검증되지 않는 영웅입니다. 랭크가 높아도 승률은 평균 이하일 수 있습니다.
        - `밴 압박` (밴률 1.5 이상, 픽률 0 미만): 픽은 적지만 밴으로 강하게 의식되는 영웅입니다.
        - `저평가 픽` (존재감 0.5 미만, 성능 1.25 이상): 덜 쓰이지만 수축 승률로 봐도 성능이 매우 뚜렷한 영웅입니다.
        - `전문가 픽` (픽률 -1.0 이하, 수축 전 승률 1.0 이상): 적게 쓰이지만 고른 사람은 잘 이기는 영웅입니다. 영웅이 강해서라기보다 숙련자가 고르기 때문일 수 있습니다.
        - `비주류` (존재감 -1.25 이하, 성능 -0.25 이하): 존재감도 성능 신호도 약한 영웅입니다.
        - 여러 조건에 걸리면 위에 있는 라벨이 붙습니다. 어디에도 걸리지 않으면 `보통`이라 라벨을 달지 않습니다.
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
