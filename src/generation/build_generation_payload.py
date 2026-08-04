import json
import os

class GenerationPayloadBuilder:
    def __init__(self, data_dir="data", output_dir="outputs"):
        self.data_dir = data_dir
        self.output_dir = output_dir

    def build_payload(self):
        # 1. Load prompt
        prompt_path = os.path.join(self.output_dir, "final_prompt.txt")
        final_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                final_prompt = f.read().strip()
        
        # 2. Load specs
        specs = {}
        spec_files = {
            "composition": "composition_spec.json",
            "copy": "copy_spec.json",
            "campaign": "campaign_context.json",
            "anchors": "layout_anchors.json"
        }
        
        for key, filename in spec_files.items():
            # some files might be in root, some in data/
            path = filename if os.path.exists(filename) else os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    specs[key] = json.load(f)
            else:
                print(f"Warning: {filename} not found.")
                specs[key] = {}

        # 3. Assemble payload
        payload = {
            "scene_prompt": final_prompt,
            "product_image": specs.get("campaign", {}).get("product_image", "assets/products/product.png"),
            # Placeholder for person image if required by composition
            "person_image": specs.get("campaign", {}).get("person_options", ["assets/person_assets/person.png"])[0],
            
            "layout_anchors": specs.get("anchors", {}), # New Field
            
            "composition": {
                "product_position": specs.get("composition", {}).get("product_position", "center"),
                "person_position": specs.get("composition", {}).get("person_position"),
                "text_position": specs.get("composition", {}).get("text_position", "top")
            },
            
            "copy": specs.get("copy", {}),
            
            "generator_constraints": {
                "do_not_generate_product": True,
                "do_not_generate_person": True,
                "empty_space_for_product": True,
                "empty_space_for_person": True if specs.get("composition", {}).get("person_position") else False,
                "instruction": "The model should generate ONLY the background scene as described in the scene_prompt. Do not include any branded products or human subjects."
            }
        }

        # 4. Save payload
        payload_path = os.path.join(self.data_dir, "generation_payload.json")
        with open(payload_path, "w") as f:
            json.dump(payload, f, indent=4)
            
        print(f"Generation payload saved to {payload_path}")
        return payload

if __name__ == "__main__":
    builder = GenerationPayloadBuilder()
    builder.build_payload()
