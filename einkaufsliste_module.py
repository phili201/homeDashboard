import json

def load_list():
    try:
        with open("shopping.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_list(lst):
    with open("shopping.json", "w") as f:
        json.dump(lst, f, indent=4)

def add_item(name):
    lst = load_list()
    lst.append({"name": name, "done": False})
    save_list(lst)

def toggle_item(index):
    lst = load_list()
    lst[index]["done"] = not lst[index]["done"]
    save_list(lst)

def delete_item(index):
    lst = load_list()
    lst.pop(index)
    save_list(lst)

def add_items(items):
    lst = load_list()
    for i in items:
        lst.append({"name": i, "done": False})
    save_list(lst)
