import streamlit as st
import pandas as pd
import html
import os
import re
from app_data import (
    DATA_CACHE_TTL,
    get_hero_banner_art,
    get_hero_color,
    get_hero_subrole,
    get_map_image_url,
    load_latest_balance_patch_note,
    load_latest_patch_ai_analysis,
    load_latest_stats,
    read_data_parquet,
    translate_role_name,
    translate_subrole_name,
    translate_tier_name,
)
from ui import (
    COLS_ART_KPI,
    GAP,
    page_shell,
    section,
    resolve_tier,
    GLOBAL_GOOD_COLOR,
    GLOBAL_INFO_COLOR,
    GLOBAL_DANGER_COLOR,
    GLOBAL_MUTED_TEXT_COLOR,
    GLOBAL_WARN_COLOR,
    render_hero_showcase,
    MINOR_PERK_COLOR,
)

_shell = page_shell(
    page_key="detail",
    title="영웅 상세 리포트",
    badge="Hero Deep Dive",
    filters=("tier",),
)
_shell.__enter__()
PERK_DATA_PATH = os.path.join("data", "latest", "latest_perks.parquet")
DEFAULT_PERK_IMAGE_URL = "https://dummyimage.com/48x48/1f2937/94a3b8.png&text=Perk"


def normalize_hero_key(hero_name):
    text = str(hero_name).strip().lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", text)


@st.cache_data(ttl=DATA_CACHE_TTL)
def load_hero_perk_data():
    df = read_data_parquet(PERK_DATA_PATH)
    if df is None or df.empty:
        return pd.DataFrame()

    required_cols = {"hero", "perk_type", "perk_name", "pick_rate"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    if "update_date" in df.columns and not df.empty:
        df["update_date"] = df["update_date"].astype(str)
        latest_date = df["update_date"].max()
        df = df[df["update_date"] == latest_date].copy()

    if "perk_description" not in df.columns:
        df["perk_description"] = ""

    df["hero_norm"] = df["hero"].astype(str).map(normalize_hero_key)
    df["perk_type"] = df["perk_type"].astype(str).str.lower()
    df["pick_rate"] = pd.to_numeric(df["pick_rate"], errors="coerce")
    return df


def get_hero_perk_rows(hero_name):
    perks_df = load_hero_perk_data()
    if perks_df.empty:
        return {"minor": [], "major": []}

    hero_norm = normalize_hero_key(hero_name)
    hero_perks = perks_df[perks_df["hero_norm"] == hero_norm].copy()
    if hero_perks.empty:
        return {"minor": [], "major": []}

    hero_perks = hero_perks.sort_values("pick_rate", ascending=False)
    minor_rows = hero_perks[hero_perks["perk_type"] == "minor"].head(2).to_dict("records")
    major_rows = hero_perks[hero_perks["perk_type"] == "major"].head(2).to_dict("records")
    return {"minor": minor_rows, "major": major_rows}


hero_from_query = st.session_state.get("detail_hero") or st.query_params.get("hero")
if isinstance(hero_from_query, list):
    hero_from_query = hero_from_query[0] if hero_from_query else None

if not hero_from_query:
    st.warning("영웅이 선택되지 않았습니다. 메인 또는 분포 페이지에서 영웅을 선택해 주세요.")
    st.stop()

hero_name = str(hero_from_query)

df_raw = load_latest_stats()
hero_summary_df = df_raw[(df_raw["hero"].astype(str) == hero_name) & (df_raw["map"] == "all-maps")].copy()

if hero_summary_df.empty:
    st.warning("선택한 영웅 데이터를 찾을 수 없습니다.")
    st.stop()

tier_candidates = sorted(
    t for t in hero_summary_df["data_tier"].dropna().astype(str).unique().tolist()
    if t != "All"
)
if "All" not in tier_candidates:
    tier_candidates = ["All"] + tier_candidates
# 티어는 사이드바 전역 필터. 표에서 ?tier= 로 넘어온 값이 있으면 전역 선택을
# 거기에 맞춰준다(링크를 눌러 들어온 의도가 우선).
_incoming = str(st.session_state.pop("detail_tier", "") or st.query_params.get("tier", ""))
if _incoming and _incoming in tier_candidates:
    st.session_state["selected_tier"] = _incoming
selected_tier = resolve_tier(tier_candidates)

hero_tier_df = hero_summary_df[hero_summary_df["data_tier"] == selected_tier].copy()
if hero_tier_df.empty:
    hero_row = hero_summary_df.sort_values("total_score", ascending=False).iloc[0]
else:
    hero_row = hero_tier_df.sort_values("total_score", ascending=False).iloc[0]

def _fmt_percent(value):
    numeric_value = pd.to_numeric(value, errors="coerce")
    return "-" if pd.isna(numeric_value) else f"{numeric_value:.1f}%"


def _fmt_score(value):
    numeric_value = pd.to_numeric(value, errors="coerce")
    return "-" if pd.isna(numeric_value) else f"{numeric_value:+.2f}"


rank_value = html.escape(str(hero_row.get("rank", "-")))
score_strength_raw = str(hero_row.get("score_strength", "보통") or "보통")
score_strength = html.escape(score_strength_raw)
score_strength_class = {
    "메타 지배": "hero-score-dominant",
    "과열 주의": "hero-score-overheated",
    "과열주의": "hero-score-overheated",
    "밴 압박": "hero-score-ban-pressure",
    "밴압박": "hero-score-ban-pressure",
    "저평가 픽": "hero-score-underrated",
    "저평가픽": "hero-score-underrated",
    "전문가 픽": "hero-score-expert",
    "전문가픽": "hero-score-expert",
    "비주류": "hero-score-niche",
}.get(score_strength_raw)

# 지시서 STEP 5: 나란히 놓인 5개 카드를 페이지1 과 같은 HERO 카드 1개로 통합.
# 워터마크만 종합 점수로 바꾼다. 단위는 <span class="unit"> 로 분리해 줄바꿈을 막는다.
def _stat(value, suffix="%"):
    v = pd.to_numeric(value, errors="coerce")
    return "-" if pd.isna(v) else f"{v:.1f}<span class='unit'>{suffix}</span>"


_score_val = pd.to_numeric(hero_row.get("total_score"), errors="coerce")
render_hero_showcase(
    hero_name=hero_name,
    art=get_hero_banner_art(hero_name),
    accent=get_hero_color(hero_name),
    watermark="-" if pd.isna(_score_val) else f"{_score_val:+.2f}",
    eyebrow="Hero Deep Dive",
    meta=f"{translate_tier_name(selected_tier)} · "
         f"{translate_role_name(str(hero_row.get('role', '')))} · "
         f"랭크 {hero_row.get('rank', '-')} · {score_strength_raw}",
    stats=[
        ("승률", _stat(hero_row.get("win_rate"))),
        ("픽률", _stat(hero_row.get("pick_rate"))),
        ("밴률", _stat(hero_row.get("ban_rate"))),
        ("종합 점수", "-" if pd.isna(_score_val) else f"{_score_val:+.2f}"),
    ],
)

left_col, right_col = st.columns(COLS_ART_KPI, gap=GAP)

with left_col:
    # 2차 지시서 D-7: 초상화 카드 / 이름 / 역할 배지는 상단 HERO 카드와 정보가 100% 중복이라
    # 제거했다. 하위 역할 정보만 살려 PERKS 위에 한 줄로 둔다.
    subrole = get_hero_subrole(hero_name)
    if subrole:
        st.markdown(
            f"<div class='eyebrow' style='margin-bottom:8px;'>"
            f"하위 역할 · {html.escape(translate_subrole_name(subrole))}</div>",
            unsafe_allow_html=True,
        )

    balance_patch_note = load_latest_balance_patch_note()
    patch_analysis = load_latest_patch_ai_analysis(balance_patch_note.get("id") if balance_patch_note else None)
    hero_ai_rows = []
    if patch_analysis:
        for group_label, rows in [
            ("직접 변경", patch_analysis.get("direct_hero_impacts") or []),
            ("간접 영향", patch_analysis.get("indirect_hero_impacts") or []),
        ]:
            for row in rows:
                if isinstance(row, dict) and str(row.get("hero")) == hero_name:
                    hero_ai_rows.append((group_label, row))

    if patch_analysis and hero_ai_rows:
        phase = html.escape(str(patch_analysis.get("analysis_phase") or "관찰 단계"))
        patch_title = html.escape(str((balance_patch_note or {}).get("title") or "최근 밸런스 패치"))
        sentence = html.escape(str(hero_ai_rows[0][1].get("display_sentence") or hero_ai_rows[0][1].get("reason") or ""))
        group_label = html.escape(hero_ai_rows[0][0])
        st.markdown(
            f'<div class="hero-ai-note">'
            f'<div class="hero-ai-kicker">AI Hero Note</div>'
            f'<div class="hero-ai-title">최근 밸런스 패치 요약 · {group_label}</div>'
            f'<div class="hero-ai-meta">{patch_title} · {phase}</div>'
            f'<div class="hero-ai-body">{sentence}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    perk_rows = get_hero_perk_rows(hero_name)

    def render_perk_line(perks, line_title, accent_color):
        if not perks:
            return (
                f'<div class="perk-empty">'
                f'{line_title}: 특전 데이터 없음'
                f'</div>'
            )

        numeric_rates = pd.to_numeric(
            [perk.get("pick_rate") for perk in perks],
            errors="coerce",
        )
        best_idx = int(numeric_rates.argmax()) if len(numeric_rates) and pd.notna(numeric_rates).any() else -1

        cards = []
        for idx, perk in enumerate(perks):
            perk_name = html.escape(str(perk.get("perk_name", "-")))
            raw_description = perk.get("perk_description", "")
            if pd.isna(raw_description) or not str(raw_description).strip():
                raw_description = "상세 설명 데이터가 없습니다."
            perk_description = html.escape(str(raw_description).strip())
            perk_rate = perk.get("pick_rate")
            if pd.notna(perk_rate):
                perk_rate_text = f"{float(perk_rate):.0f}%"
            else:
                perk_rate_text = "-"
            is_best = idx == best_idx

            perk_image_url = perk.get("perk_image_raw_url") or perk.get("perk_image_url") or DEFAULT_PERK_IMAGE_URL
            perk_image_url = html.escape(str(perk_image_url))

            # 지시서 STEP 5: 아이콘 확대 + 선호도 프로그레스 바. 퍽 이름은 nowrap.
            bar_width = float(perk_rate) if pd.notna(perk_rate) else 0.0
            cards.append(
                f'<div class="perk-card" tabindex="0" aria-label="{perk_name} 특전 상세 설명">'
                f'<img class="perk-icon" src="{perk_image_url}" alt="" />'
                f'<div class="perk-main">'
                f'<div class="perk-name nowrap">{perk_name}</div>'
                f'<div class="perk-bar"><span style="width:{min(max(bar_width, 0), 100):.0f}%;'
                f'background:{accent_color if is_best else "rgba(255,255,255,0.28)"};"></span></div>'
                f'</div>'
                f'<div class="perk-rate nowrap" style="color:{accent_color if is_best else GLOBAL_MUTED_TEXT_COLOR};">{perk_rate_text}</div>'
                f'<div class="perk-tooltip" role="tooltip">'
                f'<div class="perk-tooltip-head">'
                f'<img class="perk-tooltip-icon" src="{perk_image_url}" alt="" />'
                f'<div class="perk-tooltip-name">{perk_name}</div>'
                f'<div class="perk-tooltip-rate">{perk_rate_text}</div>'
                f'</div>'
                f'<div class="perk-tooltip-description">{perk_description}</div>'
                f'</div>'
                f'</div>'
            )

        return (
            f'<div style="margin-top:10px;">'
            f'<div style="font-size:0.72rem;font-weight:800;letter-spacing:0.04em;color:{accent_color};text-transform:uppercase;">{line_title}</div>'
            f'{"".join(cards)}'
            f'</div>'
        )

    perk_html = (
        '<div style="margin-top:12px;">'
        + render_perk_line(perk_rows["minor"], "Minor Perks", MINOR_PERK_COLOR)
        + render_perk_line(perk_rows["major"], "Major Perks", GLOBAL_WARN_COLOR)
        + '</div>'
    )
    st.markdown(perk_html, unsafe_allow_html=True)

with right_col:
    section("전장별 승률", "이 영웅이 강한 전장과 약한 전장")

    hero_map_df = df_raw[
        (df_raw["hero"].astype(str) == hero_name)
        & (df_raw["map"] != "all-maps")
        & (df_raw["data_tier"].astype(str) == selected_tier)
    ].sort_values("win_rate", ascending=False)

    if hero_map_df.empty:
        st.info("이 티어의 전장별 데이터가 없습니다.")
    else:
        def make_map_card(row, badge_label=None, badge_color=GLOBAL_GOOD_COLOR):
            m_id = str(row["map"])
            m_name = html.escape(str(row.get("map_name", m_id)))
            w_rate = float(row["win_rate"])
            p_rate = float(row["pick_rate"])
            rate_color = GLOBAL_GOOD_COLOR if w_rate >= 50 else GLOBAL_DANGER_COLOR
            bg_image = html.escape(get_map_image_url(m_id))
            badge = (
                f'<div class="hmap-badge" style="background:{badge_color}22;border-color:{badge_color}88;color:{badge_color};">{badge_label}</div>'
                if badge_label else ""
            )
            return (
                f'<div class="hmap-card" style="background-image:url(\'{bg_image}\');">'
                f'<div class="hmap-scrim"></div>'
                f'{badge}'
                f'<div class="hmap-left">'
                f'<div class="hmap-name">{m_name}</div>'
                f'<div class="hmap-sub">픽률 {p_rate:.1f}%</div>'
                f'</div>'
                f'<div class="hmap-right">'
                f'<div class="hmap-rate" style="color:{rate_color};">{w_rate:.1f}%</div>'
                f'<div class="hmap-sub">승률</div>'
                f'</div></div>'
            )

        top_win_df = hero_map_df.nlargest(2, "win_rate")
        top_pick_df = hero_map_df.nlargest(2, "pick_rate")

        st.markdown("**Top Winrate**")
        st.markdown(
            "".join(make_map_card(row, "TOP WIN", GLOBAL_GOOD_COLOR) for _, row in top_win_df.iterrows()),
            unsafe_allow_html=True,
        )

        st.markdown("**Top Pickrate**")
        st.markdown(
            "".join(make_map_card(row, "TOP PICK", GLOBAL_INFO_COLOR) for _, row in top_pick_df.iterrows()),
            unsafe_allow_html=True,
        )

        with st.expander(f"모두 보기 ({len(hero_map_df)}개 전장)"):
            st.markdown(
                "".join(make_map_card(row) for _, row in hero_map_df.iterrows()),
                unsafe_allow_html=True,
            )

_shell.__exit__(None, None, None)
