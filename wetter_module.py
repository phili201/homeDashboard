import requests

def weather_icon(code):
    mapping = {
        0: "☀️",
        1: "🌤️",
        2: "⛅",
        3: "☁️",
        45: "🌫️",
        48: "🌫️",
        51: "🌦️",
        53: "🌦️",
        55: "🌦️",
        61: "🌧️",
        63: "🌧️",
        65: "🌧️",
        71: "❄️",
        73: "❄️",
        75: "❄️",
        95: "⛈️",
        96: "⛈️",
        99: "⛈️",
    }
    return mapping.get(code, "🌡️")


def weather_text(code):
    mapping = {
        0: "Klarer Himmel",
        1: "Überwiegend klar",
        2: "Teilweise bewölkt",
        3: "Bewölkt",
        45: "Nebel",
        48: "Nebel",
        51: "Leichter Nieselregen",
        53: "Mäßiger Nieselregen",
        55: "Starker Nieselregen",
        61: "Leichter Regen",
        63: "Mäßiger Regen",
        65: "Starker Regen",
        71: "Leichter Schneefall",
        73: "Mäßiger Schneefall",
        75: "Starker Schneefall",
        95: "Gewitter",
        96: "Gewitter mit leichtem Hagel",
        99: "Gewitter mit starkem Hagel",
    }
    return mapping.get(code, "Unbekannt")


def get_weather():
    lat = 51.801
    lon = 7.738

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&hourly=temperature_2m,relativehumidity_2m,precipitation,precipitation_probability,"
        f"windspeed_10m,winddirection_10m,uv_index,cloudcover"
        f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"precipitation_probability_max,sunrise,sunset,uv_index_max,wind_speed_10m_max"
        f"&timezone=Europe/Berlin"
    )

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except Exception:
        return {}

    # CURRENT erweitern
    current = data.get("current_weather", {})
    current["code_text"] = weather_text(current.get("weathercode"))


    warnings = get_warnings(current, data.get("hourly", {}))

    # DAILY ICONS ERZEUGEN
    daily = data.get("daily", {})
    codes = daily.get("weathercode", [])
    daily["icon"] = [weather_icon(c) for c in codes]

    return {
        "current": current,
        "hourly": data.get("hourly", {}),
        "daily": daily,
        "warnings": warnings
    }


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

def get_warnings(current, hourly):
    warnings = []

    temp = current.get("temperature")
    wind = current.get("windspeed")
    uv = hourly.get("uv_index", [0])[0]
    rain = hourly.get("precipitation", [0])[0]

    if wind and wind >= 60:
        warnings.append("Sturmwarnung: Starke Windböen erwartet!")
    if wind and wind >= 90:
        warnings.append("Orkanwarnung: Sehr gefährliche Windgeschwindigkeiten!")

    if rain and rain >= 5:
        warnings.append("Starkregenwarnung: Hohe Niederschlagsmengen!")
    if rain and rain >= 15:
        warnings.append("Unwetterregen: Extrem starke Niederschläge!")

    if temp and temp >= 30:
        warnings.append("Hitze-Warnung: Sehr hohe Temperaturen!")
    if temp and temp <= 0:
        warnings.append("Frost-Warnung: Temperaturen unter 0°C!")

    if uv and uv >= 7:
        warnings.append("UV-Warnung: Sehr hohe UV-Strahlung!")

    return warnings
