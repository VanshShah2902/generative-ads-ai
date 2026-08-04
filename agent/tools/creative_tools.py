"""
Wraps the generative_ads_ai pipeline for use as agent tools.
"""

import json
import os
import sys
import time

# Ensure project root is on path so pipeline imports work
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from generation_engine.pipeline_runner import AdGenerationPipeline
from src.compliance.nmc_filter import audit_payload

# ---------------------------------------------------------------------------
# Hardcoded Arjuna Cardio Care Tea product data
# Source: "15 Short Benefits Per Ingredient" document
# Used when user does not provide these fields (default flow)
# ---------------------------------------------------------------------------
_ARJUNA_INGREDIENTS = [
    "Tez Patta", "Elaichi", "Clove", "Shankpushpi", "Nagarmotha",
    "Brahmi", "Ashwagandha", "Dalchini", "Arjun Chal", "Harad",
    "Tulsi", "Sonth", "Saunf", "Black Tea", "Green Tea",
]

_ARJUNA_BENEFITS = [
    "Supports heart health",
    "Helps maintain healthy cholesterol levels",
    "May help with stress management",
    "Supports healthy blood circulation",
    "Helps boost energy and stamina",
]

_ARJUNA_SOLUTIONS = [
    "Supports cardiovascular well-being",
    "Helps maintain healthy blood pressure",
    "Supports natural stress relief",
]

_ARJUNA_PROBLEMS = [
    "Feeling tired and low on energy",
    "Concerned about heart health",
    "Struggling with stress and anxiety",
]

_pipeline: AdGenerationPipeline | None = None


def _get_pipeline() -> AdGenerationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AdGenerationPipeline()
    return _pipeline


def generate_prompts(
    product_name: str,
    brand_name: str,
    price: str = "",
    offer: str = "",
    theme: str = "KR_2D",
    num_variations: int = 5,
    product_image: str = "",
    person_image: str = "",
    # kept for backward compat — ignored, autofilled from product document
    category: str = "Ayurvedic Health Tea",
    benefits: list = None,
    problems: list = None,
    solutions: list = None,
    ingredients: list = None,
) -> dict:
    """
    Runs the prompt generation stage of the pipeline.
    benefits/problems/solutions/ingredients are autofilled from the
    hardcoded Arjuna Cardio Care Tea ingredient document if not provided.
    """
    # Autofill from document — ignore user-provided empty lists
    benefits    = benefits    if benefits    else _ARJUNA_BENEFITS
    problems    = problems    if problems    else _ARJUNA_PROBLEMS
    solutions   = solutions   if solutions   else _ARJUNA_SOLUTIONS
    ingredients = ingredients if ingredients else _ARJUNA_INGREDIENTS

    # NMC compliance pass
    safe_payload = audit_payload({
        "benefits":  benefits,
        "solutions": solutions,
        "problems":  problems,
    })
    benefits  = safe_payload["benefits"]
    solutions = safe_payload["solutions"]
    problems  = safe_payload["problems"]

    campaign = _build_campaign_json(
        product_name, brand_name, category, benefits, problems,
        solutions, ingredients, price, offer, product_image, person_image,
        theme=theme,
    )
    input_path = _save_campaign(campaign)

    pipeline = _get_pipeline()
    all_clusters = ["product_first", "solution_first", "doctor_first", "ingredient_first", "problem_first"]

    cluster_prompts = pipeline.run(input_path, num_variations=num_variations)

    # Retry any clusters that failed silently (Groq rate-limit during sequential calls)
    missing = [c for c in all_clusters if c not in cluster_prompts]
    if missing:
        print(f"[creative_tools] Retrying missing clusters after 5s: {missing}")
        time.sleep(5)
        retry_result = pipeline.run(input_path, num_variations=num_variations)
        for c in missing:
            if c in retry_result:
                cluster_prompts[c] = retry_result[c]
                print(f"[creative_tools] Retry succeeded for {c}")
            else:
                print(f"[creative_tools] Retry also failed for {c} — skipping")

    # Persist the merged result
    prompts_file = os.path.join("outputs", "prompts", "cluster_prompts.json")
    with open(prompts_file, "w") as f:
        json.dump(cluster_prompts, f, indent=4)

    return {
        "status": "success",
        "cluster_prompts": cluster_prompts,
    }


def generate_creative(selected_prompts: dict) -> dict:
    """
    Runs image generation for user-selected prompts.
    selected_prompts format: {"product_first": ["chosen prompt text"], ...}

    Returns:
        {
            "status": "success",
            "images": [
                {"path": "outputs/generated_ads/product_first.png", "cluster": "product_first"},
                ...
            ]
        }
    """
    # Write selected prompts to the file the pipeline reads
    selected_path = os.path.join("outputs", "prompts", "selected_prompts.json")
    os.makedirs(os.path.dirname(selected_path), exist_ok=True)
    with open(selected_path, "w") as f:
        json.dump(selected_prompts, f, indent=4)

    pipeline = _get_pipeline()
    pipeline.generate_from_selected()

    # Collect generated image paths
    ads_dir = os.path.join("outputs", "generated_ads")
    images = []
    for cluster in selected_prompts:
        prompts = selected_prompts[cluster]
        if isinstance(prompts, str):
            prompts = [prompts]
        for i in range(len(prompts)):
            suffix = f"_{i+1}" if len(prompts) > 1 else ""
            fname = f"{cluster}{suffix}.png"
            fpath = os.path.join(ads_dir, fname)
            if os.path.exists(fpath):
                images.append({"path": fpath, "cluster": cluster})

    return {
        "status": "success",
        "images": images,
    }


def lookup_product(product_name: str) -> dict:
    """
    Search product memory for a product by name (case-insensitive partial match).
    Returns the matched product fields so the agent can offer autofill to the user.

    Returns:
        {"status": "found", "product": {...}}   if a match is found
        {"status": "not_found"}                 if no match
    """
    import sys, os
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

    from src.memory.product_memory import ProductMemory
    memory = ProductMemory()
    all_products = memory.get_all_products()

    search = product_name.lower().strip()
    for p in all_products:
        if search in p.get("product_name", "").lower():
            # Return only the fields needed for campaign generation
            return {
                "status": "found",
                "product": {
                    "product_name":  p.get("product_name", ""),
                    "brand_name":    p.get("brand_name", ""),
                    "category":      p.get("category", ""),
                    "benefits":      p.get("benefits", p.get("benefit_points", [])),
                    "problems":      p.get("problems", []),
                    "solutions":     p.get("solutions", []),
                    "ingredients":   p.get("ingredients", []),
                    "price":         p.get("price", ""),
                    "offer":         p.get("offer", ""),
                    "product_image": p.get("product_image", ""),
                    "person_image":  p.get("person_image", ""),
                },
            }

    return {"status": "not_found"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_campaign_json(
    product_name, brand_name, category, benefits, problems,
    solutions, ingredients, price, offer, product_image, person_image,
    theme: str = "KR_2D",
) -> dict:
    return {
        "product_name": product_name,
        "brand_name": brand_name,
        "category": category,
        "benefits": benefits[:5],
        "problems": problems[:3],
        "solutions": solutions[:3],
        "ingredients": ingredients[:5],
        "price": price,
        "offer": offer,
        "product_image": product_image,
        "person_image": person_image,
        "creative_type": "standard",
        "theme": theme,
    }


def _save_campaign(campaign: dict) -> str:
    os.makedirs("inputs", exist_ok=True)
    path = os.path.join("inputs", "campaign_input.json")
    with open(path, "w") as f:
        json.dump(campaign, f, indent=4)
    return path


# ---------------------------------------------------------------------------
# Doctor Template Creative
# ---------------------------------------------------------------------------

def generate_template_creative(
    template: str,
    brand_name: str,
    product_name: str,
    ingredients: list,
    generate_image: bool = True,
    price: str = "",
    sachets: str = "",
    offer: str = "",
    tagline: str = "Formulated for Quality",
    person_image: str = "",
    product_image: str = "",
) -> dict:
    """
    Generate a doctor-endorsement style ad using the winning PIL template.

    If generate_image=False: returns a structured layout description/prompt only (no image files).
    If generate_image=True:  renders the actual image via PIL. person_image and product_image required.

    template: "cards" (Image 1 style) | "table" (Image 2 style)
    """

    # Build campaign summary used in both modes
    campaign_data = {
        "brand_name":   brand_name,
        "product_name": product_name,
        "ingredients":  ingredients,
        "price":        price,
        "sachets":      sachets,
        "offer":        offer,
        "tagline":      tagline,
    }

    # Shared helpers
    layout_name = "Cards Layout (doctor left, ingredient cards right)" if template == "cards" \
                  else "Table Layout (doctor left, large product center, ingredient table bottom)"
    ing_lines = []
    for ing in ingredients[:3]:
        ing_lines.append(
            f"  • {ing.get('name','')} — {ing.get('dose_per','')} | "
            f"{ing.get('dose_daily','')} daily — {ing.get('benefit','')}"
        )
    banner_text = tagline
    if sachets and price:
        banner_text += f"  |  {sachets} {price}"
    if offer:
        banner_text += f" ({offer})"

    # 3 variation seeds — same structure, different emphasis/mood per variation
    _VARIATIONS = [
        {
            "label":       "V1 — Authority",
            "bg_note":     "white marble texture, clean and clinical",
            "doctor_note": "doctor facing camera, arms folded, confident posture",
            "light_note":  "bright even studio lighting, high-key",
            "accent":      "gold accents prominent",
        },
        {
            "label":       "V2 — Warm & Approachable",
            "bg_note":     "soft warm-tinted marble, slight cream warmth",
            "doctor_note": "doctor in a relaxed open stance, slight smile",
            "light_note":  "warm natural side lighting, inviting feel",
            "accent":      "gold slightly muted, forest green dominant",
        },
        {
            "label":       "V3 — Trust & Science",
            "bg_note":     "pure white background, minimal and clean",
            "doctor_note": "doctor gesturing toward product, explaining expression",
            "light_note":  "flat even white lighting, clinical precision",
            "accent":      "deep green dominant, gold as detail only",
        },
    ]

    # ── Prompt-only mode — 4 variation descriptions ─────────────────────────
    if not generate_image:
        base_layout = (
            f"  • 1080×1080 px canvas\n"
            f"  • Doctor/person: left {'40%' if template == 'cards' else '35%'} of canvas, full height, background removed, NO stethoscope\n"
            f"  • Product box: {'bottom-left overlapping doctor' if template == 'cards' else 'center-right, large, floating above table'}\n"
            f"  • {'3 stacked white cards — dark-green border, gold icon circles, ingredient name + dosage + benefit' if template == 'cards' else 'Gold-bordered table: PER SACHET | DAILY (2x) columns, gold icon circles'}\n"
            f"  • Full-width gold/amber bottom banner: \"{banner_text}\"\n"
            f"  • Fonts: Bold serif title (brand dark green, product gold), bold all-caps ingredient names, light descriptions\n"
        )

        prompts = []
        for v in _VARIATIONS:
            desc = (
                f"Doctor Template Ad — {layout_name} | {v['label']}\n\n"
                f"Brand: {brand_name}  |  Product: {product_name}\n\n"
                f"Ingredients:\n" + "\n".join(ing_lines) + "\n\n"
                f"Layout:\n{base_layout}\n"
                f"Variation details:\n"
                f"  • Background: {v['bg_note']}\n"
                f"  • Doctor pose: {v['doctor_note']}\n"
                f"  • Lighting: {v['light_note']}\n"
                f"  • Accent style: {v['accent']}\n"
            )
            prompts.append(desc)

        return {
            "status": "success",
            "prompt_only": True,
            "prompts": prompts,          # list of 4 variation descriptions
            "prompt_description": "\n\n---\n\n".join(prompts),  # joined for agent display
            "campaign_data": campaign_data,
        }

    # ── Image generation mode — 4 rendered images ───────────────────────────
    from PIL import Image
    from utils.compositing_utils import remove_background
    from generation_engine.template_renderer import DoctorTemplateRenderer
    import uuid

    # Doctor image — optional
    if person_image and os.path.exists(person_image):
        doctor_base = Image.open(person_image).convert("RGBA")
        try:
            doctor_base = remove_background(doctor_base)
        except Exception as e:
            print(f"[TemplateCreative] Background removal failed: {e} — using original")
    else:
        print("[TemplateCreative] No doctor image — using placeholder silhouette")
        doctor_base = Image.new("RGBA", (400, 900), (180, 180, 180, 200))

    # Product image — optional
    if product_image and os.path.exists(product_image):
        product_base = Image.open(product_image).convert("RGBA")
    else:
        print("[TemplateCreative] No product image — using placeholder box")
        product_base = Image.new("RGBA", (300, 300), (15, 60, 30, 220))

    out_dir = os.path.join("outputs", "generated_ads")
    os.makedirs(out_dir, exist_ok=True)

    renderer = DoctorTemplateRenderer()
    images = []

    # Colour tweaks per variation applied via campaign_data overrides
    _VAR_COLOR_OVERRIDES = [
        {},                                                          # V1 default
        {"amber_bg": [220, 185, 90]},                               # V2 warmer gold
        {"amber_bg": [200, 160, 50], "dark_green": [5, 80, 35]},    # V3 brighter green
    ]

    for idx, (v, color_ovr) in enumerate(zip(_VARIATIONS, _VAR_COLOR_OVERRIDES)):
        var_data = dict(campaign_data)
        if color_ovr:
            var_data["_color_overrides"] = color_ovr

        output_img = renderer.render(template, doctor_base.copy(), product_base.copy(), var_data)

        filename = f"doctor_template_{template}_v{idx+1}_{uuid.uuid4().hex[:6]}.png"
        out_path = os.path.join(out_dir, filename)
        output_img.save(out_path)
        print(f"[TemplateCreative] Saved {v['label']} → {out_path}")
        images.append({"path": out_path, "cluster": f"doctor_template_{template}_v{idx+1}"})

    return {
        "status": "success",
        "prompt_only": False,
        "images": images,   # list of 3 image dicts
    }


# ---------------------------------------------------------------------------
# Reference Image Analysis → 4 Prompt Variations
# ---------------------------------------------------------------------------

def analyse_reference_image(image_path: str, product_context: str = "", my_product: dict = None) -> dict:
    """
    Analyse a reference ad image with Gemini Vision and return a single
    ready-to-use image generation prompt that recreates the same visual style,
    layout, composition, colors, and mood — with no product substitution.

    The prompt can be fed directly to an image generation model (Gemini Imagen,
    Midjourney, DALL-E, etc.) to produce a similar-looking ad creative.

    Args:
        image_path: Path to the uploaded reference image.
        product_context: Unused — kept for backward compat.
        my_product:      Unused — kept for backward compat.

    Returns:
        {"status": "success", "prompt": "...", "analysis": "..."}
    """
    import io
    import google.generativeai as genai
    from PIL import Image as PILImage

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY not set in environment"}

    if not image_path or not os.path.exists(image_path):
        return {"status": "error", "message": f"Reference image not found: {image_path}"}

    img = PILImage.open(image_path).convert("RGB")
    img.thumbnail((1024, 1024), PILImage.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    analysis_prompt = """You are an expert visual analyst and image generation prompt engineer.

Look at this advertisement image carefully. Your job is to write a single, detailed image generation prompt that would recreate this exact image — same layout, same composition, same colors, same mood, same visual style, same element positions.

Analyse:
- Overall layout and composition (where every element sits, as % of frame)
- Exact color palette (name every color you see)
- Background style (marble, gradient, plain, textured — describe the exact look)
- Lighting (direction, quality, mood)
- Any people/subjects (position, pose, clothing, expression — describe without naming)
- Product/object placement (position, size, angle, any glow/shadow effects)
- Text/badge panels (style, position, how many, shape)
- Typography style (bold/light, serif/sans, color hierarchy)
- Footer/banner (position, color, content style)
- Any decorative elements (icons, lines, botanical art, gradients, overlays)
- Overall mood and aesthetic

Then write ONE complete image generation prompt (200–350 words) that captures ALL of this so precisely that an AI image model would recreate the same visual. Use placeholder text like "[Product Name]", "[Brand Name]", "[Ingredient 1]" etc. where specific text appears.

Return your response in exactly this format:

ANALYSIS:
[Your detailed visual breakdown — every element, color, position, style]

PROMPT:
[Your complete image generation prompt — ready to paste into an image model]"""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        print("[AnalyseReference] Sending image to Gemini...")

        response = model.generate_content([
            {"inline_data": {"mime_type": "image/png", "data": image_bytes}},
            {"text": analysis_prompt},
        ])
        raw_text = response.text.strip()
        print(f"[AnalyseReference] Response received ({len(raw_text)} chars)")

        import re
        analysis, prompt = "", ""

        m = re.search(r"ANALYSIS:\s*(.*?)(?=PROMPT:|$)", raw_text, re.DOTALL)
        if m:
            analysis = m.group(1).strip()

        m = re.search(r"PROMPT:\s*(.*?)$", raw_text, re.DOTALL)
        if m:
            prompt = m.group(1).strip()

        if not prompt:
            prompt = raw_text  # fallback: return full response as prompt

        return {
            "status": "success",
            "analysis": analysis,
            "prompt": prompt,
        }

    except Exception as e:
        print(f"[AnalyseReference] Error: {e}")
        return {"status": "error", "message": str(e)}
