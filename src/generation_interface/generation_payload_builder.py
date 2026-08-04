import json
import os

class GenerationPayloadBuilder:
    def build_payload(self):
        files = {
            "scene": "scene_prompt.json",
            "composition": "composition_spec.json",
            "copy": "copy_spec.json"
        }
        
        data = {}
        for key, filename in files.items():
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    data[key] = json.load(f)
            else:
                print(f"Warning: {filename} not found.")
                data[key] = {}

        # Merge into final output
        payload = {
            "scene_prompt": data["scene"].get("scene_prompt", ""),
            "product_position": data["composition"].get("product_position"),
            "person_position": data["composition"].get("person_position"),
            "text_position": data["composition"].get("text_position"),
            "headline": data["copy"].get("headline", ""),
            "subheadline": data["copy"].get("subheadline", ""),
            "cta": data["copy"].get("cta", ""),
            "lighting": data["composition"].get("shadow_type") # linked to lighting
        }

        output_path = "generation_input.json"
        with open(output_path, "w") as f:
            json.dump(payload, f, indent=4)
            
        print(f"Final generation payload saved to {output_path}")
        return payload

if __name__ == "__main__":
    builder = GenerationPayloadBuilder()
    builder.build_payload()
