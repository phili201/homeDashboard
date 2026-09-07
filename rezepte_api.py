import requests
import json

def get_api_key():
    with open("spoonacular.json", "r") as f:
        return json.load(f)["api_key"]

def search_recipes(query):
    api_key = get_api_key()
    url = f"https://api.spoonacular.com/recipes/complexSearch?query={query}&number=20&addRecipeInformation=true&apiKey={api_key}"
    try:
        r = requests.get(url, timeout=6)
        data = r.json()
    except Exception:
        return []

    results = []
    for item in data.get("results", []):
        results.append({
            "id": item.get("id"),
            "title": item.get("title", "-"),
            "image": item.get("image", ""),
            "readyInMinutes": item.get("readyInMinutes", "?"),
            "servings": item.get("servings", "?"),
        })

    return results


def get_recipe_details(recipe_id):
    api_key = get_api_key()
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?apiKey={api_key}"
    try:
        r = requests.get(url, timeout=6)
        data = r.json()
    except Exception:
        return {
            "title": "Nicht verfügbar",
            "image": "",
            "ingredients": [],
            "steps": [],
            "readyInMinutes": "?",
            "servings": "?"
        }

    ingredients = []
    for ing in data.get("extendedIngredients", []):
        ingredients.append(f"{ing.get('amount','')} {ing.get('unit','')} {ing.get('name','')}")

    steps = []
    if data.get("analyzedInstructions"):
        for step in data["analyzedInstructions"][0].get("steps", []):
            steps.append(step.get("step", ""))

    return {
        "title": data.get("title", "-"),
        "image": data.get("image", ""),
        "ingredients": ingredients,
        "steps": steps,
        "readyInMinutes": data.get("readyInMinutes", "?"),
        "servings": data.get("servings", "?")
    }
