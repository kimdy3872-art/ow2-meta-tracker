"""UI 실측 검증. 헤드리스 Chrome(DevTools 프로토콜)으로 기기별 레이아웃과 터치 동작을 잰다.

    OW2_LOCAL_DATA=1 .venv/bin/python -m streamlit run main.py --server.port 8599 --server.headless true
    .venv/bin/python scripts/ui_check.py                      # 전부
    .venv/bin/python scripts/ui_check.py layout --page main   # 일부

검사:
    layout    페이지별 PC 1440×900 / 폰 390×844 블록 위치·가로 넘침·작은 탭 영역·작은 글자
    sidebar   아이패드 820×1180 · 1180×820, PC 에서 사이드바 펼침/접힘
    interact  폰 필터·정렬, 전장별 영웅 탭, 차트 위 스와이프, 3D 회전·시점 초기화, 특전 탭, TOP 4 순환, 표 전체화면

수치는 표준 출력, 스크린샷은 logs/ui_check/ (gitignore 됨). 가로 넘침이 있거나 검사가
예외로 끝나면 종료 코드 1. websocket-client 가 필요하다(selenium 이 끌고 온다).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websocket

CHROME = os.environ.get("CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PORT = 9333
OUT = Path(__file__).resolve().parent.parent / "logs" / "ui_check"
BASE = "http://localhost:8599"

PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = ("Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
           "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
# (폭, 높이, 터치 기기 UA). UA 가 None 이면 마우스 기기.
DEVICES = {
    "phone": (390, 844, PHONE_UA),
    "ipad_portrait": (820, 1180, IPAD_UA),
    "ipad_landscape": (1180, 820, IPAD_UA),
    "pc": (1440, 900, None),
}
CHART = "[data-testid=stPlotlyChart]"
# (경로, 다 그려졌다고 볼 셀렉터)
PAGES = {
    "main": ("/", ".table-wrap"),
    "maps": ("/map_heroes", ".mh-card"),
    "dist": ("/pick_win_distribution", CHART),
    "trends": ("/hero_trends", ".kpi-row"),
    "detail": ("/?hero=%EC%95%84%EB%82%98&tier=Gold", ".hmap-card"),
}
SCROLL_TOP = "document.querySelector('[data-testid=stMain]').scrollTop"


# --- Chrome DevTools 프로토콜 ------------------------------------------------

def _chrome_up():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
        return True
    except Exception:
        return False


def launch():
    """헤드리스 Chrome 을 띄운다. 이미 떠 있으면 None."""
    if _chrome_up():
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={OUT / 'chrome-prof'}", "--no-first-run",
         "--no-default-browser-check", "--hide-scrollbars", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        if _chrome_up():
            return proc
        time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("chrome did not start")


class Tab:
    def __init__(self, device, path=None, wait_selector=None, settle=4.0):
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?about:blank", method="PUT")
        info = json.load(urllib.request.urlopen(req))
        self.id = info["id"]
        # suppress_origin 이 없으면 Chrome 이 403 으로 거절한다.
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60,
                                              suppress_origin=True)
        self.n = 0
        width, height, ua = DEVICES[device]
        touch = ua is not None
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=height,
                  deviceScaleFactor=2 if touch else 1, mobile=touch)
        self.send("Emulation.setTouchEmulationEnabled", enabled=touch, maxTouchPoints=5 if touch else 1)
        if touch:
            self.send("Emulation.setUserAgentOverride", userAgent=ua)
        # Streamlit 이 사이드바 펼침 상태를 localStorage 에 남긴다. 지우지 않으면 앞 탭에서 펼쳐 둔
        # 사이드바가 폰 탭에서도 펼쳐진 채 떠서 본문 터치를 전부 가로챈다.
        self.send("Storage.clearDataForOrigin", origin=BASE, storageTypes="local_storage")
        if path is not None:
            self.goto(path, wait_selector, settle)

    def send(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    def goto(self, path, wait_selector, settle=4.0, timeout=40):
        self.send("Page.enable")
        self.send("Page.navigate", url=BASE + path)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.js(f"!!document.querySelector({json.dumps(wait_selector)})"):
                    break
            except Exception:
                pass
            time.sleep(0.3)
        else:
            raise RuntimeError(f"timeout waiting {wait_selector}")
        time.sleep(settle)  # 뒤따르는 레일·표·애니메이션이 자리 잡을 때까지

    def shot(self, name):
        data = self.send("Page.captureScreenshot", format="png")["data"]
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_bytes(base64.b64decode(data))

    def center_of(self, sel, index=0):
        """요소를 화면 가운데로 옮기고 그 중심 좌표를 돌려준다."""
        return self.js(f"""(() => {{ const e = document.querySelectorAll({json.dumps(sel)})[{index}];
            e.scrollIntoView({{block: 'center'}}); const r = e.getBoundingClientRect();
            return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)]; }})()""")

    def tap(self, sel, index=0):
        """손가락 탭. BaseWeb 셀렉트는 JS 의 .click() 으로는 열리지 않는다."""
        x, y = self.center_of(sel, index)
        time.sleep(0.4)
        self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
        self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])

    def drag(self, x, y, dx, dy, steps=12):
        """한 손가락으로 (x, y) 에서 (dx, dy) 만큼 끈다."""
        self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
        for i in range(1, steps + 1):
            self.send("Input.dispatchTouchEvent", type="touchMove",
                      touchPoints=[{"x": x + dx * i / steps, "y": y + dy * i / steps}])
            time.sleep(0.02)
        self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
        time.sleep(0.5)

    def swipe_scroll(self, x, y, dist=300):
        """손가락으로 밀어 스크롤하는 제스처. 움직인 scrollTop 크기를 돌려준다.

        아래로 갈 자리가 없으면(페이지 끝) 반대 방향으로 민다. 끝에서 아래로 밀면
        스크롤이 막힌 게 아닌데도 0 이 나온다.
        """
        room = self.js("(() => { const s = document.querySelector('[data-testid=stMain]');"
                       " return s.scrollHeight - s.clientHeight - s.scrollTop; })()")
        before = self.js(SCROLL_TOP)
        self.send("Input.synthesizeScrollGesture", x=x, y=y, yDistance=-dist if room >= dist else dist,
                  gestureSourceType="touch", speed=800)
        time.sleep(0.8)
        return abs(round(self.js(SCROLL_TOP) - before))

    def close(self):
        self.ws.close()
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/close/{self.id}")


# --- layout: 페이지별 PC/폰 실측 ---------------------------------------------

MEASURE = r"""
(() => {
  const sc = document.querySelector('[data-testid=stMain]');
  const top0 = sc.getBoundingClientRect().top - sc.scrollTop;
  const box = e => { const r = e.getBoundingClientRect(); return {y: Math.round(r.top - top0), h: Math.round(r.height), x: Math.round(r.left), w: Math.round(r.width)}; };
  const vh = innerHeight, vw = innerWidth;
  const parts = {
    head: '.ow-page-head', search: '.st-key-search_hero', hero: '.hero-showcase-card',
    carousel: '.rot-wrap', maps: '.map-grid', tableTitle: '.ow-section', table: '.table-wrap',
    metaScore: '.meta-score-card', rankRail: '.ow-rail', firstExpander: '[data-testid=stExpander]',
    trendContext: '.trend-context', portrait: '.portrait-card', kpi: '.kpi-row', tabs: '.stTabs',
    perks: '.perk-card', mapCards: '.hmap-card', pills: '[data-testid=stPills]', mapHeroes: '.mh-grid',
  };
  const out = {vw, vh, scrollHeight: sc.scrollHeight, blocks: {}};
  for (const [k, s] of Object.entries(parts)) { const e = document.querySelector(s); if (e) out.blocks[k] = box(e); }
  out.railCards = [...document.querySelectorAll('.rail-card, .ow-rail')].map(e => box(e).y);
  out.charts = [...document.querySelectorAll('[data-testid=stPlotlyChart]')].map(box);
  out.aboveFold = Object.entries(out.blocks).filter(([k, b]) => b.y < vh && b.h > 0).map(([k, b]) => `${k}(${Math.max(0, Math.min(vh, b.y + b.h) - b.y)}/${b.h}px)`);
  const rows = [...document.querySelectorAll('.overwatch-table tbody tr')];
  if (rows.length) {
    const hs = rows.map(r => { const hr = r.getBoundingClientRect().height; return hr || r.querySelector('td').getBoundingClientRect().height; });
    out.table = {rows: rows.length, avgRowH: Math.round(hs.reduce((a, b) => a + b, 0) / hs.length),
                 headerVisible: (() => { const th = document.querySelector('.overwatch-table th'); return !!th && th.getBoundingClientRect().height > 0; })()};
  }
  const sb = document.querySelector('[data-testid=stSidebar]');
  if (sb) { const r = sb.getBoundingClientRect(); out.sidebar = {x: Math.round(r.left), w: Math.round(r.width), expanded: sb.getAttribute('aria-expanded'), visible: r.right > 0 && r.left < vw}; }
  const small = [];
  for (const a of document.querySelectorAll('a[href], [tabindex="0"]')) {
    const r = a.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.height < 44 || r.width < 44) small.push(`${(a.className || a.tagName).toString().split(' ')[0]}:${Math.round(r.width)}x${Math.round(r.height)}`);
  }
  const counts = {}; small.forEach(s => { const k = s.split(':')[0]; counts[k] = (counts[k] || 0) + 1; });
  out.smallTapTargets = {total: small.length, byClass: counts, examples: [...new Set(small)].slice(0, 8)};
  let tiny = 0; const tinyEx = new Set();
  const walker = document.createTreeWalker(document.querySelector('[data-testid=stMain]'), NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement; const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 12 && el.getBoundingClientRect().width > 0) { tiny++; if (tinyEx.size < 6) tinyEx.add(`${el.className.toString().split(' ')[0] || el.tagName}:${fs}px`); }
  }
  out.tinyText = {count: tiny, examples: [...tinyEx]};
  const L = document.querySelector('.hero-showcase-left'), A = document.querySelector('.hero-showcase-art');
  if (L && A) {
    const a = L.getBoundingClientRect(), b = A.getBoundingClientRect();
    const ix = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    const iy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    out.heroTextArtOverlap = Math.round(100 * ix * iy / (a.width * a.height)) + '% of text column';
    out.heroArtWidth = Math.round(b.width);
  }
  const ta = [...document.querySelectorAll('[data-testid=stPlotlyChart] *')].filter(e => getComputedStyle(e).touchAction === 'none');
  out.touchActionNone = ta.length ? Math.round(Math.max(...ta.map(e => e.getBoundingClientRect().width * e.getBoundingClientRect().height)) / (vw * vh) * 100) + '% of viewport (largest)' : 'none';
  const res = performance.getEntriesByType('resource');
  const sum = f => Math.round(res.filter(f).reduce((a, r) => a + (r.transferSize || r.encodedBodySize || 0), 0) / 1024);
  out.transferKB = {total: sum(() => true), img: sum(r => r.initiatorType === 'img' || /\.(png|jpe?g|webp|gif|svg)(\?|$)/.test(r.name) || r.initiatorType === 'css' && /\.(png|jpe?g|webp)/.test(r.name)),
                    remoteImgs: res.filter(r => /overfast|wiki|fandom|blizzard/.test(r.name)).length};
  out.hOverflow = sc.scrollWidth > sc.clientWidth + 1;
  return out;
})()
"""


def layout(pages):
    """가로 넘침이 난 (페이지, 기기) 목록을 돌려준다."""
    overflow = []
    for page in pages:
        path, sel = PAGES[page]
        results = {}
        for dev in ("pc", "phone"):
            tab = Tab(dev, path, sel, settle=9)
            results[dev] = tab.js(MEASURE)
            tab.shot(f"{page}_{dev}_0.png")
            if dev == "phone":  # 폰은 스크롤 위치 몇 곳을 더 찍는다
                for i in (1, 2):
                    tab.js(f"{SCROLL_TOP} = {DEVICES[dev][1] * i}")
                    time.sleep(0.8)
                    tab.shot(f"{page}_{dev}_{i}.png")
            tab.close()
            if results[dev]["hOverflow"]:
                overflow.append(f"layout {page}/{dev}: 가로 넘침")
        print(f"[layout] {page}", json.dumps(results, ensure_ascii=False, indent=1))
    return overflow


# --- sidebar: 사이드바 펼침/접힘 ----------------------------------------------

SIDEBAR_STATE = r"""
(() => {
  const sb = document.querySelector('[data-testid=stSidebar]');
  const cs = getComputedStyle(sb);
  const main = document.querySelector('[data-testid=stMain]').getBoundingClientRect();
  const block = document.querySelector('[data-testid=stMainBlockContainer]').getBoundingClientRect();
  const cols = [...document.querySelectorAll('[data-testid=stMainBlockContainer] [data-testid=stHorizontalBlock]')]
      .map(h => [...h.children].map(c => Math.round(c.getBoundingClientRect().width)))
      .filter(a => a.length > 1).slice(0, 2);
  const r = sb.getBoundingClientRect();
  return {
    expanded: sb.getAttribute('aria-expanded'),
    sidebarRect: [Math.round(r.left), Math.round(r.width)],
    sidebarCss: {width: cs.width, minWidth: cs.minWidth, maxWidth: cs.maxWidth, transform: cs.transform,
                 marginLeft: cs.marginLeft, position: cs.position},
    sidebarInline: sb.getAttribute('style'),
    mainLeftWidth: [Math.round(main.left), Math.round(main.width)],
    blockWidth: Math.round(block.width),
    columns: cols,
    railSide: (() => { const c = document.querySelector('.rail-side'); return c ? [getComputedStyle(c.closest('[data-testid=stColumn]')).display, Math.round(c.getBoundingClientRect().width)] : null; })(),
    railStrip: (() => { const r = document.querySelector('.rail-strip'); return r ? getComputedStyle(r).display : null; })(),
    tableMode: (() => { const t = document.querySelector('.overwatch-table thead'); return t && getComputedStyle(t).display !== 'none' ? 'table' : 'list'; })(),
    mbar: (() => { const m = document.querySelector('.st-key-mbar'); return m ? getComputedStyle(m.parentElement).display : null; })(),
    searchW: Math.round(document.querySelector('.st-key-search_hero').getBoundingClientRect().width),
    metaOverflow: (() => { const v = document.querySelector('.meta-score-value'); return v ? v.scrollWidth > v.clientWidth + 1 : null; })(),
  };
})()
"""

TOGGLE = r"""
(() => { const b = document.querySelector('[data-testid=stSidebarCollapseButton] button'); if (!b) return 'no button'; b.click(); return 'clicked'; })()
"""


def sidebar():
    """사이드바를 토글해 두 상태를 다 잰다. 토글되지 않은 기기 목록을 돌려준다."""
    out, failed = {}, []
    for dev in ("ipad_portrait", "ipad_landscape", "pc"):
        tab = Tab(dev, "/", ".table-wrap", settle=8)
        res = {}
        for _ in range(2):
            state = tab.js(SIDEBAR_STATE)
            # 시작 상태는 Streamlit 이 창 폭을 보고 정한다. 잰 값으로 이름을 붙인다.
            name = "expanded" if state["expanded"] == "true" else "collapsed"
            res[name] = state
            tab.shot(f"{dev}_{name}.png")
            tab.js(TOGGLE)
            time.sleep(1.5)
        tab.close()
        if len(res) < 2:
            failed.append(f"sidebar {dev}: 토글되지 않음")
        out[dev] = res
    print("[sidebar]", json.dumps(out, ensure_ascii=False, indent=1))
    return failed


# --- interact: 폰 상호작용 ----------------------------------------------------

def main_filter_and_sort():
    tab = Tab("phone", "/", ".table-wrap", settle=6)
    meta = "document.querySelector('.hero-showcase-meta').textContent"
    print("[main] before:", tab.js(meta))
    # 본문 필터 줄의 티어 셀렉트를 열고 다이아몬드를 고른다
    tab.tap(".st-key-mtiersel [data-baseweb=select] > div")
    time.sleep(0.8)
    picked = tab.js("""(() => { const o = [...document.querySelectorAll('li[role=option]')].find(li => li.textContent.includes('다이아몬드'));
        if (!o) return 'no option'; o.click(); return 'clicked'; })()""")
    time.sleep(5)
    print("[main] pick diamond:", picked, "->", tab.js(meta),
          "| sidebar tier widget:", tab.js("document.querySelector('.st-key-tiersel').textContent.slice(0, 12)"))
    # 정렬 칩(승률)을 누르면 전체 리로드. 티어가 유지되는지
    href = tab.js("[...document.querySelectorAll('.sort-chip a')].find(a => a.textContent.includes('승률')).getAttribute('href')")
    print("[main] sort chip href:", href)
    tab.goto("/" + href, ".table-wrap", settle=6)
    print("[main] after sort reload:", tab.js("document.querySelector('.hero-showcase-eyebrow').textContent"), "|", tab.js(meta))
    tab.close()


# 3D 차트의 실제 GL 카메라. _fullLayout.scene.camera 는 드래그 중에 갱신되지 않아 늘 처음 값이다.
CAMERA_3D = """(() => { const c = document.querySelectorAll('.js-plotly-plot')[1]._fullLayout.scene._scene.getCamera();
    const r = v => [v.x, v.y, v.z].map(n => +n.toFixed(2));
    return {eye: r(c.eye), center: r(c.center)}; })()"""


def dist_page():
    tab = Tab("phone", *PAGES["dist"], settle=6)
    order = tab.js("""(() => [...document.querySelectorAll('.ow-section-title, [data-testid=stPlotlyChart]')]
        .filter(e => e.getBoundingClientRect().height > 0)
        .map(e => (e.classList.contains('ow-section-title') ? 'T:' + e.textContent : 'chart')
             + '@' + Math.round(e.getBoundingClientRect().top)))()""")
    print("[dist] order:", order)
    # 글자 위와 2D 차트 위의 스와이프는 페이지를 내린다
    for name, sel in (("text", ".ow-page-head"), ("2D chart", CHART)):
        x, y = tab.center_of(sel)
        if name == "text" and y < 400:
            y += 100
        time.sleep(0.5)
        print(f"[dist] swipe on {name} -> {tab.swipe_scroll(x, y)}px scrolled")
    print("[dist] legend orientation (2D):", tab.js("(() => { const g = document.querySelector('.legend'); if (!g) return null; const r = g.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })()"))

    # 3D 차트 위의 스와이프는 큐브를 돌린다. 어떻게 밀어도 중심과 거리가 그대로여야 틀 안에 남는다.
    x, y = tab.center_of(CHART, 1)
    time.sleep(0.5)
    start = tab.js(CAMERA_3D)
    for dx, dy in ((0, -250), (230, 0), (0, 400), (0, 400), (-200, 300)):
        tab.drag(x, y, dx, dy)
    moved = tab.js(CAMERA_3D)
    print("[dist] 3D camera:", start, "->", moved)

    def distance(cam):
        return round(sum((e - c) ** 2 for e, c in zip(cam["eye"], cam["center"])) ** 0.5, 1)

    assert moved["eye"] != start["eye"], "3D 차트가 터치 드래그로 회전하지 않는다"
    assert moved["center"] == start["center"] and distance(moved) == distance(start), "3D 차트가 틀 밖으로 밀려났다"
    tab.shot("interact_dist_3d_rotated.png")
    tab.tap(".st-key-pick_win_scatter_3d .modebar-btn")
    time.sleep(1)
    reset = tab.js(CAMERA_3D)
    print("[dist] 3D camera after reset:", reset)
    assert reset == start, "시점 초기화 버튼이 처음 시점으로 되돌리지 않는다"
    tab.shot("interact_dist_3d_reset.png")
    tab.close()


def maps_page():
    """전장별 영웅: 카드 칸 수, 탭 영역, 영웅을 누르면 같은 티어의 영웅 상세로 가는지."""
    tab = Tab("phone", *PAGES["maps"], settle=5)
    info = tab.js("""(() => { const cards = [...document.querySelectorAll('.mh-card')], picks = [...document.querySelectorAll('.mh-pick')];
        const p = picks[0], r = p.getBoundingClientRect();
        return {cards: cards.length, picks: picks.length,
                columns: new Set(cards.slice(0, 7).map(c => Math.round(c.getBoundingClientRect().left))).size,
                pickSize: [Math.round(r.width), Math.round(r.height)], hero: p.querySelector('.mh-hero').textContent,
                clipped: picks.filter(a => { const h = a.querySelector('.mh-hero'); return h.scrollWidth > h.clientWidth + 1; }).length}; })()""")
    print("[maps]", json.dumps(info, ensure_ascii=False))
    assert info["pickSize"][1] >= 44, "영웅 탭 영역이 44px 보다 낮다"
    tab.tap(".mh-pick")
    for _ in range(24):
        time.sleep(0.5)
        if tab.js("!!document.querySelector('.hmap-card')"):
            break
    landed = tab.js("(document.querySelector('.hero-showcase-card') || document.body).innerText.split('\\n').slice(0, 4).join(' / ')")
    print("[maps] tap", info["hero"], "->", tab.js("location.pathname"), "|", landed)
    assert info["hero"] in landed, "누른 영웅의 상세로 가지 않았다"
    tab.close()


def trends_page():
    tab = Tab("phone", *PAGES["trends"], settle=5)
    print("[trends]", json.dumps(tab.js("""(() => ({
        filters: [...document.querySelectorAll('.st-key-trend-filters [data-testid=stSelectbox]')].map(s => { const r = s.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width)]; }),
        portrait: getComputedStyle(document.querySelector('.portrait-card').closest('[data-testid=stColumn]')).display,
        kpiCards: [...document.querySelectorAll('.kpi-card')].map(k => { const r = k.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }),
        chartTop: (() => { const sc = document.querySelector('[data-testid=stMain]'); const c = document.querySelector('[data-testid=stPlotlyChart]'); return Math.round(c.getBoundingClientRect().top + sc.scrollTop); })(),
        modebar: (() => { const m = document.querySelector('.modebar-container'); return m ? getComputedStyle(m).display : 'none'; })(),
        scrollHeight: document.querySelector('[data-testid=stMain]').scrollHeight,
    }))()"""), ensure_ascii=False))
    tab.shot("interact_trends_phone.png")
    tab.close()


def detail_page():
    tab = Tab("phone", *PAGES["detail"], settle=5)
    print("[detail]", json.dumps(tab.js("""(() => [...document.querySelectorAll('.hmap-card')].slice(0, 2).map(c => {
        const b = c.querySelector('.hmap-badge').getBoundingClientRect(); const r = c.querySelector('.hmap-right').getBoundingClientRect();
        return {badgeRight: Math.round(b.right), rateLeft: Math.round(r.left), overlap: b.right > r.left}; }))()"""), ensure_ascii=False))
    tab.js("document.querySelector('.hmap-card').scrollIntoView({block: 'center'})")
    time.sleep(0.6)
    tab.shot("interact_detail_phone.png")
    # 특전 카드를 탭하면 툴팁이 보이는가
    tab.tap(".perk-card")
    time.sleep(0.5)
    print("[detail] perk tooltip after tap: opacity =",
          tab.js("getComputedStyle(document.querySelector('.perk-tooltip')).opacity"),
          "| active element =", tab.js("document.activeElement.className"))
    tab.close()


def rot_cycle():
    """TOP 4 가 hover 없는 환경에서 어떻게 넘어가는지(탭 색이 6.5초 뒤 달라지는지)."""
    tab = Tab("phone", "/", ".rot-wrap", settle=2)
    state = "[...document.querySelectorAll('.rot-tab')].map(t => getComputedStyle(t).color)"
    print("[rot] tabs t0:", tab.js(state))
    time.sleep(6.5)
    print("[rot] tabs t+6.5s:", tab.js(state))
    print("[rot] hover media:", tab.js("[matchMedia('(hover: hover)').matches, matchMedia('(pointer: coarse)').matches]"))
    tab.close()


def dataframe_fullscreen():
    """컨테이너 쿼리(레이아웃 격리)가 st.dataframe 전체화면을 본문 상자에 가두지 않는지."""
    tab = Tab("pc", *PAGES["trends"], settle=5)
    tab.js("[...document.querySelectorAll('[data-testid=stExpander] summary')].find(s => s.textContent.includes('스냅샷')).click()")
    time.sleep(2)
    tab.js("""(() => { const df = document.querySelector('[data-testid=stDataFrame]'); df.scrollIntoView({block: 'center'});
        df.dispatchEvent(new MouseEvent('mouseover', {bubbles: true})); })()""")
    time.sleep(0.8)
    clicked = tab.js("""(() => { const b = document.querySelector('[data-testid=stElementToolbar] button[aria-label*="ullscreen"], [data-testid=stElementToolbarButton] button[aria-label*="ullscreen"], button[title*="ullscreen"]');
        if (!b) return [...document.querySelectorAll('[data-testid=stElementToolbar] button')].map(x => x.getAttribute('aria-label') || x.title);
        b.click(); return 'clicked'; })()""")
    time.sleep(1.5)
    print("[dataframe] fullscreen button:", clicked)
    print("[dataframe] rect after:", tab.js("""(() => { const d = document.querySelector('[data-testid=stDataFrame]'); const r = d.getBoundingClientRect();
        return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height), innerWidth, innerHeight]; })()"""))
    tab.shot("interact_df_fullscreen.png")
    tab.close()


def interact():
    """예외로 끝난 검사 목록을 돌려준다. 한 항목이 실패해도 나머지는 본다."""
    failed = []
    for fn in (main_filter_and_sort, maps_page, dist_page, trends_page, detail_page, rot_cycle, dataframe_fullscreen):
        try:
            fn()
        except Exception as e:
            print(f"[{fn.__name__}] ERROR {e}")
            failed.append(f"interact {fn.__name__}: {e}")
    return failed


def main():
    global BASE
    checks = ("layout", "sidebar", "interact")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("checks", nargs="*", help=f"{' | '.join(checks)} (생략하면 전부)")
    ap.add_argument("--page", action="append", choices=list(PAGES), help="layout 에서 볼 페이지(여러 번 가능)")
    ap.add_argument("--base", default=BASE, help=f"앱 주소 (기본 {BASE})")
    args = ap.parse_args()
    if set(args.checks) - set(checks):  # nargs="*" 에 choices 를 걸면 3.9 에서 빈 목록이 거절된다
        ap.error(f"검사는 {', '.join(checks)} 중에서 고른다")
    BASE = args.base.rstrip("/")
    try:
        urllib.request.urlopen(BASE + "/_stcore/health", timeout=3)
    except Exception:
        sys.exit(f"{BASE} 에 앱이 없다. 먼저 띄운다:\n"
                 "  OW2_LOCAL_DATA=1 .venv/bin/python -m streamlit run main.py --server.port 8599 --server.headless true")

    chrome = launch()
    failed = []
    try:
        for check in args.checks or checks:
            if check == "layout":
                failed += layout(args.page or list(PAGES))
            elif check == "sidebar":
                failed += sidebar()
            else:
                failed += interact()
    finally:
        if chrome:
            chrome.terminate()
    print(f"screenshots: {OUT}")
    if failed:
        sys.exit("FAILED\n  " + "\n  ".join(failed))


if __name__ == "__main__":
    main()
