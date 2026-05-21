"""Compose a static PNG of Brno + okolí: OpenStreetMap base + Rain Viewer radar overlay.

Returns (png_bytes, frame_unix_timestamp) ready for Telegram sendPhoto.
"""

import io
import math
import requests
from PIL import Image, ImageDraw

LAT, LON = 49.1951, 16.6068        # Brno
ZOOM = 7                            # Rain Viewer free tier max
TILE_SIZE = 512                     # 512 px tiles, free tier supported
CROP_SIZE = 384                     # final output in px (≈ 150 km square)
RADAR_OPACITY = 0.75
COLOR_SCHEME = 2                    # 2 = Universal Blue (RV default)
SMOOTH = "1_1"                      # smooth=1, snow=1 (rain + snow tinted)
USER_AGENT = "Brno-bot/1.0 (+https://github.com/marvisiocz/Brno-bot)"

OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
RAINVIEWER_INDEX = "https://api.rainviewer.com/public/weather-maps.json"

_HEADERS = {"User-Agent": USER_AGENT}


def _latlon_to_tile_xy(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Convert (lat, lon) to fractional tile coordinates (XYZ scheme)."""
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _fetch_image(url: str, timeout: int = 20) -> Image.Image | None:
    """Fetch a PNG; return RGBA Image, or None if 404 / empty / error."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        if r.status_code != 200 or len(r.content) < 100:
            return None
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        return None


def make_brno_radar() -> tuple[bytes, int]:
    """Return (png_bytes, frame_unix_timestamp) for current Brno+okolí radar."""
    # 1) Latest radar frame metadata
    idx = requests.get(RAINVIEWER_INDEX, headers=_HEADERS, timeout=15).json()
    frame = idx["radar"]["past"][-1]    # last observed (real) frame
    host = idx["host"]
    radar_tmpl = (
        f"{host}{frame['path']}/{TILE_SIZE}"
        f"/{{z}}/{{x}}/{{y}}/{COLOR_SCHEME}/{SMOOTH}.png"
    )

    # 2) Locate Brno in tile space and pick a 2x2 grid around it
    bx, by = _latlon_to_tile_xy(LAT, LON, ZOOM)
    tx0 = int(math.floor(bx - 0.5))
    ty0 = int(math.floor(by - 0.5))

    base = Image.new("RGBA", (TILE_SIZE * 2, TILE_SIZE * 2), (240, 240, 240, 255))
    radar = Image.new("RGBA", (TILE_SIZE * 2, TILE_SIZE * 2), (0, 0, 0, 0))

    for dx in range(2):
        for dy in range(2):
            tx, ty = tx0 + dx, ty0 + dy

            # OSM serves 256 px tiles; upscale to TILE_SIZE for clean compositing
            osm = _fetch_image(OSM_TILE_URL.format(z=ZOOM, x=tx, y=ty))
            if osm is not None:
                if osm.size != (TILE_SIZE, TILE_SIZE):
                    osm = osm.resize((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
                base.paste(osm, (dx * TILE_SIZE, dy * TILE_SIZE))

            rad = _fetch_image(radar_tmpl.format(z=ZOOM, x=tx, y=ty))
            if rad is not None:
                radar.paste(rad, (dx * TILE_SIZE, dy * TILE_SIZE), rad)

    # 3) Apply radar opacity
    if RADAR_OPACITY < 1.0:
        a = radar.split()[3].point(lambda p: int(p * RADAR_OPACITY))
        radar.putalpha(a)

    composed = Image.alpha_composite(base, radar)

    # 4) Crop centered on Brno
    bx_px = (bx - tx0) * TILE_SIZE
    by_px = (by - ty0) * TILE_SIZE
    half = CROP_SIZE // 2
    left = int(max(0, min(composed.width - CROP_SIZE, bx_px - half)))
    top = int(max(0, min(composed.height - CROP_SIZE, by_px - half)))
    cropped = composed.crop((left, top, left + CROP_SIZE, top + CROP_SIZE))

    # 5) Draw a small red marker at Brno
    draw = ImageDraw.Draw(cropped)
    cx, cy = bx_px - left, by_px - top
    r_px = 7
    draw.ellipse(
        (cx - r_px, cy - r_px, cx + r_px, cy + r_px),
        fill=(220, 30, 30, 255),
        outline=(0, 0, 0, 255),
        width=2,
    )

    # 6) PNG bytes
    buf = io.BytesIO()
    cropped.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue(), frame["time"]


if __name__ == "__main__":
    png, ts = make_brno_radar()
    with open("brno-radar.png", "wb") as f:
        f.write(png)
    print(f"Saved brno-radar.png ({len(png) // 1024} KB), frame ts={ts}")
