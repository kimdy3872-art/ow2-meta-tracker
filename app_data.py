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
    "presence_score",
    "shrunk_win_rate",
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
    "Ana": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/985b06beae46b7ba3ca87d1512d0fc62ca7f206ceca58ef16fc44d43a1cc84ed.png",
    "Anran": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/2c38b41d79a1ce9a08b9ad8eb7edf3ff819bd448af16a5815be8c7fdb7203aa0.png",
    "Ashe": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4076bbaa2eb52a0bfe612434071e56e7702d5454473dbbea2f9e392a9d997a94.png",
    "Baptiste": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/d4e6f1ca45d9f88fa89260787397f141a6f007b14e5b26698883b6a17bab9680.png",
    "Bastion": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4ede795c2a681aaccfa72d0c901cba0cb8a2c292fd6a97b2ba9faed161c2d184.png",
    "Brigitte": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/795fba91376d87d441a7f359ae12a3175dfa95825ccc4414cc6b95b129fc4cb0.png",
    "Cassidy": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/9240cd64cc8ef58df9acbf55204ab1b5d8578f743fda5931f0dbccbd75ab841b.png",
    "D.Va": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/df5a5532862d9292634fb3dc0e51a4705aa601de65e5e815513ccc663d84de56.png",
    "Domina": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/1161c112292c56c052c0ae711792fcde06e3251b98bc9709e582dd7585b5dcd6.png",
    "Doomfist": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ff5c54f43ad253c7faeda9c4ed31d42582ea6b19205d197866f3dd0c0aa14c16.png",
    "Echo": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/d4f2d5b0c2b7e82d61353186c5f23152ccba9d3569b50839aa580dca3e9114ba.png",
    "Emre": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/c51e2f698138861c0e3b6cfab3c3ca9d67fd709be175e7c397aa6f2649712a30.png",
    "Freja": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/811963897c352d9f178bec882d94bd0281074feee7c429c5145b6b8ea8ebe862.png",
    "Genji": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/156b12c20b1aea872c1eeb5bb37a7de1047b2ab30ecefd0663a8925badde1ea8.png",
    "Hanzo": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/78b61c3e806fb26b02b8980fba62189155074fc15bd865b0883268e546030be5.png",
    "Hazard": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ca48b96dbae6ea7f58ce8a5e73513c8c62b1685bdbf258020fb78bb21a008b5f.png",
    "Illari": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ce42d1455e03e79f321345fea84b27a8918b5db8bd7ab9b2ca9e569606ede9e4.png",
    "Jetpack Cat": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/03a184cd0de27091e0099ac22635ad9615a8f6997881a5c25cc5f2444764f729.png",
    "Junker Queen": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/06eeecb359f311f43a8f5121d4f9f3a93c565d70b30e94ef543c05596c9a39dc.png",
    "Junkrat": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/7660b9fc6f25f30858fdd8797fe0d52b2306f1e78fef99843f58a274e69af046.png",
    "Juno": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/c0167d251e57b0aa2b1e16c37d87f0e7c77263db9dd0503d77b5f2589bf3e4a0.png",
    "Kiriko": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/408603fe037e8576078eaac5eab2fb251489ced4003b11f5f522776d43d0b83d.png",
    "Lifeweaver": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/3376515cebed0904012e67e956f6d1b9c12e03da642845eeaf787b7e4c7b339d.png",
    "Lúcio": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/040bb13f5123ab93faad2f95627ba184608aef4b2469a4d3003859c7087df044.png",
    "Mauga": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/33d39bb439c08975197fc52eff4874716839711b5356c4fdc174f9c24bac1d0e.png",
    "Mei": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4a55ced3bd597fb08e0fde9dc007f8543ac616ba98ca3db9b0e4d871a8ae17f8.png",
    "Mercy": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/3bfb8bd8ec827e53d870f1238ab73d8aa1f5dbfbcfaaf7f96ffcd35b5c6102ab.png",
    "Mizuki": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/a9733c2367e0cbd70b9316fd2e1e17028653ec56d0051ea6ff098531dc4f99fc.png",
    "Moira": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/f48f8485056d5d00dad195859188d23e50f7126b8b08b5646f46ef1b42f5e1de.png",
    "Orisa": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/a73958a28551f5254f3ab3f97c5f5f8d698a95c0b6a515d1a2b1caac169205a6.png",
    "Pharah": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/60ac2d5de4a6d34644d8872233da402f1436c87f804bb11a21661bb30bf4a51f.png",
    "Ramattra": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ddef7c9fb8ce4256e8508196b486f81950efe7aaa6cf27fec4668beb4cd15774.png",
    "Reaper": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/dc6ff07ac790c00dc95a40882449617bb6e0e38906b353a630cffe0c815270a9.png",
    "Reinhardt": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/551fbe070c16fdfcc17f7f1de63af22c53e7d2f1340fc2f3172441504527bc4e.png",
    "Roadhog": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/89ddf07e4b619ed96169042e296a1b8856d102746f35add88284b44a9a5a6a03.png",
    "Shion": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/070481cf871590a2b45a51d1335f9fe3d65eb4e4d361ecdd998b34fae2ed65d5.png",
    "Sierra": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4bfd3d8b95844231115cb5bf4db03344c71bc3e865189c52403b2dc51438e63a.png",
    "Sigma": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/a4c032fa466c9a6d9c6974747635d7ef910027f91cd58892af0c899db565f92d.png",
    "Sojourn": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/82b8c1b8765dcb9a0ba16e343c3516bf324c771ac81e9878473280216e70a889.png",
    "Soldier: 76": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/c93b5f0a528c40473188f77cc2a267aee7d5b6cf5c9e104105d634b4388674e2.png",
    "Sombra": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/47727b02a16e3bd7b2447d86ae1edf11587bc320b2aecb4f2f16a7ca4ad4e8a0.png",
    "Symmetra": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ebec57e8bd68b3d4383edfeb34f8f52dd0b94a6467d594c2fee722e8a97c32aa.png",
    "Torbjörn": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ce17118cedc29b0d2ac1e059666bed36b9531c85079b0b894bb402d12c917ba9.png",
    "Tracer": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4504f6f15cb3feaa92ecd38e01dcf751cb5abdac2e0bb52d0555727e53277502.png",
    "Vendetta": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/cf8ffb52b6f315546d5e94e9d6defad5a2c570798776956de23f47536f9529da.png",
    "Venture": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/dcab9123f5f55df22e54d4e797de43c71b917e0149dd059a7fd6136f48464cd0.png",
    "Widowmaker": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/6e4702b45f196aaf51555cf57327322721f45458b17f5f0643ed008a88378259.png",
    "Winston": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/46a10db3aa908c590ddc4e7606376a88143d1f1306ecfbea043263040f9529a5.png",
    "Wrecking Ball": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/9ef1d58867136e0b26f928d896000b9dab216118f6e2f59e53f2e975e1e27afa.png",
    "Wuyang": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4959500b495b35c0908be2abda56b53f2601b2c5cc39a1cfde8df1bffd38d66d.png",
    "Zarya": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/9b6f63cc66ddf9d5e0862173c733cc0d2e574c5c89357798d91b93b2f95a7080.png",
    "Zenyatta": "https://d15f34w2p8l1cc.cloudfront.net/overwatch/7d1546b1541a8afc39353f9337a408d6275a141b0432b7e560ef61579996b0fc.png",
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
    "paraíso": "paraiso",
    "esperança": "esperanca",
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
    return (
        load_hero_portrait_map().get(api_name)
        or HERO_PORTRAIT_FALLBACKS.get(api_name)
        or HERO_PORTRAIT_FALLBACKS.get(hero_name)
    )


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
    map_id = str(map_id)
    alias = MAP_ID_ALIAS.get(map_id, map_id)
    image_map = load_map_image_map()
    url = image_map.get(alias) or image_map.get(map_id)
    if url:
        return url
    if alias and alias != "all-maps":
        return f"https://overfast-api.tekrop.fr/static/maps/{alias}.jpg"
    return f"https://dummyimage.com/600x100/1f2937/475569.png&text={map_id}"
