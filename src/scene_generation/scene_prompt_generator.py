import json
import os

class ScenePromptGenerator:
    def generate_prompt(self, layout_spec_path="layout_spec.json", strategy_path="creative_strategy.json"):
        if not os.path.exists(layout_spec_path) or not os.path.exists(strategy_path):
            print("Layout spec or strategy file missing.")
            return None

        with open(layout_spec_path, "r") as f:
            layout = json.load(f)
        with open(strategy_path, "r") as f:
            strategy = json.load(f)

        # Build prompt logic from blueprint plus strategy focus
        lighting = layout["lighting"]
        scene_base = "premium photography style, advertising editorial"
        
        # Placeholder mapping for scene types based on layout or strategy
        scene_type = "studio setting"
        if strategy["strategy"] == "doctor_first":
            scene_type = "medical clinic interior"
        elif strategy["strategy"] == "ingredients_first":
            scene_type = "nature herb garden or clean laboratory"
        elif strategy["strategy"] == "solution_first":
            scene_type = "clean home interior"

        # Reserve empty spaces
        placement_rules = []
        if layout["product_position"]:
            placement_rules.append(f"empty space on {layout['product_position']} reserved for product placement")
        if layout["person_position"]:
            placement_rules.append(f"empty space on {layout['person_position']} reserved for person placement")
            
        scene_prompt = f"{scene_type}, {lighting} lighting, {scene_base}, {', '.join(placement_rules)}"
        
        output = {
            "scene_prompt": scene_prompt
        }

        output_path = "scene_prompt.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=4)
            
        print(f"Scene prompt saved to {output_path}")
        return output

if __name__ == "__main__":
    gen = ScenePromptGenerator()
    gen.generate_prompt()
