"""Test gemini-3.1-flash-image at 512px resolution to reduce cost."""
import os, sys, time, json
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ref_path = os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 11.png")
analysis_path = os.path.join(BASE, "tests", "variant_results", "analysis_20260727_161416.json")
with open(analysis_path, "r") as f:
    analysis = json.load(f)

with open(ref_path, "rb") as f:
    img_data = f.read()

image_part = types.Part.from_bytes(data=img_data, mime_type="image/png")

prompt = """You are given a reference advertisement image. Edit it according to the instructions below.
KEEP everything else EXACTLY the same — same layout, same product, same imagery, same composition.
The output must look like a professional, production-ready advertisement.

COLOR CHANGE: Shift the entire ad's color scheme to fresh teal, natural green-blue, calming aqua tones.
Primary color: #148f77, Secondary/accent: #76d7c4.
Recolor backgrounds, accents, decorative elements, and tints to match the new palette.
Keep product packaging, doctor/person photos, and food/drink items looking natural.

CRITICAL RULES:
- Output MUST be a complete, production-ready advertisement image
- ALL text must be sharp, readable, and CORRECTLY SPELLED
- The PRODUCT BOX/PACKAGING must remain EXACTLY as it is
- Only change the AD BACKGROUND, AD TEXT, and AD DECORATIVE ELEMENTS — never the product itself
- Do NOT add any watermarks, borders, or extra elements not in the original"""

print("Test 1: 512px resolution")
print("=" * 50)
start = time.time()
try:
    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=["REFERENCE AD IMAGE — edit this image:", image_part, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(image_size="512"),
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            ],
        ),
    )
    elapsed = time.time() - start
    usage = response.usage_metadata
    print(f"  Input tokens: {usage.prompt_token_count}")
    print(f"  Output tokens: {usage.candidates_token_count}")
    print(f"  Time: {elapsed:.1f}s")

    # Batch rate: $30/1M output
    cost_usd = usage.candidates_token_count * 30 / 1_000_000
    cost_inr = cost_usd * 84
    print(f"  Batch cost: ${cost_usd:.4f} = Rs {cost_inr:.2f}")

    candidate = response.candidates[0]
    parts = getattr(getattr(candidate, "content", None), "parts", None)
    if parts:
        for part in parts:
            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
                out_path = os.path.join(BASE, "tests", "variant_results", "lowres_512_teal.png")
                with open(out_path, "wb") as f:
                    f.write(part.inline_data.data)
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(part.inline_data.data))
                print(f"  Output size: {img.size[0]}x{img.size[1]}")
                print(f"  Saved: {out_path}")

                # Upscale to 1080
                upscaled = img.resize((1080, 1080), Image.LANCZOS)
                up_path = os.path.join(BASE, "tests", "variant_results", "lowres_512_teal_upscaled.png")
                upscaled.save(up_path)
                print(f"  Upscaled to 1080x1080: {up_path}")
                break
        else:
            print("  No image in response")
    else:
        print("  No content parts")
except Exception as e:
    print(f"  ERROR: {e}")
    elapsed = time.time() - start
    print(f"  Time: {elapsed:.1f}s")
