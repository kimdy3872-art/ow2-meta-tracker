#!/usr/bin/env python3
"""Streamlit Community Cloud 앱이 잠들지 않도록 유지하는 keep-alive 스크립트.

Streamlit Community Cloud 무료 앱은 트래픽이 없으면 잠자기 모드로 들어가며,
최근에는 앱 앞단에 쿠키/인증 리다이렉트가 붙어 단순 HTTP 핑(curl, UptimeRobot 등)은
CDN 껍데기만 응답하고 실제 앱 컨테이너까지 도달하지 못한다.

따라서 실제 브라우저 세션(websocket)을 여는 것이 슬립 타이머를 리셋하는 유일하게
신뢰할 수 있는 방법이다. 이 프로젝트는 이미 Selenium + Chrome을 쓰므로 같은 스택으로
헤드리스 방문을 수행한다. 이미 잠들어 있으면 wake 버튼을 눌러 깨운다.

사용:
    python scripts/keep_alive.py                       # 기본 URL 방문
    APP_URL=https://... python scripts/keep_alive.py   # 환경변수로 URL 지정
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

APP_URL = os.environ.get("APP_URL", "https://ow2metatracker.streamlit.app").rstrip("/")

# 앱 컨테이너가 렌더될 때까지 최대 대기(초). 콜드 부팅은 오래 걸릴 수 있다.
BOOT_TIMEOUT = int(os.environ.get("KEEP_ALIVE_BOOT_TIMEOUT", "180"))
# 앱이 뜬 뒤 세션을 유지하는 시간(초). 잠깐이라도 실사용자 세션으로 잡히게 한다.
LINGER_SECONDS = int(os.environ.get("KEEP_ALIVE_LINGER", "20"))
PAGE_LOAD_TIMEOUT = int(os.environ.get("KEEP_ALIVE_PAGE_LOAD_TIMEOUT", "90"))

# Streamlit 슬립 화면의 "다시 깨우기" 버튼 텍스트(로케일/문구 변화에 대비해 여러 후보).
WAKE_BUTTON_XPATHS = [
    "//button[contains(., 'get this app back up')]",
    "//button[contains(., 'Yes, get this app back up')]",
    "//button[contains(., 'back up')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
    "'abcdefghijklmnopqrstuvwxyz'), 'wake')]",
]

# 실제 앱이 렌더됐음을 나타내는 컨테이너 후보.
APP_READY_SELECTORS = [
    '[data-testid="stAppViewContainer"]',
    '[data-testid="stApp"]',
    'section.main',
]


def build_options():
    opts = Options()
    opts.page_load_strategy = "eager"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--window-size=1280,900")
    return opts


def find_wake_button(driver):
    # 슬립/wake 버튼은 share.streamlit.io 껍데기(최상위 문서)에 있다.
    driver.switch_to.default_content()
    for xpath in WAKE_BUTTON_XPATHS:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
        except WebDriverException:
            buttons = []
        for btn in buttons:
            if btn.is_displayed() and btn.is_enabled():
                return btn
    return None


def _has_app_container(driver):
    for selector in APP_READY_SELECTORS:
        try:
            if driver.find_elements(By.CSS_SELECTOR, selector):
                return True
        except WebDriverException:
            pass
    return False


def app_is_ready(driver):
    """실제 Streamlit 앱은 share.streamlit.io 껍데기의 iframe 안에서 렌더된다.

    최상위 문서와 각 iframe 내부를 모두 확인한다.
    """
    driver.switch_to.default_content()
    if _has_app_container(driver):
        return True

    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
    except WebDriverException:
        frames = []
    for frame in frames:
        try:
            if not frame.is_displayed():
                continue
            driver.switch_to.frame(frame)
            found = _has_app_container(driver)
        except WebDriverException:
            found = False
        finally:
            driver.switch_to.default_content()
        if found:
            return True
    return False


def main():
    print(f"[keep-alive] 방문 대상: {APP_URL}")
    driver = None
    try:
        driver = webdriver.Chrome(options=build_options())
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        try:
            driver.get(APP_URL)
        except TimeoutException:
            # eager 전략에서도 타임아웃이 날 수 있으나 세션은 이미 시작됨.
            print("[keep-alive] 초기 페이지 로드 타임아웃(계속 진행)")

        # 슬립 화면이면 wake 버튼을 눌러 깨운다.
        deadline = time.time() + BOOT_TIMEOUT
        clicked_wake = False
        while time.time() < deadline:
            if app_is_ready(driver):
                break
            btn = find_wake_button(driver)
            if btn is not None and not clicked_wake:
                print("[keep-alive] 앱이 잠들어 있음 → wake 버튼 클릭")
                try:
                    btn.click()
                    clicked_wake = True
                except WebDriverException as exc:
                    print(f"[keep-alive] wake 버튼 클릭 실패: {exc}")
            time.sleep(3)

        if not app_is_ready(driver):
            print("[keep-alive] 경고: 앱 컨테이너 렌더를 확인하지 못함")
            print(f"[keep-alive] 현재 URL: {driver.current_url}")
            print(f"[keep-alive] 제목: {driver.title!r}")
            return 1

        state = "깨워서 기동" if clicked_wake else "이미 깨어있음"
        print(f"[keep-alive] 앱 렌더 확인 ({state}). {LINGER_SECONDS}초간 세션 유지")
        time.sleep(LINGER_SECONDS)
        print("[keep-alive] 완료")
        return 0
    except WebDriverException as exc:
        print(f"[keep-alive] 드라이버 오류: {exc}")
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
