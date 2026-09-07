import requests

def get_pv_data():
    lat = 51.801
    lon = 7.738

    url = (
        f"https://api.open-meteo.com/v1/solar?"
        f"latitude={lat}&longitude={lon}&hourly=solar_radiation"
    )

    data = {}
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                data = {}
    except Exception:
        data = {}

    # Defensive parsing: API may return unexpected payload
    radiation = 0
    try:
        hourly = data.get("hourly", {})
        radiation_list = hourly.get("solar_radiation") if isinstance(hourly, dict) else None
        if radiation_list and isinstance(radiation_list, (list, tuple)) and len(radiation_list) > 0:
            radiation = radiation_list[0]
    except Exception:
        radiation = 0

    try:
        power = int(radiation * 1.25)
    except Exception:
        power = 0

    status = "Produktion" if power > 10 else "Nacht" if power == 0 else "Standby"

    return {
        "power": power,
        "status": status,
        "radiation": radiation
    }
