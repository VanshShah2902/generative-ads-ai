import json
import os
import random

def generate_campaign_batch():
    schema_path = "data/campaign_schema.json"
    blueprints_path = "data/layout_blueprints_v2.json"
    
    if not os.path.exists(schema_path) or not os.path.exists(blueprints_path):
        print("Required campaign schema or blueprints file missing.")
        return

    with open(schema_path, "r") as f:
        schema = json.load(f)
    with open(blueprints_path, "r") as f:
        blueprints = json.load(f)

    variations = []
    styles = schema.get("creative_styles", [])
    persons = schema.get("person_options", [])
    num_to_gen = schema.get("num_variations", 5)
    
    # Map styles to clusters
    style_to_clusters = {}
    for cluster_id, blueprint in blueprints.items():
        style = blueprint["framework"]
        if style not in style_to_clusters:
            style_to_clusters[style] = []
        style_to_clusters[style].append(cluster_id)

    count = 0
    # Iterate through styles and persons to create combinations
    for style in styles:
        possible_clusters = style_to_clusters.get(style, [])
        if not possible_clusters:
            continue
            
        for person in persons:
            # Match person requirements with frameworks
            # Custom logic: doctor framework prefers doctor person; products/ingredients often have no person
            if style == "doctor_first" and person["type"] != "doctor":
                continue
                
            for cluster_id in possible_clusters:
                if count >= num_to_gen:
                    break
                    
                v_id = f"creative_{str(count + 1).zfill(3)}"
                variation = {
                    "variation_id": v_id,
                    "product_name": schema["product"]["name"],
                    "product_category": schema["product"]["category"],
                    "target_audience": schema["target_audience"],
                    "person_image": person["image"],
                    "person_type": person["type"],
                    "creative_style": style,
                    "layout_cluster": cluster_id
                }
                variations.append(variation)
                count += 1
                
        if count >= num_to_gen:
            break

    campaign_output = {
        "campaign_id": f"{schema['product']['name'].lower().replace(' ', '_')}_campaign",
        "variations": variations
    }

    output_path = "data/campaign_variations.json"
    with open(output_path, "w") as f:
        json.dump(campaign_output, f, indent=4)
        
    print(f"Generated {len(variations)} variations in {output_path}")
    return campaign_output

if __name__ == "__main__":
    generate_campaign_batch()
