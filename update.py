from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
import time
import urllib.request
from datetime import date, datetime
from difflib import get_close_matches
from html.parser import HTMLParser
from typing import Dict, List
from urllib.parse import urlencode, urlparse, parse_qs, unquote, urljoin

import numpy as np
import pandas as pd
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
except ImportError:
    webdriver = None
    Options = None
    By = None
    WebDriverWait = None
    EC = None
    SessionNotCreatedException = RuntimeError
    WebDriverException = RuntimeError
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from time import perf_counter

# 1. 영웅별 포지션 매핑 딕셔너리
role_dict = {
    'D.VA': 'Tank', '라인하르트': 'Tank', '윈스턴': 'Tank', '자리야': 'Tank', 
    '오리사': 'Tank', '로드호그': 'Tank', '시그마': 'Tank', '레킹볼': 'Tank', 
    '둠피스트': 'Tank', '라마트라': 'Tank', '마우가': 'Tank', '도미나': 'Tank',
    '정커퀸': 'Tank', '해저드': 'Tank',
    '겐지': 'Damage', '트레이서': 'Damage', '리퍼': 'Damage', '파라': 'Damage', 
    '캐서디': 'Damage', '애쉬': 'Damage', '솔저: 76': 'Damage', '솜브라': 'Damage', 
    '위도우메이커': 'Damage', '한조': 'Damage', '메이': 'Damage', '정크랫': 'Damage', 
    '토르비욘': 'Damage', '바스티온': 'Damage', '시메트라': 'Damage', '에코': 'Damage', '소전': 'Damage',
    '시에라': 'Damage',
    '벤처': 'Damage', '벤데타': 'Damage', '안란': 'Damage', '엠레': 'Damage', '프레야': 'Damage',
    '시온': 'Damage',
    '메르시': 'Support', '아나': 'Support', '루시우': 'Support', '젠야타': 'Support', 
    '모이라': 'Support', '바티스트': 'Support', '브리기테': 'Support', '키리코': 'Support', 
    '라이프위버': 'Support', '일리아리': 'Support', '주노': 'Support', '미즈키': 'Support', '우양' : 'Support',
    '제트팩 캣': 'Support'
}

# 2. 티어 리스트 정의
tiers = ["All", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster"]

map_dict = {
    "all-maps": "전체 전장",

    # 푸시
    "colosseo": "콜로세오",
    "esperanca": "에스페란사",
    "runasapi": "루나사피",
    "new-queen-street": "뉴 퀸 스트리트",

    # 하이브리드
    "hollywood": "할리우드",
    "paraiso": "파라이수",
    "kings-row": "왕의 길",
    "eichenwalde": "아이헨발데",
    "blizzard-world": "블리자드 월드",
    "midtown": "미드타운",
    "numbani": "눔바니",

    # 플래시포인트
    "aatlis": "아틀리스",
    "suravasa": "수라바사",
    "new-junk-city": "뉴 정크 시티",

    # 호위
    "havana": "하바나",
    "junkertown": "정크타운",
    "circuit-royal": "서킷 로얄",
    "shambali-monastery": "샴발리 수도원",
    "rialto": "리알토",
    "dorado": "도라도",
    "watchpoint-gibraltar": "감시 기지: 지브롤터",
    "route-66": "66번 국도",

    # 쟁탈
    "ilios": "일리오스",
    "oasis": "오아시스",
    "samoa": "사모아",
    "busan": "부산",
    "lijiang-tower": "리장 타워",
    "nepal": "네팔",
    "antarctic-peninsula": "남극 반도"
}

STATS_COLUMNS = [
    'hero', 'role', 'data_tier', 'map', 'map_name', 'update_date',
    'win_rate', 'pick_rate', 'ban_rate',
    'win_rate_z', 'pick_rate_log', 'pick_rate_z', 'ban_rate_log', 'ban_rate_z',
    'presence_score', 'shrunk_win_rate',
    'persistence_score', 'pick_stability_multiplier', 'performance_score',
    'total_score', 'score_strength', 'pick_rate_warning', 'rank',
]

DATA_DIR = "data"
LATEST_DIR = os.path.join(DATA_DIR, "latest")
HISTORY_DIR = os.path.join(DATA_DIR, "history")

LATEST_STATS_PATH = os.path.join(LATEST_DIR, "latest_tier.parquet")
LATEST_PERKS_PATH = os.path.join(LATEST_DIR, "latest_perks.parquet")
RANK_DIAGNOSTICS_PATH = os.path.join(LATEST_DIR, "rank_diagnostics.json")
WEEKLY_HISTORY_ROOT = os.path.join(HISTORY_DIR, "weekly")
DAILY_HISTORY_ROOT = os.path.join(HISTORY_DIR, "daily")
PATCH_NOTES_DIR = os.path.join(DATA_DIR, "patch_notes")
PATCH_NOTES_PATH = os.path.join(PATCH_NOTES_DIR, "patch_notes.json")
PATCH_AI_ANALYSIS_PATH = os.path.join(PATCH_NOTES_DIR, "patch_ai_analysis.json")
WEEKLY_SNAPSHOT_WEEKDAY = int(os.getenv("WEEKLY_SNAPSHOT_WEEKDAY", "0"))

# 메타 지배력 산식: 존재감(픽+밴) 주도 + 수축 승률 검증
META_PRESENCE_WEIGHT = float(os.getenv("META_PRESENCE_WEIGHT", "0.65"))
META_PERFORMANCE_WEIGHT = round(1.0 - META_PRESENCE_WEIGHT, 4)
PRESENCE_BAN_WEIGHT = float(os.getenv("PRESENCE_BAN_WEIGHT", "1.0"))
SHRINK_MIN_PICK_RATE = 0.1
QUADRANT_PRESENCE_HIGH_Z = 0.5
QUADRANT_PERFORMANCE_HIGH_Z = 0.5
OVERHEAT_REVIEW_THRESHOLD = 0.15

# 레거시 승률 중심 산식 상수: 진단 리포트의 비교 후보 계산에만 사용
PERFORMANCE_WIN_WEIGHT = 0.75
PERFORMANCE_PERSISTENCE_WEIGHT = 0.25
PERFORMANCE_BAN_PRESSURE_WEIGHT = 0.05
PICK_STABILITY_SCALE = 0.08
PICK_STABILITY_MIN = 0.85
PICK_STABILITY_MAX = 1.05
PERSISTENCE_WEEKS = int(os.getenv("PERFORMANCE_PERSISTENCE_WEEKS", "3"))
PERSISTENCE_EWMA_DECAY = float(os.getenv("PERFORMANCE_PERSISTENCE_EWMA_DECAY", "0.4"))
LOW_PICK_RATE_WARNING = 1.0
VERY_LOW_PICK_RATE_WARNING = 0.5
RANK_LABELS = ['D', 'C', 'B', 'A', 'S']
# 존재감 축은 하한이 눌린 분포라 D 임계만 -1.25에서 -1.00으로 보정
RANK_THRESHOLDS = {
    "S": 1.25,
    "A": 0.50,
    "C": -0.50,
    "D": -1.00,
}

BASE_URL = "https://owperks.com"
OFFICIAL_PATCH_NOTES_BASE_URL = "https://overwatch.blizzard.com/ko-kr/news/patch-notes/live"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")
OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate")
ENABLE_OLLAMA_ANALYSIS = os.getenv(
    "ENABLE_OLLAMA_ANALYSIS",
    "0" if os.getenv("GITHUB_ACTIONS") == "true" else "1",
) != "0"
FORCE_PATCH_AI_ANALYSIS = os.getenv("FORCE_PATCH_AI_ANALYSIS", "0") == "1"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))
PATCH_PROMPT_VERSION = "patch-impact-v2"
DEFAULT_LOCALE = "ko"
STATS_INPUT = "PC"
STATS_REGION = "Asia"
STATS_ROLE = "All"
STATS_GAME_MODE_RQ = os.getenv("STATS_GAME_MODE_RQ", "2")
STATS_GAME_MODE_RQ_CANDIDATES = [
    value.strip()
    for value in os.getenv("STATS_GAME_MODE_RQ_CANDIDATES", STATS_GAME_MODE_RQ).split(",")
    if value.strip()
]
if not STATS_GAME_MODE_RQ_CANDIDATES:
    STATS_GAME_MODE_RQ_CANDIDATES = ["2", "1"]
if STATS_GAME_MODE_RQ not in STATS_GAME_MODE_RQ_CANDIDATES:
    STATS_GAME_MODE_RQ_CANDIDATES.insert(0, STATS_GAME_MODE_RQ)
ACTIVE_STATS_GAME_MODE_RQ = None

CATEGORY_TO_ROLE = {
    "tanks": "Tank",
    "damages": "Damage",
    "supports": "Support",
}

VALID_HERO_NAMES = set(role_dict.keys())
HERO_NAME_ALIASES = {
    "두피스트": "둠피스트",
    "둠피": "둠피스트",
    "디바": "D.VA",
    "D.Va": "D.VA",
    "DVA": "D.VA",
    "솔저76": "솔저: 76",
    "솔저 76": "솔저: 76",
    "위도우": "위도우메이커",
    "브리": "브리기테",
    "루시": "루시우",
}

HERO_LINK_RE = re.compile(r"^https://owperks\.com/ko/(tanks|damages|supports)/([^/?#]+)$")


DEFAULT_MAX_WORKERS = 2
MAX_WORKERS = int(os.getenv("MAX_WORKERS", str(DEFAULT_MAX_WORKERS)))
DRIVER_CREATE_RETRIES = 3
TASK_RETRIES = int(os.getenv("TASK_RETRIES", "3"))
MIN_HERO_ROWS = 20
DRIVER_PAGE_LOAD_TIMEOUT = int(os.getenv("DRIVER_PAGE_LOAD_TIMEOUT", "75"))
DRIVER_SCRIPT_TIMEOUT = int(os.getenv("DRIVER_SCRIPT_TIMEOUT", "30"))

STOP_REQUESTED = threading.Event()
ACTIVE_DRIVERS = set()
ACTIVE_DRIVERS_LOCK = threading.Lock()


def normalize_tier_name(tier_name):
    if tier_name in ["Grandmaster % Champion", "Grandmaster & Champion"]:
        return "Grandmaster"
    return tier_name

def format_elapsed(seconds):
    total_seconds = int(round(seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}시간 {minutes}분 {seconds}초"
    if minutes > 0:
        return f"{minutes}분 {seconds}초"
    return f"{seconds}초"

def build_chrome_options(headless=True):
    opts = Options()
    opts.page_load_strategy = "eager"
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-sync")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--remote-debugging-pipe")
    opts.add_argument("--window-size=1920,1080")
    return opts


def register_driver(driver):
    with ACTIVE_DRIVERS_LOCK:
        ACTIVE_DRIVERS.add(driver)


def unregister_driver(driver):
    with ACTIVE_DRIVERS_LOCK:
        ACTIVE_DRIVERS.discard(driver)


def quit_active_drivers():
    with ACTIVE_DRIVERS_LOCK:
        drivers = list(ACTIVE_DRIVERS)

    for driver in drivers:
        try:
            driver.quit()
        except Exception:
            pass


def create_driver(headless=True, max_retries=DRIVER_CREATE_RETRIES):
    """Create Chrome session with retries for CI renderer startup failures."""
    if webdriver is None or Options is None:
        raise RuntimeError("selenium이 설치되어 있지 않아 브라우저 수집을 실행할 수 없습니다.")

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            opts = build_chrome_options(headless=headless)
            driver = webdriver.Chrome(options=opts)
            driver.set_page_load_timeout(DRIVER_PAGE_LOAD_TIMEOUT)
            driver.set_script_timeout(DRIVER_SCRIPT_TIMEOUT)
            return driver
        except (SessionNotCreatedException, WebDriverException) as exc:
            last_error = exc
            wait_sec = attempt * 2
            print(f"⚠️  드라이버 세션 생성 실패(시도 {attempt}/{max_retries}), {wait_sec}초 후 재시도")
            if attempt < max_retries:
                STOP_REQUESTED.wait(wait_sec)
            if STOP_REQUESTED.is_set():
                raise KeyboardInterrupt

    raise RuntimeError(f"Chrome 세션 생성 실패: {last_error}")

def normalize_dataset_for_scoring(df):
    valid_maps = set(map_dict.keys())

    if 'map' not in df.columns:
        df['map'] = 'all-maps'

    df = df[df['map'].isin(valid_maps)].copy()
    df['map_name'] = df['map'].map(map_dict)
    return df


def get_active_stats_game_mode_rq():
    return ACTIVE_STATS_GAME_MODE_RQ or STATS_GAME_MODE_RQ


def build_rates_url(map_id, tier_name):
    params = {
        "input": STATS_INPUT,
        "map": map_id,
        "region": STATS_REGION,
        "role": STATS_ROLE,
        "rq": get_active_stats_game_mode_rq(),
        "tier": normalize_tier_name(tier_name),
    }
    return "https://overwatch.blizzard.com/ko-kr/rates/?" + urlencode(params)


def build_rates_url_with_rq(map_id, tier_name, rq):
    params = {
        "input": STATS_INPUT,
        "map": map_id,
        "region": STATS_REGION,
        "role": STATS_ROLE,
        "rq": rq,
        "tier": normalize_tier_name(tier_name),
    }
    return "https://overwatch.blizzard.com/ko-kr/rates/?" + urlencode(params)


def page_context_matches(driver, expected_map, expected_tier, expected_rq=None):
    if expected_rq is None:
        expected_rq = get_active_stats_game_mode_rq()
    context = current_page_context(driver)
    return (
        context["input"] == STATS_INPUT
        and context["map"] == expected_map
        and context["region"] == STATS_REGION
        and context["role"] == STATS_ROLE
        and context["rq"] == expected_rq
        and context["tier"] == normalize_tier_name(expected_tier)
    )


def current_page_context(driver):
    parsed = urlparse(driver.current_url)
    query = parse_qs(parsed.query)
    return {
        "input": query.get("input", [""])[0],
        "map": query.get("map", [""])[0],
        "region": query.get("region", [""])[0],
        "role": query.get("role", [""])[0],
        "rq": query.get("rq", [""])[0],
        "tier": query.get("tier", [""])[0],
        "url": driver.current_url,
    }


def is_unsupported_all_maps_tier_redirect(expected_map, expected_tier, page_context):
    return (
        normalize_tier_name(expected_tier) != "All"
        and page_context.get("map") == expected_map
        and page_context.get("tier") == "All"
    )


def wait_for_page_context(driver, expected_map, expected_tier, expected_rq=None, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page_context_matches(driver, expected_map, expected_tier, expected_rq=expected_rq):
            return True, current_page_context(driver)
        time.sleep(0.5)

    return False, current_page_context(driver)


def wait_for_rates_content(driver, timeout=20):
    def has_rates_content(active_driver):
        if active_driver.find_elements(By.CLASS_NAME, "hero-name"):
            return True
        body_text = active_driver.find_element(By.TAG_NAME, "body").text
        return "영웅" in body_text and "%" in body_text

    WebDriverWait(driver, timeout).until(has_rates_content)


def parse_percent(value):
    if value is None:
        return "0%"
    text = str(value).strip()
    return text if text else "0%"


def scrape_rates_from_dom(driver):
    script = """
    let data = [];
    let names = document.querySelectorAll('.hero-name');
    let winrates = document.querySelectorAll('.winrate-cell');
    let pickrates = document.querySelectorAll('.pickrate-cell');
    let banrates = document.querySelectorAll('.banrate-cell');
    if (banrates.length === 0) {
        banrates = document.querySelectorAll('[class*=\"ban\"]');
    }
    for (let i = 0; i < names.length; i++) {
        data.push({
            'hero': names[i].innerText.trim(),
            'win_rate': winrates[i] ? winrates[i].innerText : '0%',
            'pick_rate': pickrates[i] ? pickrates[i].innerText : '0%',
            'ban_rate': banrates[i] ? banrates[i].innerText : '0%'
        });
    }
    return data;
    """
    return pd.DataFrame(driver.execute_script(script))


def scrape_rates_from_text(driver):
    body_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    try:
        start_idx = lines.index("영웅 픽률 승률") + 1
    except ValueError:
        try:
            start_idx = lines.index("영웅") + 1
        except ValueError:
            return pd.DataFrame()

    rows = []
    i = start_idx
    percent_re = re.compile(r"^(?:--|\d+(?:\.\d+)?)%$")
    stop_markers = {"자주 묻는 질문", "미래는 쟁취할 가치가 있습니다. 함께하세요!", "지금 플레이"}
    while i < len(lines):
        hero = lines[i]
        if hero in stop_markers or hero.startswith("## "):
            break
        if percent_re.match(hero):
            i += 1
            continue
        if i + 2 >= len(lines):
            break

        first_rate = lines[i + 1]
        second_rate = lines[i + 2]
        if percent_re.match(first_rate) and percent_re.match(second_rate):
            rows.append(
                {
                    "hero": hero,
                    # The visible Korean table says pick/win, but the rendered text
                    # order is hero, win rate, pick rate on the current Blizzard page.
                    "win_rate": parse_percent(first_rate),
                    "pick_rate": parse_percent(second_rate),
                    "ban_rate": "0%",
                }
            )
            i += 3
        else:
            i += 1

    return pd.DataFrame(rows)


def validate_scraped_df(df):
    if df.empty:
        return False, "빈 DataFrame"

    if "hero" not in df.columns or "win_rate" not in df.columns or "pick_rate" not in df.columns:
        return False, "필수 컬럼 누락"

    if len(df) < MIN_HERO_ROWS:
        return False, f"영웅 행 수 부족({len(df)}행)"

    if df["hero"].astype(str).nunique() < MIN_HERO_ROWS:
        return False, "영웅 고유 개수 부족"

    win = pd.to_numeric(df["win_rate"].astype(str).str.replace('%', '', regex=False).replace('--', '0'), errors="coerce")
    pick = pd.to_numeric(df["pick_rate"].astype(str).str.replace('%', '', regex=False).replace('--', '0'), errors="coerce")

    if win.notna().sum() < MIN_HERO_ROWS or pick.notna().sum() < MIN_HERO_ROWS:
        return False, "승률/픽률 숫자 변환 실패"

    if win.nunique(dropna=True) <= 1 and pick.nunique(dropna=True) <= 1:
        return False, "승률/픽률 분산 없음"

    return True, "ok"


def is_degenerate_snapshot(df):
    if df.empty:
        return True

    map_rows = df[df['map'].astype(str) != 'all-maps'].copy()
    if map_rows.empty:
        return True

    map_rows['win_rate'] = pd.to_numeric(map_rows['win_rate'], errors='coerce')
    map_rows['pick_rate'] = pd.to_numeric(map_rows['pick_rate'], errors='coerce')

    by_hero_tier_win = map_rows.groupby(['hero', 'data_tier'])['win_rate'].nunique(dropna=True)
    by_hero_tier_pick = map_rows.groupby(['hero', 'data_tier'])['pick_rate'].nunique(dropna=True)

    if by_hero_tier_win.empty or by_hero_tier_pick.empty:
        return True

    no_win_variance_ratio = (by_hero_tier_win <= 1).mean()
    no_pick_variance_ratio = (by_hero_tier_pick <= 1).mean()
    return no_win_variance_ratio >= 0.98 and no_pick_variance_ratio >= 0.98


def assign_score_rank(scores):
    numeric_scores = pd.to_numeric(scores, errors='coerce')
    ranks = pd.Series('B', index=scores.index, dtype=object)
    ranks[numeric_scores >= RANK_THRESHOLDS['S']] = 'S'
    ranks[(numeric_scores >= RANK_THRESHOLDS['A']) & (numeric_scores < RANK_THRESHOLDS['S'])] = 'A'
    ranks[(numeric_scores <= RANK_THRESHOLDS['C']) & (numeric_scores > RANK_THRESHOLDS['D'])] = 'C'
    ranks[numeric_scores <= RANK_THRESHOLDS['D']] = 'D'
    ranks[numeric_scores.isna()] = 'B'
    return ranks


def safe_zscore(series):
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series([0] * len(series), index=series.index)
    return (series - series.mean()) / std


def add_normalized_metric_columns(df, group_key=None):
    if group_key is None:
        group_key = ['data_tier', 'map', 'role']

    df['win_rate_z'] = df.groupby(group_key)['win_rate'].transform(safe_zscore)
    df['pick_rate_log'] = np.log1p(df['pick_rate'])
    df['pick_rate_z'] = df.groupby(group_key)['pick_rate_log'].transform(safe_zscore)
    df['ban_rate_log'] = np.log1p(df['ban_rate'])
    df['ban_rate_z'] = df.groupby(group_key)['ban_rate_log'].transform(safe_zscore)
    return df


def add_meta_axis_columns(df, group_key=None):
    if group_key is None:
        group_key = ['data_tier', 'map', 'role']

    df['presence_log'] = np.log1p(
        df['pick_rate'] + PRESENCE_BAN_WEIGHT * df['ban_rate']
    )
    df['presence_score'] = df.groupby(group_key)['presence_log'].transform(safe_zscore)

    group_mean_win = df.groupby(group_key)['win_rate'].transform('mean')
    shrink_k = (
        df.groupby(group_key)['pick_rate'].transform('median')
        .clip(lower=SHRINK_MIN_PICK_RATE)
    )
    df['shrunk_win_rate'] = (
        (df['pick_rate'] * df['win_rate'] + shrink_k * group_mean_win)
        / (df['pick_rate'] + shrink_k)
    )
    df['performance_score'] = df.groupby(group_key)['shrunk_win_rate'].transform(safe_zscore)
    return df


def add_scoring_columns(df, group_key=None, persistence_df=None):
    if group_key is None:
        group_key = ['data_tier', 'map', 'role']

    derived_cols = [
        'presence_log',
        'presence_score',
        'shrunk_win_rate',
        'persistence_score',
        'pick_stability_multiplier',
        'performance_score',
        'total_score',
        'score_strength',
        'pick_rate_warning',
    ]
    df = df.drop(columns=[col for col in derived_cols if col in df.columns])
    df = add_normalized_metric_columns(df, group_key=group_key)
    df = add_meta_axis_columns(df, group_key=group_key)
    if persistence_df is None:
        persistence_df = build_recent_persistence_frame()

    entity_key = ['hero', 'role', 'data_tier', 'map']
    if persistence_df is not None and not persistence_df.empty:
        df = df.merge(persistence_df, on=entity_key, how='left')
    if 'persistence_score' not in df.columns:
        df['persistence_score'] = np.nan

    # persistence/pick_stability는 점수에 직접 쓰지 않지만
    # 레거시 후보 산식 진단과 추세 확인용으로 계속 계산해 저장
    df['persistence_score'] = pd.to_numeric(df['persistence_score'], errors='coerce')
    df['persistence_score'] = df['persistence_score'].fillna(df['win_rate_z'])
    df['pick_stability_multiplier'] = (
        1 + PICK_STABILITY_SCALE * df['pick_rate_z']
    ).clip(PICK_STABILITY_MIN, PICK_STABILITY_MAX)

    df['total_score'] = (
        META_PRESENCE_WEIGHT * df['presence_score']
        + META_PERFORMANCE_WEIGHT * df['performance_score']
    )
    df['score_strength'] = np.select(
        [
            (df['presence_score'] >= QUADRANT_PRESENCE_HIGH_Z)
            & (df['performance_score'] >= 0),
            (df['presence_score'] >= QUADRANT_PRESENCE_HIGH_Z)
            & (df['performance_score'] < 0),
            (df['presence_score'] < QUADRANT_PRESENCE_HIGH_Z)
            & (df['performance_score'] >= QUADRANT_PERFORMANCE_HIGH_Z),
            (df['presence_score'] <= -QUADRANT_PRESENCE_HIGH_Z)
            & (df['performance_score'] < QUADRANT_PERFORMANCE_HIGH_Z),
        ],
        ['메타 지배', '과열 주의', '저평가 픽', '비주류'],
        default='보통',
    )
    df['pick_rate_warning'] = np.select(
        [
            df['pick_rate'] < VERY_LOW_PICK_RATE_WARNING,
            df['pick_rate'] < LOW_PICK_RATE_WARNING,
        ],
        ['저픽률 주의', '픽률 낮음'],
        default='',
    )
    return df


def weekly_snapshot_paths():
    paths = []
    if not os.path.isdir(WEEKLY_HISTORY_ROOT):
        return paths

    for dirpath, _dirnames, filenames in os.walk(WEEKLY_HISTORY_ROOT):
        if "tier_snapshot.parquet" not in filenames:
            continue
        path = os.path.join(dirpath, "tier_snapshot.parquet")
        match = re.search(r"year=(\d+)/week=(\d+)/tier_snapshot\.parquet$", path)
        if match:
            sort_key = (int(match.group(1)), int(match.group(2)))
        else:
            sort_key = (0, len(paths))
        paths.append((sort_key, path))

    return [path for _sort_key, path in sorted(paths)]


def load_weekly_history_for_persistence():
    frames = []
    for snapshot_order, path in enumerate(weekly_snapshot_paths()):
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            print(f"⚠️  지속성 계산용 스냅샷 로드 실패: {path} -> {exc}")
            continue

        required_cols = {'hero', 'role', 'data_tier', 'map', 'win_rate', 'pick_rate', 'ban_rate'}
        if not required_cols.issubset(frame.columns):
            continue

        frame = frame.copy()
        frame['snapshot_order'] = snapshot_order
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_recent_persistence_frame(max_weeks=None, history_df=None):
    if max_weeks is None:
        max_weeks = PERSISTENCE_WEEKS
    if history_df is None:
        history_df = load_weekly_history_for_persistence()

    if history_df.empty:
        return pd.DataFrame()

    required_cols = {'snapshot_order', 'hero', 'role', 'data_tier', 'map', 'win_rate', 'pick_rate', 'ban_rate'}
    if not required_cols.issubset(history_df.columns):
        return pd.DataFrame()

    df = history_df.copy()
    for col in ['win_rate', 'pick_rate', 'ban_rate']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    df = add_normalized_metric_columns(df, group_key=['snapshot_order', 'data_tier', 'map', 'role'])
    entity_key = ['hero', 'role', 'data_tier', 'map']
    df = df.sort_values(entity_key + ['snapshot_order'])
    recent = df.groupby(entity_key, group_keys=False).tail(max_weeks).copy()
    recent['reverse_age'] = recent.groupby(entity_key).cumcount(ascending=False)
    recent['persistence_weight'] = PERSISTENCE_EWMA_DECAY ** recent['reverse_age']
    weighted = (
        recent.assign(weighted_win_rate_z=recent['win_rate_z'] * recent['persistence_weight'])
        .groupby(entity_key, as_index=False)
        .agg(
            weighted_sum=('weighted_win_rate_z', 'sum'),
            weight_sum=('persistence_weight', 'sum'),
        )
    )
    weighted['persistence_score'] = weighted['weighted_sum'] / weighted['weight_sum']
    return weighted[entity_key + ['persistence_score']]


def rank_index_value(rank_value):
    try:
        return RANK_LABELS.index(str(rank_value))
    except ValueError:
        return -1


def calculate_candidate_scores(df):
    legacy_base_score = (
        PERFORMANCE_WIN_WEIGHT * df['win_rate_z']
        + PERFORMANCE_PERSISTENCE_WEIGHT * df['persistence_score']
    )
    return {
        "presence_led_meta_score": (
            META_PRESENCE_WEIGHT * df['presence_score']
            + META_PERFORMANCE_WEIGHT * df['performance_score']
        ),
        "presence_only": df['presence_score'],
        "shrunk_win_only": df['performance_score'],
        "win_rate_only": df['win_rate_z'],
        "persistence_only": df['persistence_score'],
        "legacy_win_centric_score": (
            legacy_base_score * df['pick_stability_multiplier']
            + PERFORMANCE_BAN_PRESSURE_WEIGHT * df['ban_rate_z']
        ),
    }


def top_quartile_precision(group, score_col, target_col):
    if group.empty or group[target_col].nunique(dropna=True) < 2:
        return np.nan
    top_n = max(1, len(group) // 4)
    target_cutoff = group[target_col].quantile(0.75)
    selected = group.sort_values(score_col, ascending=False).head(top_n)
    return float((selected[target_col] >= target_cutoff).mean())


def build_walk_forward_diagnostics(history_df):
    if history_df.empty:
        return {"available": False, "reason": "no_weekly_history"}

    required_cols = {
        'snapshot_order', 'hero', 'role', 'data_tier', 'map',
        'win_rate_z', 'persistence_score', 'pick_rate_z', 'ban_rate_z',
        'pick_stability_multiplier', 'presence_score', 'performance_score',
    }
    if not required_cols.issubset(history_df.columns):
        return {
            "available": False,
            "reason": "missing_columns",
            "missing_columns": sorted(required_cols - set(history_df.columns)),
        }

    entity_key = ['hero', 'role', 'data_tier', 'map']
    df = history_df.copy().sort_values(entity_key + ['snapshot_order'])
    # 목표를 두 개로 나눠 평가: 성능(다음 주 승률)과 지배력(다음 주 존재감)
    df['next_win_rate_z'] = df.groupby(entity_key)['win_rate_z'].shift(-1)
    df['next_presence_z'] = df.groupby(entity_key)['presence_score'].shift(-1)
    df = df.dropna(subset=['next_win_rate_z', 'next_presence_z']).copy()
    if df.empty:
        return {"available": False, "reason": "no_next_week_pairs"}

    for name, score in calculate_candidate_scores(df).items():
        df[name] = score

    score_cols = list(calculate_candidate_scores(df).keys())
    grouped_key = ['snapshot_order', 'data_tier', 'map', 'role']
    targets = {
        "next_week_win_rate_z": "next_win_rate_z",
        "next_week_presence_z": "next_presence_z",
    }
    target_reports = {}
    for target_name, target_col in targets.items():
        correlations = {
            col: float(df[[col, target_col]].corr().iloc[0, 1])
            for col in score_cols
            if df[col].nunique(dropna=True) > 1
        }
        grouped = df.groupby(grouped_key, group_keys=False)
        top_quartile_precision_by_score = {
            col: float(grouped.apply(
                lambda group: top_quartile_precision(group, col, target_col),
                include_groups=False,
            ).mean())
            for col in score_cols
        }
        target_reports[target_name] = {
            "correlation_to_target": correlations,
            "top_quartile_precision": top_quartile_precision_by_score,
        }

    return {
        "available": True,
        "rows": int(len(df)),
        "weekly_snapshots": int(history_df['snapshot_order'].nunique()),
        "targets": target_reports,
    }


def score_variant_for_sensitivity(df, presence_weight, presence_ban_weight, group_key):
    presence_log = np.log1p(
        df['pick_rate'] + presence_ban_weight * df['ban_rate']
    )
    presence_z = (
        df.assign(_variant_presence_log=presence_log)
        .groupby(group_key)['_variant_presence_log']
        .transform(safe_zscore)
    )
    return presence_weight * presence_z + (1.0 - presence_weight) * df['performance_score']


def build_sensitivity_diagnostics(latest_df):
    required_cols = {
        'hero', 'role', 'data_tier', 'map', 'rank',
        'pick_rate', 'ban_rate', 'performance_score',
    }
    if latest_df.empty or not required_cols.issubset(latest_df.columns):
        return {"available": False, "reason": "missing_latest_columns"}

    group_key = ['data_tier', 'map', 'role']
    baseline = latest_df.copy()
    baseline['baseline_rank_index'] = baseline['rank'].map(rank_index_value)
    variants = []
    for presence_weight in [0.55, 0.65, 0.75]:
        for presence_ban_weight in [0.50, 0.75, 1.00]:
            variant = baseline.copy()
            variant['variant_score'] = score_variant_for_sensitivity(
                variant,
                presence_weight=presence_weight,
                presence_ban_weight=presence_ban_weight,
                group_key=group_key,
            )
            variant['variant_rank'] = variant.groupby(group_key)['variant_score'].transform(assign_score_rank)
            variant['variant_rank_index'] = variant['variant_rank'].map(rank_index_value)
            rank_delta = (variant['variant_rank_index'] - variant['baseline_rank_index']).abs()
            baseline_s = variant['rank'].astype(str) == 'S'
            variant_s = variant['variant_rank'].astype(str) == 'S'
            variants.append(
                {
                    "presence_weight": presence_weight,
                    "performance_weight": round(1.0 - presence_weight, 4),
                    "presence_ban_weight": presence_ban_weight,
                    "rank_change_rate": float((rank_delta > 0).mean()),
                    "avg_abs_rank_delta": float(rank_delta.mean()),
                    "s_membership_change_rate": float((baseline_s != variant_s).mean()),
                }
            )

    return {
        "available": True,
        "variants": variants,
        "summary": {
            "variant_count": len(variants),
            "avg_rank_change_rate": float(np.mean([row["rank_change_rate"] for row in variants])),
            "max_rank_change_rate": float(np.max([row["rank_change_rate"] for row in variants])),
            "avg_s_membership_change_rate": float(np.mean([row["s_membership_change_rate"] for row in variants])),
            "max_s_membership_change_rate": float(np.max([row["s_membership_change_rate"] for row in variants])),
        },
    }


def build_overheat_monitor(latest_df):
    required_cols = {'rank', 'performance_score'}
    if latest_df.empty or not required_cols.issubset(latest_df.columns):
        return {"available": False, "reason": "missing_latest_columns"}

    top_ranks = latest_df[latest_df['rank'].astype(str).isin(['S', 'A'])]
    if top_ranks.empty:
        return {"available": False, "reason": "no_s_or_a_rows"}

    perf = pd.to_numeric(top_ranks['performance_score'], errors='coerce')
    return {
        "available": True,
        "s_a_rows": int(len(top_ranks)),
        "s_a_perf_negative_share": float((perf < 0).mean()),
        "review_threshold": OVERHEAT_REVIEW_THRESHOLD,
        "note": (
            "S/A 랭크 중 성능 z<0(존재감만으로 상위) 비율. "
            "이 값이 지속적으로 review_threshold를 넘으면 "
            "PRESENCE_BAN_WEIGHT 하향(예: 0.5)을 검토합니다."
        ),
    }


def build_rank_diagnostics(latest_df=None):
    history_df = load_weekly_history_for_persistence()
    if latest_df is None and os.path.exists(LATEST_STATS_PATH):
        latest_df = pd.read_parquet(LATEST_STATS_PATH)
    if latest_df is None:
        latest_df = pd.DataFrame()

    # 과거 스냅샷에는 존재감/수축 승률 컬럼이 없거나 구식이므로
    # 현재 산식 기준으로 스냅샷 그룹 내에서 재계산해 비교 일관성을 확보
    history_required = {'pick_rate', 'ban_rate', 'win_rate', 'snapshot_order'}
    if not history_df.empty and history_required.issubset(history_df.columns):
        history_df = add_meta_axis_columns(
            history_df.copy(),
            group_key=['snapshot_order', 'data_tier', 'map', 'role'],
        )

    metric_cols = [
        'win_rate_z', 'persistence_score', 'presence_score', 'performance_score',
        'pick_rate_z', 'ban_rate_z', 'total_score',
    ]
    diagnostics = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "method_note": (
            "Diagnostics are used to audit the hand-designed presence-led meta formula; "
            "they do not automatically optimize production weights."
        ),
        "long_term_plan": "patch_buff_nerf_history_based_regression",
        "formula": {
            "presence_weight": META_PRESENCE_WEIGHT,
            "performance_weight": META_PERFORMANCE_WEIGHT,
            "presence_ban_weight": PRESENCE_BAN_WEIGHT,
        },
        "data_summary": {
            "latest_rows": int(len(latest_df)),
            "weekly_rows": int(len(history_df)),
            "weekly_snapshots": int(history_df['snapshot_order'].nunique()) if 'snapshot_order' in history_df.columns else 0,
        },
        "correlation_matrix": {},
        "variance": {},
        "overheat_monitor": build_overheat_monitor(latest_df),
        "walk_forward": build_walk_forward_diagnostics(history_df),
        "sensitivity": build_sensitivity_diagnostics(latest_df),
    }

    if not history_df.empty and set(metric_cols).issubset(history_df.columns):
        metrics = history_df[metric_cols].apply(pd.to_numeric, errors='coerce')
        diagnostics["correlation_matrix"] = {
            col: {
                nested_col: (
                    None if pd.isna(value) else float(value)
                )
                for nested_col, value in metrics.corr().loc[col].items()
            }
            for col in metric_cols
        }
        diagnostics["variance"] = {
            col: float(metrics[col].var())
            for col in metric_cols
        }

    return diagnostics


def save_rank_diagnostics(latest_df=None):
    os.makedirs(os.path.dirname(RANK_DIAGNOSTICS_PATH), exist_ok=True)
    diagnostics = build_rank_diagnostics(latest_df)
    with open(RANK_DIAGNOSTICS_PATH, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, ensure_ascii=False, indent=2)
    return diagnostics


def build_snapshot_compare_frame(df):
    str_cols = ['hero', 'data_tier', 'map']
    num_cols = [col for col in ['win_rate', 'pick_rate', 'ban_rate'] if col in df.columns]

    for col in str_cols:
        if col not in df.columns:
            df[col] = ''

    str_df = df[str_cols].astype(str).reset_index(drop=True)
    num_df = df[num_cols].apply(pd.to_numeric, errors='coerce').round(4)
    compare_cols = str_cols + num_cols

    return (
        pd.concat([str_df, num_df], axis=1)
        .sort_values(compare_cols)
        .reset_index(drop=True)
    )


def build_perk_compare_frame(df):
    ignore_cols = {"update_date"}
    compare_cols = [col for col in df.columns if col not in ignore_cols]

    if not compare_cols:
        return pd.DataFrame()

    compare_df = df[compare_cols].copy()
    for col in compare_df.columns:
        if pd.api.types.is_numeric_dtype(compare_df[col]):
            compare_df[col] = pd.to_numeric(compare_df[col], errors="coerce").round(4)
        else:
            compare_df[col] = compare_df[col].fillna("").astype(str)

    return compare_df.sort_values(compare_cols).reset_index(drop=True)


def save_parquet(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)


def save_weekly_snapshot_if_due(snapshot_df, today_obj):
    if today_obj.weekday() != WEEKLY_SNAPSHOT_WEEKDAY:
        return "(skip) 저장 요일 아님"

    iso = today_obj.isocalendar()
    weekly_dir = os.path.join(
        WEEKLY_HISTORY_ROOT,
        f"year={iso.year}",
        f"week={iso.week:02d}",
    )
    weekly_parquet_path = os.path.join(weekly_dir, "tier_snapshot.parquet")
    save_parquet(snapshot_df, weekly_parquet_path)
    return weekly_parquet_path


def save_daily_snapshot(snapshot_df, today_obj):
    daily_dir = os.path.join(
        DAILY_HISTORY_ROOT,
        f"year={today_obj.year}",
        f"month={today_obj.month:02d}",
    )
    daily_parquet_path = os.path.join(daily_dir, "tier_snapshot.parquet")

    existing_df = None
    if os.path.exists(daily_parquet_path):
        try:
            existing_df = pd.read_parquet(daily_parquet_path)
        except Exception:
            existing_df = None

    if existing_df is not None and not existing_df.empty:
        existing_df = existing_df[
            existing_df.get("snapshot_date", "").astype(str) != today_obj.isoformat()
        ].copy()
        snapshot_df = pd.concat([existing_df, snapshot_df], ignore_index=True, sort=False)

    save_parquet(snapshot_df, daily_parquet_path)
    return daily_parquet_path


class PatchTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "li", "h3", "h4", "h5", "div", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "li", "h3", "h4", "h5", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        raw = "\n".join(self.parts)
        lines = []
        for line in raw.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned and cleaned not in {"위로 이동"}:
                lines.append(cleaned)
        return "\n".join(lines)


def html_to_text(html_text):
    parser = PatchTextExtractor()
    parser.feed(html_text)
    return parser.get_text()


def load_json_list(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def save_json_list(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch_patch_month_html(year, month):
    url = f"{OFFICIAL_PATCH_NOTES_BASE_URL}/{year}/{month}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.url


def month_candidates(today_obj, months_back=6):
    year = today_obj.year
    month = today_obj.month
    for _ in range(months_back):
        yield year, month
        month -= 1
        if month == 0:
            month = 12
            year -= 1


def parse_patch_blocks(page_html, page_url):
    blocks = re.split(r'(?=<div class="PatchNotes-patch[^"]*")', page_html)
    patches = []
    for block in blocks:
        if 'class="PatchNotes-patch' not in block:
            continue

        patch_id_match = re.search(r'<div class="anchor" id="([^"]+)"', block)
        date_match = re.search(r'<div class="PatchNotes-date">(.+?)</div>', block, re.S)
        title_match = re.search(r'<h3 class="PatchNotes-patchTitle">(.+?)</h3>', block, re.S)
        if not date_match or not title_match:
            continue

        patch_id = patch_id_match.group(1) if patch_id_match else ""
        raw_date = html_to_text(date_match.group(1))
        title = html_to_text(title_match.group(1))
        parsed_date = parse_korean_patch_date(raw_date, title, patch_id)
        if not parsed_date:
            continue

        raw_content = html_to_text(block)
        content_lines = [
            line for line in raw_content.splitlines()
            if line not in {raw_date, title, "위로 이동"}
        ]
        parsed_content = "\n".join(content_lines).strip()
        affected_heroes = sorted(set(re.findall(r'class="PatchNotesHeroUpdate-icon"[^>]*alt="([^"]+)"', block)))
        has_hero_updates = bool(affected_heroes) or "PatchNotes-section-hero_update" in block
        summary_items = build_patch_summary_items(parsed_content, affected_heroes)
        summary = " · ".join(summary_items[:3]) if summary_items else "상세 패치노트를 확인하세요."
        if not patch_id:
            patch_id = "patch-" + hashlib.sha1(f"{parsed_date}-{title}".encode("utf-8")).hexdigest()[:12]

        patches.append(
            {
                "id": patch_id,
                "patch_version": patch_id.replace("patch-", ""),
                "title": title,
                "patch_date": parsed_date,
                "source_url": f"{page_url.split('#')[0]}#{patch_id}",
                "raw_content": raw_content,
                "parsed_content": parsed_content,
                "summary": summary,
                "summary_items": summary_items,
                "affected_heroes": affected_heroes,
                "has_hero_updates": has_hero_updates,
                "patch_category": "hero_balance" if has_hero_updates else "general",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    return patches


def fetch_patch_candidates(today_obj=None, months_back=6):
    today_obj = today_obj or date.today()
    all_patches = []
    for year, month in month_candidates(today_obj, months_back=months_back):
        try:
            page_html, page_url = fetch_patch_month_html(year, month)
            month_patches = parse_patch_blocks(page_html, page_url)
            all_patches.extend(month_patches)
        except Exception as exc:
            print(f"⚠️  패치노트 페이지 수집 실패({year}/{month}): {exc}")

        if any(row.get("has_hero_updates") for row in all_patches):
            break

    return all_patches


def parse_korean_patch_date(raw_date, title, patch_id):
    candidates = [raw_date, title, patch_id]
    for value in candidates:
        match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(value))
        if match:
            year, month, day = (int(part) for part in match.groups())
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                continue
    return ""


def build_patch_summary_items(parsed_content, affected_heroes):
    lines = []
    for line in parsed_content.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) < 8:
            continue
        if cleaned.startswith("오버워치 2 패치 노트"):
            continue
        if re.match(r"^\d{4}년", cleaned):
            continue
        lines.append(cleaned)

    items = []
    if affected_heroes:
        preview = ", ".join(affected_heroes[:6])
        suffix = " 등" if len(affected_heroes) > 6 else ""
        items.append(f"영향 영웅: {preview}{suffix}")
    for line in lines:
        if line not in items:
            items.append(line)
        if len(items) >= 6:
            break
    return items


def fetch_latest_patch_note(today_obj=None):
    all_patches = fetch_patch_candidates(today_obj=today_obj, months_back=1)
    if not all_patches:
        return None

    return max(all_patches, key=lambda row: (row["patch_date"], row["id"]))


def fetch_latest_patch_bundle(today_obj=None):
    all_patches = fetch_patch_candidates(today_obj=today_obj, months_back=6)
    if not all_patches:
        return None, None

    latest_patch = max(all_patches, key=lambda row: (row["patch_date"], row["id"]))
    balance_patches = [row for row in all_patches if row.get("has_hero_updates")]
    latest_balance_patch = None
    if balance_patches:
        latest_balance_patch = max(balance_patches, key=lambda row: (row["patch_date"], row["id"]))
    return latest_patch, latest_balance_patch


def upsert_patch_note(patch_note):
    rows = load_json_list(PATCH_NOTES_PATH)
    now = datetime.now().isoformat(timespec="seconds")
    patch_note = dict(patch_note)
    patch_note["updated_at"] = now

    for idx, row in enumerate(rows):
        if row.get("id") == patch_note.get("id"):
            patch_note["created_at"] = row.get("created_at") or patch_note.get("created_at") or now
            rows[idx] = patch_note
            save_json_list(sorted(rows, key=lambda item: item.get("patch_date", "")), PATCH_NOTES_PATH)
            return patch_note, False

    patch_note["created_at"] = patch_note.get("created_at") or now
    rows.append(patch_note)
    save_json_list(sorted(rows, key=lambda item: item.get("patch_date", "")), PATCH_NOTES_PATH)
    return patch_note, True


def build_metrics_digest(current_df, previous_df=None, tier="Gold"):
    if current_df is None or current_df.empty:
        return "지표 데이터가 없습니다."

    current = current_df[
        (current_df["map"].astype(str) == "all-maps")
        & (current_df["data_tier"].astype(str) == tier)
    ].copy()
    if current.empty:
        current = current_df[current_df["map"].astype(str) == "all-maps"].copy()

    for col in ["win_rate", "pick_rate", "ban_rate", "total_score"]:
        if col in current.columns:
            current[col] = pd.to_numeric(current[col], errors="coerce")

    compare = current[["hero", "role", "data_tier", "win_rate", "pick_rate", "ban_rate", "rank"]].copy()
    if previous_df is not None and not previous_df.empty:
        previous = previous_df[
            (previous_df["map"].astype(str) == "all-maps")
            & (previous_df["data_tier"].astype(str).isin(compare["data_tier"].astype(str).unique()))
        ].copy()
        for col in ["win_rate", "pick_rate", "ban_rate"]:
            if col in previous.columns:
                previous[col] = pd.to_numeric(previous[col], errors="coerce")
        previous = previous[["hero", "data_tier", "win_rate", "pick_rate", "ban_rate", "rank"]].rename(
            columns={
                "win_rate": "prev_win_rate",
                "pick_rate": "prev_pick_rate",
                "ban_rate": "prev_ban_rate",
                "rank": "prev_rank",
            }
        )
        compare = compare.merge(previous, on=["hero", "data_tier"], how="left")
        compare["win_delta"] = compare["win_rate"] - compare["prev_win_rate"]
        compare["pick_delta"] = compare["pick_rate"] - compare["prev_pick_rate"]
        compare["ban_delta"] = compare["ban_rate"] - compare["prev_ban_rate"]
        compare["impact_score"] = (
            compare["win_delta"].abs().fillna(0)
            + compare["pick_delta"].abs().fillna(0)
            + compare["ban_delta"].abs().fillna(0) * 0.5
        )
        compare = compare.sort_values("impact_score", ascending=False)
    else:
        compare = compare.sort_values(["rank", "pick_rate"], ascending=[False, False])

    rows = []
    for _, row in compare.head(16).iterrows():
        rows.append(
            {
                "hero": row.get("hero"),
                "role": row.get("role"),
                "tier": row.get("data_tier"),
                "rank": row.get("rank"),
                "prev_rank": row.get("prev_rank", ""),
                "win_rate": round(float(row.get("win_rate", 0) or 0), 2),
                "pick_rate": round(float(row.get("pick_rate", 0) or 0), 2),
                "ban_rate": round(float(row.get("ban_rate", 0) or 0), 2),
                "win_delta": round(float(row.get("win_delta", 0) or 0), 2),
                "pick_delta": round(float(row.get("pick_delta", 0) or 0), 2),
                "ban_delta": round(float(row.get("ban_delta", 0) or 0), 2),
            }
        )

    return json.dumps(rows, ensure_ascii=False, indent=2)


def normalize_hero_name(hero_name):
    text = str(hero_name or "").strip()
    if not text:
        return ""
    if text in VALID_HERO_NAMES:
        return text
    if text in HERO_NAME_ALIASES:
        return HERO_NAME_ALIASES[text]

    normalized = re.sub(r"[\s\.\-_:]+", "", text).lower()
    for alias, hero in HERO_NAME_ALIASES.items():
        if re.sub(r"[\s\.\-_:]+", "", alias).lower() == normalized:
            return hero
    for hero in VALID_HERO_NAMES:
        if re.sub(r"[\s\.\-_:]+", "", hero).lower() == normalized:
            return hero

    match = get_close_matches(text, sorted(VALID_HERO_NAMES), n=1, cutoff=0.72)
    return match[0] if match else ""


def polish_korean_sentence(text):
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""

    replacements = [
        ("반영한다.", "반영한 것으로 보입니다."),
        ("나타낸다.", "나타내고 있습니다."),
        ("보여준다.", "보여주고 있습니다."),
        ("보인다.", "보입니다."),
        ("예상된다.", "예상됩니다."),
        ("가능성이 있다.", "가능성이 있습니다."),
        ("수 있다.", "수 있습니다."),
        ("영향을 미치고 있다.", "영향을 주고 있습니다."),
        ("기록하고 있다.", "기록하고 있습니다."),
        ("유지하고 있다.", "유지하고 있습니다."),
        ("강화시킨 것으로 보인다.", "강화한 것으로 보입니다."),
        ("약한 지위를 나타내며", "다소 약한 흐름을 보이며"),
        ("그의", "해당 영웅의"),
        ("그들의", "해당 영웅들의"),
    ]
    for old, new in replacements:
        cleaned = cleaned.replace(old, new)

    if cleaned.endswith(("합니다", "습니다", "입니다")):
        pass
    elif cleaned.endswith("다"):
        cleaned = cleaned[:-1] + "습니다"
    if not cleaned.endswith((".", "요", "니다", "습니다")):
        cleaned += "."
    return cleaned


def build_display_sentence(hero_name, tone_label, reason):
    reason_text = polish_korean_sentence(reason)
    if not reason_text:
        return f"{topic_phrase(hero_name)} 최신 지표 변화가 관찰되어 추가 추이를 확인해볼 만합니다."

    if reason_text.startswith(hero_name):
        return reason_text

    label = str(tone_label or "").strip()
    if label:
        return f"{topic_phrase(hero_name)} {label}. {reason_text}"
    return f"{topic_phrase(hero_name)} {reason_text}"


def topic_particle(word):
    text = str(word or "")
    if not text:
        return "은"
    last = text[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return "은" if (code - 0xAC00) % 28 else "는"
    return "는"


def topic_phrase(word):
    return f"{word}{topic_particle(word)}"


def normalize_tone_label(label):
    text = polish_korean_sentence(label).rstrip(".")
    label_map = {
        "상승": "지표가 좋아진 편입니다",
        "하락": "지표가 다소 약해진 편입니다",
        "중립": "큰 변화는 아직 뚜렷하지 않습니다",
        "관찰": "추이를 더 지켜볼 필요가 있습니다",
    }
    return label_map.get(text, text or "추이를 더 지켜볼 필요가 있습니다")


def get_analysis_phase(patch_date, analysis_date=None):
    analysis_date = analysis_date or date.today().isoformat()
    try:
        patch_day = date.fromisoformat(str(patch_date))
        analysis_day = date.fromisoformat(str(analysis_date))
    except ValueError:
        return "관찰 단계", None

    days = max((analysis_day - patch_day).days, 0)
    if days <= 1:
        return "초기 관찰", days
    if days <= 4:
        return "단기 변화", days
    if days <= 7:
        return "안정화 추세", days
    return "장기 반영 확인", days


def sanitize_impact_rows(rows, affected_heroes=None, limit=5):
    affected_heroes = {
        normalized for normalized in (normalize_hero_name(hero) for hero in (affected_heroes or []))
        if normalized
    }
    cleaned_rows = []
    seen_heroes = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue

        hero_name = normalize_hero_name(row.get("hero"))
        if not hero_name or hero_name in seen_heroes:
            continue

        raw_hero_name = str(row.get("hero") or "").strip()
        tone_label = normalize_tone_label(row.get("tone_label") or row.get("direction") or "주목할 만합니다")
        reason = polish_korean_sentence(row.get("reason", ""))
        if raw_hero_name and raw_hero_name != hero_name:
            reason = reason.replace(raw_hero_name, hero_name)
        display_sentence = polish_korean_sentence(
            row.get("display_sentence") or build_display_sentence(hero_name, tone_label, reason)
        )
        if raw_hero_name and raw_hero_name != hero_name:
            display_sentence = display_sentence.replace(raw_hero_name, hero_name)
        cleaned_rows.append(
            {
                "hero": hero_name,
                "tone_label": tone_label,
                "reason": reason,
                "display_sentence": display_sentence,
                "impact_type": "direct" if hero_name in affected_heroes else "indirect",
            }
        )
        seen_heroes.add(hero_name)
        if len(cleaned_rows) >= limit:
            break
    return cleaned_rows


def sanitize_patch_ai_payload(ai_payload, patch_note=None, analysis_date=None):
    summary = polish_korean_sentence(ai_payload.get("summary", ""))
    meta_analysis = polish_korean_sentence(ai_payload.get("meta_analysis", ""))
    confidence_note = polish_korean_sentence(ai_payload.get("confidence_note", ""))
    affected_heroes = {
        normalized
        for normalized in (
            normalize_hero_name(hero)
            for hero in ((patch_note or {}).get("affected_heroes") or [])
        )
        if normalized
    }
    analysis_phase = str(ai_payload.get("analysis_phase") or "").strip()
    phase_days = None
    if not analysis_phase:
        analysis_phase, phase_days = get_analysis_phase((patch_note or {}).get("patch_date"), analysis_date)
    else:
        _fallback_phase, phase_days = get_analysis_phase((patch_note or {}).get("patch_date"), analysis_date)

    direct_hero_impacts = sanitize_impact_rows(
        ai_payload.get("direct_hero_impacts") or [],
        affected_heroes=affected_heroes,
        limit=5,
    )
    indirect_hero_impacts = sanitize_impact_rows(
        ai_payload.get("indirect_hero_impacts") or [],
        affected_heroes=affected_heroes,
        limit=5,
    )
    if not direct_hero_impacts and not indirect_hero_impacts:
        legacy_rows = sanitize_impact_rows(
            ai_payload.get("hero_impacts") or [],
            affected_heroes=affected_heroes,
            limit=8,
        )
        direct_hero_impacts = [row for row in legacy_rows if row["impact_type"] == "direct"][:5]
        indirect_hero_impacts = [row for row in legacy_rows if row["impact_type"] != "direct"][:5]
    hero_impacts = (direct_hero_impacts + indirect_hero_impacts)[:8]

    if not summary:
        summary = "최신 지표와 패치 내용을 함께 보면 일부 영웅의 선택률과 견제 흐름을 조금 더 지켜볼 필요가 있습니다."
    if not meta_analysis:
        meta_analysis = summary
    if not confidence_note:
        confidence_note = "이 분석은 현재 수집된 지표를 기준으로 작성되었으며, 표본이 쌓이면 해석이 달라질 수 있습니다."

    return {
        "summary": summary,
        "meta_analysis": meta_analysis,
        "hero_impacts": hero_impacts,
        "direct_hero_impacts": direct_hero_impacts,
        "indirect_hero_impacts": indirect_hero_impacts,
        "analysis_phase": analysis_phase,
        "phase_days": phase_days,
        "confidence_note": confidence_note,
    }


def build_metrics_fallback_analysis(patch_note, metrics_digest, analysis_date=None):
    try:
        metrics_rows = json.loads(metrics_digest)
    except json.JSONDecodeError:
        metrics_rows = []

    scored_rows = []
    for row in metrics_rows:
        if not isinstance(row, dict):
            continue
        hero_name = normalize_hero_name(row.get("hero"))
        if not hero_name:
            continue
        win_rate = float(row.get("win_rate") or 0)
        pick_rate = float(row.get("pick_rate") or 0)
        ban_rate = float(row.get("ban_rate") or 0)
        score = (ban_rate * 0.45) + (pick_rate * 0.35) + (max(win_rate - 50, 0) * 0.2)
        scored_rows.append((score, hero_name, win_rate, pick_rate, ban_rate))

    scored_rows.sort(reverse=True)
    affected_heroes = {
        normalized
        for normalized in (normalize_hero_name(hero) for hero in (patch_note.get("affected_heroes") or []))
        if normalized
    }
    direct_source_rows = [row for row in scored_rows if row[1] in affected_heroes]
    indirect_source_rows = [row for row in scored_rows if row[1] not in affected_heroes]
    direct_rows = direct_source_rows[:5]
    indirect_rows = indirect_source_rows[:5]
    top_rows = (direct_rows + indirect_rows)[:5]
    hero_names = [row[1] for row in (direct_rows or top_rows)[:3]]
    hero_preview = ", ".join(hero_names) if hero_names else "일부 영웅"
    title = str(patch_note.get("title") or "최근 패치")
    analysis_phase, phase_days = get_analysis_phase(patch_note.get("patch_date"), analysis_date)

    summary = (
        f"{analysis_phase} 기준으로 보면, 최근 영웅 밸런스 패치 이후 {hero_preview}의 지표 흐름을 우선 확인해볼 필요가 있습니다. "
        "직접 변경 영웅과 주변 메타의 반응을 분리해서 보는 편이 안전합니다."
    )

    def build_rows(source_rows, impact_type):
        impact_rows = []
        for _score, hero_name, win_rate, pick_rate, ban_rate in source_rows:
            if ban_rate >= 25:
                tone_label = "견제 비중이 높은 편입니다"
                sentence = (
                    f"{topic_phrase(hero_name)} 현재 밴률이 {ban_rate:.1f}%로 높게 나타나 "
                    "상대 팀이 우선적으로 의식하는 영웅으로 보입니다."
                )
            elif pick_rate >= 20:
                tone_label = "선택률이 눈에 띄는 편입니다"
                sentence = (
                    f"{topic_phrase(hero_name)} 현재 픽률이 {pick_rate:.1f}%로 높아 "
                    "실전에서 자주 선택되는 흐름이 확인됩니다."
                )
            elif win_rate >= 52:
                tone_label = "성과가 안정적인 편입니다"
                sentence = (
                    f"{topic_phrase(hero_name)} 현재 승률이 {win_rate:.1f}%로 안정적이라 "
                    "추가 추이를 확인해볼 만합니다."
                )
            else:
                tone_label = "추이를 더 지켜볼 필요가 있습니다"
                sentence = (
                    f"{topic_phrase(hero_name)} 현재 지표 변화가 관찰되어 "
                    "다음 수집 데이터와 함께 비교해볼 필요가 있습니다."
                )
            impact_rows.append(
                {
                    "hero": hero_name,
                    "tone_label": tone_label,
                    "reason": sentence,
                    "display_sentence": sentence,
                    "impact_type": impact_type,
                }
            )
        return impact_rows

    direct_hero_impacts = build_rows(direct_rows, "direct")
    indirect_hero_impacts = build_rows(indirect_rows, "indirect")
    hero_impacts = (direct_hero_impacts + indirect_hero_impacts)[:8]

    if not direct_hero_impacts and affected_heroes:
        for hero_name in sorted(affected_heroes)[:5]:
            sentence = (
                f"{topic_phrase(hero_name)} 이번 밸런스 패치의 직접 변경 대상입니다. "
                "다만 현재 선택한 기준 지표에서는 뚜렷한 변화가 아직 제한적으로 관찰됩니다."
            )
            direct_hero_impacts.append(
                {
                    "hero": hero_name,
                    "tone_label": "직접 변경 대상입니다",
                    "reason": sentence,
                    "display_sentence": sentence,
                    "impact_type": "direct",
                }
            )
        hero_impacts = (direct_hero_impacts + indirect_hero_impacts)[:8]

    meta_analysis = (
        f"{title}는 영웅 밸런스 변경이 포함된 패치입니다. "
        f"현재 분석은 {analysis_phase} 단계로, 직접 변경된 영웅의 지표와 그 주변 영웅의 선택률·밴률 반응을 나누어 보는 것이 좋습니다. "
        f"현재는 {hero_preview}를 중심으로 후속 데이터를 확인해볼 필요가 있습니다."
    )
    return {
        "summary": summary,
        "meta_analysis": meta_analysis,
        "hero_impacts": hero_impacts,
        "direct_hero_impacts": direct_hero_impacts,
        "indirect_hero_impacts": indirect_hero_impacts,
        "analysis_phase": analysis_phase,
        "phase_days": phase_days,
        "confidence_note": "이 분석은 최신 영웅 밸런스 패치와 현재 수집된 지표를 함께 본 결과이므로, 표본이 더 쌓이면 해석이 달라질 수 있습니다.",
    }


def request_ollama_patch_analysis(patch_note, metrics_digest):
    prompt = f"""
너는 오버워치 2 메타 분석 대시보드의 한국어 에디터입니다.
아래 공식 패치노트와 최신 영웅 지표 변화를 연결해서, 사용자에게 설명하는 자연스러운 존댓말로 작성해 주세요.

작성 규칙:
- 반드시 JSON만 출력해 주세요.
- 모든 문장은 존댓말로 작성해 주세요.
- "~한다", "~이다", "~보인다" 같은 반말/딱딱한 보고서체 종결을 피하고, "~습니다", "~보입니다", "~확인됩니다"를 사용해 주세요.
- "상승", "하락" 같은 단어만 단독으로 쓰지 말고, "선택률이 좋아진 편입니다", "지표가 다소 약해졌습니다", "추이를 더 지켜볼 필요가 있습니다"처럼 자연스럽게 작성해 주세요.
- 영웅명은 아래 [사용 가능한 영웅명] 목록에 있는 표기만 사용해 주세요. 목록에 없는 이름은 절대 만들지 마세요.
	- 이 입력 패치노트는 영웅 밸런스 변경이 포함된 패치입니다.
	- [영향 영웅]에 있는 영웅은 direct_hero_impacts에 우선 작성해 주세요.
	- [영향 영웅]에는 없지만 지표 변화가 눈에 띄는 영웅은 indirect_hero_impacts에 작성해 주세요.
	- 직접 변경 영웅과 간접 영향 가능 영웅을 섞지 말고 분리해 주세요.
	- 지표만으로 단정하지 말고 "현재 지표 기준", "관찰됩니다", "가능성이 있습니다"처럼 신중하게 작성해 주세요.

	스키마:
	{{
	  "summary": "메인 페이지에 보여줄 존댓말 1~2문장 요약",
	  "analysis_phase": "초기 관찰|단기 변화|안정화 추세|장기 반영 확인 중 하나",
	  "meta_analysis": "상세 분석 존댓말 3~6문장",
	  "direct_hero_impacts": [
	    {{
	      "hero": "사용 가능한 영웅명 중 하나",
	      "tone_label": "자연어 상태 표현",
	      "reason": "지표와 패치 내용을 연결한 존댓말 이유",
	      "display_sentence": "메인 화면에 그대로 보여줄 한 문장 존댓말 설명"
	    }}
	  ],
	  "indirect_hero_impacts": [
	    {{
	      "hero": "사용 가능한 영웅명 중 하나",
	      "tone_label": "자연어 상태 표현",
	      "reason": "직접 변경은 아니지만 주변 메타나 지표에서 관찰되는 이유",
	      "display_sentence": "메인 화면에 그대로 보여줄 한 문장 존댓말 설명"
	    }}
	  ],
	  "confidence_note": "표본/시차/주의사항"
	}}

[사용 가능한 영웅명]
{", ".join(sorted(VALID_HERO_NAMES))}

[패치노트]
	제목: {patch_note.get("title")}
	날짜: {patch_note.get("patch_date")}
	분석 단계: {get_analysis_phase(patch_note.get("patch_date"))[0]} ({get_analysis_phase(patch_note.get("patch_date"))[1]}일차)
	영향 영웅: {", ".join(patch_note.get("affected_heroes") or [])}
내용:
{str(patch_note.get("parsed_content") or "")[:8000]}

[최신 지표 변화]
{metrics_digest}
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    response_text = body.get("response", "").strip()
    return json.loads(response_text)


def upsert_patch_ai_analysis(analysis_row):
    rows = load_json_list(PATCH_AI_ANALYSIS_PATH)
    replaced = False
    for idx, row in enumerate(rows):
        if (
            row.get("patch_note_id") == analysis_row.get("patch_note_id")
            and row.get("analysis_date") == analysis_row.get("analysis_date")
            and row.get("metrics_snapshot_id") == analysis_row.get("metrics_snapshot_id")
        ):
            rows[idx] = analysis_row
            replaced = True
            break
    if not replaced:
        rows.append(analysis_row)
    rows = sorted(rows, key=lambda item: (item.get("analysis_date", ""), item.get("patch_note_id", "")))
    save_json_list(rows, PATCH_AI_ANALYSIS_PATH)
    return not replaced


def run_patch_update(stats_result=None):
    today_obj = date.today()
    latest_patch_note, balance_patch_note = fetch_latest_patch_bundle(today_obj=today_obj)
    if not latest_patch_note:
        print("⚠️  최신 패치노트를 찾지 못했습니다.")
        return

    latest_patch_note, is_new = upsert_patch_note(latest_patch_note)
    print(f"{'🆕' if is_new else '✅'} 최신 패치노트 저장: {latest_patch_note['title']} ({latest_patch_note['patch_date']})")
    if balance_patch_note:
        balance_patch_note, balance_is_new = upsert_patch_note(balance_patch_note)
        print(
            f"{'🆕' if balance_is_new else '✅'} 최신 밸런스 패치 저장: "
            f"{balance_patch_note['title']} ({balance_patch_note['patch_date']})"
        )
    else:
        print("⏭️  최근 6개월 안에서 영웅 밸런스 패치를 찾지 못해 AI 분석을 건너뜁니다.")
        return

    current_df = None
    previous_df = None
    metrics_snapshot_id = ""
    data_changed = False

    if stats_result:
        current_df = stats_result.get("latest_df")
        previous_df = stats_result.get("previous_latest_df")
        metrics_snapshot_id = stats_result.get("daily_snapshot_path") or ""
        data_changed = bool(stats_result.get("data_changed"))
    elif os.path.exists(LATEST_STATS_PATH):
        current_df = pd.read_parquet(LATEST_STATS_PATH)
        snapshot_dates = current_df.get("snapshot_date", pd.Series(dtype=str)).astype(str)
        update_dates = current_df.get("update_date", pd.Series(dtype=str)).astype(str)
        data_changed = today_obj.isoformat() in set(snapshot_dates) or today_obj.isoformat() in set(update_dates)
        metrics_snapshot_id = LATEST_STATS_PATH

    if current_df is None or current_df.empty:
        print("⚠️  AI 분석 생성을 건너뜁니다. 지표 데이터가 없습니다.")
        return
    if not data_changed and not FORCE_PATCH_AI_ANALYSIS:
        print("⏭️  지표 변동이 없어 AI 패치 영향 분석 생성을 건너뜁니다.")
        return
    if not ENABLE_OLLAMA_ANALYSIS:
        print("⏭️  ENABLE_OLLAMA_ANALYSIS=0 설정으로 AI 패치 영향 분석 생성을 건너뜁니다.")
        return

    metrics_digest = build_metrics_digest(
        current_df,
        previous_df=previous_df,
        tier="Gold",
    )
    try:
        ai_payload = request_ollama_patch_analysis(balance_patch_note, metrics_digest)
    except Exception as exc:
        print(f"⚠️  Ollama AI 분석 생성 실패: {exc}")
        return
    ai_payload = sanitize_patch_ai_payload(
        ai_payload,
        patch_note=balance_patch_note,
        analysis_date=today_obj.isoformat(),
    )
    if not ai_payload.get("hero_impacts"):
        ai_payload = build_metrics_fallback_analysis(
            balance_patch_note,
            metrics_digest,
            analysis_date=today_obj.isoformat(),
        )

    now = datetime.now().isoformat(timespec="seconds")
    analysis_row = {
        "id": hashlib.sha1(
            f"{balance_patch_note['id']}|{today_obj.isoformat()}|{metrics_snapshot_id}|{OLLAMA_MODEL}|{PATCH_PROMPT_VERSION}".encode("utf-8")
        ).hexdigest()[:16],
        "patch_note_id": balance_patch_note["id"],
        "analysis_date": today_obj.isoformat(),
        "metrics_snapshot_id": metrics_snapshot_id,
        "model_name": OLLAMA_MODEL,
        "prompt_version": PATCH_PROMPT_VERSION,
        "summary": ai_payload.get("summary", ""),
        "hero_impacts": ai_payload.get("hero_impacts", []),
        "direct_hero_impacts": ai_payload.get("direct_hero_impacts", []),
        "indirect_hero_impacts": ai_payload.get("indirect_hero_impacts", []),
        "analysis_phase": ai_payload.get("analysis_phase", ""),
        "phase_days": ai_payload.get("phase_days"),
        "meta_analysis": ai_payload.get("meta_analysis", ""),
        "confidence_note": ai_payload.get("confidence_note", ""),
        "created_at": now,
    }
    created = upsert_patch_ai_analysis(analysis_row)
    print(f"{'🧠' if created else '♻️'} AI 패치 영향 분석 저장: {analysis_row['analysis_date']}")


def resolve_stats_game_mode_rq():
    probe_map = "all-maps"
    probe_tier = "All"
    probe_driver = None

    try:
        probe_driver = create_driver()
        register_driver(probe_driver)

        for rq in ["1", "2"]:
            try:
                probe_driver.get(build_rates_url_with_rq(probe_map, probe_tier, rq))
                wait_for_rates_content(probe_driver)
                context_ok, page_context = wait_for_page_context(
                    probe_driver,
                    probe_map,
                    probe_tier,
                    expected_rq=rq,
                )
                if context_ok:
                    print(f"✅ 경쟁전 rq 확정: {rq}")
                    return rq

                current_rq = page_context.get("rq")
                print(
                    f"⚠️  rq={rq} probe 실패: {probe_map}/{probe_tier}에서 rq={current_rq}로 리다이렉트됨"
                )

                if current_rq != "0":
                    print(f"⚠️  예상과 다른 rq로 리다이렉트됨: {current_rq}")
            except Exception as exc:
                print(f"⚠️  rq={rq} probe 실패: {probe_map}/{probe_tier} -> {exc}")

        return None
    finally:
        if probe_driver is not None:
            unregister_driver(probe_driver)
            try:
                probe_driver.quit()
            except Exception:
                pass


def scrape_data(driver, tier_name, map_id):
    """기존 드라이버로 특정 티어 + 전장 데이터 수집"""
    rq = get_active_stats_game_mode_rq()
    url = build_rates_url_with_rq(map_id, tier_name, rq)
    try:
        driver.get(url)
        wait_for_rates_content(driver)
        context_ok, page_context = wait_for_page_context(driver, map_id, tier_name, expected_rq=rq)
        if not context_ok:
            if is_unsupported_all_maps_tier_redirect(map_id, tier_name, page_context):
                print(
                    f"↪️  {tier_name} / {map_id} 조합은 현재 페이지에서 All 티어로 리다이렉트됩니다. "
                    "기존 latest 행 유지 대상으로 표시합니다."
                )
                return None

            print(f"⚠️  페이지 파라미터 불일치(rq={rq}): 요청 map={map_id}, tier={tier_name} / 현재 URL={page_context['url']}")
            return pd.DataFrame()
        time.sleep(1)

        df = scrape_rates_from_dom(driver)
        dom_ok, _dom_reason = validate_scraped_df(df)
        if not dom_ok:
            df = scrape_rates_from_text(driver)

        if 'ban_rate' not in df.columns:
            df['ban_rate'] = '0%'
        ok, reason = validate_scraped_df(df)
        if not ok:
            print(f"⚠️  수집 검증 실패({tier_name}/{map_id}, rq={rq}): {reason}")
            return pd.DataFrame()

        if not df.empty:
            df['role'] = df['hero'].map(role_dict).fillna("Unknown")
            df['data_tier'] = normalize_tier_name(tier_name)
            df['map'] = map_id
            df['map_name'] = df['map'].map(map_dict)
            df['update_date'] = str(date.today())
        return df

    except Exception as e:
        print(f"❌ {tier_name} / {map_id} 에러: {e}")
        return pd.DataFrame()

def scrape_task(task):
    tier_name, map_id = task
    for attempt in range(1, TASK_RETRIES + 1):
        if STOP_REQUESTED.is_set():
            break

        driver = None
        try:
            driver = create_driver()
            register_driver(driver)
            df = scrape_data(driver, tier_name, map_id)
            if df is None:
                return {
                    'tier_name': tier_name,
                    'map_id': map_id,
                    'df': pd.DataFrame(),
                    'missing': [],
                    'skipped': True,
                    'skip_reason': 'unsupported_all_maps_tier_redirect',
                }
            missing = []
            if not df.empty:
                missing = df[df['role'].isna()]['hero'].unique().tolist()
            if df.empty and attempt < TASK_RETRIES:
                print(f"⚠️  {tier_name} / {map_id} 빈 결과(시도 {attempt}/{TASK_RETRIES}), 재시도")
                STOP_REQUESTED.wait(attempt)
                continue
            return {
                'tier_name': tier_name,
                'map_id': map_id,
                'df': df,
                'missing': missing,
                'skipped': False,
                'skip_reason': '',
            }
        except KeyboardInterrupt:
            STOP_REQUESTED.set()
            raise
        except Exception as exc:
            if attempt < TASK_RETRIES:
                print(f"⚠️  {tier_name} / {map_id} 작업 실패(시도 {attempt}/{TASK_RETRIES}), 재시도: {exc}")
                STOP_REQUESTED.wait(attempt * 2)
                continue
            print(f"❌ {tier_name} / {map_id} 최종 실패: {exc}")
            return {
                'tier_name': tier_name,
                'map_id': map_id,
                'df': pd.DataFrame(),
                'missing': [],
                'skipped': False,
                'skip_reason': '',
            }
        finally:
            if driver is not None:
                unregister_driver(driver)
                try:
                    driver.quit()
                except Exception:
                    pass

    return {
        'tier_name': tier_name,
        'map_id': map_id,
        'df': pd.DataFrame(),
        'missing': [],
        'skipped': STOP_REQUESTED.is_set(),
        'skip_reason': 'stop_requested' if STOP_REQUESTED.is_set() else '',
    }


def normalize_url(href):
    if not href:
        return ""
    return urljoin(BASE_URL, href)


def extract_hero_links(driver, locale):
    landing_url = f"{BASE_URL}/{locale}"
    driver.get(landing_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
    time.sleep(1.5)

    hrefs = driver.execute_script(
        """
        const anchors = Array.from(document.querySelectorAll('a[href]'));
        return anchors.map(a => a.getAttribute('href')).filter(Boolean);
        """
    )

    links = set()
    for href in hrefs:
        absolute = normalize_url(href)
        match = HERO_LINK_RE.match(absolute)
        if match:
            links.add(absolute)

    ordered = sorted(links)
    print(f"Found {len(ordered)} hero pages from {landing_url}")
    return ordered


def extract_perk_slug(perk_image_url):
    if not perk_image_url:
        return ""

    parsed = urlparse(perk_image_url)
    query_path = parse_qs(parsed.query).get("url", [""])[0]
    if query_path:
        decoded = unquote(query_path)
        filename = os.path.basename(decoded)
    else:
        filename = os.path.basename(parsed.path)

    return os.path.splitext(filename)[0]


def extract_raw_perk_image_url(perk_image_url):
    if not perk_image_url:
        return ""

    parsed = urlparse(perk_image_url)
    query_path = parse_qs(parsed.query).get("url", [""])[0]
    if not query_path:
        return perk_image_url

    decoded = unquote(query_path)
    return urljoin(BASE_URL, decoded)


def scrape_hero_page(driver, hero_url):
    driver.get(hero_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".hero-card")))
    time.sleep(0.6)

    payload = driver.execute_script(
        """
        const card = document.querySelector('.hero-card');
        if (!card) {
            return { hero_name: '', rows: [] };
        }

        const heroName = (card.querySelector('h2')?.textContent || '').trim();
        const heroImage = card.querySelector('img[alt]')?.currentSrc || card.querySelector('img[alt]')?.src || '';

        const sections = Array.from(card.querySelectorAll('ul')).slice(0, 2);
        const sectionTypes = ['minor', 'major'];
        const rows = [];

        for (let i = 0; i < sections.length; i++) {
            const perkType = sectionTypes[i] || 'unknown';
            const items = Array.from(sections[i].querySelectorAll('li'));

            for (const li of items) {
                const text = (li.innerText || '').trim();
                const percentMatch = text.match(/(\\d+(?:\\.\\d+)?)\\s*%/);
                const pickRate = percentMatch ? Number(percentMatch[1]) : null;

                const img = li.querySelector('img');
                const perkImage = img?.currentSrc || img?.src || '';
                let perkName = (img?.alt || '').trim();

                if (!perkName) {
                    const candidate = li.querySelector('h2, h3, strong, [class*="font-bold"]');
                    perkName = (candidate?.textContent || '').trim();
                }

                if (!perkName) {
                    const lines = text
                        .split('\\n')
                        .map(v => v.trim())
                        .filter(Boolean)
                        .filter(v => !/^\\d+(?:\\.\\d+)?%$/.test(v));
                    perkName = lines.length ? lines[0] : '';
                }

                const descriptionElement = Array.from(li.children).find(
                    element => element.tagName === 'SPAN' && element.classList.contains('text-gray-300')
                );
                const perkDescription = (descriptionElement?.textContent || '').trim();

                rows.push({
                    perk_type: perkType,
                    perk_name: perkName,
                    perk_description: perkDescription,
                    pick_rate: pickRate,
                    perk_image_url: perkImage,
                });
            }
        }

        return {
            hero_name: heroName,
            hero_image_url: heroImage,
            rows,
        };
        """
    )

    category_match = re.match(r"^https://owperks\.com/ko/(tanks|damages|supports)/([^/?#]+)$", hero_url)
    if not category_match:
        return []

    category = category_match.group(1)
    hero_slug = category_match.group(2)
    role = CATEGORY_TO_ROLE.get(category, "Unknown")

    rows = []
    for row in payload.get("rows", []):
        perk_image_url = row.get("perk_image_url") or ""
        rows.append(
            {
                "hero": payload.get("hero_name") or hero_slug,
                "hero_slug": hero_slug,
                "role": role,
                "category": category,
                "perk_type": row.get("perk_type", ""),
                "perk_name": (row.get("perk_name") or "").strip(),
                "perk_description": (row.get("perk_description") or "").strip(),
                "pick_rate": row.get("pick_rate"),
                "perk_slug": extract_perk_slug(perk_image_url),
                "perk_image_url": perk_image_url,
                "perk_image_raw_url": extract_raw_perk_image_url(perk_image_url),
                "hero_image_url": payload.get("hero_image_url", ""),
                "source_url": hero_url,
                "update_date": str(date.today()),
            }
        )

    return rows


def run_perk_update(locale=DEFAULT_LOCALE, max_heroes=None, headed=False):
    started_at = time.time()

    driver = create_driver(headless=not headed)
    try:
        hero_links = extract_hero_links(driver, locale)
        if max_heroes is not None:
            hero_links = hero_links[: max(0, max_heroes)]

        if not hero_links:
            print("No hero links found. Nothing to scrape.")
            return

        all_rows: List[Dict] = []
        failed_heroes: List[str] = []
        total = len(hero_links)
        for idx, hero_url in enumerate(hero_links, start=1):
            print(f"[{idx}/{total}] scraping {hero_url}")
            try:
                rows = scrape_hero_page(driver, hero_url)
                if rows:
                    all_rows.extend(rows)
                else:
                    print(f"  warning: no perk rows parsed: {hero_url}")
                    failed_heroes.append(hero_url)
            except Exception as exc:
                print(f"  error: {hero_url} -> {exc}")
                failed_heroes.append(hero_url)

        if failed_heroes:
            print(
                f"❌ 퍼크 수집이 완전하지 않아 저장을 중단합니다. 실패 수: {len(failed_heroes)}/{total}"
            )
            print(f"❌ 실패 목록: {failed_heroes[:20]}{' ...' if len(failed_heroes) > 20 else ''}")
            return

        if not all_rows:
            print("No perk rows scraped.")
            return

        df = pd.DataFrame(all_rows)
        df["pick_rate"] = pd.to_numeric(df["pick_rate"], errors="coerce")
        df = df.drop_duplicates(
            subset=["hero_slug", "perk_type", "perk_slug", "update_date"],
            keep="last",
        ).reset_index(drop=True)

        df = df.sort_values(
            by=["role", "hero", "perk_type", "pick_rate"],
            ascending=[True, True, True, False],
        ).reset_index(drop=True)

        columns = [
            "hero",
            "hero_slug",
            "role",
            "category",
            "perk_type",
            "perk_name",
            "perk_description",
            "pick_rate",
            "perk_slug",
            "perk_image_url",
            "perk_image_raw_url",
            "hero_image_url",
            "source_url",
            "update_date",
        ]
        df = df.reindex(columns=columns)

        save_parquet(df, LATEST_PERKS_PATH)

        elapsed = int(time.time() - started_at)
        print(
            f"Done. Saved {len(df)} rows to {LATEST_PERKS_PATH} "
            f"(heroes={df['hero_slug'].nunique()}, elapsed={elapsed}s)"
        )
    finally:
        driver.quit()


def run_stats_update():
    started_at = perf_counter()
    global ACTIVE_STATS_GAME_MODE_RQ

    resolved_rq = resolve_stats_game_mode_rq()
    if resolved_rq is None:
        print("❌ rq 값을 확정하지 못해 수집을 중단합니다.")
        return

    ACTIVE_STATS_GAME_MODE_RQ = resolved_rq
    print(f"🧭 수집에 사용할 rq: {ACTIVE_STATS_GAME_MODE_RQ}")

    map_ids = list(map_dict.keys())
    print(f"🗺️  전장 {len(map_ids)}개: {map_ids}")

    tasks = [(tier_name, map_id) for map_id in map_ids for tier_name in tiers]
    total = len(tasks)
    print(f"🧵 병렬 수집 시작: worker={MAX_WORKERS}, task={total}")

    final_list = []
    failed_tasks = []
    skipped_tasks = []
    done_count = 0
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {executor.submit(scrape_task, task): task for task in tasks}
    pending = set(futures)

    try:
        while pending:
            done_futures, pending = wait(pending, timeout=1, return_when=FIRST_COMPLETED)
            for future in done_futures:
                done_count += 1
                tier_name, map_id = futures[future]
                print(f"🚀 [{done_count}/{total}] {tier_name} / {map_id} 완료")
                result = future.result()
                if result['missing']:
                    print(f"⚠️  누락 영웅: {result['missing']}")
                if result.get('skipped'):
                    skipped_tasks.append((tier_name, map_id, result.get('skip_reason', '')))
                elif not result['df'].empty:
                    final_list.append(result['df'])
                else:
                    failed_tasks.append((tier_name, map_id))
    except KeyboardInterrupt:
        STOP_REQUESTED.set()
        print("\n🛑 중단 요청 감지. 실행 중인 브라우저 세션을 정리합니다.")
        for future in pending:
            future.cancel()
        quit_active_drivers()
        executor.shutdown(wait=False, cancel_futures=True)
        raise SystemExit(130)
    finally:
        if not STOP_REQUESTED.is_set():
            executor.shutdown(wait=True, cancel_futures=False)

    if not final_list:
        print("❌ 수집된 데이터가 없습니다.")
        return

    if failed_tasks or skipped_tasks or len(final_list) != total:
        print(
            f"❌ 수집이 완전하지 않아 저장을 중단합니다. 성공 {len(final_list)}/{total}, "
            f"실패 {len(failed_tasks)}, 스킵 {len(skipped_tasks)}"
        )
        if failed_tasks:
            print(f"❌ 실패 목록: {failed_tasks[:20]}{' ...' if len(failed_tasks) > 20 else ''}")
        if skipped_tasks:
            print(f"❌ 스킵 목록: {skipped_tasks[:20]}{' ...' if len(skipped_tasks) > 20 else ''}")
        return

    # 데이터 통합
    full_df = pd.concat(final_list, ignore_index=True)

    # 숫자 변환
    full_df['win_rate']  = full_df['win_rate'].str.replace('%', '', regex=False).replace('--', '0').astype(float)
    full_df['pick_rate'] = full_df['pick_rate'].str.replace('%', '', regex=False).replace('--', '0').astype(float)
    if 'ban_rate' in full_df.columns:
        full_df['ban_rate'] = full_df['ban_rate'].str.replace('%', '', regex=False).replace('--', '0').astype(float)
    else:
        full_df['ban_rate'] = 0.0

    # 랭크 계산
    group_key = ['data_tier', 'map', 'role']
    persistence_df = build_recent_persistence_frame()
    print(
        "📐 메타 지배력 공식: "
        f"존재감={META_PRESENCE_WEIGHT:.2f} × z(log1p(픽률 + {PRESENCE_BAN_WEIGHT:.2f}×밴률)) "
        f"+ 성능={META_PERFORMANCE_WEIGHT:.2f} × z(수축 승률), "
        f"최근 {PERSISTENCE_WEEKS}주 지속성 rows={len(persistence_df)} (진단용)"
    )
    full_df = add_scoring_columns(full_df, group_key=group_key, persistence_df=persistence_df)

    full_df['rank'] = full_df.groupby(group_key)['total_score'].transform(assign_score_rank)
    full_df = normalize_dataset_for_scoring(full_df)
    full_df = full_df.reindex(columns=STATS_COLUMNS)

    if is_degenerate_snapshot(full_df):
        print("❌ 비정상 스냅샷 감지(전장별 분산 부족). 저장을 중단합니다.")
        return

    today_obj = date.today()
    today = str(today_obj)

    previous_latest_df = None
    if os.path.exists(LATEST_STATS_PATH):
        previous_latest_df = pd.read_parquet(LATEST_STATS_PATH)

    latest_df = full_df.drop_duplicates(
        subset=['hero', 'data_tier', 'map'],
        keep='last',
    ).reset_index(drop=True)

    snapshot_df = latest_df.copy()
    snapshot_df['snapshot_date'] = today_obj.isoformat()

    data_changed = True
    if previous_latest_df is not None and not previous_latest_df.empty:
        old_compare = build_snapshot_compare_frame(previous_latest_df.copy())
        new_compare = build_snapshot_compare_frame(latest_df.copy())
        data_changed = not new_compare.equals(old_compare)

    save_parquet(snapshot_df, LATEST_STATS_PATH)
    daily_saved_as = save_daily_snapshot(snapshot_df, today_obj)
    weekly_saved_as = save_weekly_snapshot_if_due(snapshot_df, today_obj)
    rank_diagnostics = save_rank_diagnostics(latest_df)

    elapsed = format_elapsed(perf_counter() - started_at)
    if data_changed:
        print(
            f"🎉 {today} 데이터 갱신 완료! "
            f"(latest={len(latest_df)}행, 소요 시간: {elapsed})"
        )
        print(f"📁 최신 데이터: {LATEST_STATS_PATH}")
    else:
        print(f"⏭️  데이터 변동 없음. latest 덮어쓰기 완료. (소요 시간: {elapsed})")
    print(f"📁 일별 스냅샷: {daily_saved_as}")
    print(f"📁 주간 스냅샷: {weekly_saved_as}")
    print(f"📁 랭크 진단 리포트: {RANK_DIAGNOSTICS_PATH}")
    return {
        "latest_df": latest_df,
        "previous_latest_df": previous_latest_df,
        "data_changed": data_changed,
        "daily_snapshot_path": daily_saved_as,
        "weekly_snapshot_path": weekly_saved_as,
        "rank_diagnostics": rank_diagnostics,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update Overwatch competitive stats and/or hero perks data."
    )
    parser.add_argument(
        "--mode",
        choices=["stats", "perks", "patch", "all"],
        default="stats",
        help="What to update (default: stats)",
    )
    parser.add_argument("--locale", default=DEFAULT_LOCALE, help="Perk scraper locale")
    parser.add_argument("--max-heroes", type=int, default=None, help="Perk scrape hero limit")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode for perk scraping",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    stats_result = None
    if args.mode in ("stats", "all"):
        stats_result = run_stats_update()
    if args.mode in ("perks", "all"):
        run_perk_update(
            locale=args.locale,
            max_heroes=args.max_heroes,
            headed=args.headed,
        )
    if args.mode in ("patch", "all"):
        run_patch_update(stats_result=stats_result)


if __name__ == "__main__":
    main()
