import json
import os
import pandas as pd

def upgrade_blueprints():
    # Load cluster data
    summary_path = "Imported_things/cluster_summary.csv"
    desc_path = "Imported_things/cluster_descriptions.csv"
    
    if not os.path.exists(summary_path) or not os.path.exists(desc_path):
        print("Required cluster data files not found.")
        return

    # User provided examples for cluster 0 and 3
    # Mapping for all clusters detected (0-5)
    blueprints = {
        "cluster_0": {
            "layout": "product_showcase",
            "framework": "product_first",
            "person_position": None,
            "product_position": "center",
            "text_position": "top",
            "scene_type": "studio",
            "lighting": "dramatic"
        },
        "cluster_1": {
            "layout": "educational_layout",
            "framework": "solution_first",
            "person_position": "right",
            "product_position": "center",
            "text_position": "left",
            "scene_type": "modern office",
            "lighting": "natural"
        },
        "cluster_2": {
            "layout": "promotional_grid",
            "framework": "solution_first",
            "person_position": "center",
            "product_position": "bottom",
            "text_position": "top",
            "scene_type": "urban setting",
            "lighting": "vibrant"
        },
        "cluster_3": {
            "layout": "doctor_recommendation",
            "framework": "doctor_first",
            "person_position": "left",
            "product_position": "right",
            "text_position": "top",
            "scene_type": "medical clinic",
            "lighting": "soft daylight"
        },
        "cluster_4": {
            "layout": "problem_solution_split",
            "framework": "solution_first",
            "person_position": "left",
            "product_position": "center",
            "text_position": "bottom",
            "scene_type": "home interior",
            "lighting": "warm"
        },
        "cluster_5": {
            "layout": "ingredient_focus",
            "framework": "ingredients_first",
            "person_position": None,
            "product_position": "right",
            "text_position": "left",
            "scene_type": "nature herb garden",
            "lighting": "bright sunshine"
        }
    }
    
    # Save to data directory
    os.makedirs("data", exist_ok=True)
    output_path = "data/layout_blueprints_v2.json"
    
    with open(output_path, "w") as f:
        json.dump(blueprints, f, indent=4)
    
    print(f"Upgraded blueprints saved to {output_path}")

if __name__ == "__main__":
    upgrade_blueprints()
