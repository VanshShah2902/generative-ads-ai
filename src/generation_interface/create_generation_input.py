import json
import os

def create_generation_input(cluster_id):
    # Load required data
    prompt_path = "structured_prompt.json"
    blueprint_v2_path = "data/layout_blueprints_v2.json"
    
    if not os.path.exists(prompt_path) or not os.path.exists(blueprint_v2_path):
        print("Required prompt or blueprint files missing.")
        return

    with open(prompt_path, "r") as f:
        structured_prompt = json.load(f)
    with open(blueprint_v2_path, "r") as f:
        blueprints = json.load(f)
        
    cluster_key = f"cluster_{cluster_id}"
    if cluster_key not in blueprints:
        print(f"Cluster {cluster_id} not found in blueprints.")
        return
        
    blueprint = blueprints[cluster_key]
    
    # Combine into final generation input
    generation_input = {
        "creative_style": blueprint["framework"],
        "layout": blueprint["layout"],
        "scene_prompt": structured_prompt["scene_prompt"],
        "product_position": structured_prompt["product_position"],
        "person_position": structured_prompt["person_position"],
        "text_position": structured_prompt["text_position"],
        "lighting": blueprint["lighting"]
    }
    
    # Save output
    output_path = "generation_input.json"
    with open(output_path, "w") as f:
        json.dump(generation_input, f, indent=4)
        
    print(f"Generation input created: {output_path}")
    return generation_input

if __name__ == "__main__":
    # Example usage for verification (matching the prompt generator's cluster_id)
    create_generation_input(3)
