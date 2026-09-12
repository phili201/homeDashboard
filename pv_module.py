import requests
from datetime import datetime

def get_pv_data():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=51.801&longitude=7.738"
        "&hourly=shortwave_radiation"
        "&models=icon_seamless"
    )

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        radiation_list = data.get("hourly", {}).get("shortwave_radiation", [])

        if radiation_list:
            hour = datetime.now().hour
            radiation = radiation_list[hour]
        else:
            # Fallback
            hour = datetime.now().hour
            radiation = 200 if 8 <= hour <= 18 else 0

    except:
        hour = datetime.now().hour
        radiation = 200 if 8 <= hour <= 18 else 0

    power = int(radiation * 1.25)
    status = "Produktion" if power > 10 else "Nacht" if power == 0 else "Standby"

    return {
        "power": power,
        "radiation": radiation,
        "status": status
    }

def get_pv_day_curve():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=51.801&longitude=7.738"
        "&hourly=shortwave_radiation"
        "&models=icon_seamless"
    )

    r = requests.get(url, timeout=5)
    data = r.json()

    radiation = data["hourly"]["shortwave_radiation"]
    curve = [int(r * 1.25) for r in radiation]  # PV-Leistung pro Stunde

    return {
        "time": data["hourly"]["time"],
        "power": curve
    }

def get_pv_yield():
    curve = get_pv_day_curve()["power"]
    wh = sum(curve)  # Summe aller Stundenwerte
    kwh = round(wh / 1000, 2)
    return {"wh": wh, "kwh": kwh}
