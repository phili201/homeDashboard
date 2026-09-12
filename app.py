from flask import Flask, render_template, request, redirect, session, abort, make_response
import json
from datetime import datetime
from pv_module import get_pv_data
from abfall_module import load_abfall_events, build_month_view, get_tomorrow_abfall
from rezepte_api import search_recipes, get_recipe_details
from ics import Calendar
import requests
from pywebpush import webpush, WebPushException
import os
from wetter_module import get_weather_widget, weather_icon, get_weather

app = Flask(__name__)
app.secret_key = "Rhode_Rhode_rhode_RHode"

@app.before_request
def check_cookie():
    # /auth muss frei sein, sonst kann der Cookie nicht gesetzt werden
    if request.path == "/auth":
        return

    allowed = request.cookies.get("auth")
    if allowed != "polizei123":
        abort(403)

@app.context_processor
def inject_dashboard_button():
    return {
        "dashboard_button": True
    }



with open('users.json', 'r') as f:
    users = json.load(f)

EINKAUFSLISTE_PATH = "einkaufsliste.json"
PUSH_SUBSCRIPTIONS_PATH = "push_subscriptions.json"
VAPID_PRIVATE_KEY = """MHcCAQEEIIYrAy5Jl6g2SHDfILiLhsrPJwB42ljlocTxAT8n9CCyoAoGCCqGSM49
AwEHoUQDQgAESaJszPEbJYy2kFMuZ/s3Em7DhxmR6TQQwXK1b5esTKH9YrwaaGs9
Euy+w/loB5eWkihHCLHnYXMfxpNYCovy6Q=="""
VAPID_CLAIMS = {"sub": "mailto:webmaster@homedashboard.de"}


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)


def load_users():
    with open("users.json", "r") as f:
        return json.load(f)


def require_user():
    if "user" not in session:
        return redirect("/dashboard?login=1")
    if users.get(session["pin"], {}).get("blocked", False):
        return redirect("/dashboard?login=1")
    return None


def require_admin():
    if "role" not in session or session["role"] != "admin":
        return redirect("/dashboard?login=1")

    if request.cookies.get("auth_admin") != "adminXYZ":
        abort(403)

    return None



LEGACY_MODULE_STATUS_ALIASES = {
    "wetter": "weather",
    "kalender": "calendar",
    "musik": "alexa",
    "netzwerk": "network",
}


def normalize_module_status(status):
    normalized = {}
    for key, value in (status or {}).items():
        canonical = LEGACY_MODULE_STATUS_ALIASES.get(key, key)
        normalized[canonical] = value
    return normalized


def load_module_status():
    try:
        with open("module_status.json") as f:
            return normalize_module_status(json.load(f))
    except:
        return {}


def load_einkaufsliste():
    if not os.path.exists(EINKAUFSLISTE_PATH):
        return {"haushalt": [], "schule": [], "urlaub": []}
    with open(EINKAUFSLISTE_PATH, "r") as f:
        try:
            return json.load(f)
        except:
            return {"haushalt": [], "schule": [], "urlaub": []}

def save_einkaufsliste(lists):
    with open(EINKAUFSLISTE_PATH, "w") as f:
        json.dump(lists, f, indent=4)


def load_push_subscriptions():
    try:
        with open(PUSH_SUBSCRIPTIONS_PATH) as f:
            return json.load(f)
    except:
        return []

def save_push_subscriptions(subs):
    with open(PUSH_SUBSCRIPTIONS_PATH, "w") as f:
        json.dump(subs, f, indent=4)

def send_push_to_all(title, body):
    subs = load_push_subscriptions()
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            print("Push-Fehler:", e)


# ---------------------------------------------------------
# Kalender laden
# ---------------------------------------------------------

def get_events_for_user(username):
    users_local = load_users()
    calendars = users_local.get(username, {}).get("ics_urls", [])
    all_events = []

    for cal in calendars:
        url = cal["url"]
        color = cal.get("color", "#3a82f7")
        cal_name = cal.get("name", "Kalender")

        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            c = Calendar(r.text)

            for event in c.events:
                all_events.append({
                    "name": event.name,
                    "start": event.begin.datetime.isoformat(),
                    "end": event.end.datetime.isoformat(),
                    "location": event.location or "",
                    "description": event.description or "",
                    "organizer": str(getattr(event, "organizer", "")),
                    "attendees": [
                        str(a.email) if hasattr(a, "email") else str(a)
                        for a in getattr(event, "attendees", [])
                    ],
                    "categories": list(event.categories) if event.categories else [],
                    "calendar_name": cal_name,
                    "calendar_color": color
                })
        except Exception as e:
            print("ICS Fehler:", e)

    return all_events


@app.route("/api/events/<username>")
def api_events(username):
    return get_events_for_user(username)


@app.route("/auth")
def auth():
    resp = make_response("Cookie gesetzt – Zugriff erlaubt.")
    resp.set_cookie(
    "auth",
    "polizei123",
    max_age=99999999,
    secure=True,
    httponly=True,
    samesite="Strict"
)
    return resp

@app.route("/auth_admin")
def auth_admin():
    resp = make_response("Admin-Cookie gesetzt.")
    resp.set_cookie(
        "auth_admin",
        "adminXYZ",
        max_age=99999999,
        secure=True,
        httponly=True,
        samesite="Strict"
    )
    return resp

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


# ---------------------------------------------------------
# Kontext für Templates
# ---------------------------------------------------------

@app.context_processor
def inject_modules():
    modules = {}
    if "pin" in session and session["pin"] in users:
        modules = users[session["pin"]].get("modules", {})

    return {
        "modules": modules,
        "show_login_modal": request.args.get("login") == "1" and "pin" not in session,
        "login_error": request.args.get("error", "")
    }


# ---------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------

@app.route("/")
def index():
    # Startseite ist immer das Dashboard, ohne Login-Pflicht
    return redirect("/dashboard")

@app.route("/api/push_subscribe", methods=["POST"])
def api_push_subscribe():
    sub = request.get_json() or {}
    subs = load_push_subscriptions()

    # einfache Duplikat-Prüfung
    if sub not in subs:
        subs.append(sub)
        save_push_subscriptions(subs)

    return {"status": "ok"}

@app.route("/push_abfall_check")
def push_abfall_check():
    events = load_abfall_events()
    tomorrow_events = get_tomorrow_abfall(events)

    if not tomorrow_events:
        return "Kein Abfall morgen."

    names = ", ".join([e["name"] for e in tomorrow_events])

    # schöner Titel je nach Abfallart
    if "Restmüll" in names:
        title = "🗑️ Restmüll morgen"
        body = "Morgen wird Restmüll abgeholt.\nBitte die schwarze Tonne rausstellen!"
    elif "Gelber Sack" in names:
        title = "♻️ Gelber Sack morgen"
        body = "Morgen wird der Gelbe Sack abgeholt.\nBitte die Säcke bereitstellen!"
    elif "Biomüll" in names:
        title = "🌿 Biomüll morgen"
        body = "Morgen wird Biomüll abgeholt.\nBitte die grüne Tonne rausstellen!"
    elif "Papier" in names:
        title = "📦 Papier morgen"
        body = "Morgen wird Papier abgeholt.\nBitte die blaue Tonne rausstellen!"
    else:
        title = "🗑️ Abfall morgen"
        body = f"Morgen wird abgeholt: {names}"

    send_push_to_all(title, body)
    return "Push gesendet."


@app.route("/api/wetter_warnings")
def wetter_warnings():
    w = get_weather()
    warnings = w.get("warnings", [])

    if not warnings:
        return {"status": "ok", "message": "Keine Warnungen"}

    for warn in warnings:
        try:
            webpush(
                subscription_info=json.loads(open("subscription.json").read()),
                data=json.dumps({"title": "Wetterwarnung", "body": warn}),
                vapid_private_key=open("vapid_private.pem").read(),
                vapid_claims={"sub": "mailto:admin@example.com"}
            )
        except Exception as e:
            print("Push Fehler:", e)

    return {"status": "sent", "count": len(warnings)}



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pin = request.form["pin"]

        if pin in users and not users[pin].get("blocked", False):
            session["pin"] = pin
            session["user"] = users[pin]["name"]
            session["calendar_id"] = users[pin]["calendar_id"]
            session["role"] = users[pin]["role"]
            session["email"] = users[pin]["email"]

            if users[pin]["role"] == "admin":
                session["is_admin"] = True
                return redirect("/admin")

            if users[pin].get("first_login", True):
                return redirect("/setup")

            session["is_admin"] = False
            return redirect("/dashboard")

        return redirect("/dashboard?login=1&error=Falsche+PIN+oder+Benutzer+blockiert")

    return redirect("/dashboard?login=1")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/dashboard")


# ---------------------------------------------------------
# Dashboard (öffentlich)
# ---------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    # Dashboard ist öffentlich und zeigt IMMER alle Module
    modules = {
        "calendar": True,
        "recipes": True,
        "pv": True,
        "alexa": True,
        "abfall": True,
        "weather": True,
        "zug": True
    }

    logged_in = "pin" in session

    from wetter_module import get_weather_widget, weather_icon
    from regenradar_module import get_radar_url

    w = get_weather_widget() or {}
    icon = weather_icon(w.get("code", 0))
    radar = get_radar_url()
    pv = get_pv_data()

    return render_template(
        "dashboard.html",
        modules=modules,
        weather=w,
        weather_icon=icon,
        radar=radar,
        pv=pv,
        pin=session.get("pin"),
        logged_in=logged_in
    )


# ---------------------------------------------------------
# Admin
# ---------------------------------------------------------

@app.route("/admin")
def admin():
    r = require_admin()
    if r:
        return r

    module_status = load_module_status()

    return render_template("admin.html", users=users, module_status=module_status)


@app.route("/admin/change_pin", methods=["POST"])
def change_pin():
    r = require_admin()
    if r:
        return r

    user_pin = request.form.get("user_pin")
    admin_pin = request.form.get("admin_pin")

    if user_pin and "0000" in users:
        users["0000"]["pin"] = user_pin

    if admin_pin and "admin" in users:
        users["admin"]["pin"] = admin_pin

    save_users()
    return redirect("/admin")


@app.route("/admin/add_user", methods=["POST"])
def add_user():
    r = require_admin()
    if r:
        return r

    name = request.form["name"]
    pin = request.form["pin"]
    calendar_id = request.form["calendar_id"]
    role = request.form["role"]
    email = request.form["email"]

    ics_urls = []
    index = 1

    while True:
        name_key = f"ics_name_{index}"
        color_key = f"ics_color_{index}"
        url_key = f"ics_url_{index}"

        if url_key not in request.form:
            break

        ics_name = request.form.get(name_key, "").strip()
        ics_color = request.form.get(color_key, "").strip() or "#3a82f7"
        ics_url = request.form.get(url_key, "").strip()

        if ics_url:
            ics_urls.append({
                "name": ics_name or f"Kalender {index}",
                "color": ics_color,
                "url": ics_url
            })

        index += 1

    users[pin] = {
        "name": name,
        "calendar_id": calendar_id,
        "role": role,
        "email": email,
        "first_login": True,
        "blocked": False,
        "modules": {
            "calendar": False,
            "recipes": False,
            "pv": False,
            "alexa": False,
            "abfall": False,
            "weather": False,
            "zug": False
        },
        "ics_urls": ics_urls
    }

    save_users()
    return redirect("/admin")


@app.route("/admin/delete_user/<pin>", methods=["POST"])
def delete_user(pin):
    r = require_admin()
    if r:
        return r

    if pin in users:
        del users[pin]
        save_users()

    return redirect("/admin")


@app.route("/admin/block_user/<pin>")
def block_user(pin):
    r = require_admin()
    if r:
        return r

    if pin in users:
        users[pin]["blocked"] = True
        save_users()

    return redirect("/admin")


@app.route("/admin/unblock_user/<pin>")
def unblock_user(pin):
    r = require_admin()
    if r:
        return r

    if pin in users:
        users[pin]["blocked"] = False
        save_users()

    return redirect("/admin")


@app.route("/admin/edit_user/<pin>", methods=["GET", "POST"])
def edit_user(pin):
    r = require_admin()
    if r:
        return r

    if request.method == "POST":
        users[pin].update({
            "name": request.form["name"],
            "calendar_id": request.form["calendar_id"],
            "role": request.form["role"],
            "email": request.form["email"]
        })
        save_users()
        return redirect("/admin")

    return render_template("edit_user.html", pin=pin, user=users.get(pin))


@app.route("/admin/reset_modules/<pin>", methods=["POST"])
def reset_modules(pin):
    r = require_admin()
    if r:
        return r

    users[pin]["modules"] = {
        "calendar": False,
        "recipes": False,
        "pv": False,
        "alexa": False,
        "abfall": False,
        "weather": False,
        "zug": False
    }

    users[pin]["first_login"] = True
    save_users()

    return redirect("/admin")


# ---------------------------------------------------------
# Setup
# ---------------------------------------------------------

@app.route("/setup", methods=["GET", "POST"])
def setup():
    r = require_user()
    if r:
        return r

    pin = session["pin"]

    if request.method == "GET":
        return render_template("setup.html", user=users[pin])

    users[pin]["modules"] = {
        "calendar": "calendar" in request.form,
        "recipes": "recipes" in request.form,
        "pv": "pv" in request.form,
        "alexa": "alexa" in request.form,
        "abfall": "abfall" in request.form,
        "weather": "weather" in request.form,
        "zug": "zug" in request.form
    }

    users[pin]["first_login"] = False
    save_users()

    # Nach Setup wieder ins Dashboard und direkt ausloggen,
    # damit der nächste Nutzer weiter machen kann
    response = redirect("/dashboard")
    session.clear()
    return response


# ---------------------------------------------------------
# Kalender UI (geschützt + Baustellenmodus)
# ---------------------------------------------------------

@app.route("/calendar_ui")
def calendar_ui():
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("calendar", "ready") != "ready":
        return render_template("baustelle.html")

    now = datetime.now()
    # nach Aufruf des Moduls bleibt Session bis zur Detailseite
    return redirect(f"/calendar_ui/{now.year}/{now.month}")


@app.route("/calendar_ui/<int:year>/<int:month>")
def calendar_ui_month(year, month):
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("calendar", "ready") != "ready":
        return render_template("baustelle.html")

    username = session["pin"]
    events = get_events_for_user(username)

    # Kalender anzeigen, danach automatisch ausloggen
    response = render_template("calendar_ui.html", events=events, year=year, month=month)
    session.clear()
    return response


# ---------------------------------------------------------
# Abfall (geschützt + Baustellenmodus)
# ---------------------------------------------------------

@app.route("/abfall")
def abfall():
    status = load_module_status()
    if status.get("abfall", "ready") != "ready":
        return render_template("baustelle.html")

    events = load_abfall_events()
    from abfall_module import get_upcoming_abfall_events

    upcoming = get_upcoming_abfall_events(events, days=21)

    return render_template("abfall.html", events=upcoming)


@app.route("/abfall_monat")
def abfall_monat():
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("abfall", "ready") != "ready":
        return render_template("baustelle.html")

    events = load_abfall_events()
    now = datetime.now()

    month_view = build_month_view(events, now.year, now.month)
    modules = users[session["pin"]].get("modules", {})

    response = render_template(
        "abfall_monat.html",
        month_view=month_view,
        year=now.year,
        month=now.month,
        modules=modules
    )
    session.clear()
    return response


# ---------------------------------------------------------
# Rezepte (geschützt + Baustellenmodus)
# ---------------------------------------------------------

@app.route("/rezepte/search")
def rezepte_search():
    status = load_module_status()
    if status.get("recipes", "ready") != "ready":
        return render_template("baustelle.html")

    query = request.args.get("q", "")
    recipes = search_recipes(query)

    return render_template("rezepte_search.html", recipes=recipes, query=query)


@app.route("/rezepte/<int:recipe_id>/cook")
def rezepte_cook(recipe_id):
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("recipes", "ready") != "ready":
        return render_template("baustelle.html")

    recipe = get_recipe_details(recipe_id)

    response = render_template("rezepte_cook.html", recipe=recipe)
    session.clear()
    return response


@app.route("/rezepte/<int:recipe_id>")
def rezepte_detail(recipe_id):
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("recipes", "ready") != "ready":
        return render_template("baustelle.html")

    recipe = get_recipe_details(recipe_id)

    response = render_template("rezepte_detail.html", recipe=recipe)
    session.clear()
    return response


@app.route("/einkaufsliste")
def einkaufsliste():
    return render_template("einkaufsliste.html")



@app.route("/api/einkaufsliste", methods=["GET", "POST"])
def api_einkaufsliste():
    if request.method == "GET":
        return load_einkaufsliste()

    data = request.get_json() or {}
    lists = data.get("lists", {})
    save_einkaufsliste(lists)
    return {"status": "ok"}

@app.route("/einkaufsliste/schreibblatt")
def einkaufsliste_schreibblatt():
    return render_template("einkaufsliste_schreibblatt.html")




# ---------------------------------------------------------
# Zug (geschützt + Baustellenmodus)
# ---------------------------------------------------------

@app.route("/zug")
def zug():
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("zug", "ready") != "ready":
        return render_template("baustelle.html")

    from zug_module import delay_color

    try:
        trains = requests.get("http://localhost:5000/api/zug_live", timeout=0.5).json()
    except Exception as e:
        print("Zug-API Fehler (lokal):", e)
        trains = []

    for t in trains:
        t["color"] = delay_color(t.get("delay", 0))

    response = render_template("zug.html", trains=trains)
    session.clear()
    return response


@app.route("/api/zug_live")
def api_zug_live():
    url = "https://iris.noncd.db.de/iris-tts/timetable/station/8001531/json"

    try:
        r = requests.get(url, timeout=3)
        if not r.text.strip():
            return []

        data = r.json()
        result = []

        for dp in data.get("departures", [])[:10]:
            result.append({
                "line": dp.get("line", "Unbekannt"),
                "direction": dp.get("direction", "Unbekannt"),
                "plannedWhen": dp.get("scheduled", ""),
                "when": dp.get("estimated", dp.get("scheduled", "")),
                "delay": dp.get("delay", 0),
                "platform": dp.get("platform", "?")
            })

        return result

    except Exception as e:
        print("Zug-API Fehler:", e)
        return []


# ---------------------------------------------------------
# PV (geschützt + Baustellenmodus)
# ---------------------------------------------------------

@app.route("/pv")
def pv():
    status = load_module_status()
    if status.get("pv", "ready") != "ready":
        return render_template("baustelle.html")

    pv_data = get_pv_data()

    return render_template("pv.html", pv=pv_data)

@app.route("/pv/day")
def pv_day():
    curve = get_pv_day_curve()
    return render_template("pv_day.html", curve=curve)


@app.route("/pv/detail")
def pv_detail():
    r = require_user()
    if r:
        return r

    status = load_module_status()
    if status.get("pv", "ready") != "ready":
        return render_template("baustelle.html")

    pv_data = get_pv_data()

    response = render_template("pv.html", pv=pv_data)
    session.clear()
    return response


# ---------------------------------------------------------
# Öffentliche Wetteransicht
# ---------------------------------------------------------

@app.route("/wetter")
def wetter():
    w = get_weather()

    # Falls API fehlschlägt → Crash verhindern
    if not w or "current" not in w:
        return "Wetterdaten konnten nicht geladen werden", 500

    icon = weather_icon(w["current"].get("weathercode"))

    return render_template("wetter.html", w=w, icon=icon)

# ---------------------------------------------------------
# Module Status API
# ---------------------------------------------------------

@app.route("/api/module_status")
def module_status():
    return load_module_status()


@app.route("/api/admin/set_status/<module>/<state>")
def set_status(module, state):
    r = require_admin()
    if r:
        return r

    status = load_module_status()
    status[module] = state

    with open("module_status.json", "w") as f:
        json.dump(status, f, indent=4)

    return redirect("/admin")


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.route('/status')
def status():
    return {
        "status": "ok",
        "users": len(users)
    }


# ---------------------------------------------------------
# Start
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2007)
