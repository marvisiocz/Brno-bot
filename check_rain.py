"""Brno rain alert — checks Open-Meteo every 15 min. Sends a Telegram alert when
rain is imminent OR already falling, but only ONCE per rain event (state kept in
state.json, persisted between runs via GitHub Actions cache). Attaches a Rain
Viewer + OSM radar snapshot of Brno + okolí; falls back to text if radar fails."""

import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from radar import make_brno_radar

LAT, LON = 49.1951, 16.6068
TZ = ZoneInfo("Europe/Prague")

# Tunable knobs
LOOKAHEAD_MIN = 45    # search for first rainy 15-min block in next N minutes
LOOKBACK_MIN  = 30    # window used to decide "it's raining now"
WET_MM_BLOCK  = 0.1   # 15-min block ≥ this many mm = "wet"
DRY_MM_TOTAL  = 0.2   # total mm in lookback above this = "raining now"
STATE_FILE    = "state.json"

TOKEN    = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_IDS = [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:  # noqa: BLE001
        print(f"Warning: could not save state: {e!r}")


# ---- fetch forecast ----
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&minutely_15=precipitation,precipitation_probability"
    "&past_days=1&forecast_days=1"
    "&timezone=Europe/Prague"
)
r = requests.get(url, timeout=30)
r.raise_for_status()
m = r.json()["minutely_15"]
times = [datetime.fromisoformat(t).replace(tzinfo=TZ) for t in m["time"]]
precs = m["precipitation"]
probs = m.get("precipitation_probability") or [None] * len(precs)

now = datetime.now(TZ)
now_epoch = now.timestamp()

# total precip over the last LOOKBACK_MIN minutes
past_total = sum(
    (p or 0)
    for t, p in zip(times, precs)
    if 0 <= (now - t).total_seconds() / 60 <= LOOKBACK_MIN
)

# first wet 15-min block in the next LOOKAHEAD_MIN minutes
first_wet = None
for t, p, pr in zip(times, precs, probs):
    dmin = (t - now).total_seconds() / 60
    if dmin <= 0:
        continue
    if dmin > LOOKAHEAD_MIN:
        break
    if (p or 0) >= WET_MM_BLOCK:
        first_wet = (t, p, pr)
        break

raining_now = past_total > DRY_MM_TOTAL
approaching = first_wet is not None

# ---- decide ----
# Genuinely clear (no rain now and none coming) -> reset the event marker so the
# next rain alerts fresh, and skip.
if not raining_now and not approaching:
    print(
        f"Skip — clear (last {LOOKBACK_MIN} min {past_total:.2f} mm, "
        f"dry next {LOOKAHEAD_MIN} min)."
    )
    save_state({"last_alert_epoch": 0})
    sys.exit(0)

# Rain is happening or imminent. Did we already alert for this event?
state = load_state()
last_alert = state.get("last_alert_epoch", 0) or 0
if last_alert:
    when = datetime.fromtimestamp(last_alert, TZ).strftime("%H:%M")
    print(f"Skip — already alerted for this rain event (at {when}).")
    sys.exit(0)

# ---- build message ----
if raining_now:
    msg = (
        f"🌧️ *Prší v Brně*\n"
        f"Posledních 30 min: ~{past_total:.1f} mm"
    )
    if approaching:
        msg += "\nDéšť pokračuje i v další půlhodině."
else:
    t, p, pr = first_wet
    mins_to_rain = max(0, int((t - now).total_seconds() // 60))
    prob_str = f" ({pr}%)" if pr is not None else ""
    msg = (
        f"☔ *Brno — déšť za ~{mins_to_rain} min*\n"
        f"Start okolo {t.strftime('%H:%M')}{prob_str}\n"
        f"První 15 min: ~{p:.1f} mm"
    )

# ---- send: photo with radar, fallback to text ----
sent = False
try:
    png, radar_ts = make_brno_radar()
    radar_dt = datetime.fromtimestamp(radar_ts, TZ)
    caption = (
        msg
        + f"\n\n_Radar: {radar_dt.strftime('%H:%M')} · "
        "© OpenStreetMap · Weather data by Rain Viewer_"
    )
    for cid in CHAT_IDS:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": cid, "caption": caption, "parse_mode": "Markdown"},
            files={"photo": ("brno-radar.png", png, "image/png")},
            timeout=60,
        )
        resp.raise_for_status()
    sent = True
    print(f"Sent photo + caption to {len(CHAT_IDS)} chat(s): {msg.splitlines()[0]}")
except Exception as e:  # noqa: BLE001
    print(f"Radar fetch/send failed ({e!r}); falling back to text-only.")
    for cid in CHAT_IDS:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"},
            timeout=30,
        )
        resp.raise_for_status()
    sent = True
    print(f"Sent to {len(CHAT_IDS)} chat(s): {msg}")

# Only mark the event as alerted once something actually went out.
if sent:
    save_state({"last_alert_epoch": now_epoch})
