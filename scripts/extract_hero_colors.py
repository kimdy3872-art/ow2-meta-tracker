"""컷아웃에서 영웅 대표색을 뽑아 assets/hero_colors.json 을 만든다 (빌드 타임 전용).

HERO 카드 배경 그라디언트를 영웅마다 다르게 주기 위한 것. colorthief 대신 PIL 만 쓴다.
불투명 픽셀만 대상으로 하고, 너무 어둡거나 채도 낮은 픽셀은 빼야 회색 캐릭터에서도
대표색이 나온다.
"""

import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ART_DIR = ROOT / "static" / "hero_art"
OUT = ROOT / "assets" / "hero_colors.json"


def dominant(path: Path):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((220, 220))
    a = np.asarray(im, dtype=np.float32)
    rgb, alpha = a[..., :3] / 255.0, a[..., 3] / 255.0

    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    val = mx
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    # 불투명 + 너무 어둡지도 밝지도 않고 + 채도가 있는 픽셀
    keep = (alpha > 0.8) & (val > 0.18) & (val < 0.95) & (sat > 0.22)
    if keep.sum() < 60:
        keep = alpha > 0.8
    if keep.sum() == 0:
        return "#3b1a5c"

    px = rgb[keep]
    # 색상환에서 최빈 구간을 찾는다(평균을 내면 보색끼리 섞여 회색이 된다)
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px])
    hist, edges = np.histogram(hsv[:, 0], bins=18, range=(0, 1),
                               weights=hsv[:, 1])
    b = int(hist.argmax())
    sel = (hsv[:, 0] >= edges[b]) & (hsv[:, 0] < edges[b + 1])
    h = float(np.median(hsv[sel, 0]))
    s = float(np.clip(np.median(hsv[sel, 1]) * 1.15, 0.45, 0.95))
    v = float(np.clip(np.median(hsv[sel, 2]) * 0.75, 0.28, 0.6))
    r, g, bl = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(bl * 255))


def main():
    colors = {p.stem: dominant(p) for p in sorted(ART_DIR.glob("*.webp"))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(colors, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(colors)}명 대표색 -> {OUT}")


if __name__ == "__main__":
    main()
