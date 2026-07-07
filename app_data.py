import json
import os
import urllib.request

import pandas as pd
import streamlit as st


ROLE_LABELS = {
    "All": "전체 포지션",
    "Tank": "돌격",
    "Damage": "공격",
    "Support": "지원",
    "Unknown": "미분류",
}
SUBROLE_LABELS = {
    "bruiser": "투사",
    "initiator": "개시자",
    "stalwart": "강건한 자",
    "flanker": "측면 공격가",
    "recon": "수색가",
    "sharpshooter": "명사수",
    "specialist": "전문가",
    "medic": "의무관",
    "survivor": "생존왕",
    "tactician": "전술가",
}
TIER_LABELS = {
    "All": "전체 티어",
    "Bronze": "브론즈",
    "Silver": "실버",
    "Gold": "골드",
    "Platinum": "플래티넘",
    "Diamond": "다이아몬드",
    "Master": "마스터",
    "Grandmaster": "그랜드마스터",
}
TIER_ORDER = ["All", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster"]
ROLE_ORDER = ["All", "Tank", "Damage", "Support"]
NUMERIC_STATS_COLUMNS = [
    "win_rate",
    "pick_rate",
    "ban_rate",
    "win_rate_z",
    "pick_rate_log",
    "pick_rate_z",
    "ban_rate_log",
    "ban_rate_z",
    "persistence_score",
    "pick_stability_multiplier",
    "performance_score",
    "total_score",
]
PATCH_NOTES_PATH = os.path.join("data", "patch_notes", "patch_notes.json")
PATCH_AI_ANALYSIS_PATH = os.path.join("data", "patch_notes", "patch_ai_analysis.json")

HERO_NAME_TO_API_NAME = {
    "D.VA": "D.Va",
    "겐지": "Genji",
    "도미나": "Domina",
    "둠피스트": "Doomfist",
    "라마트라": "Ramattra",
    "라이프위버": "Lifeweaver",
    "라인하르트": "Reinhardt",
    "레킹볼": "Wrecking Ball",
    "로드호그": "Roadhog",
    "루시우": "Lúcio",
    "리퍼": "Reaper",
    "마우가": "Mauga",
    "메르시": "Mercy",
    "메이": "Mei",
    "모이라": "Moira",
    "미즈키": "Mizuki",
    "바스티온": "Bastion",
    "바티스트": "Baptiste",
    "벤데타": "Vendetta",
    "벤처": "Venture",
    "브리기테": "Brigitte",
    "소전": "Sojourn",
    "솔저: 76": "Soldier: 76",
    "솜브라": "Sombra",
    "시그마": "Sigma",
    "시메트라": "Symmetra",
    "시에라": "Sierra",
    "시온": "Shion",
    "아나": "Ana",
    "안란": "Anran",
    "애쉬": "Ashe",
    "에코": "Echo",
    "엠레": "Emre",
    "오리사": "Orisa",
    "우양": "Wuyang",
    "위도우메이커": "Widowmaker",
    "윈스턴": "Winston",
    "일리아리": "Illari",
    "자리야": "Zarya",
    "정커퀸": "Junker Queen",
    "정크랫": "Junkrat",
    "제트팩 캣": "Jetpack Cat",
    "젠야타": "Zenyatta",
    "주노": "Juno",
    "캐서디": "Cassidy",
    "키리코": "Kiriko",
    "토르비욘": "Torbjörn",
    "트레이서": "Tracer",
    "파라": "Pharah",
    "프레야": "Freja",
    "한조": "Hanzo",
    "해저드": "Hazard",
}
HERO_PORTRAIT_FALLBACKS = {
    "시온": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/070481cf871590a2b45a51d1335f9fe3d65eb4e4d361ecdd998b34fae2ed65d5.png",
}
# Blizzard 공식 영웅 목록의 하위 역할 분류.
HERO_SUBROLES = {
    "D.VA": "initiator",
    "겐지": "flanker",
    "도미나": "stalwart",
    "둠피스트": "initiator",
    "라마트라": "stalwart",
    "라이프위버": "medic",
    "라인하르트": "stalwart",
    "레킹볼": "initiator",
    "로드호그": "bruiser",
    "루시우": "tactician",
    "리퍼": "flanker",
    "마우가": "bruiser",
    "메르시": "medic",
    "메이": "specialist",
    "모이라": "medic",
    "미즈키": "survivor",
    "바스티온": "specialist",
    "바티스트": "tactician",
    "벤데타": "flanker",
    "벤처": "flanker",
    "브리기테": "survivor",
    "소전": "sharpshooter",
    "솔저: 76": "specialist",
    "솜브라": "recon",
    "시그마": "stalwart",
    "시메트라": "specialist",
    "시에라": "recon",
    "시온": "flanker",
    "아나": "tactician",
    "안란": "flanker",
    "애쉬": "sharpshooter",
    "에코": "recon",
    "엠레": "specialist",
    "오리사": "bruiser",
    "우양": "survivor",
    "위도우메이커": "sharpshooter",
    "윈스턴": "initiator",
    "일리아리": "survivor",
    "자리야": "bruiser",
    "정커퀸": "stalwart",
    "정크랫": "specialist",
    "제트팩 캣": "tactician",
    "젠야타": "tactician",
    "주노": "survivor",
    "캐서디": "sharpshooter",
    "키리코": "medic",
    "토르비욘": "specialist",
    "트레이서": "flanker",
    "파라": "recon",
    "프레야": "recon",
    "한조": "sharpshooter",
    "해저드": "initiator",
}
MAP_ID_ALIAS = {
    "paraiso": "paraíso",
    "esperanca": "esperança",
}


def translate_role_name(role_name):
    return ROLE_LABELS.get(str(role_name), str(role_name))


def get_hero_subrole(hero_name):
    return HERO_SUBROLES.get(str(hero_name))


def translate_subrole_name(subrole_name):
    return SUBROLE_LABELS.get(str(subrole_name), str(subrole_name))


def translate_tier_name(tier_name):
    return TIER_LABELS.get(str(tier_name), str(tier_name))


def is_degenerate_snapshot(snapshot_df):
    if snapshot_df.empty:
        return True

    map_rows = snapshot_df[snapshot_df["map"].astype(str) != "all-maps"].copy()
    if map_rows.empty:
        return False

    map_rows["win_rate"] = pd.to_numeric(map_rows.get("win_rate"), errors="coerce")
    map_rows["pick_rate"] = pd.to_numeric(map_rows.get("pick_rate"), errors="coerce")

    group_cols = ["hero", "data_tier"]
    win_nunique = map_rows.groupby(group_cols)["win_rate"].nunique(dropna=True)
    pick_nunique = map_rows.groupby(group_cols)["pick_rate"].nunique(dropna=True)
    if win_nunique.empty or pick_nunique.empty:
        return False

    no_win_variance_ratio = (win_nunique <= 1).mean()
    no_pick_variance_ratio = (pick_nunique <= 1).mean()
    return no_win_variance_ratio >= 0.98 and no_pick_variance_ratio >= 0.98


@st.cache_data
def load_latest_stats():
    stats_path = os.path.join("data", "latest", "latest_tier.parquet")
    df = pd.read_parquet(stats_path)

    if "update_date" in df.columns and not df.empty:
        df["update_date"] = df["update_date"].astype(str)
        selected_date = None
        for candidate_date in sorted(df["update_date"].dropna().unique(), reverse=True):
            candidate_df = df[df["update_date"] == candidate_date].copy()
            if not is_degenerate_snapshot(candidate_df):
                selected_date = candidate_date
                break

        if selected_date is None:
            selected_date = df["update_date"].max()

        df = df[df["update_date"] == selected_date].copy()

    if "map" not in df.columns:
        df["map"] = "all-maps"
    if "map_name" not in df.columns:
        df["map_name"] = df["map"]
    if "role" not in df.columns:
        df["role"] = "Unknown"

    for col in NUMERIC_STATS_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_ordered_tiers(df, include_all=True):
    raw_tiers = set(df["data_tier"].dropna().astype(str).unique().tolist()) if "data_tier" in df.columns else set()
    ordered = [tier for tier in TIER_ORDER if tier in raw_tiers or (include_all and tier == "All")]
    extras = sorted(tier for tier in raw_tiers if tier not in TIER_ORDER)
    return ordered + extras


def get_ordered_roles(df, include_all=True):
    raw_roles = set(df["role"].dropna().astype(str).unique().tolist()) if "role" in df.columns else set()
    ordered = [role for role in ROLE_ORDER if role in raw_roles or (include_all and role == "All")]
    extras = sorted(role for role in raw_roles if role not in ROLE_ORDER)
    return ordered + extras


def get_initial_index(options, preferred):
    if preferred in options:
        return options.index(preferred)
    return 0


@st.cache_data
def load_hero_portrait_map():
    url = "https://overfast-api.tekrop.fr/heroes"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            heroes = json.load(resp)
    except Exception:
        return {}
    return {
        hero.get("name"): hero.get("portrait")
        for hero in heroes
        if hero.get("name") and hero.get("portrait")
    }


def get_hero_image_url(hero_name):
    api_name = HERO_NAME_TO_API_NAME.get(hero_name, hero_name)
    return load_hero_portrait_map().get(api_name) or HERO_PORTRAIT_FALLBACKS.get(hero_name)


def _load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


@st.cache_data
def load_latest_patch_note():
    notes = _load_json_list(PATCH_NOTES_PATH)
    if not notes:
        return None
    return max(
        notes,
        key=lambda row: (
            str(row.get("patch_date", "")),
            str(row.get("created_at", "")),
        ),
    )


@st.cache_data
def load_latest_balance_patch_note():
    notes = _load_json_list(PATCH_NOTES_PATH)
    balance_notes = [
        row for row in notes
        if row.get("has_hero_updates") or row.get("affected_heroes")
    ]
    if not balance_notes:
        return None
    return max(
        balance_notes,
        key=lambda row: (
            str(row.get("patch_date", "")),
            str(row.get("created_at", "")),
        ),
    )


@st.cache_data
def load_latest_patch_ai_analysis(patch_note_id=None):
    analyses = _load_json_list(PATCH_AI_ANALYSIS_PATH)
    if patch_note_id:
        analyses = [
            row for row in analyses
            if str(row.get("patch_note_id", "")) == str(patch_note_id)
        ]
    if not analyses:
        return None
    return max(
        analyses,
        key=lambda row: (
            str(row.get("analysis_date", "")),
            str(row.get("created_at", "")),
        ),
    )


@st.cache_data
def load_map_image_map():
    url = "https://overfast-api.tekrop.fr/maps"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            maps_data = json.load(resp)
    except Exception:
        return {}
    return {
        map_item.get("key", "").lower(): map_item.get("screenshot")
        for map_item in maps_data
        if map_item.get("key") and map_item.get("screenshot")
    }


def get_map_image_url(map_id):
    alias = MAP_ID_ALIAS.get(map_id, map_id)
    image_map = load_map_image_map()
    url = image_map.get(alias) or image_map.get(map_id)
    return url if url else f"https://dummyimage.com/600x100/1f2937/475569.png&text={map_id}"
