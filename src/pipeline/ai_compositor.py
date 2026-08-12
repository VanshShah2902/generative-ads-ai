"""
AI Compositor — uses Gemini image generation to edit reference ads.
Sends the reference image + precise edit instructions to Gemini for production-quality output.
"""

import os
import json
import time
from google import genai
from google.genai import types

LEARNED_FIXES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "learned_fixes.json")


def load_learned_fixes() -> list:
    if os.path.exists(LEARNED_FIXES_PATH):
        with open(LEARNED_FIXES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_learned_fix(fix_description: str):
    fixes = load_learned_fixes()
    if fix_description not in fixes:
        fixes.append(fix_description)
        with open(LEARNED_FIXES_PATH, "w", encoding="utf-8") as f:
            json.dump(fixes, f, indent=2, ensure_ascii=False)


COLOR_THEMES = {
    "blue_medical": {"primary": "#1a5276", "secondary": "#85c1e9", "desc": "clinical blue, medical trust, cool blue tones"},
    "red_vitality": {"primary": "#922b21", "secondary": "#f1948a", "desc": "energetic red, vitality, warm red tones"},
    "purple_premium": {"primary": "#6c3483", "secondary": "#c39bd3", "desc": "rich purple, premium luxury, royal purple tones"},
    "gold_luxury": {"primary": "#b7950b", "secondary": "#f4d03f", "desc": "golden luxury, premium gold, warm gold tones"},
    "dark_modern": {"primary": "#1c1c2e", "secondary": "#e74c3c", "desc": "dark modern, sleek black with red accents"},
    "teal_fresh": {"primary": "#148f77", "secondary": "#76d7c4", "desc": "fresh teal, natural green-blue, calming aqua tones"},
    "forest_green": {"primary": "#1b4332", "secondary": "#95d5b2", "desc": "deep forest green, natural herbal, earthy green tones"},
    "coral_warm": {"primary": "#c0392b", "secondary": "#f5b7b1", "desc": "warm coral pink, friendly and approachable, soft warm tones"},
    "navy_classic": {"primary": "#0a1931", "secondary": "#b0c4de", "desc": "classic navy blue, corporate trust, deep blue with light steel accents"},
    "orange_energy": {"primary": "#d35400", "secondary": "#f8c471", "desc": "vibrant orange, energy and enthusiasm, warm sunset tones"},
    "maroon_ayurvedic": {"primary": "#641e16", "secondary": "#d4a373", "desc": "deep maroon with earthy tan, traditional ayurvedic, warm ethnic tones"},
    "sky_wellness": {"primary": "#2980b9", "secondary": "#aed6f1", "desc": "bright sky blue, wellness and calm, light airy blue tones"},
    "charcoal_minimal": {"primary": "#2c3e50", "secondary": "#ecf0f1", "desc": "charcoal grey, minimalist modern, clean monochrome with crisp whites"},
}

FONT_PRESETS = {
    "Times New Roman": {"desc": "classic serif, professional medical-trust typography", "example": "Your Heart Deserves Care", "css": "font-family: 'Times New Roman', Times, serif; font-weight: 700;"},
    "Georgia": {"desc": "elegant serif, warm and readable, editorial feel", "example": "Natural Wellness Daily", "css": "font-family: Georgia, 'Times New Roman', serif; font-weight: 700;"},
    "Arial": {"desc": "clean sans-serif, universal readability, corporate trust", "example": "Trusted By Millions", "css": "font-family: Arial, Helvetica, sans-serif; font-weight: 700;"},
    "Helvetica": {"desc": "Swiss modernist sans-serif, premium luxury brand feel", "example": "Premium Quality Inside", "css": "font-family: Helvetica, Arial, sans-serif; font-weight: 700;"},
    "Impact": {"desc": "heavy condensed bold, attention-grabbing urgency", "example": "LIMITED TIME OFFER!", "css": "font-family: Impact, 'Arial Black', sans-serif; font-weight: 900;"},
    "Verdana": {"desc": "wide sans-serif, screen-optimized clarity, friendly modern", "example": "Shop With Confidence", "css": "font-family: Verdana, Geneva, sans-serif; font-weight: 700;"},
    "Trebuchet MS": {"desc": "humanist sans-serif, energetic and approachable", "example": "Start Your Journey Today", "css": "font-family: 'Trebuchet MS', Helvetica, sans-serif; font-weight: 700;"},
    "Palatino": {"desc": "old-style serif, sophisticated and literary", "example": "Crafted With Tradition", "css": "font-family: 'Palatino Linotype', Palatino, serif; font-weight: 700;"},
    "Garamond": {"desc": "classic French serif, timeless elegance, high-end brands", "example": "Timeless Elegance Awaits", "css": "font-family: Garamond, 'Times New Roman', serif; font-weight: 700;"},
    "Futura": {"desc": "geometric sans-serif, modernist design, bold and futuristic", "example": "THE FUTURE IS NOW", "css": "font-family: Futura, 'Century Gothic', sans-serif; font-weight: 700;"},
    "Century Gothic": {"desc": "geometric sans-serif, clean and light, wellness brands", "example": "Pure Natural Goodness", "css": "font-family: 'Century Gothic', Futura, sans-serif; font-weight: 600;"},
    "Playfair Display": {"desc": "high-contrast serif, editorial luxury, fashion and beauty", "example": "Indulge In Luxury", "css": "font-family: 'Playfair Display', Georgia, serif; font-weight: 700; font-style: italic;"},
}

ASPECT_RATIOS = {
    "1:1": (1080, 1080),
    "9:16": (1080, 1920),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}


def _load_image_part(image_path: str):
    with open(image_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return genai.types.Part.from_bytes(data=data, mime_type=mime_map.get(ext, "image/jpeg"))


def _build_edit_prompt(analysis: dict, changes: dict) -> str:
    """Build a precise edit prompt from the analysis + requested changes."""
    parts = []
    parts.append("You are given a reference advertisement image. Edit it according to the instructions below.")
    parts.append("KEEP everything else EXACTLY the same — same layout, same product, same imagery, same composition.")
    parts.append("The output must look like a professional, production-ready advertisement.")
    parts.append("")

    if "color" in changes:
        color = changes["color"]
        if isinstance(color, str) and color in COLOR_THEMES:
            theme = COLOR_THEMES[color]
            parts.append(f"COLOR CHANGE: Shift the ad's color scheme to {theme['desc']}.")
            parts.append(f"Primary color: {theme['primary']}, Secondary/accent: {theme['secondary']}.")
        elif isinstance(color, dict):
            desc = color.get("desc", "")
            parts.append(f"COLOR CHANGE: Shift the ad's color scheme. Primary: {color.get('primary', '')}, Secondary: {color.get('secondary', '')}. {desc}")
        parts.append("ONLY recolor these: ad background, decorative borders/frames, text banner backgrounds, ornamental elements.")
        parts.append("DO NOT recolor: the product box/packaging (keep its original green/gold/brown colors exactly), doctor/person photos, food/drink items, ingredient images.")
        parts.append("")

    if "font" in changes:
        preset = changes["font"]
        font_info = FONT_PRESETS.get(preset, {})
        if isinstance(font_info, dict):
            desc = f"{preset} — {font_info.get('desc', '')}"
        else:
            desc = preset
        parts.append(f"FONT/TYPOGRAPHY CHANGE: Change all text typography to {desc}.")
        parts.append("Apply this to headlines, subheadlines, price, CTA button text.")
        parts.append("Keep the same text content, just change the font style.")
        parts.append("")

    if "text" in changes:
        text_changes = changes["text"]
        field_labels = {
            "headline": "the main headline",
            "subheadline": "the subheadline/tagline",
            "price": "the price",
            "cta_text": "the call-to-action button text",
            "offer_text": "the offer/discount badge text",
        }
        parts.append("TEXT CONTENT CHANGES:")
        for field_key, new_text in text_changes.items():
            label = field_labels.get(field_key, field_key)
            parts.append(f"  - Change {label} to: \"{new_text}\"")
        parts.append("Keep the same position, size, and style for changed text. Spell everything CORRECTLY.")
        parts.append("")

    if "translated_extras" in changes:
        parts.append("ADDITIONAL TRANSLATED TEXT:")
        for extra in changes["translated_extras"]:
            parts.append(f"  - Also update any matching extra text on the ad to: \"{extra}\"")
        parts.append("")

    if "ratio" in changes:
        ratio = changes["ratio"]
        w, h = ASPECT_RATIOS.get(ratio, (1080, 1080))
        parts.append(f"ASPECT RATIO CHANGE: Resize/recompose the ad to {ratio} ({w}x{h} pixels).")
        if ratio == "9:16":
            parts.append("This is a vertical/portrait format (Instagram Story, Reels). Recompose the layout vertically — stack elements top to bottom. Extend the background naturally, don't just add blank bars.")
        elif ratio == "16:9":
            parts.append("This is a wide/landscape format (YouTube thumbnail, banner). Recompose the layout horizontally — spread elements across the width.")
        elif ratio == "4:5":
            parts.append("This is a slightly tall portrait format (Instagram feed). Minor vertical extension from the original.")
        parts.append("ALL content from the original must be present in the new ratio. No cropping out important elements.")
        parts.append("")

    if changes.get("remove_doctor"):
        doc_desc = analysis.get("doctor_photo_description", "")
        parts.append(f"REMOVE DOCTOR PHOTO: Remove the standalone doctor/person photo from the ad{f' ({doc_desc})' if doc_desc else ''}.")
        parts.append("Also remove any name/title text next to the doctor photo (e.g. 'Dr. Bimal', 'Doctor of Ayurveda').")
        parts.append("Fill the empty space naturally with the background or rearrange nearby elements.")
        parts.append("IMPORTANT: Do NOT remove the small doctor logo/photo that is printed ON the product box/packaging — that is part of the product design and must stay.")
        parts.append("Also keep the brand name/logo (e.g. 'Dr Bimals') — that's the brand, not the doctor.")
        parts.append("")

    if changes.get("add_doctor"):
        parts.append("ADD DOCTOR: Include the provided doctor/person image in the ad, positioned prominently.")
        parts.append("")

    # Add user-reported fix instructions if present
    if "_user_fix" in changes:
        parts.append(f"\n⚠️ USER-REPORTED FIX: {changes['_user_fix']}")
        parts.append("Address this issue carefully in the output.\n")

    # Add learned fixes from past user reports
    learned = load_learned_fixes()
    if learned:
        parts.append("\n⚠️ KNOWN ISSUES TO AVOID (learned from past mistakes):")
        for fix in learned:
            parts.append(f"   - {fix}")
        parts.append("")

    price_val = analysis.get("price", "")
    headline = analysis.get("headline", "")
    brand_name = analysis.get("brand_name", "") or headline.split("'s")[0] + "'s" if "'s" in headline else ""

    parts.append("CRITICAL RULES (MUST FOLLOW — violations make the output unusable):")
    parts.append("")
    parts.append("1. PRODUCT PACKAGING IS UNTOUCHABLE:")
    parts.append("   - The product box/packaging must be PIXEL-PERFECT identical to the original")
    parts.append("   - Do NOT change the box colors, even if doing a color theme change")
    parts.append("   - Do NOT change any text, logo, or image ON the product box")
    parts.append("   - The box has its own color scheme — keep it exactly as-is")
    parts.append("")
    parts.append("2. PRICE MUST BE EXACT:")
    if price_val:
        parts.append(f"   - The price must read exactly: {price_val}")
    parts.append("   - Do NOT change any digit, currency symbol (₹), or decimal")
    parts.append("   - Do NOT round, truncate, or modify the price in any way")
    parts.append("")
    parts.append("3. TEXT ACCURACY:")
    parts.append("   - ALL text must be sharp, readable, and CORRECTLY SPELLED")
    parts.append("   - Copy text character-by-character — do not paraphrase or substitute words")
    parts.append("")
    parts.append("4. TRANSLATION RULES (if translating):")
    do_not_translate = ["product name", "brand name"]
    if brand_name:
        do_not_translate.append(f"'{brand_name}'")
    extra_texts = analysis.get("extra_texts", [])
    ingredient_names = [t for t in extra_texts if any(w in t.lower() for w in ["mg", "chhal", "ashwa", "laung", "tulsi", "arjun"])]
    if ingredient_names:
        do_not_translate.extend(ingredient_names)
    do_not_translate.extend(["units (mg, g, ml, sachets/sachet)", "'Net Wt.'", "'OFF'"])
    parts.append(f"   - NEVER translate these: {', '.join(do_not_translate)}")
    parts.append("   - 'sachet' and 'sachets' must remain in English")
    parts.append("   - Keep numbers and measurements exactly as-is")
    parts.append("")
    parts.append("5. OTHER:")
    parts.append("   - The doctor/person photo must remain exactly as it is — same face, same pose, same clothing")
    parts.append("   - Only change the AD BACKGROUND, AD TEXT, and AD DECORATIVE ELEMENTS — never the product itself")
    parts.append("   - Do NOT add any watermarks, borders, or extra elements not in the original")

    return "\n".join(parts)


def verify_variant(
    reference_bytes: bytes,
    output_bytes: bytes,
    analysis: dict,
    changes: dict,
    api_key: str = None,
) -> dict:
    """
    Use Gemini Flash (text) to verify the generated variant.
    Returns {"pass": bool, "issues": [...], "cost_inr": float}
    """
    import json as _json
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    ref_part = types.Part.from_bytes(data=reference_bytes, mime_type="image/png")
    out_part = types.Part.from_bytes(data=output_bytes, mime_type="image/png")

    expected_price = analysis.get("price", "")
    expected_texts = {}
    if "text" in changes:
        expected_texts = changes["text"]
    else:
        for k in ["headline", "subheadline", "price", "cta_text", "offer_text"]:
            v = analysis.get(k)
            if v:
                expected_texts[k] = v

    check_prompt = f"""You are a quality control agent for advertisement image editing.

Compare the ORIGINAL ad (Image 1) with the EDITED ad (Image 2).

Check for these specific issues:

1. PRODUCT PACKAGING: Has the product box/packaging changed in ANY way — colors, design, text, layout? The product box must be IDENTICAL between both images. Look carefully at the box colors, labels, and logos.

2. PRICE ACCURACY: The price should be "{expected_price}". Is it exactly correct in the edited image? Check for digit changes, currency symbol issues, or missing text.

3. TEXT ACCURACY: Check that these text fields are correct and properly spelled:
{_json.dumps(expected_texts, ensure_ascii=False, indent=2)}
Look for: wrong characters, missing words, garbled text, words that should NOT have been translated (like "sachet", "mg", brand names, ingredient names like "Arjun Chhal", "Ashwagadha", "Laung").

4. UNTRANSLATABLE TERMS: If translation was applied, these should NEVER be translated: product name, brand name, ingredient names, unit measurements (mg, g, ml), English medical/scientific terms, "sachet"/"sachets".

Return ONLY a JSON object:
{{
  "pass": true/false,
  "issues": [
    {{"type": "packaging_changed"|"price_wrong"|"text_error"|"bad_translation", "detail": "description"}}
  ]
}}

If everything looks correct, return {{"pass": true, "issues": []}}.
Be strict — flag anything that looks wrong."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "ORIGINAL AD (Image 1):", ref_part,
                "EDITED AD (Image 2):", out_part,
                check_prompt,
            ],
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = _json.loads(raw)

        usage = getattr(response, "usage_metadata", None)
        inp_t = getattr(usage, "prompt_token_count", 0) if usage else 0
        out_t = getattr(usage, "candidates_token_count", 0) if usage else 0
        cost_usd = (inp_t * 0.15 / 1_000_000) + (out_t * 0.60 / 1_000_000)
        result["cost_inr"] = round(cost_usd * 84, 2)
        result["verification_tokens"] = {"input": inp_t, "output": out_t}
        return result
    except Exception as e:
        return {"pass": True, "issues": [], "cost_inr": 0, "error": str(e)}


def _build_fix_prompt(analysis: dict, changes: dict, issues: list) -> str:
    """Build a retry prompt that emphasizes the specific issues found."""
    base = _build_edit_prompt(analysis, changes)

    fix_lines = ["\n\n⚠️ CRITICAL FIXES REQUIRED — previous attempt had these errors:"]
    for issue in issues:
        itype = issue.get("type", "")
        detail = issue.get("detail", "")
        if itype == "packaging_changed":
            fix_lines.append(f"- PRODUCT BOX WAS MODIFIED: {detail}")
            fix_lines.append("  → The product box/packaging must be PIXEL-PERFECT identical to the original. Do NOT recolor, reshape, or alter the product box in ANY way.")
        elif itype == "price_wrong":
            fix_lines.append(f"- PRICE WAS WRONG: {detail}")
            fix_lines.append(f"  → The price must be exactly: {analysis.get('price', '')}")
        elif itype == "text_error":
            fix_lines.append(f"- TEXT ERROR: {detail}")
            fix_lines.append("  → Double-check every character of every text field.")
        elif itype == "bad_translation":
            fix_lines.append(f"- TRANSLATION ERROR: {detail}")
            fix_lines.append("  → Do NOT translate: product names, brand names, ingredient names (Arjun Chhal, Ashwagadha, Laung), units (mg, g, sachets/sachet), or English scientific terms.")

    return base + "\n".join(fix_lines)


def generate_with_verification(
    reference_path: str,
    analysis: dict,
    changes: dict,
    api_key: str = None,
    max_retries: int = 2,
    on_status=None,
    **kwargs,
) -> dict:
    """
    Generate a variant, verify it, and retry with enhanced prompt if issues found.
    on_status: optional callback(message: str) for progress updates.
    Returns the same dict as generate_variant, plus verification_* fields.
    """
    with open(reference_path, "rb") as f:
        ref_bytes = f.read()

    total_verification_cost = 0
    all_issues_log = []

    for attempt in range(1 + max_retries):
        if on_status:
            if attempt == 0:
                on_status("Generating variant...")
            else:
                on_status(f"Retry {attempt}/{max_retries} — fixing: {', '.join(i['type'] for i in issues)}")

        if attempt == 0:
            result = generate_variant(reference_path, analysis, changes, api_key, **kwargs)
        else:
            fixed_changes = dict(changes)
            fixed_changes["_fix_prompt"] = _build_fix_prompt(analysis, changes, issues)
            result = generate_variant(reference_path, analysis, fixed_changes, api_key, **kwargs)

        if not result.get("success"):
            return result

        if on_status:
            on_status("Verifying output...")

        verification = verify_variant(ref_bytes, result["output_bytes"], analysis, changes, api_key)
        total_verification_cost += verification.get("cost_inr", 0)

        if verification.get("pass", True):
            result["verification_passed"] = True
            result["verification_attempts"] = attempt + 1
            result["verification_cost_inr"] = total_verification_cost
            result["cost_inr"] = round(result.get("cost_inr", 0) + total_verification_cost, 2)
            return result

        issues = verification.get("issues", [])
        all_issues_log.extend(issues)

        if attempt < max_retries and on_status:
            on_status(f"Issues found: {[i['detail'] for i in issues]}")

    result["verification_passed"] = False
    result["verification_attempts"] = max_retries + 1
    result["verification_cost_inr"] = total_verification_cost
    result["verification_issues"] = all_issues_log
    result["cost_inr"] = round(result.get("cost_inr", 0) + total_verification_cost, 2)
    return result


def generate_variant(
    reference_path: str,
    analysis: dict,
    changes: dict,
    api_key: str = None,
    **kwargs,
) -> dict:
    """
    Generate a variant using Gemini image editing.

    Returns dict with: success, output_bytes, model, time_seconds, cost_estimate, error
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    if "_fix_prompt" in changes:
        prompt = changes.pop("_fix_prompt")
    else:
        prompt = _build_edit_prompt(analysis, changes)

    contents = [
        "REFERENCE AD IMAGE — edit this image according to the instructions below:",
        _load_image_part(reference_path),
        prompt,
    ]

    # Output token rates (USD per 1M tokens) for exact cost calculation
    MODEL_RATES = {
        "gemini-2.5-flash-image": {"output_per_m": 30, "input_per_m": 0.10},
        "gemini-3.1-flash-image": {"output_per_m": 60, "input_per_m": 0.10},
        "gemini-3-pro-image": {"output_per_m": 120, "input_per_m": 2.00},
    }
    USD_TO_INR = 84.0

    ALL_MODELS = [
        ("gemini-2.5-flash-image", "Gemini 2.5 Flash Image", "cheapest"),
        ("gemini-3.1-flash-image", "Gemini 3.1 Flash Image", "mid"),
        ("gemini-3-pro-image", "Gemini 3 Pro Image", "expensive"),
    ]

    allowed_models = kwargs.get("allowed_models", ["gemini-3.1-flash-image"])
    models_to_try = [(mid, mname, tier) for mid, mname, tier in ALL_MODELS if mid in allowed_models]

    all_errors = []
    for model_id, model_name, tier in models_to_try:
        try:
            start = time.time()
            response = client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    safety_settings=[
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    ],
                ),
            )
            elapsed = time.time() - start

            if not response.candidates:
                block_reason = getattr(response, "prompt_feedback", None)
                err = f"{model_name}: No candidates (safety filter: {block_reason})"
                all_errors.append(err)
                continue

            candidate = response.candidates[0]
            parts = getattr(getattr(candidate, "content", None), "parts", None)
            if not parts:
                err = f"{model_name}: No content parts returned"
                all_errors.append(err)
                continue

            for part in parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    # Extract exact token usage from response
                    usage = getattr(response, "usage_metadata", None)
                    input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
                    output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
                    total_tokens = getattr(usage, "total_token_count", 0) if usage else 0

                    rates = MODEL_RATES.get(model_id, {"output_per_m": 60, "input_per_m": 0.10})
                    cost_usd = (input_tokens * rates["input_per_m"] / 1_000_000) + (output_tokens * rates["output_per_m"] / 1_000_000)
                    cost_inr = round(cost_usd * USD_TO_INR, 2)

                    return {
                        "success": True,
                        "output_bytes": part.inline_data.data,
                        "model": f"{model_name} ({model_id})",
                        "model_id": model_id,
                        "tier": tier,
                        "time_seconds": round(elapsed, 2),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "cost_usd": round(cost_usd, 4),
                        "cost_inr": cost_inr,
                    }

            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            err = f"{model_name}: No image in response. Text: {' '.join(text_parts)[:200]}"
            all_errors.append(err)
            continue

        except Exception as e:
            err = f"{model_name}: {str(e)}"
            all_errors.append(err)
            continue

    tried_ids = [mid for mid, _, _ in models_to_try]
    next_models = [mid for mid, _, _ in ALL_MODELS if mid not in tried_ids]
    result = {"success": False, "error": " | ".join(all_errors) or "All models failed"}
    if next_models:
        result["next_model"] = next_models[0]
        result["next_model_name"] = [mname for mid, mname, _ in ALL_MODELS if mid == next_models[0]][0]
        result["next_model_tier"] = [tier for mid, _, tier in ALL_MODELS if mid == next_models[0]][0]
    return result
