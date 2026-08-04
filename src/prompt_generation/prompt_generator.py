import json
import os

def generate_prompt_from_variation(variation):
    """
    Step 5: Connect with Prompt Generator using a variation object.
    """
    cluster_id = variation["layout_cluster"].replace("cluster_", "")
    product_name = variation["product_name"]
    product_category = variation["product_category"]
    target_audience = variation["target_audience"]
    
    # Pass along person type for better prompt context if needed
    person_type = variation.get("person_type", "person")
    
    return generate_prompt(cluster_id, product_name, product_category, target_audience)

def generate_prompt(cluster_id, product_name, product_category, target_audience):
    # Load requirements
    blueprint_path = "data/layout_blueprints_v2.json"
    frameworks_path = "data/creative_frameworks.json"
    
    if not os.path.exists(blueprint_path) or not os.path.exists(frameworks_path):
        print("Required config files missing in data/ folder.")
        return

    with open(blueprint_path, "r") as f:
        blueprints = json.load(f)
    with open(frameworks_path, "r") as f:
        frameworks = json.load(f)
        
    cluster_key = f"cluster_{cluster_id}"
    if cluster_key not in blueprints:
        print(f"Cluster {cluster_id} not found in blueprints.")
        return
        
    blueprint = blueprints[cluster_key]
    framework_name = blueprint["framework"]
    framework = frameworks[framework_name]
    
    # Generate scene prompt
    lighting = blueprint["lighting"]
    scene_type = blueprint["scene_type"]
    
    # Heuristic for placement
    placement_note = f"empty space on {blueprint['product_position']} for product placement"
    if blueprint["person_position"]:
        placement_note += f", person placed on {blueprint['person_position']}"
        
    scene_prompt = f"clean premium {scene_type} interior with {lighting} lighting, advertising photography style, {placement_note}"
    
    output = {
        "scene_prompt": scene_prompt,
        "person_required": framework["person_required"],
        "product_position": blueprint["product_position"],
        "person_position": blueprint["person_position"],
        "text_position": blueprint["text_position"]
    }
    
    # Save to file (Base generation for backward compatibility)
    output_path = "structured_prompt.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4)
        
    # print(f"Structured prompt generated: {output_path}")
    return output

if __name__ == "__main__":
    # Example usage for verification
    generate_prompt(3, "Ashwagandha Extract", "Health Supplement", "Busy Professionals")
