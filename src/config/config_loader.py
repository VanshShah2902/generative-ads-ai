import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def load_json(file_name):
    path = os.path.join(BASE_DIR, "config", file_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_fonts():
    return load_json("fonts.json")

def load_emotions():
    return load_json("emotions.json")

def load_prompts():
    return load_json("prompts.json")

def load_ingredient_benefits():
    return load_json("ingredient_benefits.json")
