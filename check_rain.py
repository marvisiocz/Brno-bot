"""Brno rain alert — checks Open-Meteo every 15 min, pings Telegram if rain
expected within ~30–45 min and the last 30 min were dry. When alerting,
attaches a Rain Viewer + OSM radar snapshot of Brno + okolí."""

import os
import sys
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from radar import make_brno_radar

LAT, LON = 49.1951, 16.6068
TZ = ZoneInfo("Europe/Prague")

# Tunable knobs
LOOKAHEAD_MIN = 45    # search for first rainy 15-min block in next N minutes
LOOKBACK_MIN  = 30    # last N minutes must be dry for alert to fire
WET_MM_BLOCK  = 0.0   # 15-min block ≥ this many mm = "wet"
DRY_MM_TOTAL  = 999   # total mm in lookback above this = "already raining"

TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&minutely_15=precipitation,precipitation_probability"
    "&past_days=1&forecast_days=1"
    "&timezone=Europe/Prague"
)

r = requests.get(url, timeout=30)
r.raise_for_status()
data = r.json()
m = data["minutely_15"]

times = [datetime.fromisoformat(t).replace(tzinfo=TZ) for t in m["time"]]
precs = m["precipitation"]
probs = m.get("precipitation_probability") or [None] * len(precs)

now = datetime.now(TZ)

# 1) Past LOOKBACK_MIN minutes must be roughly dry
past_total = sum(
    (p or 0)
    for t, p in zip(times, precs)
    if 0 <= (now - t).total_seconds() / 60 <= LOOKBACK_MIN
)

# 2) First wet 15-min block in next LOOKAHEAD_MIN minutes
first_wet = None
for t, p, pr in zip(times, precs, probs):
    delta_min = (t - now).total_seconds() / 60
    if delta_min <= 0:
        continue
    if delta_min > LOOKAHEAD_MIN:
        break
    if (p or 0) >= WET_MM_BLOCK:
        first_wet = (t, p, pr)
        break

if not first_wet:
    print(f"Skip — no rain in next {LOOKAHEAD_MIN} min.")
    sys.exit(0)

if past_total > DRY_MM_TOTAL:
    print(
        f"Skip — already raining "
        f"(last {LOOKBACK_MIN} min total: {past_total:.2f} mm)."
    )
    sys.exit(0)

t, p, pr = first_wet
mins_to_rain = max(0, int((t - now).total_seconds() // 60))
prob_str = f" ({pr}%)" if pr is not None else ""

msg = (
    f"☔ *Brno — déšť za ~{mins_to_rain} min*\n"
    f"Start okolo {t.strftime('%H:%M')}{prob_str}\n"
    f"První 15 min: ~{p:.1f} mm"
)

# Try sendPhoto with radar; fall back to sendMessage if radar fetch fails.
try:
    png, radar_ts = make_brno_radar()
    radar_dt = datetime.fromtimestamp(radar_ts, TZ)
    caption = (
        msg
        + f"\n\n_Radar: {radar_dt.strftime('%H:%M')} · "
        "© OpenStreetMap · Weather data by Rain Viewer_"
    )
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        data={
            "chat_id": CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown",
        },
        files={"photo": ("brno-radar.png", png, "image/png")},
        timeout=60,
    )
    resp.raise_for_status()
    print(f"Sent photo + caption: {msg.splitlines()[0]}")
except Exception as e:
    print(f"Radar fetch/send failed ({e!r}); falling back to text-only.")
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"Sent: {msg}")
