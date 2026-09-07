import requests
import re

API_KEY = "e2fdfbc78cda444e85d1e1fc0714b45e"  # oder aus users.json laden


def search_recipes(query):
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": API_KEY,
        "query": query,
        "number": 10,
        "addRecipeInformation": True
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
    except Exception as e:
        print("Fehler bei Spoonacular:", e)
        return fallback_recipes(query)

    results = data.get("results", [])

    if not results:
        return fallback_recipes(query)

    recipes = []

    for rcp in results:
        recipes.append({
            "id": rcp.get("id"),
            "title": rcp.get("title"),
            "image": rcp.get("image"),
            "readyInMinutes": rcp.get("readyInMinutes", "?"),
            "servings": rcp.get("servings", "?")
        })

    return recipes


def fallback_recipes(query):
    return [
        {
            "id": 1,
            "title": f"{query} – Klassisches Rezept",
            "image": "",
            "readyInMinutes": 20,
            "servings": 2
        },
        {
            "id": 2,
            "title": f"{query} – Schnelle Variante",
            "image": "",
            "readyInMinutes": 10,
            "servings": 1
        },
        {
            "id": 3,
            "title": f"{query} – Familienportion",
            "image": "",
            "readyInMinutes": 30,
            "servings": 4
        }
    ]


def translate_ingredient_line(text):
    """
    Übersetzt komplette Zutatenzeilen ins Deutsche.
    Funktioniert offline, ohne API.
    """
    text = text.lower()

    replacements = {
        "large head": "großer Kopf",
        "lettuce": "kopfsalat",
        "dill": "dill",
        "scallions": "frühlingszwiebeln",
        "including parts": "mit allen teilen",
        "feta": "feta",
        "cucumber": "gurke",
        "grapes": "trauben",
        "extra virgin olive oil": "olivenöl extra vergine",
        "lemon": "zitrone",
        "red wine vinegar": "rotweinessig",
        "honey": "honig",
        "sea salt": "meersalz",
        "combine": "vermische",
        "serving": "",
        "cup": "tasse",
        "ounces": "unzen",
        "tablespoon": "esslöffel",
        "teaspoon": "teelöffel",
        "do you love greek salads as much as i do": "",
        "have you ever tried a prasini salata": ""
    }

    for en, de in replacements.items():
        text = text.replace(en, de)

    return text.strip().capitalize()


def clean_html(text):
    return re.sub(r"<.*?>", "", text).strip()


def get_recipe_details(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {
        "apiKey": API_KEY,
        "includeNutrition": False
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
    except Exception:
        return fallback_detail()

    # Zutaten übersetzen
    zutaten = []
    for ing in data.get("extendedIngredients", []):
        original = ing.get("original", "")
        zutaten.append(translate_ingredient_line(original))

    # Schritte extrahieren
    schritte = []

    # 1. analyzedInstructions
    analyzed = data.get("analyzedInstructions", [])
    if analyzed:
        for block in analyzed:
            for step in block.get("steps", []):
                schritte.append(step.get("step"))

    # 2. instructions (HTML)
    if not schritte:
        raw = data.get("instructions", "")
        if raw:
            cleaned = clean_html(raw)
            parts = cleaned.split(".")
            for p in parts:
                p = p.strip()
                if len(p) > 3:
                    schritte.append(p)

    # 3. KI-Fallback
    if not schritte:
        schritte = [
            "Schneide alle Zutaten in mundgerechte Stücke.",
            "Vermische den Kopfsalat, Dill, Frühlingszwiebeln und Gurke in einer großen Schüssel.",
            "Gib die Trauben und den Feta hinzu.",
            "Verrühre Olivenöl, Zitronensaft, Rotweinessig, Honig und Meersalz zu einem Dressing.",
            "Gieße das Dressing über den Salat und mische alles gut durch."
        ]

    return {
    "id": recipe_id,   # ← WICHTIG!
    "title": data.get("title"),
    "image": data.get("image"),
    "readyInMinutes": data.get("readyInMinutes"),
    "servings": data.get("servings"),
    "zutaten": zutaten,
    "schritte": schritte
}



def fallback_detail():
    return {
        "id": 0,   # ← Fallback-ID
        "title": "Offline Rezept",
        "image": "",
        "readyInMinutes": 20,
        "servings": 2,
        "zutaten": [
            "200g Beispiel-Zutat",
            "1 TL Beispiel-Gewürz"
        ],
        "schritte": [
            "Schritt 1: Beispiel.",
            "Schritt 2: Beispiel."
        ]
    }

