import json
import os

class CompositionSpecGenerator:
    def generate_spec(self, layout_spec_path="layout_spec.json"):
        if not os.path.exists(layout_spec_path):
            print("Layout spec file missing.")
            return None

        with open(layout_spec_path, "r") as f:
            layout = json.load(f)

        comp_spec = {
            "product_position": layout["product_position"],
            "person_position": layout["person_position"],
            "text_position": layout["text_position"],
            "shadow_type": "soft" if "soft" in layout["lighting"].lower() else "defined",
            "perspective": layout["camera_angle"]
        }

        output_path = "composition_spec.json"
        with open(output_path, "w") as f:
            json.dump(comp_spec, f, indent=4)
            
        print(f"Composition spec saved to {output_path}")
        return comp_spec

if __name__ == "__main__":
    gen = CompositionSpecGenerator()
    gen.generate_spec()
