from flask import Flask, render_template, request, redirect, session
import json
from datetime import datetime, timedelta
from pv_module import get_pv_data
from calendar_module import get_calendar_service
from abfall_module import load_abfall_events, build_month_view
from rezepte_api import search_recipes, get_recipe_details, fallback_recipes
from ics import Calendar
import requests
# calendar_module uses google auth libs; import lazily where needed
# abfall_module has external dependency 'ics'; import lazily in routes


app = Flask(__name__)
app.secret_key = "Rhode_Rhode_rhode_RHode"

with open('users.json', 'r') as f:
    users = json.load(f)

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def load_users():
    with open("users.json", "r") as f:
        return json.load(f)


def get_events_for_user(username):
    users = load_users()
    ics_url = users[username]["ics_url"]

    r = requests.get(ics_url)
    c = Calendar(r.text)

    events = []
    for event in c.events:
        events.append({
            "name": event.name,
            "start": event.begin.datetime.isoformat(),
            "end": event.end.datetime.isoformat()
        })
    return events



@app.route("/api/events/<username>")
def api_events(username):
    return get_events_for_user(username)


@app.context_processor
def inject_modules():
    # Ensure `modules` is always available in templates to avoid Jinja errors
    if "pin" in session and session["pin"] in users:
        return {"modules": users[session["pin"]].get("modules", {})}
    return {"modules": {}}

@app.route("/")
def index():
    if "user" in session:
        return redirect("/dashboard")
    else:
        return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pin = request.form["pin"]

        if pin in users:
            session["pin"] = pin
            session["user"] = users[pin]["name"]
            session["calendar_id"] = users[pin]["calendar_id"]
            session["role"] = users[pin]["role"]
            session["email"] = users[pin]["email"]
            if users[pin]["role"] == "admin":
                session["is_admin"] = True
                return redirect("/admin")
            elif users[pin].get("first_login", True):
                return redirect("/setup")
            else:
                session["is_admin"] = False
                return redirect("/dashboard")
        else:
            return render_template("login.html", error="Falsche PIN")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    pin = session["pin"]          # WICHTIG!
    modules = users[pin].get("modules", {
        "calendar": False,
        "recipes": False,
        "pv": False,
        "alexa": False,
        "abfall": False,
        "weather": False,
        "pin": pin
    })

    from wetter_module import get_weather_widget, weather_icon
    from regenradar_module import get_radar_url
    from pv_module import get_pv_data

    w = get_weather_widget()
    icon = weather_icon(w["code"])
    radar = get_radar_url()
    pv = get_pv_data()

    return render_template(
        "dashboard.html",
        modules=modules,
        weather=w,
        weather_icon=icon,
        radar=radar,
        pv=pv,
        pin=pin
    )



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/admin")
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    return render_template("admin.html", users=users)

@app.route("/admin/add_user", methods=["POST"])
def add_user():
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    name = request.form["name"]
    pin = request.form["pin"]
    calendar_id = request.form["calendar_id"]
    role = request.form["role"]
    email = request.form["email"]
    ics_url = request.form["ics_url"]

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
            "weather": False
        },
        "abfall_ics": "https://www.awb-warendorf.de/abfuhrkalender/kalender.ics?oid=10457",
        "shopping_shared": True,
        "ics_url": ics_url
    }

    save_users()
    return redirect("/admin")

@app.route("/admin/delete_user/<pin>", methods=["POST"])
def delete_user(pin):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    if pin in users:
        del users[pin]
        save_users()

    return redirect("/admin")

@app.route("/admin/block_user/<pin>", methods=["GET", "POST"])
def block_user(pin):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    if pin in users:
        users[pin]["blocked"] = True
        save_users()

    return redirect("/admin")

@app.route("/admin/unblock_user/<pin>", methods=["GET", "POST"])
def unblock_user(pin):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    if pin in users:
        users[pin]["blocked"] = False
        save_users()

    return redirect("/admin")

@app.route("/admin/edit_user/<pin>", methods=["GET", "POST"])
def edit_user(pin):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        calendar_id = request.form["calendar_id"]
        role = request.form["role"]
        email = request.form["email"]

        if pin in users:
            users[pin].update({
                "name": name,
                "calendar_id": calendar_id,
                "role": role,
                "email": email
            })
        else:
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
                    "weather": False
                },
                "abfall_ics": "https://www.kreis-warendorf.de/abfallkalender/kalender.ics?oid=10457",
                "shopping_shared": True
            }

        save_users()
        return redirect("/admin")

    user = users.get(pin)
    if user:
        return render_template("edit_user.html", pin=pin, user=user)
    else:
        return redirect("/admin")

@app.route("/admin/reset_modules/<pin>", methods=["POST"])
def reset_modules(pin):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    users[pin]["modules"] = {
        "calendar": False,
        "recipes": False,
        "pv": False,
        "alexa": False
    }

    users[pin]["first_login"] = True
    save_users()

    return redirect("/admin")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if "user" not in session:
        return redirect("/login")

    pin = session["pin"]

    if request.method == "GET":
        return render_template("setup.html", user=users[pin])

    if request.method == "POST":
        users[pin].setdefault("modules", {
            "calendar": False,
            "recipes": False,
            "pv": False,
            "alexa": False,
            "abfall": False,
            "weather": False
        })

        users[pin]["modules"]["calendar"] = "calendar" in request.form
        users[pin]["modules"]["recipes"] = "recipes" in request.form
        users[pin]["modules"]["pv"] = "pv" in request.form
        users[pin]["modules"]["alexa"] = "alexa" in request.form
        users[pin]["modules"]["abfall"] = "abfall" in request.form
        users[pin]["modules"]["recipes"] = "recipes" in request.form
        users[pin]["modules"]["weather"] = "weather" in request.form



        users[pin]["first_login"] = False

        save_users()

        return redirect("/dashboard")

@app.route("/calendar_ui")
def calendar_ui():
    if "user" not in session:
        return redirect("/login")

    username = session["pin"]
    events = get_events_for_user(username)

    return render_template("calendar_ui.html", events=events)




@app.route("/abfall")
def abfall():
    events = load_abfall_events()
    return render_template("abfall.html", events=events)

@app.route("/abfall_monat")
def abfall_monat():
    if "user" not in session:
        return redirect("/login")

    # Lokale JSON laden – KEINE ICS-URL mehr
    events = load_abfall_events()

    now = datetime.now()
    year = now.year
    month = now.month

    # Monatsansicht erzeugen
    month_view = build_month_view(events, year, month)

    modules = users[session["pin"]].get("modules", {})

    return render_template(
        "abfall_monat.html",
        month_view=month_view,
        year=year,
        month=month,
        modules=modules
    )

@app.route("/rezepte/search")
def rezepte_search():
    query = request.args.get("q", "")
    recipes = search_recipes(query)
    return render_template("rezepte_search.html", recipes=recipes, query=query)

@app.route("/rezepte/<int:recipe_id>/cook")
def rezepte_cook(recipe_id):
    recipe = get_recipe_details(recipe_id)
    return render_template("rezepte_cook.html", recipe=recipe)



@app.route("/rezepte/view_api/<rid>")
def rezepte_view_api(rid):
    from rezepte_api import get_recipe_details
    recipe = get_recipe_details(rid)

    return render_template("rezepte_view_api.html", recipe=recipe, rid=rid)

@app.route("/rezepte/<int:recipe_id>")
def rezepte_detail(recipe_id):
    recipe = get_recipe_details(recipe_id)
    return render_template("rezepte_detail.html", recipe=recipe)

@app.route("/einkaufsliste/add_from_api/<rid>")
def einkaufsliste_add_from_api(rid):
    from rezepte_api import get_recipe_details
    from einkaufsliste_module import add_items

    recipe = get_recipe_details(rid)
    add_items(recipe["ingredients"])

    return redirect("/einkaufsliste")

@app.route("/api/shopping")
def api_shopping():
    from einkaufsliste_module import load_list
    return load_list()

@app.route("/api/shopping/add", methods=["POST"])
def api_shopping_add():
    from einkaufsliste_module import add_item
    add_item(request.form["name"])
    return {"status": "ok"}

@app.route("/api/shopping/toggle", methods=["POST"])
def api_shopping_toggle():
    from einkaufsliste_module import toggle_item
    toggle_item(int(request.form["index"]))
    return {"status": "ok"}

@app.route("/api/shopping/delete", methods=["POST"])
def api_shopping_delete():
    from einkaufsliste_module import delete_item
    delete_item(int(request.form["index"]))
    return {"status": "ok"}


@app.route("/wetter")
def wetter():
    from wetter_module import get_weather, weather_icon
    w = get_weather()
    icon = weather_icon(w["code"])

    return render_template("wetter.html", w=w, icon=icon)

@app.route("/zug")
def zug():
    from zug_module import filter_trains, delay_color
    trains = filter_trains()

    # Farben hinzufügen
    for t in trains:
        t["color"] = delay_color(t.get("delay"))

    return render_template("zug.html", trains=trains)

@app.route("/pv")
def pv():
    from pv_module import get_pv_data
    pv = get_pv_data()
    return render_template("pv.html", pv=pv)


@app.route('/status')
def status():
    # Lightweight health endpoint
    return {
        "status": "ok",
        "users": len(users)
    }


if __name__ == "__main__":
    app.run(host="0.0.0", port=5000)