"""
compare_analysis.py
===================
Side-by-side comparison: Local (YOLO + OCR + OpenCV) vs Gemini Flash
for analyzing a reference ad image.

Usage:
    .venv_new/Scripts/python tests/compare_analysis.py <image_path>
    .venv_new/Scripts/python tests/compare_analysis.py  # uses a default sample image

Output: prints both analyses side-by-side so you can judge quality.
"""

import os
import sys
import json
import time
import base64
import argparse

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))


# ═══════════════════════════════════════════════════════════════════════════
# METHOD 1: LOCAL ANALYSIS (YOLO + OCR + OpenCV)
# ═══════════════════════════════════════════════════════════════════════════

def run_local_analysis(image_path: str) -> dict:
    """Extract features using local tools only — zero API cost."""
    start = time.time()
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"Could not load image: {image_path}"}

    h, w = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    result = {
        "method": "LOCAL (YOLO + OCR + OpenCV)",
        "image_size": f"{w}x{h}",
        "aspect_ratio": round(w / h, 2),
    }

    # ── 1. Visual Features (OpenCV) ──────────────────────────────────────
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    dom_r = float(np.mean(img_rgb[:, :, 0]))
    dom_g = float(np.mean(img_rgb[:, :, 1]))
    dom_b = float(np.mean(img_rgb[:, :, 2]))
    color_variance = float(np.std(img_rgb))

    # Dominant color name (heuristic)
    max_ch = max(dom_r, dom_g, dom_b)
    if max_ch == dom_r and dom_r > 150:
        dominant_color = "red/warm"
    elif max_ch == dom_g and dom_g > 150:
        dominant_color = "green"
    elif max_ch == dom_b and dom_b > 150:
        dominant_color = "blue"
    elif brightness > 200:
        dominant_color = "white/light"
    elif brightness < 60:
        dominant_color = "dark/black"
    else:
        dominant_color = "neutral/mixed"

    # Color palette extraction (top 5 colors via k-means)
    pixels = img_rgb.reshape(-1, 3).astype(np.float32)
    k = 5
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    palette = []
    for center in centers.astype(int):
        hex_color = "#{:02x}{:02x}{:02x}".format(center[0], center[1], center[2])
        palette.append(hex_color)

    result["visual"] = {
        "brightness": round(brightness, 1),
        "brightness_level": "bright" if brightness > 150 else ("dark" if brightness < 80 else "medium"),
        "contrast": round(contrast, 1),
        "dominant_color": dominant_color,
        "color_palette_hex": palette,
        "color_variance": round(color_variance, 1),
    }

    # ── 2. Layout Analysis (edge density per region) ─────────────────────
    edges = cv2.Canny(gray, 50, 150)

    regions = {
        "top_left":     edges[:h//3, :w//3],
        "top_center":   edges[:h//3, w//3:2*w//3],
        "top_right":    edges[:h//3, 2*w//3:],
        "mid_left":     edges[h//3:2*h//3, :w//3],
        "mid_center":   edges[h//3:2*h//3, w//3:2*w//3],
        "mid_right":    edges[h//3:2*h//3, 2*w//3:],
        "bot_left":     edges[2*h//3:, :w//3],
        "bot_center":   edges[2*h//3:, w//3:2*w//3],
        "bot_right":    edges[2*h//3:, 2*w//3:],
    }

    densities = {name: round(float(np.sum(r)) / (r.size * 255), 4) for name, r in regions.items()}
    busy_regions = [name for name, d in densities.items() if d > 0.08]
    empty_regions = [name for name, d in densities.items() if d < 0.03]

    result["layout"] = {
        "busy_regions": busy_regions,
        "empty_regions": empty_regions,
        "region_densities": densities,
    }

    # ── 3. YOLO Object Detection ────────────────────────────────────────
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        detections = model(img, verbose=False)[0]
        boxes = detections.boxes

        objects = []
        person_present = False
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            cls_ids = boxes.cls.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            names = detections.names

            for i, box in enumerate(xyxy):
                x1, y1, x2, y2 = box
                cls_name = names[int(cls_ids[i])]
                conf = float(confs[i])

                cx = (x1 + x2) / 2 / w
                cy = (y1 + y2) / 2 / h
                area = ((x2 - x1) / w) * ((y2 - y1) / h)

                col = "left" if cx < 0.33 else ("right" if cx > 0.66 else "center")
                row = "top" if cy < 0.33 else ("bottom" if cy > 0.66 else "middle")

                if cls_name == "person":
                    person_present = True

                objects.append({
                    "class": cls_name,
                    "confidence": round(conf, 2),
                    "position": f"{row}_{col}",
                    "area_pct": round(float(area) * 100, 1),
                })

        result["objects"] = {
            "count": len(objects),
            "person_present": person_present,
            "detected": objects[:10],  # cap for readability
        }
    except Exception as e:
        result["objects"] = {"error": str(e)}

    # ── 4. OCR Text Detection ───────────────────────────────────────────
    try:
        import pytesseract
        ocr_text = pytesseract.image_to_string(gray, config="--psm 11")
        words = ocr_text.strip().split()

        CTA_KEYWORDS = {"buy", "shop", "order", "try", "learn", "get", "download",
                        "subscribe", "sign", "book", "explore", "discover", "claim"}
        flat = " ".join(w.lower() for w in words)
        has_cta = any(kw in flat for kw in CTA_KEYWORDS)

        result["text"] = {
            "ocr_text": ocr_text.strip()[:500],
            "word_count": len(words),
            "char_count": len(ocr_text.strip()),
            "cta_detected": has_cta,
        }
    except Exception as e:
        result["text"] = {"error": str(e)}

    # ── 5. Summary (best-effort concept guess) ──────────────────────────
    concept_signals = []
    if result.get("objects", {}).get("person_present"):
        concept_signals.append("has person/model")
    if result.get("text", {}).get("cta_detected"):
        concept_signals.append("has CTA")
    if brightness > 150:
        concept_signals.append("bright/clean aesthetic")
    elif brightness < 80:
        concept_signals.append("dark/dramatic aesthetic")
    if len(busy_regions) <= 3:
        concept_signals.append("minimal layout")
    else:
        concept_signals.append("complex/busy layout")

    result["concept_guess"] = concept_signals

    result["time_seconds"] = round(time.time() - start, 2)
    result["cost"] = "$0.00"
    return result


# ═══════════════════════════════════════════════════════════════════════════
# METHOD 2: GEMINI FLASH ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def run_gemini_analysis(image_path: str) -> dict:
    """Analyze reference image using Gemini 2.0 Flash — semantic understanding."""
    start = time.time()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not found in .env"}

    # Try new SDK first, fall back to legacy
    genai = None
    use_new_sdk = False
    try:
        from google import genai as _genai
        genai = _genai
        use_new_sdk = True
    except ImportError:
        try:
            import google.generativeai as _genai
            genai = _genai
        except ImportError:
            return {"error": "Neither google-genai nor google-generativeai installed. Run: pip install google-genai"}

    if not use_new_sdk:
        genai.configure(api_key=api_key)

    # Read and encode image
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Detect mime type
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = """Analyze this advertisement image in detail. Return a JSON object with these exact fields:

{
    "ad_type": "product_hero / doctor_endorsement / lifestyle / ingredient_showcase / problem_solution / testimonial / comparison / other",
    "creative_concept": "one sentence describing the core creative concept/idea",
    "layout": {
        "composition": "centered / left-right split / top-bottom split / z-pattern / diagonal / grid / asymmetric",
        "person_position": "left / right / center / none",
        "product_position": "left / right / center / bottom / none",
        "text_position": "top / bottom / left / right / overlay",
        "whitespace_usage": "minimal / moderate / generous"
    },
    "visual_style": {
        "lighting": "bright studio / natural / dramatic / warm / clinical / moody",
        "color_palette": ["primary color", "secondary color", "accent color"],
        "mood": "premium / urgent / trustworthy / natural / scientific / playful / clinical",
        "photography_style": "product shot / lifestyle / flat lay / portrait / macro / editorial"
    },
    "text_content": {
        "headline": "exact headline text if readable",
        "subheadline": "exact subheadline if readable",
        "cta": "exact CTA text if present",
        "language": "detected language",
        "text_density": "low / medium / high"
    },
    "elements": {
        "person_present": true/false,
        "person_type": "doctor / model / customer / influencer / none",
        "product_visible": true/false,
        "product_type": "packshot / in-use / illustrated / none",
        "badges_icons": true/false,
        "ingredients_shown": true/false,
        "price_shown": true/false
    },
    "hook_type": "trust / fear / benefit / curiosity / authority / problem / social_proof",
    "emotion": "confidence / urgency / relief / calm / excitement / trust / fear",
    "replication_notes": "key elements to replicate: specific layout positions, color choices, visual hierarchy, and composition rules"
}

Return ONLY valid JSON. No markdown, no explanation, no backticks."""

    try:
        if use_new_sdk:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    prompt,
                    genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
            )
        else:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": image_bytes}
            ])

        # Parse response
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        analysis = json.loads(text)

        # Calculate approximate cost
        # Gemini 2.0 Flash: ~1500 input tokens (image + prompt), ~500 output tokens
        input_cost = 1500 * 0.10 / 1_000_000   # $0.10 per 1M input tokens
        output_cost = 500 * 0.40 / 1_000_000    # $0.40 per 1M output tokens
        total_cost = input_cost + output_cost

        return {
            "method": "GEMINI 2.0 FLASH",
            "analysis": analysis,
            "time_seconds": round(time.time() - start, 2),
            "cost": f"~${total_cost:.5f} (~{total_cost * 85:.3f} INR)",
        }

    except json.JSONDecodeError as e:
        return {
            "method": "GEMINI 2.0 FLASH",
            "error": f"JSON parse error: {e}",
            "raw_response": text[:1000],
            "time_seconds": round(time.time() - start, 2),
        }
    except Exception as e:
        return {
            "method": "GEMINI 2.0 FLASH",
            "error": str(e),
            "time_seconds": round(time.time() - start, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# COMPARISON OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def print_section(title, content, indent=0):
    prefix = "  " * indent
    print(f"{prefix}{'─' * 50}")
    print(f"{prefix}  {title}")
    print(f"{prefix}{'─' * 50}")
    if isinstance(content, dict):
        for k, v in content.items():
            if isinstance(v, dict):
                print(f"{prefix}  {k}:")
                for k2, v2 in v.items():
                    print(f"{prefix}    {k2}: {v2}")
            elif isinstance(v, list):
                print(f"{prefix}  {k}: {v}")
            else:
                print(f"{prefix}  {k}: {v}")
    else:
        print(f"{prefix}  {content}")


def run_comparison(image_path: str):
    print("=" * 70)
    print(f"  REFERENCE IMAGE ANALYSIS COMPARISON")
    print(f"  Image: {image_path}")
    print(f"  Size: {os.path.getsize(image_path) / 1024:.1f} KB")
    print("=" * 70)

    # Run both
    print("\n[1/2] Running LOCAL analysis (YOLO + OCR + OpenCV)...")
    local = run_local_analysis(image_path)

    print("\n[2/2] Running GEMINI FLASH analysis...")
    gemini = run_gemini_analysis(image_path)

    # Display results
    print("\n")
    print("=" * 70)
    print("  LOCAL ANALYSIS RESULTS")
    print(f"  Time: {local.get('time_seconds', '?')}s | Cost: {local.get('cost', '?')}")
    print("=" * 70)

    if "error" in local:
        print(f"  ERROR: {local['error']}")
    else:
        print_section("VISUAL FEATURES", local.get("visual", {}))
        print_section("LAYOUT (edge density)", local.get("layout", {}))
        print_section("OBJECTS (YOLO)", local.get("objects", {}))
        print_section("TEXT (OCR)", local.get("text", {}))
        print_section("CONCEPT GUESS", {"signals": local.get("concept_guess", [])})

    print("\n")
    print("=" * 70)
    print("  GEMINI FLASH ANALYSIS RESULTS")
    print(f"  Time: {gemini.get('time_seconds', '?')}s | Cost: {gemini.get('cost', '?')}")
    print("=" * 70)

    if "error" in gemini:
        print(f"  ERROR: {gemini['error']}")
        if "raw_response" in gemini:
            print(f"  RAW: {gemini['raw_response'][:500]}")
    else:
        analysis = gemini.get("analysis", {})
        print_section("AD TYPE & CONCEPT", {
            "ad_type": analysis.get("ad_type"),
            "concept": analysis.get("creative_concept"),
            "hook": analysis.get("hook_type"),
            "emotion": analysis.get("emotion"),
        })
        print_section("LAYOUT", analysis.get("layout", {}))
        print_section("VISUAL STYLE", analysis.get("visual_style", {}))
        print_section("TEXT CONTENT", analysis.get("text_content", {}))
        print_section("ELEMENTS", analysis.get("elements", {}))
        print_section("REPLICATION NOTES", analysis.get("replication_notes", "N/A"))

    # Save raw JSON for detailed review
    output_dir = os.path.join(BASE_DIR, "tests", "analysis_results")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "local_analysis.json"), "w") as f:
        json.dump(local, f, indent=2, default=str)
    with open(os.path.join(output_dir, "gemini_analysis.json"), "w") as f:
        json.dump(gemini, f, indent=2, default=str)

    print(f"\nRaw JSON saved to: {output_dir}/")

    # Verdict
    print("\n")
    print("=" * 70)
    print("  COMPARISON SUMMARY")
    print("=" * 70)
    print(f"  LOCAL:  {local.get('time_seconds', '?')}s | {local.get('cost', '?')} | Structural data only")
    print(f"  GEMINI: {gemini.get('time_seconds', '?')}s | {gemini.get('cost', '?')} | Semantic understanding")
    print()
    print("  Key differences to evaluate:")
    print("  - Does Gemini correctly identify the ad TYPE/CONCEPT?")
    print("  - Does Gemini give useful REPLICATION NOTES?")
    print("  - Is the local OCR readable or garbled?")
    print("  - Does YOLO detect the right objects/positions?")
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare local vs Gemini image analysis")
    parser.add_argument("image", nargs="?", help="Path to reference ad image")
    args = parser.parse_args()

    if args.image:
        img_path = args.image
    else:
        # Try to find a sample image
        candidates = [
            os.path.join(BASE_DIR, "outputs", "campaigns", "campaign_20260314_042203", "ad_01.png"),
            os.path.join(BASE_DIR, "outputs", "best_creatives", "top_creative_creative_003.png"),
        ]
        # Also check ads_images
        ads_dir = os.path.join(BASE_DIR, "..", "ads_images", "ads_images")
        if os.path.isdir(ads_dir):
            for f in os.listdir(ads_dir)[:1]:
                candidates.append(os.path.join(ads_dir, f))

        img_path = None
        for c in candidates:
            if os.path.exists(c):
                img_path = c
                break

        if not img_path:
            print("No image found. Pass an image path as argument:")
            print("  python tests/compare_analysis.py path/to/ad.png")
            sys.exit(1)

    if not os.path.exists(img_path):
        print(f"Image not found: {img_path}")
        sys.exit(1)

    run_comparison(img_path)
