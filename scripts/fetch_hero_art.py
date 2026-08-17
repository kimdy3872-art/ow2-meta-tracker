"""히어로 배너 아트 수집 + 배경 제거 컷아웃 생성 (빌드 타임 전용).

Streamlit 런타임에서는 절대 실행되지 않는다. onnxruntime / rembg 모델이 무겁기 때문에
로컬에서 수동으로 돌려 결과물(WebP + 매니페스트)만 커밋한다.

    pip install -r scripts/requirements-art.txt
    python scripts/fetch_hero_art.py            # 전체
    python scripts/fetch_hero_art.py kiriko dva # 일부만 다시

출력:
    assets/hero_art/{key}.webp        투명 배경 컷아웃
    data/hero_art_manifest.json       배너 렌더링에 필요한 메타데이터
"""

import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# 결과물은 저장소에 커밋하고, 앱은 GitHub raw 로 읽는다(데이터 로딩과 같은 경로).
ART_DIR = ROOT / "static" / "hero_art"
# 저장소 상대 경로만 기록한다. 실제 URL 은 app_data 가 GitHub raw 기준으로 만든다
# (Streamlit Cloud 는 /app/static/... 절대 경로를 앱 셸이 가로채 이미지를 못 준다).
ART_REPO_PATH = "static/hero_art"
MANIFEST_PATH = ROOT / "data" / "hero_art_manifest.json"

OVERFAST_BASE = "https://overfast-api.tekrop.fr"
# focal_x 는 카드 배경(2600 스플래시)에 쓰이므로 2600 기준으로 계산해야 한다.
FOCAL_SIZE = "2600"
# 컷아웃은 1600 크롭으로 뜬다. 인물 픽셀 크기는 2600 과 같고(둘 다 높이 760) 배경만
# 좁아서 피사체 비율이 높아진다.
CUTOUT_SIZE = "1600"
UA = {"User-Agent": "Mozilla/5.0"}

# isnet-general-use 는 빠르지만 어두운 배경을 남긴다(53명 중 절반가량 실패).
# birefnet-general 이 확연히 깨끗하다.
REMBG_MODEL = "birefnet-general"


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
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 + attempt * 2)


def focal_x(im):
    """캐릭터는 선명하고 배경은 블러라는 성질을 이용해 캐릭터의 가로 위치를 추정한다.

    컬럼별 그래디언트 에너지의 무게중심을 0~1로 반환. CSS object-position 값으로 쓴다.
    """
    a = np.asarray(im.convert("L").resize((400, 190)), dtype=np.float32)
    gx = np.abs(np.diff(a, axis=1, prepend=a[:, :1]))
    gy = np.abs(np.diff(a, axis=0, prepend=a[:1, :]))
    col = (gx + gy).sum(axis=0)
    col = np.maximum(col - np.percentile(col, 55), 0)
    if col.sum() == 0:
        return 0.5
    return round(float((col * np.arange(col.size)).sum() / col.sum()) / col.size, 3)


def cutout_health(rgba, src_size):
    """컷아웃이 실패했는지 판별할 지표. 육안 QA 대상을 좁히는 용도."""
    alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
    solid = float((alpha > 128).mean())
    return {
        # bbox 안에서 불투명 픽셀 비율. 0.85 이상이면 배경을 통째로 남긴 것.
        "solid_ratio": round(solid, 3),
        # 원본 대비 잘린 폭. 0.9 이상이면 배경까지 피사체로 잡았을 가능성이 높다.
        "width_ratio": round(rgba.width / src_size[0], 3),
    }


def make_session():
    """birefnet 세션.

    rembg 의 new_session 은 SessionOptions 를 받지 않는데, onnxruntime 의 기본 그래프
    최적화가 이 973MB 모델에서 무한정 멈춘다(CPU 0%로 60분+ 관측). 최적화를 끄면
    세션 생성 3초 / 추론 11초로 정상 동작하므로 세션 클래스를 직접 만든다.
    """
    import onnxruntime as ort
    from rembg.sessions.birefnet_general import BiRefNetSessionGeneral

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    return BiRefNetSessionGeneral(REMBG_MODEL, opts, ["CPUExecutionProvider"])


def build(keys=None):
    from rembg import remove

    ART_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    heroes = fetch_json(f"{OVERFAST_BASE}/heroes")
    if keys:
        heroes = [h for h in heroes if h["key"] in set(keys)]

    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    session = make_session()

    for i, hero in enumerate(heroes, 1):
        key, name = hero["key"], hero["name"]
        try:
            detail = fetch_json(f"{OVERFAST_BASE}/heroes/{key}")
            backgrounds = [b.get("url") for b in (detail.get("backgrounds") or []) if b.get("url")]
            focal_src_url = next((u for u in backgrounds if f"/{FOCAL_SIZE}_" in u), None)
            cutout_src_url = next((u for u in backgrounds if f"/{CUTOUT_SIZE}_" in u), None)
            if not focal_src_url or not cutout_src_url:
                print(f"[{i}/{len(heroes)}] {key}: 배너 아트 없음 - 건너뜀")
                continue

            src = fetch_image(focal_src_url)
            # alpha_matting은 어두운 영역에 유령 잔상을 남기므로 켜지 않는다.
            rgba = remove(fetch_image(cutout_src_url), session=session)
            bbox = rgba.getchannel("A").getbbox()
            if bbox is None:
                print(f"[{i}/{len(heroes)}] {key}: 컷아웃 전부 투명 - 건너뜀")
                continue
            cut = rgba.crop(bbox)

            out_path = ART_DIR / f"{key}.webp"
            cut.save(out_path, "WEBP", quality=82, method=6)

            manifest[key] = {
                "name": name,
                "role": hero.get("role"),
                "portrait": hero.get("portrait"),
                "splash": {s: next((u for u in backgrounds if f"/{s}_" in u), None)
                           for s in ("960", "1600", "2600")},
                "cutout_path": f"{ART_REPO_PATH}/{key}.webp",
                "cutout_size": list(cut.size),
                "focal_x": focal_x(src),
                "health": cutout_health(cut, src.size),
                # 배경 제거 실패 판정은 육안 QA로만 가능해서(지표로는 안 잡힌다) 사람이
                # 내린 False 는 재실행해도 유지한다. 다시 살리려면 매니페스트에서 직접 true 로.
                "use_cutout": manifest.get(key, {}).get("use_cutout", True),
            }
            h = manifest[key]["health"]
            print(f"[{i}/{len(heroes)}] {key}: {cut.size} "
                  f"solid={h['solid_ratio']} width={h['width_ratio']} "
                  f"focal={manifest[key]['focal_x']} -> {out_path.name}")
        except Exception as exc:
            print(f"[{i}/{len(heroes)}] {key}: 실패 - {exc}")

        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    print(f"\n완료: {len(manifest)}명 / 매니페스트 {MANIFEST_PATH}")


if __name__ == "__main__":
    build(sys.argv[1:] or None)
