import json
from datetime import datetime

def load_abfall_events():
    try:
        with open("abfall_data.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        print("Fehler beim Laden der Abfall-JSON:", e)
        return []

    events = []

    for item in data.get("termine", []):
        date = item.get("datum")
        art = item.get("bezeichnung", "")

        icon, css = classify_abfall(art)

        events.append({
            "name": art,
            "begin": date,
            "weekday": datetime.strptime(date, "%Y-%m-%d").strftime("%A"),
            "icon": icon,
            "css": css
        })

    return events


def classify_abfall(name):
    name_lower = name.lower()

    if "rm" in name_lower:
        return ("🟫", "rest")
    if "bio" in name_lower:
        return ("🟩", "bio")
    if "pt" in name_lower:
        return ("🟦", "papier")
    if "gt" in name_lower:
        return ("🟨", "gelb")
    if "s" in name_lower:
        return ("🟥", "sperr")

    return ("⬜", "default")

def build_month_view(events, year, month):
    cal = calendar.Calendar(firstweekday=0)  # Montag
    month_days = cal.monthdatescalendar(year, month)

    # Events nach Datum mappen
    event_map = {}
    for e in events:
        event_map[e["begin"]] = e

    month_grid = []

    for week in month_days:
        week_row = []
        for day in week:
            day_str = day.strftime("%Y-%m-%d")
            entry = event_map.get(day_str, None)

            if entry:
                week_row.append({
                    "date": day_str,
                    "name": entry["name"],
                    "icon": entry["icon"],
                    "css": entry["css"]
                })
            else:
                week_row.append({
                    "date": day_str,
                    "name": None,
                    "icon": None,
                    "css": "none"
                })

        month_grid.append(week_row)

    return month_grid