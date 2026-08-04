"""
test_image_generation.py
========================
Test Gemini Imagen 3 vs GPT-4o for ad image generation.

Usage:
    python tests/test_image_generation.py [--reference path/to/ref.png]
    python tests/test_image_generation.py --gemini-only
    python tests/test_image_generation.py --gpt-only
"""

import os
import sys
import json
import time
import base64
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

OUTPUT_DIR = os.path.join(BASE_DIR, "tests", "generation_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: Analyze reference image with Gemini Flash (if provided)
# ═══════════════════════════════════════════════════════════════════════════

def analyze_reference(image_path: str) -> dict:
    """Use Gemini Flash to understand the reference ad's concept."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = """Analyze this advertisement image. Return JSON with:
{
    "ad_concept": "one sentence describing the core creative idea",
    "layout_description": "detailed description of how elements are positioned",
    "visual_style": "lighting, mood, color palette, photography style",
    "text_on_image": "all readable text including headline, subheadline, CTA, price",
    "key_elements": ["list of important visual elements"],
    "replication_prompt": "A detailed image generation prompt that would recreate this ad's concept and layout for a DIFFERENT product. Focus on the composition pattern, not the specific product."
}
Return ONLY valid JSON."""

    print("[Gemini Flash] Analyzing reference image...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


# ═══════════════════════════════════════════════════════════════════════════
# HARDCODED REFERENCE ANALYSIS (from the attached Arjuna Tea ad)
# Used when no reference image path is provided
# ═══════════════════════════════════════════════════════════════════════════

REFERENCE_ANALYSIS = {
    "ad_concept": "Comparison ad — swap your regular green tea with Arjuna Cardio Care Tea, showing both teas side by side with the product box and price",
    "layout_description": "Top: bold headline 'Swap your regular green tea'. Middle: two tea cups side by side (green tea left with red X negatives, Arjuna tea right glowing amber with benefits). Bottom: product packshot with ingredients, price ₹599, Shop Now CTA. Brand logo top-right.",
    "visual_style": "Warm natural lighting, wooden table surface, cozy home setting with window light in background. Rich earthy color palette — golden amber, dark green, cream, wood brown. Premium product photography with steam rising from cups.",
    "key_elements": [
        "side-by-side comparison of two tea cups",
        "red X marks for negatives on regular tea",
        "product packshot with ingredient details",
        "price badge ₹599 in gold",
        "Shop Now CTA button",
        "6 Ayurvedic Herbs callout",
        "brand logo Dr. Bimal's",
        "decorative ribbon/wave elements"
    ]
}


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: Build generation prompt from analysis
# ═══════════════════════════════════════════════════════════════════════════

def build_generation_prompt(analysis: dict, product: dict, aspect_ratio: str) -> str:
    """Build a detailed image generation prompt from reference analysis + product data."""

    # Aspect ratio to pixel dimensions
    dims = {
        "1:1":  (1024, 1024),
        "9:16": (1080, 1920),
        "4:5":  (1080, 1350),
    }
    w, h = dims.get(aspect_ratio, (1024, 1024))

    prompt = f"""Create a professional commercial advertisement image for {product['name']}.

CREATIVE CONCEPT (replicate this pattern):
{analysis.get('ad_concept', analysis.get('replication_prompt', ''))}

LAYOUT:
{analysis.get('layout_description', '')}

VISUAL STYLE:
{analysis.get('visual_style', '')}
Ultra-realistic commercial advertising photography, 8K quality, professional product shoot.

PRODUCT DETAILS:
- Product: {product['name']}
- Brand: {product.get('brand', '')}
- Price: {product.get('price', '')}
- Key Benefits: {', '.join(product.get('benefits', []))}
- Ingredients: {', '.join(product.get('ingredients', []))}

TEXT TO INCLUDE IN THE IMAGE:
- Headline: {product.get('headline', product['name'])}
- Subheadline: {product.get('subheadline', '')}
- Price: {product.get('price', '')}
- CTA: {product.get('cta', 'Shop Now')}

CRITICAL RULES:
- All text must be sharp, readable, and CORRECTLY SPELLED — double-check every word
- DO NOT place any text on top of the doctor/person or product — text goes in dedicated zones only
- Product packaging must look authentic and professional
- If product and doctor images are provided, preserve their EXACT appearance — do not alter faces or product design
- Maintain premium advertising quality throughout
- Clean visual hierarchy — headline > product > price > CTA
- Image dimensions: {w}x{h} pixels ({aspect_ratio} aspect ratio)
- The output image MUST be in {aspect_ratio} aspect ratio ({w}x{h})
"""
    return prompt


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: Generate with Gemini Imagen 3
# ═══════════════════════════════════════════════════════════════════════════

def _load_image_part(image_path: str):
    """Load an image file as a Gemini Part for multimodal input."""
    from google import genai

    with open(image_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return genai.types.Part.from_bytes(data=data, mime_type=mime_map.get(ext, "image/jpeg"))


def generate_gemini(prompt: str, aspect_ratio: str, output_name: str,
                    product_image: str = None, doctor_image: str = None) -> dict:
    """Generate ad image using Gemini. Optionally include product/doctor images as input."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found"}

    client = genai.Client(api_key=api_key)

    has_input_images = product_image or doctor_image
    print(f"[Gemini] Generating {aspect_ratio} image (input images: {bool(has_input_images)})...")
    start = time.time()

    # If we have input images, skip Imagen (text-only) and go straight to Gemini multimodal
    if not has_input_images:
        imagen_models = [
            ("imagen-4.0-generate-001", "Imagen 4.0"),
            ("imagen-4.0-fast-generate-001", "Imagen 4.0 Fast"),
        ]
        for model_id, model_name in imagen_models:
            try:
                print(f"[Gemini] Trying {model_name} ({model_id})...")
                response = client.models.generate_images(
                    model=model_id,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                        safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    ),
                )
                duration = time.time() - start
                if response.generated_images:
                    img_data = response.generated_images[0].image.image_bytes
                    output_path = os.path.join(OUTPUT_DIR, f"gemini_{output_name}.png")
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    print(f"[{model_name}] Saved to {output_path}")
                    return {
                        "model": f"{model_name} ({model_id})",
                        "output_path": output_path,
                        "time_seconds": round(duration, 2),
                        "cost_estimate": "~$0.03-0.04 (~₹2.50-3.50)",
                        "aspect_ratio": aspect_ratio,
                        "success": True,
                    }
                else:
                    print(f"[{model_name}] No images generated (safety filter?)")
                    continue
            except Exception as e:
                print(f"[{model_name}] Failed: {e}")
                continue

    # Gemini native image gen (supports multimodal input)
    gemini_image_models = [
        ("gemini-2.5-flash-image", "Gemini 2.5 Flash Image"),
        ("gemini-3.1-flash-image", "Gemini 3.1 Flash Image"),
    ]

    # Build multimodal contents
    contents = []
    if product_image and os.path.exists(product_image):
        contents.append(f"PRODUCT IMAGE — use this EXACT product box in the ad, preserve its design faithfully:")
        contents.append(_load_image_part(product_image))
    if doctor_image and os.path.exists(doctor_image):
        contents.append(f"DOCTOR IMAGE — include this EXACT person in the ad, preserve their face and appearance:")
        contents.append(_load_image_part(doctor_image))
    contents.append(prompt)

    for model_id, model_name in gemini_image_models:
        try:
            print(f"[Gemini] Trying native image gen: {model_name} ({'with' if has_input_images else 'without'} input images)...")
            response = client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    output_path = os.path.join(OUTPUT_DIR, f"gemini_{output_name}.png")
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    print(f"[{model_name}] Saved to {output_path}")
                    return {
                        "model": f"{model_name} ({model_id})",
                        "output_path": output_path,
                        "time_seconds": round(time.time() - start, 2),
                        "cost_estimate": "~$0.04",
                        "aspect_ratio": aspect_ratio,
                        "input_images": bool(has_input_images),
                        "success": True,
                    }
            print(f"[{model_name}] No image in response")

        except Exception as e:
            print(f"[{model_name}] Failed: {e}")
            continue

    return {
        "model": "All Gemini models failed",
        "error": "None of the available models generated an image",
        "time_seconds": round(time.time() - start, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STEP 4: Generate with GPT-4o / gpt-image-1
# ═══════════════════════════════════════════════════════════════════════════

def generate_gpt4o(prompt: str, aspect_ratio: str, output_name: str) -> dict:
    """Generate ad image using OpenAI GPT-4o image generation."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY not found in .env — add it to test GPT-4o"}

    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai package not installed. Run: pip install openai"}

    client = OpenAI(api_key=api_key)

    # Map aspect ratios to OpenAI sizes
    size_map = {
        "1:1":  "1024x1024",
        "9:16": "1024x1536",  # closest portrait
        "4:5":  "1024x1536",  # closest to 4:5
    }
    size = size_map.get(aspect_ratio, "1024x1024")

    print(f"[GPT-4o] Generating {aspect_ratio} image (size={size})...")
    start = time.time()

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality="high",
            n=1,
        )

        duration = time.time() - start

        # gpt-image-1 returns base64
        if response.data and response.data[0].b64_json:
            img_data = base64.b64decode(response.data[0].b64_json)
            output_path = os.path.join(OUTPUT_DIR, f"gpt4o_{output_name}.png")
            with open(output_path, "wb") as f:
                f.write(img_data)

            print(f"[GPT-4o] Saved to {output_path}")
            return {
                "model": "GPT-4o (gpt-image-1)",
                "output_path": output_path,
                "time_seconds": round(duration, 2),
                "cost_estimate": "~$0.04-0.08 (~₹3.50-7)",
                "aspect_ratio": aspect_ratio,
                "size": size,
                "success": True,
            }
        elif response.data and response.data[0].url:
            import urllib.request
            output_path = os.path.join(OUTPUT_DIR, f"gpt4o_{output_name}.png")
            urllib.request.urlretrieve(response.data[0].url, output_path)
            print(f"[GPT-4o] Saved to {output_path}")
            return {
                "model": "GPT-4o (gpt-image-1)",
                "output_path": output_path,
                "time_seconds": round(duration, 2),
                "cost_estimate": "~$0.04-0.08 (~₹3.50-7)",
                "aspect_ratio": aspect_ratio,
                "size": size,
                "success": True,
            }
        else:
            return {"model": "GPT-4o", "error": "No image data in response", "time_seconds": round(duration, 2)}

    except Exception as e:
        return {
            "model": "GPT-4o",
            "error": str(e),
            "time_seconds": round(time.time() - start, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

# Test product data (Arjuna Cardio Care Tea — same product, new ad)
TEST_PRODUCT = {
    "name": "Dr. Bimal's Arjuna Cardio Care Tea",
    "brand": "Dr. Bimal's Jaadu Diet",
    "price": "₹599",
    "headline": "Swap your Regular Green Tea with Arjuna Cardio Care Tea",
    "subheadline": "6 Ayurvedic Herbs for a healthy heart",
    "cta": "Shop Now →",
    "benefits": [
        "Supports healthy lipid levels",
        "Helps maintain healthy blood pressure",
        "Supports overall heart health",
        "Supports healthy cholesterol function",
    ],
    "ingredients": [
        "Arjuna Bark", "Ashwagandha", "Tulsi",
        "Dalchini", "Brahmi", "Haradbadi"
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Test image generation models")
    parser.add_argument("--reference", type=str, help="Path to reference ad image")
    parser.add_argument("--gemini-only", action="store_true", help="Test Gemini only")
    parser.add_argument("--gpt-only", action="store_true", help="Test GPT-4o only")
    parser.add_argument("--ratio", type=str, default="1:1", choices=["1:1", "9:16", "4:5"],
                        help="Aspect ratio to generate")
    parser.add_argument("--product-image", type=str, help="Path to product image to composite")
    parser.add_argument("--doctor-image", type=str, help="Path to doctor/person image to composite")
    parser.add_argument("--with-images", action="store_true",
                        help="Use default product + doctor images from assets/")
    args = parser.parse_args()

    # Resolve input images
    product_img = args.product_image
    doctor_img = args.doctor_image
    if args.with_images:
        product_img = product_img or os.path.join(BASE_DIR, "assets", "products", "AT 2 Box.png")
        doctor_img = doctor_img or os.path.join(BASE_DIR, "assets", "people", "dr-bimal-img.jpg")

    print("=" * 70)
    print("  IMAGE GENERATION MODEL TEST")
    print(f"  Aspect Ratio: {args.ratio}")
    print(f"  Product: {TEST_PRODUCT['name']}")
    if product_img:
        print(f"  Product Image: {product_img}")
    if doctor_img:
        print(f"  Doctor Image: {doctor_img}")
    print("=" * 70)

    # Step 1: Analyze reference or use hardcoded analysis
    if args.reference and os.path.exists(args.reference):
        print(f"\n[1] Analyzing reference image: {args.reference}")
        try:
            analysis = analyze_reference(args.reference)
            print("[1] Reference analysis complete:")
            print(json.dumps(analysis, indent=2)[:500])
        except Exception as e:
            print(f"[1] Analysis failed: {e}, using hardcoded analysis")
            analysis = REFERENCE_ANALYSIS
    else:
        print("\n[1] Using hardcoded reference analysis (Arjuna Tea comparison ad)")
        analysis = REFERENCE_ANALYSIS

    # Step 2: Build prompt
    prompt = build_generation_prompt(analysis, TEST_PRODUCT, args.ratio)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{args.ratio.replace(':', 'x')}_{timestamp}"

    # Save prompt for review
    prompt_path = os.path.join(OUTPUT_DIR, f"prompt_{output_name}.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\n[2] Generation prompt saved to: {prompt_path}")
    print(f"    Prompt length: {len(prompt)} chars")

    results = {}

    # Step 3: Generate with Gemini
    if not args.gpt_only:
        print(f"\n[3] GEMINI — generating {args.ratio}...")
        results["gemini"] = generate_gemini(prompt, args.ratio, output_name,
                                            product_image=product_img,
                                            doctor_image=doctor_img)
        print(json.dumps(results["gemini"], indent=2))

    # Step 4: Generate with GPT-4o
    if not args.gemini_only:
        print(f"\n[4] GPT-4o — generating {args.ratio}...")
        results["gpt4o"] = generate_gpt4o(prompt, args.ratio, output_name)
        print(json.dumps(results["gpt4o"], indent=2))

    # Summary
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    for name, r in results.items():
        status = "SUCCESS" if r.get("success") else "FAILED"
        print(f"\n  {name.upper()}: {status}")
        if r.get("success"):
            print(f"    Model: {r['model']}")
            print(f"    Time: {r['time_seconds']}s")
            print(f"    Cost: {r['cost_estimate']}")
            print(f"    Output: {r['output_path']}")
        else:
            print(f"    Error: {r.get('error', 'Unknown')}")

    # Save full results
    results_path = os.path.join(OUTPUT_DIR, f"results_{output_name}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Full results: {results_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
