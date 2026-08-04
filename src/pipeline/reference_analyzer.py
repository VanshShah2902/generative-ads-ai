"""
Analyze a reference ad image using Gemini Flash.
Extracts only the editable fields — text the user might change, colors, and doctor presence.
"""

import os
import json
from google import genai


ANALYSIS_PROMPT = """Look at this advertisement image. I need to know ONLY the editable parts — the text a user might want to change and the overall style.

IGNORE all text printed on the product packaging/box itself. Only extract text that is part of the ad layout (headlines, price labels, buttons, etc.).

Return a JSON object with this EXACT structure:

{
    "headline": "the main headline text of the ad",
    "subheadline": "the subheadline or tagline, or null if none",
    "price": "the price shown (e.g. ₹599), or null if none",
    "cta_text": "call-to-action button text (e.g. SHOP NOW), or null if none",
    "offer_text": "any discount/offer badge text (e.g. 24% OFF), or null if none",
    "extra_texts": ["any other editable ad-layout text NOT on the product box itself"],
    "color_palette": {
        "primary": "#hex (dominant brand/background color)",
        "secondary": "#hex (accent color)",
        "text_color": "#hex (headline text color)"
    },
    "has_doctor_photo": true or false,
    "doctor_photo_description": "where the standalone doctor photo is located and how big it is, e.g. 'circular photo on the left side, medium size'. null if no doctor photo. NOTE: a small doctor logo/photo printed ON the product box does NOT count — only a separate standalone doctor photo in the ad layout counts.",
    "layout_type": "single_column|two_column|comparison|hero_product|grid",
    "ad_description": "one sentence describing the ad's visual concept and layout"
}

IMPORTANT:
- Do NOT include text that is part of the product packaging design (brand name on box, ingredient names on box, etc.)
- Only include text that the ad designer placed in the layout
- For has_doctor_photo: a small circular doctor logo on the product box does NOT count. Only a separate, standalone doctor/person photo placed in the ad layout counts.

Return ONLY valid JSON, no markdown formatting."""


def analyze_reference(image_path: str, api_key: str = None) -> dict:
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            ANALYSIS_PROMPT,
            genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)
