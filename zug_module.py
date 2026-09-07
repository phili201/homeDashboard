import requests
from datetime import datetime

# Stations-IDs
DREN = 8001531
HILTRUP = 8002820
HAMM = 8000152

def get_departures(station_id):
    url = f"https://v5.db.transport.rest/stops/{station_id}/departures"
    try:
        r = requests.get(url, timeout=5)
        try:
            if r.status_code != 200:
                return []
            return r.json()
        except Exception:
            return []
    except Exception:
        return []

def is_between(time_str, start_h, end_h):
    if not time_str:
        return False
    try:
        t = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return start_h <= t.hour < end_h
    except Exception:
        return False

def filter_trains():
    result = []

    # 1️⃣ Morgens: Drensteinfurt → Hiltrup/Hamm (06–08)
    morning = get_departures(DREN)
    for d in morning:
        if is_between(d["plannedWhen"], 6, 8):
            if "hiltrup" in d["direction"].lower() or "hamm" in d["direction"].lower():
                result.append(d)

    # 2️⃣ Mittags: Hiltrup/Hamm → Drensteinfurt (13–16)
    midday_hiltrup = get_departures(HILTRUP)
    midday_hamm = get_departures(HAMM)

    for d in midday_hiltrup + midday_hamm:
        if is_between(d["plannedWhen"], 13, 16):
            if "drensteinfurt" in d["direction"].lower():
                result.append(d)

    return result


def delay_color(delay):
    if delay is None:
        return "white"
    minutes = delay // 60
    if minutes <= 2:
        return "lightgreen"
    if minutes <= 7:
        return "yellow"
    return "red"
