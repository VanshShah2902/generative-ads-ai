import json
import os
import random

class CreativeVariationEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.blueprints_path = os.path.join(data_dir, "layout_blueprints_v2.json")
        self.blueprints = self._load_blueprints()

    def _load_blueprints(self):
        if os.path.exists(self.blueprints_path):
            with open(self.blueprints_path, "r") as f:
                return json.load(f)
        return {}

    def generate_variations(self, context_path="data/campaign_context.json"):
        if not os.path.exists(context_path):
            print(f"Campaign context {context_path} not found.")
            return None

        with open(context_path, "r") as f:
            context = json.load(f)

    def generate_variations(self, context_path="data/campaign_context.json"):
        if not os.path.exists(context_path):
            print(f"Campaign context {context_path} not found.")
            return None

        with open(context_path, "r") as f:
            context = json.load(f)

        product_name = context.get("product_name")
        product_category = context.get("product_category")
        person_options = context.get("person_options", [])
        creative_styles = context.get("creative_styles", [])
        num_variations = context.get("num_variations", 20)

        # Map styles to layout clusters from blueprints
        style_map = {}
        for cluster_id, blueprint in self.blueprints.items():
            style = blueprint["framework"]
            if style not in style_map:
                style_map[style] = []
            style_map[style].append(cluster_id)

        variations = []
        for i in range(num_variations):
            style = random.choice(creative_styles)
            clusters = style_map.get(style, list(self.blueprints.keys()))
            cluster = random.choice(clusters)
            
            # Select person based on style requirements (heuristic)
            person = None
            if self.blueprints.get(cluster, {}).get("person_position"):
                person = random.choice(person_options) if person_options else None
            
            var = {
                "variation_id": f"creative_{str(i+1).zfill(3)}",
                "product_name": product_name,
                "product_category": product_category,
                "creative_style": style,
                "layout_cluster": cluster,
                "person_asset": person,
                "target_audience": context.get("target_audience")
            }
            variations.append(var)

        output = {
            "campaign_id": f"{product_name.lower().replace(' ', '_')}_campaign",
            "variations": variations
        }

        output_path = os.path.join(self.data_dir, "campaign_variations.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=4)
        
        print(f"Generated {len(variations)} variations and saved to {output_path}")
        return output

if __name__ == "__main__":
    engine = CreativeVariationEngine()
    engine.generate_variations()
