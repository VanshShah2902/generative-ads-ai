import os
import json
import sys

def generate_gemini_prompt(input_path="inputs/campaigns/arjuna_tea.json"):
    """
    Generates a Gemini-specific image generation prompt based on campaign inputs.
    """
    if not os.path.exists(input_path):
        # Fallback to campaign_input.json if requested specifically in the prompt but arjuna is my working file
        alternate_path = "inputs/campaigns/campaign_input.json"
        if os.path.exists(alternate_path):
            input_path = alternate_path
        else:
            print(f"Error: Campaign input not found at {input_path}")
            return

    # 1. Load Campaign Input
    with open(input_path, "r") as f:
        data = json.load(f)

    product_name = data.get("product_name", "the product")
    product_cat = data.get("product_category", "product")
    style = data.get("creative_style", "product_showcase")
    
    # 2. Map Style to Prompt Components
    if style == "doctor_endorsement":
        environment = "modern medical clinic consultation room with wooden desk, framed medical certificates and indoor plants"
        lighting = "soft natural daylight with studio lighting"
        composition = (
            "place the uploaded doctor image on the LEFT side of the frame and "
            "the uploaded product image on the RIGHT side on the desk. "
            "Leave space at the TOP for headline text."
        )
    elif style == "product_showcase":
        environment = "premium studio setting with minimalist aesthetic, clean marble surface, and blurred architectural background"
        lighting = "dramatic rim lighting with soft fill light, high-end commercial style"
        composition = (
            "place the uploaded product image in the CENTER of the frame on the marble surface. "
            "Ensure the product is the hero of the shot. "
            "Leave space at the TOP and BOTTOM for marketing copy."
        )
    elif style == "benefits_grid":
        environment = "bright wellness spa interior with organic textures, wooden elements, and soft nature accents"
        lighting = "warm natural golden hour sunlight"
        composition = (
            "place the uploaded product image on the RIGHT side. "
            "Leave the LEFT side of the frame as a clean, solid-colored negative space for a benefits grid. "
            "Leave space at the TOP for the main headline."
        )
    else:
        environment = f"clean professional setting matching {product_cat} category"
        lighting = "balanced studio lighting"
        composition = "place the uploaded product image in a prominent position. Leave space for marketing text."

    # 3. Assemble Final Gemini Prompt
    prompt = (
        "Create a professional advertisement scene.\n\n"
        f"Environment: {environment}.\n\n"
        f"Lighting: {lighting}.\n\n"
        f"Composition: {composition}\n\n"
        "Camera: eye level hero shot with shallow depth of field.\n\n"
        f"Style: ultra realistic commercial product photography, 8k advertising image for {product_name}."
    )

    # 4. Print results
    print("\n" + "="*50)
    print("GENERATED GEMINI PROMPT:")
    print("="*50)
    print(prompt)
    print("="*50 + "\n")

    # 5. Save to file
    output_path = "outputs/gemini_prompt.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"Gemini prompt successfully exported to: {output_path}")

if __name__ == "__main__":
    target_input = "inputs/campaigns/arjuna_tea.json"
    if len(sys.argv) > 1:
        target_input = sys.argv[1]
        
    generate_gemini_prompt(target_input)
