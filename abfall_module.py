from ics import Calendar
import requests

def load_abfall_events(ics_url):
    r = requests.get(ics_url)
    c = Calendar(r.text)

    events = []

    for event in c.events:
        icon, css_class = classify_abfall(event.name)

        events.append({
            "name": event.name,
            "begin": event.begin.format("YYYY-MM-DD"),
            "weekday": event.begin.format("dddd"),
            "icon": icon,
            "css": css_class
        })

    return events


def classify_abfall(name):
    name_lower = name.lower()

    if "rest" in name_lower:
        return ("🟫", "rest")
    if "bio" in name_lower:
        return ("🟩", "bio")
    if "papier" in name_lower or "pappe" in name_lower:
        return ("🟦", "papier")
    if "gelb" in name_lower or "wertstoff" in name_lower:
        return ("🟨", "gelb")
    if "sperr" in name_lower:
        return ("🟥", "sperr")

    return ("⬜", "default")

import calendar
from datetime import date

def build_month_view(events, year, month):
    cal = calendar.Calendar(firstweekday=0)  # Montag = 0
    month_days = cal.monthdatescalendar(year, month)

    # Events nach Datum sortieren
    event_map = {}
    for e in events:
        event_map[e["begin"]] = e

    month_grid = []

    for week in month_days:
        week_row = []
        for day in week:
            day_str = day.strftime("%Y-%m-%d")

            if day_str in event_map:
                ev = event_map[day_str]
                week_row.append({
                    "date": day,
                    "event": ev,
                    "icon": ev["icon"],
                    "css": ev["css"]
                })
            else:
                week_row.append({
                    "date": day,
                    "event": None
                })

        month_grid.append(week_row)

    return month_grid

