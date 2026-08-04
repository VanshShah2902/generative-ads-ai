import json
import os

def build_frameworks():
    frameworks = {
        "product_first": {
            "focus": "product",
            "person_required": False,
            "ingredient_required": False,
            "product_scale": "large",
            "text_priority": "medium"
        },
        "ingredients_first": {
            "focus": "ingredients",
            "person_required": False,
            "ingredient_required": True,
            "product_scale": "medium",
            "text_priority": "low"
        },
        "solution_first": {
            "focus": "problem_solution",
            "person_required": True,
            "ingredient_required": False,
            "product_scale": "medium",
            "text_priority": "high"
        },
        "doctor_first": {
            "focus": "authority_trust",
            "person_required": True,
            "ingredient_required": False,
            "product_scale": "medium",
            "text_priority": "medium"
        }
    }
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    output_path = "data/creative_frameworks.json"
    with open(output_path, "w") as f:
        json.dump(frameworks, f, indent=4)
    
    print(f"Creative frameworks saved to {output_path}")

if __name__ == "__main__":
    build_frameworks()
