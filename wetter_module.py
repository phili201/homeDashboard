import requests

def get_weather():
    # Drensteinfurt Koordinaten
    lat = 51.801
    lon = 7.738

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        r = requests.get(url, timeout=5)
        try:
            data = r.json()
            w = data.get("current_weather") or {}
        except Exception:
            w = {}
    except Exception:
        w = {}

    return {
        "temp": w.get("temperature", None),
        "wind": w.get("windspeed", None),
        "code": w.get("weathercode", None)
    }

def weather_icon(code):
    if code == 0:
        return "☀️"
    if code in [1, 2, 3]:
        return "⛅"
    if code in [45, 48]:
        return "🌫️"
    if code in [51, 53, 55]:
        return "🌦️"
    if code in [61, 63, 65]:
        return "🌧️"
    if code in [71, 73, 75]:
        return "❄️"
    if code in [95, 96, 99]:
        return "⛈️"
    return "🌡️"


def get_weather_widget():
    lat = 51.801
    lon = 7.738

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        w = data.get("current_weather") or {}
    except Exception:
        w = {}

    return {
        "temp": w.get("temperature", None),
        "code": w.get("weathercode", None)
    }