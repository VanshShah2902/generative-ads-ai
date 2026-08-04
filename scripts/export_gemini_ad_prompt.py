import os
import json
import pandas as pd
import sys

def get_competitor_strategy(data_dir="Imported_things"):
    """
    Reads competitor intelligence files and determines the dominant layout strategy.
    """
    summary_path = os.path.join(data_dir, "cluster_summary.csv")
    desc_path = os.path.join(data_dir, "cluster_descriptions.csv")
    
    if not os.path.exists(summary_path) or not os.path.exists(desc_path):
        print(f"Warning: Competitor data not found in {data_dir}. Using defaults.")
        return {
            "cluster_id": 3,
            "description": "Bright product-focused creatives with minimal text",
            "ingredient_emphasis": False
        }

    # Load Data
    summary_df = pd.read_csv(summary_path)
    desc_df = pd.read_csv(desc_path)

    # 1. Determine dominant cluster (highest ads_count)
    dominant_cluster_row = summary_df.loc[summary_df['ads_count'].idxmax()]
    cluster_id = int(dominant_cluster_row['cluster'])
    
    # 2. Get Description
    description_row = desc_df[desc_df['cluster'] == cluster_id]
    description = description_row.iloc[0]['description'] if not description_row.empty else "Standard professional layout"

    # 3. Analyze Intensity
    # If text density is high (>0.2) or cluster description mentions text, adjust emphasis
    text_density = dominant_cluster_row.get('avg_text_density', 0.15)
    
    # Special Case: Cluster 0 and 5 often emphasize ingredients or lifestyles
    ingredient_emphasis = cluster_id in [0, 5]

    return {
        "cluster_id": cluster_id,
        "description": description,
        "ingredient_emphasis": ingredient_emphasis,
        "text_density": text_density
    }

def generate_gemini_ad_prompt(input_path="inputs/campaigns/arjuna_tea.json"):
    """
    Generates a structured Gemini ad prompt based on campaign data and competitor intelligence.
    """
    if not os.path.exists(input_path):
        alternate_path = "inputs/campaigns/campaign_input.json"
        if os.path.exists(alternate_path):
            input_path = alternate_path
        else:
            print(f"Error: Campaign input not found at {input_path}")
            return

    # 1. Load Campaign Data
    with open(input_path, "r") as f:
        data = json.load(f)

    product_name = data.get("product_name", "the product")
    product_cat = data.get("product_category", "supplement")
    benefits = data.get("benefits", [])
    ingredients = data.get("ingredients", [])
    creative_style = data.get("creative_style", "doctor_endorsement")

    # 2. Get Competitor Intelligence
    strategy = get_competitor_strategy()
    cluster_id = strategy["cluster_id"]
    cluster_desc = strategy["description"]

    # 3. Environment & Placement Logic
    if "doctor" in creative_style or cluster_id == 5:
        environment = "A bright modern wellness clinic consultation room with a sleek wooden desk, indoor plants, and framed medical certificates on a clean white wall."
        doctor_placement = "Use the uploaded doctor image as a trusted medical expert standing on the LEFT side of the frame. The doctor should occupy a dominant area, looking professional and welcoming."
        product_placement = f"Use the uploaded product image placed on the RIGHT side on the desk. Position the {product_name} packaging prominently, like a professional product shoot."
    else:
        environment = "A premium minimalist studio setting with soft architectural shadows, a stone plinth, and organic textures."
        doctor_placement = "N/A - Focus on product hero shot."
        product_placement = f"Use the uploaded product image as the central hero, placed on a stone plinth in the middle of a high-end minimalist studio environment."

    # 4. Ingredient Decor
    ingredient_decor = ""
    if strategy["ingredient_emphasis"] or "ingredients" in creative_style:
        if ingredients:
            ingredient_decor = f"Place natural herbal ingredients like {', '.join(ingredients[:3])} aesthetically around the product for a natural, authentic feel."
        else:
            ingredient_decor = "Decorate the scene with high-quality organic textures and subtle herbal elements to emphasize natural wellness."
    else:
        ingredient_decor = "Keep the composition clean and focused on the primary product hero shot."

    # 5. Benefit Visuals
    benefit_bullets = "\n".join([f"• {b}" for b in benefits[:4]])
    benefit_visuals = f"Clearly display the following benefits in a clean, vertical typographic layout:\n{benefit_bullets}"

    # 6. Final Prompt Composition
    prompt = f"""
Create a professional commercial advertisement for {product_name} ({product_cat}). 
Follow the visual patterns of dominant competitor layout (Cluster {cluster_id}: {cluster_desc}).

---

ENVIRONMENT
"{environment}"

DOCTOR PLACEMENT
"{doctor_placement}"

PRODUCT PLACEMENT
"{product_placement}"

INGREDIENT DECOR
"{ingredient_decor}"

BENEFIT VISUALS
"{benefit_visuals}"

HEADLINE SPACE
"Leave empty space at the TOP of the frame for a large, bold marketing headline text."

CAMERA STYLE
"Eye level hero shot, shallow depth of field, sharp focus on the product."

QUALITY
"Ultra realistic commercial advertising photography, professional product shoot, 8k resolution, cinematic lighting."

---

INSTRUCTION FOR GEMINI:
Generate a full advertisement scene by compositing the uploaded doctor and product images according to the spatial rules above. Maintain a high-end, premium aesthetic throughout.
"""

    # 7. Output Result
    print("\n" + "="*50)
    print("STRUCTURED GEMINI AD PROMPT (Competitor Aware)")
    print("="*50)
    print(prompt.strip())
    print("="*50 + "\n")

    # Save to file
    output_path = "outputs/gemini_ad_prompt.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt.strip())

    print(f"Final Gemini ad prompt saved to: {output_path}")

if __name__ == "__main__":
    target_input = "inputs/campaigns/arjuna_tea.json"
    if len(sys.argv) > 1:
        target_input = sys.argv[1]
    
    generate_gemini_ad_prompt(target_input)
