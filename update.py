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
    'win_rate', 'pick_rate', 'ban_rate', 'win_rate_z', 'pick_rate_log', 'pick_rate_z', 'total_score', 'rank',
]

DATA_DIR = "data"
LATEST_DIR = os.path.join(DATA_DIR, "latest")
HISTORY_DIR = os.path.join(DATA_DIR, "history")

LATEST_STATS_PATH = os.path.join(LATEST_DIR, "latest_tier.parquet")
LATEST_PERKS_PATH = os.path.join(LATEST_DIR, "latest_perks.parquet")
WEEKLY_HISTORY_ROOT = os.path.join(HISTORY_DIR, "weekly")
DAILY_HISTORY_ROOT = os.path.join(HISTORY_DIR, "daily")
PATCH_NOTES_DIR = os.path.join(DATA_DIR, "patch_notes")
PATCH_NOTES_PATH = os.path.join(PATCH_NOTES_DIR, "patch_notes.json")
PATCH_AI_ANALYSIS_PATH = os.path.join(PATCH_NOTES_DIR, "patch_ai_analysis.json")
WEEKLY_SNAPSHOT_WEEKDAY = int(os.getenv("WEEKLY_SNAPSHOT_WEEKDAY", "0"))

WIN_RATE_WEIGHT = 0.5
PICK_RATE_WEIGHT = 0.3
BAN_RATE_WEIGHT = 0.2
RANK_LABELS = ['C', 'B', 'A', 'S']

BASE_URL = "https://owperks.com"
OFFICIAL_PATCH_NOTES_BASE_URL = "https://overwatch.blizzard.com/ko-kr/news/patch-notes/live"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")
OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate")
ENABLE_OLLAMA_ANALYSIS = os.getenv(
    "ENABLE_OLLAMA_ANALYSIS",
    "0" if os.getenv("GITHUB_ACTIONS") == "true" else "1",
) != "0"
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
    if len(scores) < len(RANK_LABELS) or scores.nunique(dropna=True) < 2:
        return pd.Series(['A'] * len(scores), index=scores.index)

    try:
        bins = pd.qcut(
            scores,
            q=len(RANK_LABELS),
            labels=False,
            duplicates='drop',
        )
    except ValueError:
        return pd.Series(['A'] * len(scores), index=scores.index)

    bin_count = int(bins.max()) + 1 if not bins.isna().all() else 0
    if bin_count < 2:
        return pd.Series(['A'] * len(scores), index=scores.index)

    label_indexes = np.linspace(0, len(RANK_LABELS) - 1, bin_count).round().astype(int)
    dynamic_labels = [RANK_LABELS[index] for index in label_indexes]
    return bins.map(lambda bin_index: dynamic_labels[int(bin_index)] if pd.notna(bin_index) else 'A')


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
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    return patches


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
    today_obj = today_obj or date.today()
    all_patches = []
    for year, month in month_candidates(today_obj):
        try:
            page_html, page_url = fetch_patch_month_html(year, month)
            all_patches.extend(parse_patch_blocks(page_html, page_url))
        except Exception as exc:
            print(f"⚠️  패치노트 페이지 수집 실패({year}/{month}): {exc}")
        if all_patches:
            break

    if not all_patches:
        return None

    return max(all_patches, key=lambda row: (row["patch_date"], row["id"]))


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

    if cleaned.endswith("다"):
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
    return "은"


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


def sanitize_patch_ai_payload(ai_payload):
    summary = polish_korean_sentence(ai_payload.get("summary", ""))
    meta_analysis = polish_korean_sentence(ai_payload.get("meta_analysis", ""))
    confidence_note = polish_korean_sentence(ai_payload.get("confidence_note", ""))

    hero_impacts = []
    seen_heroes = set()
    for row in ai_payload.get("hero_impacts", []):
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
        hero_impacts.append(
            {
                "hero": hero_name,
                "tone_label": tone_label,
                "reason": reason,
                "display_sentence": display_sentence,
            }
        )
        seen_heroes.add(hero_name)
        if len(hero_impacts) >= 5:
            break

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
        "confidence_note": confidence_note,
    }


def build_metrics_fallback_analysis(patch_note, metrics_digest):
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
    top_rows = scored_rows[:5]
    hero_names = [row[1] for row in top_rows[:3]]
    hero_preview = ", ".join(hero_names) if hero_names else "일부 영웅"
    title = str(patch_note.get("title") or "최근 패치")

    summary = (
        "이번 패치는 영웅 성능을 직접 바꾸는 패치라기보다 이벤트 조정에 가까워 보입니다. "
        f"다만 현재 지표 기준으로는 {hero_preview}의 선택률과 견제 흐름을 함께 지켜볼 필요가 있습니다."
    )
    hero_impacts = []
    for _score, hero_name, win_rate, pick_rate, ban_rate in top_rows:
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
        hero_impacts.append(
            {
                "hero": hero_name,
                "tone_label": tone_label,
                "reason": sentence,
                "display_sentence": sentence,
            }
        )

    meta_analysis = (
        f"{title} 내용을 보면 영웅 밸런스 직접 조정보다는 이벤트 조건 완화에 가깝습니다. "
        "따라서 영웅별 지표 변화는 패치 효과라고 단정하기보다, 현재 수집된 경쟁전 지표에서 관찰되는 메타 흐름으로 보는 편이 안전합니다. "
        f"현재는 {hero_preview}처럼 선택률이나 밴률이 두드러지는 영웅을 중심으로 후속 데이터를 확인해볼 필요가 있습니다."
    )
    return {
        "summary": summary,
        "meta_analysis": meta_analysis,
        "hero_impacts": hero_impacts,
        "confidence_note": "이번 분석은 영웅 밸런스 직접 변경이 없는 패치와 최신 지표를 함께 본 결과이므로, 패치 영향으로 단정하지 않고 관찰 흐름으로 해석하는 것이 좋습니다.",
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
- 패치노트에 영웅 밸런스 변경이 없으면, 패치가 직접적인 영웅 성능 변경은 아니라고 조심스럽게 표현해 주세요.
- 영웅 밸런스 변경이 없더라도 최신 지표에서 눈에 띄는 영웅 3~5명은 "패치 효과"가 아니라 "현재 지표상 관찰되는 흐름"으로 작성해 주세요.
- 지표만으로 단정하지 말고 "현재 지표 기준", "관찰됩니다", "가능성이 있습니다"처럼 신중하게 작성해 주세요.

스키마:
{{
  "summary": "메인 페이지에 보여줄 존댓말 1~2문장 요약",
  "meta_analysis": "상세 분석 존댓말 3~6문장",
  "hero_impacts": [
    {{
      "hero": "사용 가능한 영웅명 중 하나",
      "tone_label": "자연어 상태 표현",
      "reason": "지표와 패치 내용을 연결한 존댓말 이유",
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
    patch_note = fetch_latest_patch_note(today_obj=today_obj)
    if not patch_note:
        print("⚠️  최신 패치노트를 찾지 못했습니다.")
        return

    patch_note, is_new = upsert_patch_note(patch_note)
    print(f"{'🆕' if is_new else '✅'} 최신 패치노트 저장: {patch_note['title']} ({patch_note['patch_date']})")

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
    if not data_changed:
        print("⏭️  지표 변동이 없어 AI 패치 영향 분석 생성을 건너뜁니다.")
        return
    if not ENABLE_OLLAMA_ANALYSIS:
        print("⏭️  ENABLE_OLLAMA_ANALYSIS=0 설정으로 AI 패치 영향 분석 생성을 건너뜁니다.")
        return

    metrics_digest = build_metrics_digest(current_df, previous_df=previous_df)
    try:
        ai_payload = request_ollama_patch_analysis(patch_note, metrics_digest)
    except Exception as exc:
        print(f"⚠️  Ollama AI 분석 생성 실패: {exc}")
        return
    ai_payload = sanitize_patch_ai_payload(ai_payload)
    if not ai_payload.get("hero_impacts"):
        ai_payload = build_metrics_fallback_analysis(patch_note, metrics_digest)

    now = datetime.now().isoformat(timespec="seconds")
    analysis_row = {
        "id": hashlib.sha1(
            f"{patch_note['id']}|{today_obj.isoformat()}|{metrics_snapshot_id}|{OLLAMA_MODEL}|{PATCH_PROMPT_VERSION}".encode("utf-8")
        ).hexdigest()[:16],
        "patch_note_id": patch_note["id"],
        "analysis_date": today_obj.isoformat(),
        "metrics_snapshot_id": metrics_snapshot_id,
        "model_name": OLLAMA_MODEL,
        "prompt_version": PATCH_PROMPT_VERSION,
        "summary": ai_payload.get("summary", ""),
        "hero_impacts": ai_payload.get("hero_impacts", []),
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
    def safe_zscore(series):
        std = series.std()
        if std == 0 or pd.isna(std):
            return pd.Series([0] * len(series), index=series.index)
        return (series - series.mean()) / std

    group_key = ['data_tier', 'map']
    full_df['win_rate_z']    = full_df.groupby(group_key)['win_rate'].transform(safe_zscore)
    full_df['pick_rate_log'] = np.log1p(full_df['pick_rate'])
    full_df['pick_rate_z']   = full_df.groupby(group_key)['pick_rate_log'].transform(safe_zscore)
    full_df['ban_rate_log']  = np.log1p(full_df['ban_rate'])
    full_df['ban_rate_z']    = full_df.groupby(group_key)['ban_rate_log'].transform(safe_zscore)
    full_df['total_score']   = (
        full_df['win_rate_z'] * WIN_RATE_WEIGHT
        + full_df['pick_rate_z'] * PICK_RATE_WEIGHT
        + full_df['ban_rate_z'] * BAN_RATE_WEIGHT
    )

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
    return {
        "latest_df": latest_df,
        "previous_latest_df": previous_latest_df,
        "data_changed": data_changed,
        "daily_snapshot_path": daily_saved_as,
        "weekly_snapshot_path": weekly_saved_as,
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
