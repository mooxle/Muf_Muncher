import base64
import json
import os
import sys
import time as _time

# Force UTC so plotext's date axis (which uses local-time fromtimestamp
# internally) lines up with the UTC timestamps we feed it.
os.environ["TZ"] = "UTC"
_time.tzset()

import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import plotext as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# In the Docker container this is set to /data so output lands in the mounted
# volume, separate from the script itself; locally it defaults next to muf.py.
OUTPUT_DIR = os.environ.get("MUF_OUTPUT_DIR", SCRIPT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

JSON_PATH = os.path.join(OUTPUT_DIR, "muf_data.json")
ISO_FORM = "%Y-%m-%dT%H:%M:%SZ"

# 1. Generate timestamps in the format expected by the new endpoint (YYYY/MM/DD HH:MM:SS)
now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)
from_time = cutoff.strftime("%Y/%m/%d %H:%M:%S")
to_time = now.strftime("%Y/%m/%d %H:%M:%S")

# The old /common/DIDBGetValues servlet has been retired by the server (404).
# It was replaced by /fastchar/getbest, discovered via the scaled.php search form on giro.uml.edu.
stations = {
    "DB049": "Dourbes",
    "JR055": "Juliusruh",
}
# foEs included alongside foF2/MUF(D): during strong Sporadic-E the F2 trace can
# be unscoreable ("---" in the raw feed), so foEs is often the only usable value.
chars = "foF2,MUF(D),foEs"

# Ticker: more European stations, current MUF(D) only (no 24h history/chart -
# that's what keeps these cheap to add). Picked from GIRO's full station list
# (https://lgdc.uml.edu/ionoweb/locations) for European coverage, then pruned
# to only the ones that actually return recent data - Chilton (RL052), Warsaw
# (MZ152) and its Olsztyn alternate (OL246), Kiruna (KI167), and Nicosia
# (NI135, last reading was 12 days old) are the only stations in their
# countries but currently offline/stale, so those countries have no entry.
TICKER_STATIONS = {
    "EB040": "Roquetes",
    "FF051": "Fairford",
    "VT139": "San Vito",
    "GM037": "Gibilmanna",
    "AT138": "Athens",
    "PQ052": "Pruhonice",
    "SO148": "Sopron",
    "TR169": "Tromso",
}
# ISO 3166-1 alpha-2, shown as a small badge next to each ticker station since
# not every reader knows which country a given ionosonde sits in.
TICKER_COUNTRY = {
    "EB040": "ES",
    "FF051": "GB",
    "VT139": "IT",
    "GM037": "IT",
    "AT138": "GR",
    "PQ052": "CZ",
    "SO148": "HU",
    "TR169": "NO",
}
TICKER_LOOKBACK = timedelta(hours=6)

DATE_FORM = "d/m/Y H:M:S"


def parse_float_or_none(text):
    try:
        return float(text)
    except ValueError:
        return None


def fetch_station(station):
    query = urllib.parse.urlencode(
        {
            "ursiCode": station,
            "charName": chars,
            "fromDate": from_time,
            "toDate": to_time,
        }
    )
    url = f"https://lgdc.uml.edu/fastchar/getbest?{query}"

    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )

    records = []
    with urllib.request.urlopen(req) as response:
        raw_data = response.read().decode("utf-8")

    for line in raw_data.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        ts = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        records.append(
            {
                "time": ts.strftime(ISO_FORM),
                "foF2": parse_float_or_none(parts[2]),
                "muf": parse_float_or_none(parts[4]),
                "foEs": parse_float_or_none(parts[6]),
            }
        )
    return records


def fetch_ticker_value(station):
    """Latest MUF(D) only, short lookback window - no history kept, just
    today's reading for the ticker row."""
    query = urllib.parse.urlencode(
        {
            "ursiCode": station,
            "charName": "MUF(D)",
            "fromDate": (now - TICKER_LOOKBACK).strftime("%Y/%m/%d %H:%M:%S"),
            "toDate": to_time,
        }
    )
    url = f"https://lgdc.uml.edu/fastchar/getbest?{query}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    with urllib.request.urlopen(req) as response:
        raw_data = response.read().decode("utf-8")

    latest = None
    for line in raw_data.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        ts = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        muf = parse_float_or_none(parts[2])
        if muf is not None:
            latest = {"time": ts.strftime(ISO_FORM), "muf": muf}
    return latest


def fetch_kindex():
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        raw = json.loads(response.read().decode("utf-8"))
    records = []
    for row in raw:
        ts = datetime.strptime(row["time_tag"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        records.append({"time": ts.strftime(ISO_FORM), "kp": row["Kp"], "aRunning": row["a_running"]})
    return records


def fetch_sfi():
    url = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        raw = json.loads(response.read().decode("utf-8"))
    records = []
    for row in raw:
        ts = datetime.strptime(row["time_tag"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        records.append({"time": ts.strftime(ISO_FORM), "flux": row["flux"]})
    return records


# Rough bounding box covering mainland Europe, UK, Scandinavia, Iceland and
# European Russia west of the Urals - good enough for "is this spot in Europe",
# not meant to be a precise DXCC/continent boundary.
EU_LAT_RANGE = (34.0, 72.0)
EU_LON_RANGE = (-25.0, 40.0)
POTA_MAX_AGE = timedelta(minutes=15)

# (band, low_kHz, high_kHz) - HF only, deliberately excludes 6m/VHF/UHF per
# the "no VHF/UHF" requirement, and excludes 160m's LF-adjacent edge cases.
HF_BANDS = [
    ("160m", 1800, 2000),
    ("80m", 3500, 4000),
    ("60m", 5330, 5410),
    ("40m", 7000, 7300),
    ("30m", 10100, 10150),
    ("20m", 14000, 14350),
    ("17m", 18068, 18168),
    ("15m", 21000, 21450),
    ("12m", 24890, 24990),
    ("10m", 28000, 29700),
]


def khz_to_band(freq_khz):
    for name, lo, hi in HF_BANDS:
        if lo <= freq_khz <= hi:
            return name
    return None


def fetch_pota_spots():
    url = "https://api.pota.app/spot/activator"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        raw = json.loads(response.read().decode("utf-8"))

    spots = []
    for row in raw:
        try:
            freq_khz = float(row["frequency"])
            lat, lon = float(row["latitude"]), float(row["longitude"])
            spot_time = datetime.strptime(row["spotTime"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue

        if now - spot_time > POTA_MAX_AGE:
            continue
        if not (EU_LAT_RANGE[0] <= lat <= EU_LAT_RANGE[1] and EU_LON_RANGE[0] <= lon <= EU_LON_RANGE[1]):
            continue
        band = khz_to_band(freq_khz)
        if band is None:
            continue

        spots.append(
            {
                "activator": row.get("activator"),
                "reference": row.get("reference"),
                "parkName": row.get("name"),
                "band": band,
                "mode": row.get("mode"),
                "frequencyKHz": freq_khz,
                "spotTime": spot_time.strftime(ISO_FORM),
            }
        )
    spots.sort(key=lambda s: s["spotTime"], reverse=True)
    return spots


def merge_and_prune(existing_records, fresh_records):
    """Dedup by timestamp, drop anything older than the 24h cutoff, sort by time."""
    by_time = {r["time"]: r for r in existing_records}
    for r in fresh_records:
        by_time[r["time"]] = r
    return sorted(
        (r for r in by_time.values() if datetime.strptime(r["time"], ISO_FORM).replace(tzinfo=timezone.utc) >= cutoff),
        key=lambda r: r["time"],
    )


def load_store():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            return json.load(f)
    return {}


def save_store(store):
    with open(JSON_PATH, "w") as f:
        json.dump(store, f, indent=2)


def last_non_null(records, key):
    for r in reversed(records):
        if r.get(key) is not None:
            return r[key]
    return None


SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary.json")
# Same reason as EXTRA_OUTPUT_PATHS below: NPM forwards the reverse-proxied
# request path unstripped (confirmed while chasing the original /muf/ 404),
# so anything reachable at /muf/<file> must also physically exist there.
EXTRA_SUMMARY_PATHS = [os.path.join(OUTPUT_DIR, "muf", "summary.json")]


def render_summary(store, stations, generated_at):
    """A small flat JSON, separate from muf_data.json's full 24h history, meant
    for dashboards like gethomepage/homepage whose custom-API widget maps fixed
    top-level fields - it can't index "the last item" of a variable-length array."""
    summary = {"generatedAt": generated_at.strftime(ISO_FORM)}
    for code, name in stations.items():
        records = store.get(code, {}).get("records", [])
        summary[name.lower()] = {
            "name": name,
            "muf": last_non_null(records, "muf"),
            "foF2": last_non_null(records, "foF2"),
            "foEs": last_non_null(records, "foEs"),
        }
    kindex = store.get("_indices", {}).get("kindex", [])
    sfi = store.get("_indices", {}).get("sfi", [])
    summary["sfi"] = sfi[-1]["flux"] if sfi else None
    summary["kp"] = kindex[-1]["kp"] if kindex else None
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    for path in EXTRA_SUMMARY_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
    return SUMMARY_PATH


HTML_TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "dashboard_template.html")
ICON_PATH = os.path.join(SCRIPT_DIR, "mufmuncher-icon.png")
HTML_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "dashboard.html")
# Written to every one of these paths so the page loads correctly regardless
# of whether a reverse proxy in front strips its location prefix or not:
#   /              -> index.html
#   /dashboard.html -> dashboard.html
#   /muf/          -> muf/index.html  (matches an unstripped "/muf/" proxy_pass)
EXTRA_OUTPUT_PATHS = [
    os.path.join(OUTPUT_DIR, "index.html"),
    os.path.join(OUTPUT_DIR, "muf", "index.html"),
]


def render_html(store, stations, generated_at, pota_spots, ticker_stations):
    payload = {
        "generatedAt": generated_at.strftime(ISO_FORM),
        "stations": [
            {"code": code, "name": store[code]["name"], "records": store[code]["records"]}
            for code in stations
            if code in store
        ],
        "indices": store.get("_indices", {"kindex": [], "sfi": []}),
        "potaSpots": pota_spots,
        "tickerStations": [
            {"code": code, "name": name, "country": TICKER_COUNTRY.get(code), **store["_ticker"][code]}
            for code, name in ticker_stations.items()
            if code in store.get("_ticker", {})
        ],
    }
    with open(HTML_TEMPLATE_PATH) as f:
        template = f.read()
    with open(ICON_PATH, "rb") as f:
        icon_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    html = template.replace("__MUF_DATA_JSON__", json.dumps(payload)).replace("__MUF_MUNCHER_ICON__", icon_b64)
    with open(HTML_OUTPUT_PATH, "w") as f:
        f.write(html)
    for path in EXTRA_OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(html)
    return HTML_OUTPUT_PATH


store = load_store()

data = {}
for station, name in stations.items():
    print(f"Fetching {name} ({station})...")
    try:
        fresh_records = fetch_station(station)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason} for {name}")
        fresh_records = []

    pruned = merge_and_prune(store.get(station, {}).get("records", []), fresh_records)
    store[station] = {"name": name, "records": pruned}

    times = [datetime.strptime(r["time"], ISO_FORM).strftime("%d/%m/%Y %H:%M:%S") for r in pruned]
    fof2 = [r["foF2"] for r in pruned]
    muf = [r["muf"] for r in pruned]
    foEs = [r["foEs"] for r in pruned]
    data[name] = (times, fof2, muf, foEs)

print("Fetching space weather indices (NOAA SWPC)...")
indices = store.get("_indices", {"kindex": [], "sfi": []})
try:
    indices["kindex"] = merge_and_prune(indices.get("kindex", []), fetch_kindex())
except urllib.error.URLError as e:
    print(f"Failed to fetch K-index: {e}")
try:
    indices["sfi"] = merge_and_prune(indices.get("sfi", []), fetch_sfi())
except urllib.error.URLError as e:
    print(f"Failed to fetch SFI: {e}")
store["_indices"] = indices

print("Fetching POTA activator spots (Europe, HF, last 15min)...")
try:
    pota_spots = fetch_pota_spots()
except urllib.error.URLError as e:
    print(f"Failed to fetch POTA spots: {e}")
    pota_spots = []

ticker = store.get("_ticker", {})
for code, name in TICKER_STATIONS.items():
    print(f"Fetching ticker value for {name} ({code})...")
    try:
        latest = fetch_ticker_value(code)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Failed to fetch ticker value for {name}: {e}")
        latest = None
    if latest is not None:
        ticker[code] = latest
    # else: keep whatever value (if any) is already in the store, so a
    # transient failure shows the last known reading instead of nothing.
store["_ticker"] = ticker

save_store(store)
html_path = render_html(store, stations, now, pota_spots, TICKER_STATIONS)
summary_path = render_summary(store, stations, now)
print(f"Dashboard written to {html_path}")
print(f"Summary written to {summary_path}")

if not sys.stdout.isatty():
    # Non-interactive run (cron, redirected log, etc.) - the JSON/HTML output
    # above is the point; skip the terminal chart so logs don't fill with ANSI codes.
    sys.exit(0)

# Hourly tick marks (every 2h) instead of plotext's default, unevenly spaced ones
tick_start = cutoff.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
tick_times = []
t = tick_start
while t <= now:
    tick_times.append(t)
    t += timedelta(hours=2)
xtick_positions = [t.strftime("%d/%m/%Y %H:%M:%S") for t in tick_times]
xtick_labels = [t.strftime("%H:%M") for t in tick_times]

station_colors = {"Dourbes": "blue", "Juliusruh": "green"}
METRICS = [("foF2", 1), ("muf", 2), ("foEs", 3)]  # (data-tuple index, chart row)

plt.subplots(2, 1)
plt.subplot(1, 1).plotsize(120, 10)
plt.subplot(2, 1).plotsize(120, 60)


# --- Dashboard row: current-value KPI tiles ---
# Built manually with text() rather than indicator(), since indicator()
# hardcodes its value's text background to the terminal default (a dark
# box) regardless of canvas_color/axes_color set afterwards.
def kpi_tile(subplot, title, value, color):
    subplot.canvas_color("white")
    subplot.axes_color("white")
    subplot.frame(False)
    subplot.xfrequency(0)
    subplot.yfrequency(0)
    subplot.title(title)
    subplot.xlim(0, 1)
    subplot.ylim(0, 1)
    subplot.text(value, 0.5, 0.5, color=color, background="white", style="bold", alignment="center")


def last_value_str(values):
    for v in reversed(values):
        if v is not None:
            return f"{v:.2f} MHz"
    return "n/a"


n_tiles = 2 * len(data) + 1  # +1 for the "last updated" tile
plt.subplot(1, 1).subplots(1, n_tiles)

kpi_tile(plt.subplot(1, 1).subplot(1, 1), "Updated (UTC)", now.strftime("%H:%M:%S"), "gray+")

col = 2
for name, (times, fof2, muf, foEs) in data.items():
    color = station_colors.get(name)
    kpi_tile(plt.subplot(1, 1).subplot(1, col), f"{name} foF2", last_value_str(fof2), color)
    kpi_tile(plt.subplot(1, 1).subplot(1, col + 1), f"{name} MUF(D)", last_value_str(muf), color)
    col += 2

# --- Charts: foF2, MUF(D), foEs stacked ---
plt.subplot(2, 1).subplots(3, 1)

titles = {
    "foF2": "foF2 [MHz] - last 24h",
    "muf": "MUF(D) [MHz] - last 24h",
    "foEs": "foEs [MHz] - last 24h (Sporadic-E)",
}
value_index = {"foF2": 1, "muf": 2, "foEs": 3}

MAX_GAP = timedelta(minutes=20)


def plot_with_gaps(times, series, name, color):
    """Plot points as one continuous run; a single missed sample (common -
    autoscaling can fail on an individual ionogram) does not break the line,
    only a real time gap (>MAX_GAP) between two valid points does. Only the
    first run per station gets a label, so the legend doesn't repeat."""
    labeled = False
    run_t, run_v = [], []
    last_dt = None
    for t_, v_ in zip(times, series):
        if v_ is None:
            continue
        dt = datetime.strptime(t_, "%d/%m/%Y %H:%M:%S")
        if last_dt is not None and dt - last_dt > MAX_GAP:
            if len(run_t) > 1:
                plt.plot(run_t, run_v, marker="braille", color=color, label=None if labeled else name)
                labeled = True
            run_t, run_v = [], []
        run_t.append(t_)
        run_v.append(v_)
        last_dt = dt
    if len(run_t) > 1:
        plt.plot(run_t, run_v, marker="braille", color=color, label=None if labeled else name)


for metric, row in METRICS:
    plt.subplot(2, 1).subplot(row, 1)
    plt.date_form(DATE_FORM)
    for name, values in data.items():
        times = values[0]
        series = values[value_index[metric]]
        plot_with_gaps(times, series, name, station_colors.get(name))
    plt.xticks(xtick_positions, xtick_labels)
    plt.title(titles[metric])
    if metric == "foEs":
        plt.xlabel("Time (UTC)")

plt.show()
