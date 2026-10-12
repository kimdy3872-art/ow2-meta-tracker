import glob
import io
import json
import os
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st


# --- 데이터 소스 -----------------------------------------------------------
# 배포(Streamlit Community Cloud)에서는 keep-alive로 앱 프로세스가 계속 warm 상태라
# 예전처럼 슬립→콜드스타트로 새 커밋을 pull 하지 않는다. 그 결과 로컬 파일이 배포 시점에
# 고정돼 데이터가 멈춘다. 이를 피하려고 데이터를 GitHub raw에서 직접 읽고(항상 최신),
# 짧은 TTL 캐시로 감싼다. 로컬 개발은 OW2_LOCAL_DATA=1 로 로컬 파일을 쓴다.
DATA_REPO = os.environ.get("OW2_DATA_REPO", "kimdy3872-art/ow2-meta-tracker")
DATA_BRANCH = os.environ.get("OW2_DATA_BRANCH", "main")
DATA_RAW_BASE = f"https://raw.githubusercontent.com/{DATA_REPO}/{DATA_BRANCH}"
USE_LOCAL_DATA = os.environ.get("OW2_LOCAL_DATA", "").strip().lower() in {"1", "true", "yes", "on"}
DATA_HTTP_TIMEOUT = int(os.environ.get("OW2_DATA_HTTP_TIMEOUT", "20"))
# 데이터 캐시 TTL(초). 데이터는 매일 갱신되므로 30분이면 충분히 최신.
DATA_CACHE_TTL = int(os.environ.get("OW2_DATA_CACHE_TTL", "1800"))
# 통계 출처를 넥슨 한국 서버로 바꾼 첫 스냅샷 날짜. 그 전은 Blizzard 아시아 서버 값이다.
STATS_SOURCE_SINCE = "2026-09-10"


def _remote_url(relpath):
    return f"{DATA_RAW_BASE}/{relpath.replace(os.sep, '/')}"


def _fetch_bytes(relpath):
    req = urllib.request.Request(_remote_url(relpath), headers={"User-Agent": "ow2meta-app"})
    with urllib.request.urlopen(req, timeout=DATA_HTTP_TIMEOUT) as resp:
        return resp.read()


def read_data_parquet(relpath):
    """data/ 하위 parquet을 읽는다. 기본은 GitHub raw(항상 최신), 실패 시 로컬 폴백."""
    if USE_LOCAL_DATA:
        return pd.read_parquet(relpath) if os.path.exists(relpath) else pd.DataFrame()
    try:
        return pd.read_parquet(io.BytesIO(_fetch_bytes(relpath)))
    except Exception:
        if os.path.exists(relpath):
            try:
                return pd.read_parquet(relpath)
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


def read_data_json(relpath):
    """data/ 하위 JSON을 읽는다. 기본은 GitHub raw(항상 최신), 실패 시 로컬 폴백."""
    if not USE_LOCAL_DATA:
        try:
            return json.loads(_fetch_bytes(relpath).decode("utf-8"))
        except Exception:
            pass
    if os.path.exists(relpath):
        try:
            with open(relpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def list_data_files(prefix, suffix=".parquet"):
    """data/ 하위에서 prefix로 시작하고 suffix로 끝나는 파일 경로 목록(정렬)."""
    prefix = prefix.replace(os.sep, "/")
    if not USE_LOCAL_DATA:
        api = f"https://api.github.com/repos/{DATA_REPO}/git/trees/{DATA_BRANCH}?recursive=1"
        try:
            req = urllib.request.Request(
                api,
                headers={"User-Agent": "ow2meta-app", "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(req, timeout=DATA_HTTP_TIMEOUT) as resp:
                tree = json.load(resp).get("tree", [])
            return sorted(
                node["path"]
                for node in tree
                if node.get("type") == "blob"
                and node["path"].startswith(prefix)
                and node["path"].endswith(suffix)
            )
        except Exception:
            pass  # 원격 실패 시 로컬 glob 폴백
    return sorted(glob.glob(os.path.join(prefix, "**", "*" + suffix), recursive=True))


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
    "Emerald": "에메랄드",
    "Diamond": "다이아몬드",
    "Master": "마스터",
    "Grandmaster": "그랜드마스터",
    "Champion": "챔피언",
}
# 에메랄드는 2026-08-12 신설 티어. 데이터가 들어오기 시작하면 자동으로 노출된다.
TIER_ORDER = ["All", "Bronze", "Silver", "Gold", "Platinum", "Emerald",
              "Diamond", "Master", "Grandmaster", "Champion"]
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
    "neff",
]
PATCH_NOTES_PATH = os.path.join("data", "patch_notes", "patch_notes.json")
HEROES_PATH = os.path.join("data", "latest", "heroes.json")
PATCH_AI_ANALYSIS_PATH = os.path.join("data", "patch_notes", "patch_ai_analysis.json")
META_TYPE_PRESENCE_HIGH_Z = 1.25
META_TYPE_PERFORMANCE_POSITIVE_Z = 0.75
META_TYPE_PICK_HIGH_Z = 1.25
META_TYPE_BAN_HIGH_Z = 1.5
META_TYPE_UNDERRATED_PERFORMANCE_Z = 1.25
META_TYPE_EXPERT_LOW_PICK_Z = -1.0
META_TYPE_EXPERT_HIGH_WIN_Z = 1.0
META_TYPE_NICHE_LOW_PRESENCE_Z = -1.25
META_TYPE_NICHE_MAX_PERFORMANCE_Z = -0.25
# update.py 와 같은 환경변수. 화면 랭크는 불러올 때 여기 값으로 다시 계산된다.
META_PRESENCE_WEIGHT = float(os.getenv("META_PRESENCE_WEIGHT", "0.65"))
META_PERFORMANCE_WEIGHT = round(1.0 - META_PRESENCE_WEIGHT, 4)
PRESENCE_BAN_WEIGHT = float(os.getenv("PRESENCE_BAN_WEIGHT", "1.0"))
SHRINK_MIN_PICK_RATE = 0.1
RANK_THRESHOLDS = {
    "S": 1.25,
    "A": 0.50,
    "C": -0.50,
    "D": -1.00,
}

MAP_ID_ALIAS = {
    "paraíso": "paraiso",
    "esperança": "esperanca",
}

# OverFast 가 전장 목록에는 올렸지만 스크린샷은 아직 없는 경우가 있다
# (neon-junction 은 /static/maps/neon-junction.jpg 가 404). 그대로 두면 카드가
# 깨진 이미지로 뜨므로, 받아서 저장소에 커밋해 둔 것을 대신 쓴다.
# OverFast 에 스크린샷이 올라오면 이 줄만 지우면 된다.
MAP_IMAGE_OVERRIDES = {
    "neon-junction": "static/map_art/neon-junction.webp",
}


def translate_role_name(role_name):
    return ROLE_LABELS.get(str(role_name), str(role_name))


def get_hero_subrole(hero_name):
    return _hero_meta(hero_name).get("subrole") or None


def translate_subrole_name(subrole_name):
    return SUBROLE_LABELS.get(str(subrole_name), str(subrole_name))


def tier_option_label(tier):
    """드롭다운 표시용 라벨. 뱃지 그림은 ui.icon_selectbox 가 CSS 로 얹는다."""
    return translate_tier_name(tier)


def role_option_label(role):
    return translate_role_name(role)


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


def safe_zscore(series):
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series([0] * len(series), index=series.index)
    return (series - series.mean()) / std


def assign_score_rank(scores):
    numeric_scores = pd.to_numeric(scores, errors="coerce")
    ranks = pd.Series("B", index=scores.index, dtype=object)
    ranks[numeric_scores >= RANK_THRESHOLDS["S"]] = "S"
    ranks[
        (numeric_scores >= RANK_THRESHOLDS["A"])
        & (numeric_scores < RANK_THRESHOLDS["S"])
    ] = "A"
    ranks[
        (numeric_scores <= RANK_THRESHOLDS["C"])
        & (numeric_scores > RANK_THRESHOLDS["D"])
    ] = "C"
    ranks[numeric_scores <= RANK_THRESHOLDS["D"]] = "D"
    ranks[numeric_scores.isna()] = "B"
    return ranks


def add_current_scoring_columns(df, group_key=None):
    if df.empty:
        return df
    if group_key is None:
        group_key = ["data_tier", "map", "role"]
    required_cols = {"win_rate", "pick_rate", "ban_rate", *group_key}
    if not required_cols.issubset(df.columns):
        return df

    df = df.copy()
    for col in ["win_rate", "pick_rate", "ban_rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["win_rate_z"] = df.groupby(group_key)["win_rate"].transform(safe_zscore)
    df["pick_rate_log"] = np.log1p(df["pick_rate"])
    df["pick_rate_z"] = df.groupby(group_key)["pick_rate_log"].transform(safe_zscore)
    df["ban_rate_log"] = np.log1p(df["ban_rate"])
    df["ban_rate_z"] = df.groupby(group_key)["ban_rate_log"].transform(safe_zscore)
    df["presence_log"] = np.log1p(
        df["pick_rate"] + PRESENCE_BAN_WEIGHT * df["ban_rate"]
    )
    df["presence_score"] = df.groupby(group_key)["presence_log"].transform(safe_zscore)

    # 전장별 행의 승률 보정은 같은 티어 전체 전장 값이 필요해서 update.py 가 표본 기반으로
    # 계산해 저장한다. 저장값이 없는 옛 스냅샷만 여기서 픽률 가중 수축으로 채운다.
    group_mean_win = df.groupby(group_key)["win_rate"].transform("mean")
    shrink_k = (
        df.groupby(group_key)["pick_rate"].transform("median")
        .clip(lower=SHRINK_MIN_PICK_RATE)
    )
    pick_shrunk = (
        (df["pick_rate"] * df["win_rate"] + shrink_k * group_mean_win)
        / (df["pick_rate"] + shrink_k)
    )
    stored = df["shrunk_win_rate"] if "shrunk_win_rate" in df.columns else pd.Series(np.nan, index=df.index)
    df["shrunk_win_rate"] = pd.to_numeric(stored, errors="coerce").fillna(pick_shrunk)
    df["performance_score"] = df.groupby(group_key)["shrunk_win_rate"].transform(safe_zscore)
    df["total_score"] = (
        META_PRESENCE_WEIGHT * df["presence_score"]
        + META_PERFORMANCE_WEIGHT * df["performance_score"]
    )
    df["rank"] = assign_score_rank(df["total_score"])
    if "sample_warning" in df.columns:
        df.loc[df["sample_warning"].eq("표본 부족"), "rank"] = "-"
    return df


def add_meta_type_label(df):
    required_cols = {"presence_score", "performance_score", "pick_rate_z", "win_rate_z"}
    if df.empty or not required_cols.issubset(df.columns):
        return df

    df = df.copy()
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["score_strength"] = np.select(
        [
            (df["presence_score"] >= META_TYPE_PRESENCE_HIGH_Z)
            & (df["performance_score"] >= META_TYPE_PERFORMANCE_POSITIVE_Z),
            (df["pick_rate_z"] >= META_TYPE_PICK_HIGH_Z)
            & (df["performance_score"] <= META_TYPE_NICHE_MAX_PERFORMANCE_Z),
            (df["ban_rate_z"] >= META_TYPE_BAN_HIGH_Z)
            & (df["pick_rate_z"] < 0),
            (df["presence_score"] < 0.5)
            & (df["performance_score"] >= META_TYPE_UNDERRATED_PERFORMANCE_Z),
            (df["pick_rate_z"] <= META_TYPE_EXPERT_LOW_PICK_Z)
            & (df["win_rate_z"] >= META_TYPE_EXPERT_HIGH_WIN_Z)
            & (df["performance_score"] < META_TYPE_UNDERRATED_PERFORMANCE_Z),
            (df["presence_score"] <= META_TYPE_NICHE_LOW_PRESENCE_Z)
            & (df["performance_score"] <= META_TYPE_NICHE_MAX_PERFORMANCE_Z),
        ],
        ["메타 지배", "과열 주의", "밴 압박", "저평가 픽", "전문가 픽", "비주류"],
        default="보통",
    )
    return df


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
def load_latest_stats():
    df = read_data_parquet(os.path.join("data", "latest", "latest_tier.parquet"))

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

    df = add_current_scoring_columns(df)
    df = add_meta_type_label(df)
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


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
def load_hero_meta():
    """update.py 가 OverFast 에서 받아 둔 영웅 정보. {통계와 같은 한글 이름: {key, role, subrole, portrait}}

    역할·하위 역할·초상화를 여기서 읽으므로, 새 영웅이나 역할 변경(솜브라 2026-10)에 손으로 고칠 표가 없다.
    """
    rows = read_data_json(HEROES_PATH) or []
    return {row["hero"]: row for row in rows if isinstance(row, dict) and row.get("hero")}


def _hero_meta(hero_name):
    return load_hero_meta().get(str(hero_name)) or {}


def get_hero_image_url(hero_name):
    return _hero_meta(hero_name).get("portrait") or None


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
def load_score_deltas(data_tier):
    """최근 원본 갱신 전후의 종합 점수 변화. ({영웅명: delta}, 비교 기준 날짜)

    넥슨 통계는 매일이 아니라 며칠에 한 번(패치 등) 갱신돼서, 바로 전날과 비교하면 거의
    항상 0 이다. 그래서 원본 수치(승률·픽률·밴률)가 달랐던 가장 최근 스냅샷과 비교한다.
    STATS_SOURCE_SINCE 이전은 Blizzard 아시아 서버 값이라 비교에서 뺀다(출처 변화가 변동처럼 보인다).
    비교할 스냅샷이 없으면 ({}, None).
    """
    frames = []
    for path in list_data_files(os.path.join("data", "history", "daily")):
        try:
            frames.append(read_data_parquet(path))
        except Exception:
            continue
    if not frames:
        return {}, None

    df = pd.concat(frames, ignore_index=True)
    rate_cols = ["win_rate", "pick_rate", "ban_rate"]
    needed = {"hero", "update_date", "total_score", "data_tier", "map", *rate_cols}
    if not needed.issubset(df.columns):
        return {}, None

    df["update_date"] = df["update_date"].astype(str)
    df = df[
        (df["data_tier"] == data_tier)
        & (df["map"].astype(str) == "all-maps")
        & (df["update_date"] >= STATS_SOURCE_SINCE)
    ].drop_duplicates(["update_date", "hero"], keep="last")
    by_date = {date: frame.set_index("hero").sort_index() for date, frame in df.groupby("update_date")}
    dates = sorted(by_date)
    if len(dates) < 2:
        return {}, None

    latest = by_date[dates[-1]]
    latest_rates = latest[rate_cols].round(3)
    for date in reversed(dates[:-1]):
        previous = by_date[date]
        if previous[rate_cols].round(3).reindex(latest_rates.index).equals(latest_rates):
            continue  # 원본이 그대로인 날(넥슨 미갱신)은 건너뛴다
        delta = (latest["total_score"] - previous["total_score"]).dropna()
        return {str(hero): float(value) for hero, value in delta.items()}, date
    return {}, None


def normalize_meta_score(series, reference=None):
    """z-score 기반 종합 점수를 표시용 0~1000 으로 편다.

    reference 를 주면 그 분포의 min/max 를 기준으로 편다. 정규화 풀과 조회 대상을 분리해야
    하는 경우(전 티어 기준으로 특정 영웅 값을 환산)에 쓴다.
    랭크 산정 자체는 기존 z-score 를 그대로 쓴다. 이건 화면 표시 전용이다.
    """
    values = pd.to_numeric(series, errors="coerce")
    base = values if reference is None else pd.to_numeric(reference, errors="coerce")
    lo, hi = base.min(), base.max()
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return values.notna().astype(float) * 500.0
    return ((values - lo) / (hi - lo) * 1000.0).clip(0, 1000)


HERO_ART_MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "data", "hero_art_manifest.json")
HERO_COLORS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "assets", "hero_colors.json")


@st.cache_data(show_spinner=False)
def load_hero_colors():
    """영웅 대표색. scripts/fetch_hero_art.py 가 만든다."""
    try:
        with open(HERO_COLORS_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def get_hero_color(hero_name, fallback="#3b1a5c"):
    # 색 파일과 아트 매니페스트는 OverFast key(dva, dmon …)로 저장되어 있다.
    return load_hero_colors().get(_hero_meta(hero_name).get("key"), fallback)


@st.cache_data(show_spinner=False)
def load_hero_art_manifest():
    """scripts/fetch_hero_art.py 가 만들어 둔 배너 아트 매니페스트. OverFast key -> 아트 정보.

    런타임에는 네트워크도 ML도 쓰지 않고 커밋된 결과물만 읽는다.
    """
    try:
        with open(HERO_ART_MANIFEST_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def get_hero_banner_art(hero_name):
    """히어로 배너에 쓸 아트 정보. 없으면 None.

    반환: {"splash_url", "focal_x"}. 블리자드 공식 영웅 페이지의 배경 스플래시를
    블리자드 CDN 에서 그대로 불러온다(우리 쪽에 복사본을 두지 않는다).
    """
    entry = load_hero_art_manifest().get(_hero_meta(hero_name).get("key"))
    if not entry:
        return None

    splash = entry.get("splash") or {}
    return {
        "splash_url": splash.get("2600") or splash.get("1600") or splash.get("960"),
        "focal_x": entry.get("focal_x", 0.7),
    }


def _load_json_list(path):
    payload = read_data_json(path)
    if payload is None:
        return []
    return payload if isinstance(payload, list) else []


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
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


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
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


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner=False)
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


@st.cache_data(show_spinner=False)
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
    override = MAP_IMAGE_OVERRIDES.get(alias) or MAP_IMAGE_OVERRIDES.get(map_id)
    if override:
        return _remote_url(override)
    image_map = load_map_image_map()
    url = image_map.get(alias) or image_map.get(map_id)
    if url:
        return url
    if alias and alias != "all-maps":
        return f"https://overfast-api.tekrop.fr/static/maps/{alias}.jpg"
    return f"https://dummyimage.com/600x100/1f2937/475569.png&text={map_id}"


# 전장 모드. 게임 안 표기 순서대로 둔다. 여기 없는 전장(새로 추가된 전장)은 화면에서 "기타"로 묶인다.
MAP_MODES = {
    "쟁탈": ["antarctic-peninsula", "busan", "ilios", "lijiang-tower", "nepal", "oasis", "samoa"],
    "호위": ["circuit-royal", "dorado", "havana", "junkertown", "rialto", "route-66",
             "shambali-monastery", "watchpoint-gibraltar"],
    "혼합": ["blizzard-world", "eichenwalde", "hollywood", "kings-row", "midtown", "neon-junction",
             "numbani", "paraiso"],
    "밀기": ["colosseo", "esperanca", "new-queen-street", "runasapi"],
    "플래시포인트": ["aatlis", "new-junk-city", "suravasa"],
}


def top_heroes_by_map(df, tier, per_role=2):
    """전장·포지션별 보정 승률 상위 영웅. 전장마다 포지션별로 per_role 명, 승률 높은 순.

    영웅 상세의 전장 카드와 같은 기준(shrunk_win_rate)으로 줄 세운다. 원래 승률로 세우면
    픽률이 아주 낮은 영웅의 0%/100% 가 맨 위로 온다.
    lift 는 같은 티어 전체 전장 승률과의 차이(%p)다. 어디서나 센 영웅과 이 전장에서 특히
    센 영웅을 가른다.
    """
    tier_df = df[df["data_tier"].astype(str) == str(tier)]
    is_all = tier_df["map"].astype(str) == "all-maps"
    overall = tier_df[is_all].drop_duplicates("hero").set_index("hero")["win_rate"]
    maps = tier_df[~is_all & tier_df["shrunk_win_rate"].notna()].copy()
    maps["lift"] = maps["shrunk_win_rate"] - maps["hero"].map(overall)
    return (
        maps.sort_values("shrunk_win_rate", ascending=False)
        .groupby(["map", "role"], sort=False)
        .head(per_role)
    )
