import json
import os

class LayoutAnchorEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.layout_spec_path = os.path.join(data_dir, "../layout_spec.json") # usually in root or data

    def generate_anchors(self):
        # Load layout spec
        spec_path = "layout_spec.json"
        if not os.path.exists(spec_path):
            spec_path = os.path.join(self.data_dir, "layout_spec.json")
            
        if not os.path.exists(spec_path):
            print("Layout spec not found.")
            return None

        with open(spec_path, "r") as f:
            layout_spec = json.load(f)

        layout_type = layout_spec.get("layout", "default")
        
        # Define anchors based on layout type
        anchors = {}
        
        if layout_type == "doctor_recommendation":
            anchors = {
                "headline_anchor": {"position": "top_center", "hint": "clear empty top center region for headline text"},
                "person_anchor": {"position": "left_center", "hint": "empty space on left reserved for doctor placement"},
                "product_anchor": {"position": "right_center", "hint": "empty space on right reserved for product placement"},
                "cta_anchor": {"position": "bottom_right", "hint": "clean bottom right space reserved for CTA button"},
                "logo_anchor": {"position": "top_left", "hint": "small space in top left for brand logo"}
            }
        elif layout_type == "product_showcase":
            anchors = {
                "headline_anchor": {"position": "top_center", "hint": "clear top area for product name"},
                "product_anchor": {"position": "center", "hint": "centered dramatic empty space for product hero shot"},
                "cta_anchor": {"position": "bottom_center", "hint": "bottom center reserved for call to action"},
                "logo_anchor": {"position": "bottom_left", "hint": "bottom left corner for logo"}
            }
        elif layout_type == "ingredient_focus":
             anchors = {
                "headline_anchor": {"position": "top_left", "hint": "top left region for ingredient benefits text"},
                "product_anchor": {"position": "right_center", "hint": "empty space on right for product bottle"},
                "cta_anchor": {"position": "bottom_left", "hint": "bottom left space for purchase button"},
                "logo_anchor": {"position": "top_right", "hint": "top right corner for brand logo"}
            }
        else: # Default fallback
            anchors = {
                "headline_anchor": {"position": "top_center", "hint": "clear top region for text"},
                "product_anchor": {"position": "center", "hint": "centered space for product"},
                "cta_anchor": {"position": "bottom_center", "hint": "bottom reserved for button"}
            }

        output = {
            "layout_type": layout_type,
            "anchors": anchors
        }

        output_path = os.path.join(self.data_dir, "layout_anchors.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=4)
            
        print(f"Layout anchors generated and saved to {output_path}")
        return output

if __name__ == "__main__":
    engine = LayoutAnchorEngine()
    engine.generate_anchors()
