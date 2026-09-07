# pv_module.py
import requests
from datetime import datetime

def get_pv_data():
    url = "https://api.open-meteo.com/v1/forecast?latitude=51.801&longitude=7.738&hourly=shortwave_radiation"

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        radiation_list = data.get("hourly", {}).get("shortwave_radiation", [])
        if radiation_list:
            radiation = radiation_list[0]
        else:
            # Fallback: einfache Tageskurve
            hour = datetime.now().hour
            if 8 <= hour <= 18:
                radiation = 200
            else:
                radiation = 0
    except:
        # Fallback bei API-Fehler
        hour = datetime.now().hour
        radiation = 200 if 8 <= hour <= 18 else 0

    power = int(radiation * 1.25)
    status = "Produktion" if power > 10 else "Nacht" if power == 0 else "Standby"

    return {
        "power": power,
        "radiation": radiation,
        "status": status
    }
