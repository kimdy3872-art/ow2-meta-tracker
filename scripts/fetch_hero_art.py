"""히어로 배너 아트 수집 (빌드 타임 전용).

Streamlit 런타임에서는 절대 실행되지 않는다. 로컬에서 수동으로 돌려 결과물
(WebP + 매니페스트)만 커밋한다.

    pip install -r scripts/requirements-art.txt
    python scripts/fetch_hero_art.py            # 전체
    python scripts/fetch_hero_art.py dva ana    # 일부만 다시

출력:
    static/hero_art/{key}.webp        투명 배경 전신 렌더
    data/hero_art_manifest.json       배너 렌더링에 필요한 메타데이터

아트 소스는 Overwatch Wiki(Fandom)의 인포박스 전신 렌더다. 예전에는 OverFast 의
스플래시 배너(1600 JPG)를 rembg/birefnet 으로 누끼 따서 썼는데 세 가지가 문제였다.
스플래시는 시네마틱 씬이라 인물이 상반신에서 잘리고(원본 높이 760px), 시네마틱
조명이라 어두우며(D.Va 64 / 아나 77 / 모이라 82), 알파가 없어 973MB ONNX 모델과
영웅당 11초의 추론이 필요했다. 위키 렌더는 원본부터 투명 PNG 에 균일한 스튜디오
조명이고 전신이 다 들어있어 셋 다 사라진다.

스플래시 URL 자체는 매니페스트에 계속 남긴다. 배너 배경 블러 레이어가 쓴다.
"""

import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
# 결과물은 저장소에 커밋하고, 앱은 GitHub raw 로 읽는다(데이터 로딩과 같은 경로).
ART_DIR = ROOT / "static" / "hero_art"
# 저장소 상대 경로만 기록한다. 실제 URL 은 app_data 가 GitHub raw 기준으로 만든다
# (Streamlit Cloud 는 /app/static/... 절대 경로를 앱 셸이 가로채 이미지를 못 준다).
ART_REPO_PATH = "static/hero_art"
MANIFEST_PATH = ROOT / "data" / "hero_art_manifest.json"

OVERFAST_BASE = "https://overfast-api.tekrop.fr"
WIKI_API = "https://overwatch.fandom.com/api.php"
# focal 추정은 카드 배경(2600 스플래시) 기준이어야 한다.
FOCAL_SIZE = "2600"

# Fandom 은 기본 User-Agent 를 차단한다. 식별 가능한 UA 를 붙인다.
UA = {"User-Agent": "ow2meta-art-fetch/1.0 (https://github.com/kimdy3872-art/ow2-meta-tracker)"}
# 위키에 부담을 주지 않도록 요청 사이 간격.
REQUEST_DELAY = 0.4

# 위키 문서 제목은 대체로 OverFast 의 name 과 같다. 다른 것만 여기 적는다.
# 새 영웅이 "위키 이미지 없음"으로 실패하면 한 줄 추가해서 고친다.
WIKI_TITLE_OVERRIDES = {}

# 알파 마스크 안쪽 평균 휘도를 이 값으로 맞춘다.
TARGET_LUMA = 120.0
# 감마를 풀어주면 원래 어두운 영웅(리퍼·라마트라)이 회색으로 뜬다.
GAMMA_RANGE = (0.72, 1.30)
SATURATION = 1.06
MAX_HEIGHT = 1400
# 알파>128 픽셀이 이 비율을 넘으면 투명 배경이 아니다(배경 있는 이미지를 PNG 로 감싼 것).
OPAQUE_REJECT_RATIO = 0.97


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 + attempt * 2)


def fetch_image(url, retries=3):
    """RGBA 로 연다. 위키 렌더는 원본부터 알파를 갖고 있다."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return Image.open(io.BytesIO(r.read())).convert("RGBA")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 + attempt * 2)


def wiki_render_url(name):
    """Fandom PageImages 로 인포박스 대표 이미지(= 전신 렌더) URL 을 얻는다."""
    title = WIKI_TITLE_OVERRIDES.get(name, name)
    query = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "original",
        "format": "json",
        "formatversion": "2",
    })
    payload = fetch_json(f"{WIKI_API}?{query}")
    pages = (payload.get("query") or {}).get("pages") or []
    if not pages:
        return None
    return ((pages[0].get("original") or {}).get("source")) or None


def focal_x(im):
    """스플래시 안에서 캐릭터의 가로 위치를 추정한다(0~1).

    전신 렌더 자체에는 필요 없다(정면 정중앙이라 항상 0.5). 하지만 카드 그리드와
    가로 스크롤러는 여전히 스플래시를 cover 로 크롭해서 쓰고, 그때 이 값이
    background-position 이 된다. 0.5 로 고정하면 인물이 프레임 밖으로 밀린다.

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


def mask_luma(rgba):
    """알파 마스크 안쪽 평균 휘도(0~255). 투명 영역은 세지 않는다."""
    arr = np.asarray(rgba, dtype=np.float32)
    mask = arr[:, :, 3] > 127
    if not mask.any():
        return 0.0
    rgb = arr[:, :, :3][mask]
    return float((rgb * (0.2126, 0.7152, 0.0722)).sum(axis=1).mean())


def normalize_luma(rgba):
    """알파 마스크 기준으로 밝기를 균일화한다.

    전체 이미지에 brightness 를 곱하면 투명 영역의 잔여 색까지 밝아져 테두리에
    유령 픽셀이 생긴다. 그래서 알파는 건드리지 않고 RGB 에만 감마를 건다.
    감마를 쓰는 이유는 곱셈과 달리 하이라이트를 날리지 않아서다.
    """
    before = mask_luma(rgba)
    if before <= 0:
        return rgba, before, before, 1.0

    gamma = math.log(TARGET_LUMA / 255.0) / math.log(before / 255.0)
    gamma = max(GAMMA_RANGE[0], min(GAMMA_RANGE[1], gamma))

    arr = np.asarray(rgba, dtype=np.float32)
    rgb = np.clip((arr[:, :, :3] / 255.0) ** gamma * 255.0, 0, 255)
    out = Image.fromarray(np.dstack([rgb, arr[:, :, 3]]).astype(np.uint8))
    out = ImageEnhance.Color(out).enhance(SATURATION)
    return out, before, mask_luma(out), gamma


def build(keys=None):
    ART_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    heroes = fetch_json(f"{OVERFAST_BASE}/heroes")
    if keys:
        heroes = [h for h in heroes if h["key"] in set(keys)]

    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for i, hero in enumerate(heroes, 1):
        key, name = hero["key"], hero["name"]
        tag = f"[{i}/{len(heroes)}] {key}"
        try:
            art_url = wiki_render_url(name)
            if not art_url:
                print(f"{tag}: 위키 이미지 없음 - 건너뜀 "
                      f"(WIKI_TITLE_OVERRIDES 에 {name!r} 추가 검토)")
                continue

            rgba = fetch_image(art_url)
            bbox = rgba.getchannel("A").getbbox()
            if bbox is None:
                print(f"{tag}: 전부 투명 - 건너뜀")
                continue
            cut = rgba.crop(bbox)

            solid = float((np.asarray(cut.getchannel("A")) > 128).mean())
            if solid > OPAQUE_REJECT_RATIO:
                print(f"{tag}: 투명 배경 아님(solid={solid:.3f}) - 건너뜀")
                continue

            cut, luma_before, luma_after, gamma = normalize_luma(cut)

            if cut.height > MAX_HEIGHT:
                width = round(cut.width * MAX_HEIGHT / cut.height)
                cut = cut.resize((width, MAX_HEIGHT), Image.LANCZOS)

            out_path = ART_DIR / f"{key}.webp"
            cut.save(out_path, "WEBP", quality=88, method=6)

            detail = fetch_json(f"{OVERFAST_BASE}/heroes/{key}")
            backgrounds = [b.get("url") for b in (detail.get("backgrounds") or []) if b.get("url")]
            splash = {s: next((u for u in backgrounds if f"/{s}_" in u), None)
                      for s in ("960", "1600", "2600")}

            # focal 은 2600 스플래시 기준으로 뽑는다. 이 값을 쓰는 곳(카드 그리드,
            # 스크롤러)이 전부 스플래시를 크롭해서 쓰기 때문이다.
            focal = 0.5
            if splash.get(FOCAL_SIZE):
                try:
                    focal = focal_x(fetch_image(splash[FOCAL_SIZE]))
                except Exception as exc:
                    print(f"{tag}: focal 추정 실패({exc}) - 0.5 사용")

            manifest[key] = {
                "name": name,
                "role": hero.get("role"),
                "portrait": hero.get("portrait"),
                # 배너 배경 블러 레이어와 카드 그리드가 계속 쓴다.
                "splash": splash,
                "art_source": art_url,
                "cutout_path": f"{ART_REPO_PATH}/{key}.webp",
                "cutout_size": list(cut.size),
                # 스플래시를 크롭해 쓰는 곳(카드 그리드/스크롤러) 전용.
                # 전신 렌더 자체는 정면 정중앙이라 이 값을 쓰지 않는다.
                "focal_x": focal,
                "luma": {
                    "before": round(luma_before, 1),
                    "after": round(luma_after, 1),
                    "gamma": round(gamma, 3),
                },
                # 사람이 육안 QA 로 내린 False 는 재실행해도 유지한다.
                # 다시 살리려면 매니페스트에서 직접 true 로 바꾼다.
                "use_cutout": manifest.get(key, {}).get("use_cutout", True),
            }
            print(f"{tag}: {cut.size} luma {luma_before:.0f}->{luma_after:.0f} "
                  f"(gamma {gamma:.2f}) -> {out_path.name}")
        except Exception as exc:
            print(f"{tag}: 실패 - {exc}")

        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        time.sleep(REQUEST_DELAY)

    print(f"\n완료: {len(manifest)}명 / 매니페스트 {MANIFEST_PATH}")


if __name__ == "__main__":
    build(sys.argv[1:] or None)
