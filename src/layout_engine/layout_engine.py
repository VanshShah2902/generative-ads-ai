import json
import os

class LayoutEngine:
    def __init__(self, blueprint_v2_path="data/layout_blueprints_v2.json"):
        self.blueprint_v2_path = blueprint_v2_path
        self.blueprints = self._load_blueprints()

    def _load_blueprints(self):
        if os.path.exists(self.blueprint_v2_path):
            with open(self.blueprint_v2_path, "r") as f:
                return json.load(f)
        return {}

    def generate_spec(self, cluster_id):
        cluster_key = f"cluster_{cluster_id}"
        if cluster_key not in self.blueprints:
            print(f"Cluster {cluster_id} not found.")
            return None

        blueprint = self.blueprints[cluster_key]
        
        layout_spec = {
            "layout": blueprint["layout"],
            "product_position": blueprint["product_position"],
            "person_position": blueprint["person_position"],
            "text_position": blueprint["text_position"],
            "camera_angle": "eye_level", # Default or derived from layout name
            "composition_style": "rule_of_thirds" if "focus" in blueprint["layout"] else "centered",
            "lighting": blueprint["lighting"]
        }

        # Save output
        output_path = "layout_spec.json"
        with open(output_path, "w") as f:
            json.dump(layout_spec, f, indent=4)
            
        print(f"Layout spec saved to {output_path}")
        return layout_spec

if __name__ == "__main__":
    engine = LayoutEngine()
    # Example usage
    engine.generate_spec(3)
