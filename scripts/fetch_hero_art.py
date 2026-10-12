"""배너 아트 매니페스트와 영웅색 만들기 (빌드 타임 전용).

Streamlit 런타임에서는 실행되지 않는다. 새 영웅이 나오면 로컬에서 돌리고 결과 JSON 만 커밋한다.

    pip install -r scripts/requirements-art.txt
    python scripts/fetch_hero_art.py doctrine   # 그 영웅만 (OverFast key)
    python scripts/fetch_hero_art.py            # 전체

출력:
    data/hero_art_manifest.json   key -> {name, role, portrait, splash{960,1600,2600}, focal_x}
    assets/hero_colors.json       key -> 대표색. 색이 없는 영웅만 추가한다.

배너는 블리자드 공식 영웅 페이지의 배경 스플래시를 블리자드 CDN 에서 바로 불러온다
(주소는 OverFast /heroes/{key} 의 backgrounds). 이미지 파일은 저장소에 두지 않는다.

이미 있는 영웅색은 다시 뽑지 않는다. 2026-08-17 에 예전 위키 전신 렌더 컷아웃에서 뽑은
값이라, 스플래시로 다시 뽑으면 전부 바뀐다.
"""

import colorsys
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "hero_art_manifest.json"
COLORS_PATH = ROOT / "assets" / "hero_colors.json"

OVERFAST_BASE = "https://overfast-api.tekrop.fr"
UA = {"User-Agent": "ow2meta-art-fetch/1.0 (https://github.com/kimdy3872-art/ow2-meta-tracker)"}
REQUEST_DELAY = 0.4
SIZES = ("960", "1600", "2600")
# focal·색은 카드 배경으로 쓰는 2600 스플래시 기준으로 뽑는다.
FOCAL_SIZE = "2600"


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 + attempt * 2)


def focal_x(im):
    """스플래시 안에서 캐릭터의 가로 위치를 추정한다(0~1). background-position 이 된다.

    캐릭터는 선명하고 배경은 블러라는 성질을 이용해, 컬럼별 그래디언트 에너지의
    무게중심을 잡는다.
    """
    a = np.asarray(im.convert("L").resize((400, 190)), dtype=np.float32)
    gx = np.abs(np.diff(a, axis=1, prepend=a[:, :1]))
    gy = np.abs(np.diff(a, axis=0, prepend=a[:1, :]))
    col = (gx + gy).sum(axis=0)
    col = np.maximum(col - np.percentile(col, 55), 0)
    if col.sum() == 0:
        return 0.5
    return round(float((col * np.arange(col.size)).sum() / col.sum()) / col.size, 3)


def dominant(im):
    """HERO 카드 글로우에 쓸 대표색. 너무 어둡거나 채도 낮은 픽셀은 뺀다."""
    im = im.convert("RGBA")
    im.thumbnail((220, 220))
    a = np.asarray(im, dtype=np.float32)
    rgb, alpha = a[..., :3] / 255.0, a[..., 3] / 255.0

    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    val = mx
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    keep = (alpha > 0.8) & (val > 0.18) & (val < 0.95) & (sat > 0.22)
    if keep.sum() < 60:
        keep = alpha > 0.8
    if keep.sum() == 0:
        return "#3b1a5c"

    px = rgb[keep]
    # 색상환에서 최빈 구간을 찾는다(평균을 내면 보색끼리 섞여 회색이 된다)
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px])
    hist, edges = np.histogram(hsv[:, 0], bins=18, range=(0, 1), weights=hsv[:, 1])
    b = int(hist.argmax())
    sel = (hsv[:, 0] >= edges[b]) & (hsv[:, 0] < edges[b + 1])
    h = float(np.median(hsv[sel, 0]))
    s = float(np.clip(np.median(hsv[sel, 1]) * 1.15, 0.45, 0.95))
    v = float(np.clip(np.median(hsv[sel, 2]) * 0.75, 0.28, 0.6))
    r, g, bl = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(bl * 255))


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build(keys=None):
    heroes = json.loads(fetch(f"{OVERFAST_BASE}/heroes"))
    if keys:
        heroes = [h for h in heroes if h["key"] in set(keys)]
    manifest, colors = load(MANIFEST_PATH), load(COLORS_PATH)

    for i, hero in enumerate(heroes, 1):
        key = hero["key"]
        tag = f"[{i}/{len(heroes)}] {key}"
        try:
            detail = json.loads(fetch(f"{OVERFAST_BASE}/heroes/{key}"))
            urls = [b.get("url") for b in (detail.get("backgrounds") or []) if b.get("url")]
            splash = {s: next((u for u in urls if f"/{s}_" in u), None) for s in SIZES}
            if not splash[FOCAL_SIZE]:
                print(f"{tag}: {FOCAL_SIZE} 스플래시 없음 - 건너뜀")
                continue
            im = Image.open(io.BytesIO(fetch(splash[FOCAL_SIZE])))
            manifest[key] = {
                "name": hero["name"],
                "role": hero.get("role"),
                "portrait": hero.get("portrait"),
                "splash": splash,
                "focal_x": focal_x(im),
            }
            if key not in colors:
                colors[key] = dominant(im)
                print(f"{tag}: 영웅색 추가 {colors[key]}")
            print(f"{tag}: focal_x {manifest[key]['focal_x']}")
        except Exception as exc:
            print(f"{tag}: 실패 - {exc}")
        time.sleep(REQUEST_DELAY)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    COLORS_PATH.write_text(json.dumps(colors, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n완료: 매니페스트 {len(manifest)}명, 영웅색 {len(colors)}명")


if __name__ == "__main__":
    build(sys.argv[1:] or None)
