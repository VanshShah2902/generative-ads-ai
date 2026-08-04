"""
Helper functions for JSON handling and payload validation.
"""
import json

def load_json(path: str) -> dict:
    """Loads a JSON file into a dictionary."""
    with open(path, "r") as f:
        return json.load(f)

def save_json(data: dict, path: str):
    """Saves a dictionary to a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def validate_payload(payload: dict) -> bool:
    """Validates if the payload contains all required fields."""
    required = ["scene_prompt", "layout_cluster", "headline"]
    return all(field in payload for field in required)
