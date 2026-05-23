from __future__ import annotations

import argparse
import os
import re
import threading
import time
from datetime import date
from typing import Dict, List
from urllib.parse import urlencode, urlparse, parse_qs, unquote, urljoin

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
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
WEEKLY_SNAPSHOT_WEEKDAY = int(os.getenv("WEEKLY_SNAPSHOT_WEEKDAY", "0"))

WIN_RATE_WEIGHT = 0.5
PICK_RATE_WEIGHT = 0.3
BAN_RATE_WEIGHT = 0.2

BASE_URL = "https://owperks.com"
DEFAULT_LOCALE = "ko"
STATS_INPUT = "PC"
STATS_REGION = "Asia"
STATS_ROLE = "All"
STATS_GAME_MODE_RQ = os.getenv("STATS_GAME_MODE_RQ", "2")

CATEGORY_TO_ROLE = {
    "tanks": "Tank",
    "damages": "Damage",
    "supports": "Support",
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


def build_rates_url(map_id, tier_name):
    params = {
        "input": STATS_INPUT,
        "map": map_id,
        "region": STATS_REGION,
        "role": STATS_ROLE,
        "rq": STATS_GAME_MODE_RQ,
        "tier": normalize_tier_name(tier_name),
    }
    return "https://overwatch.blizzard.com/ko-kr/rates/?" + urlencode(params)


def page_context_matches(driver, expected_map, expected_tier):
    context = current_page_context(driver)
    return (
        context["input"] == STATS_INPUT
        and context["map"] == expected_map
        and context["region"] == STATS_REGION
        and context["role"] == STATS_ROLE
        and context["rq"] == STATS_GAME_MODE_RQ
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


def wait_for_page_context(driver, expected_map, expected_tier, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page_context_matches(driver, expected_map, expected_tier):
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


def scrape_data(driver, tier_name, map_id):
    """기존 드라이버로 특정 티어 + 전장 데이터 수집"""
    url = build_rates_url(map_id, tier_name)
    try:
        driver.get(url)
        wait_for_rates_content(driver)
        context_ok, page_context = wait_for_page_context(driver, map_id, tier_name)
        if not context_ok:
            if is_unsupported_all_maps_tier_redirect(map_id, tier_name, page_context):
                print(
                    f"↪️  {tier_name} / {map_id} 조합은 현재 페이지에서 All 티어로 리다이렉트됩니다. "
                    "기존 latest 행 유지 대상으로 표시합니다."
                )
                return None

            print(f"⚠️  페이지 파라미터 불일치: 요청 map={map_id}, tier={tier_name} / 현재 URL={page_context['url']}")
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
            print(f"⚠️  수집 검증 실패({tier_name}/{map_id}): {reason}")
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

                rows.push({
                    perk_type: perkType,
                    perk_name: perkName,
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
        total = len(hero_links)
        for idx, hero_url in enumerate(hero_links, start=1):
            print(f"[{idx}/{total}] scraping {hero_url}")
            try:
                rows = scrape_hero_page(driver, hero_url)
                if rows:
                    all_rows.extend(rows)
                else:
                    print(f"  warning: no perk rows parsed: {hero_url}")
            except Exception as exc:
                print(f"  error: {hero_url} -> {exc}")

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
            "pick_rate",
            "perk_slug",
            "perk_image_url",
            "perk_image_raw_url",
            "hero_image_url",
            "source_url",
            "update_date",
        ]
        df = df.reindex(columns=columns)

        if os.path.exists(LATEST_PERKS_PATH):
            previous_perks_df = pd.read_parquet(LATEST_PERKS_PATH)
            old_compare = build_perk_compare_frame(previous_perks_df)
            new_compare = build_perk_compare_frame(df)
            if new_compare.equals(old_compare):
                elapsed = int(time.time() - started_at)
                print(
                    f"Perks unchanged. Skipped saving {LATEST_PERKS_PATH} "
                    f"(heroes={df['hero_slug'].nunique()}, elapsed={elapsed}s)"
                )
                return

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

    if failed_tasks:
        print(f"❌ 실패한 작업이 있어 저장을 중단합니다. 실패 수: {len(failed_tasks)}/{total}")
        print(f"❌ 실패 목록: {failed_tasks[:20]}{' ...' if len(failed_tasks) > 20 else ''}")
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

    def assign_rank(scores):
        if len(scores) >= 4:
            return pd.qcut(scores, q=4, labels=['C', 'B', 'A', 'S'], duplicates='drop')
        return pd.Series(['A'] * len(scores), index=scores.index)

    full_df['rank'] = full_df.groupby(group_key)['total_score'].transform(assign_rank)
    full_df = normalize_dataset_for_scoring(full_df)
    full_df = full_df.reindex(columns=STATS_COLUMNS)

    if skipped_tasks and os.path.exists(LATEST_STATS_PATH):
        previous_latest_df = pd.read_parquet(LATEST_STATS_PATH)
        preserved_frames = []
        for tier_name, map_id, _reason in skipped_tasks:
            preserved = previous_latest_df[
                (previous_latest_df['data_tier'].astype(str) == normalize_tier_name(tier_name))
                & (previous_latest_df['map'].astype(str) == map_id)
            ].copy()
            if not preserved.empty:
                preserved_frames.append(preserved.reindex(columns=STATS_COLUMNS))

        if preserved_frames:
            preserved_df = pd.concat(preserved_frames, ignore_index=True)
            full_df = pd.concat([full_df, preserved_df], ignore_index=True)
            print(
                f"↪️  리다이렉트로 수집 불가한 조합 {len(skipped_tasks)}개는 "
                f"기존 latest 행 {len(preserved_df)}개를 유지합니다."
            )
        else:
            print(f"⚠️  리다이렉트로 수집 불가한 조합 {len(skipped_tasks)}개가 있고 유지할 기존 행이 없습니다.")
    elif skipped_tasks:
        print(f"⚠️  리다이렉트로 수집 불가한 조합 {len(skipped_tasks)}개가 있고 기존 latest 파일이 없습니다.")

    if is_degenerate_snapshot(full_df):
        print("❌ 비정상 스냅샷 감지(전장별 분산 부족). 저장을 중단합니다.")
        return

    today_obj = date.today()
    today = str(today_obj)

    previous_latest_df = None
    if os.path.exists(LATEST_STATS_PATH):
        previous_latest_df = pd.read_parquet(LATEST_STATS_PATH)

    if previous_latest_df is not None and not previous_latest_df.empty:
        old_compare = build_snapshot_compare_frame(previous_latest_df.copy())
        new_compare = build_snapshot_compare_frame(full_df.copy())
        if new_compare.equals(old_compare):
            elapsed = format_elapsed(perf_counter() - started_at)
            print(f"⏭️  데이터 변동 없음. 업데이트를 건너뜁니다. (소요 시간: {elapsed})")
            return

    latest_df = full_df.drop_duplicates(
        subset=['hero', 'data_tier', 'map'],
        keep='last',
    ).reset_index(drop=True)

    snapshot_df = latest_df.copy()
    snapshot_df['snapshot_date'] = today_obj.isoformat()

    save_parquet(snapshot_df, LATEST_STATS_PATH)

    weekly_saved_as = save_weekly_snapshot_if_due(snapshot_df, today_obj)

    elapsed = format_elapsed(perf_counter() - started_at)
    print(
        f"🎉 {today} 데이터 갱신 완료! "
        f"(latest={len(latest_df)}행, 소요 시간: {elapsed})"
    )
    print(f"📁 최신 데이터: {LATEST_STATS_PATH}")
    print(f"📁 주간 스냅샷: {weekly_saved_as}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update Overwatch competitive stats and/or hero perks data."
    )
    parser.add_argument(
        "--mode",
        choices=["stats", "perks", "all"],
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

    if args.mode in ("stats", "all"):
        run_stats_update()
    if args.mode in ("perks", "all"):
        run_perk_update(
            locale=args.locale,
            max_heroes=args.max_heroes,
            headed=args.headed,
        )


if __name__ == "__main__":
    main()
