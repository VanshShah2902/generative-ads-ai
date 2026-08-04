"""
Test the hybrid ad variant pipeline.
Uses reference image as base, modifies only what you ask.

Usage:
    python tests/test_ad_variant.py --reference <path_to_your_ad>
    python tests/test_ad_variant.py --reference <path> --all-variants
    python tests/test_ad_variant.py --reference <path> --change color --change font
"""

import os
import sys
import json
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from src.pipeline.reference_analyzer import analyze_reference
from src.pipeline.ad_compositor import AdCompositor, ASPECT_RATIOS

OUTPUT_DIR = os.path.join(BASE_DIR, "tests", "variant_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PRODUCT_IMAGE = os.path.join(BASE_DIR, "assets", "products", "AT 2 Box.png")
DOCTOR_IMAGE = os.path.join(BASE_DIR, "assets", "people", "dr-bimal-img.jpg")

COLOR_THEMES = {
    "blue_medical": {"primary": "#1a5276", "secondary": "#85c1e9"},
    "red_vitality": {"primary": "#922b21", "secondary": "#f1948a"},
    "purple_premium": {"primary": "#6c3483", "secondary": "#c39bd3"},
    "gold_luxury": {"primary": "#b7950b", "secondary": "#f4d03f"},
    "dark_modern": {"primary": "#1c1c2e", "secondary": "#e74c3c"},
    "teal_fresh": {"primary": "#148f77", "secondary": "#76d7c4"},
}

FONT_PRESETS = ["trust", "premium", "calm", "bold_impact", "modern"]


def run_test(reference_path: str, changes: list, show_analysis: bool = False, cached_analysis: str = None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Step 1: Analyze reference ──
    print(f"\n{'='*60}")
    print(f"  HYBRID AD VARIANT PIPELINE TEST")
    print(f"{'='*60}")

    if cached_analysis and os.path.exists(cached_analysis):
        print(f"\n[1/3] Loading cached analysis: {cached_analysis}")
        with open(cached_analysis, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    else:
        print(f"\n[1/3] Analyzing reference: {reference_path}")
        analysis = analyze_reference(reference_path)

    analysis_path = os.path.join(OUTPUT_DIR, f"analysis_{timestamp}.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    text_elems = [e for e in analysis.get("elements", [])
                  if e.get("type") in ("headline", "subheadline", "body_text", "price", "cta_button", "brand_logo")]
    print(f"  Elements: {len(analysis.get('elements', []))} total, {len(text_elems)} text")
    print(f"  Doctor: {analysis.get('has_doctor')} | Product: {analysis.get('has_product')}")
    print(f"  Layout: {analysis.get('layout', {}).get('type')}")
    print(f"  Palette: primary={analysis.get('color_palette', {}).get('primary')}, "
          f"secondary={analysis.get('color_palette', {}).get('secondary')}")

    if show_analysis:
        for e in text_elems:
            print(f"    [{e['id']}] {e['type']}: \"{e.get('content', '')}\"")

    compositor = AdCompositor(analysis, reference_path)
    variants = []

    def save(img, name):
        path = os.path.join(OUTPUT_DIR, f"{name}_{timestamp}.png")
        img.convert("RGB").save(path, quality=95)
        print(f"    Saved: {os.path.basename(path)}")
        variants.append((name, path))

    # ── Step 2: Baseline (no changes — just proves pipeline works) ──
    print(f"\n[2/3] Generating baseline (no changes)...")
    baseline = compositor.generate()
    save(baseline, "baseline")

    # ── Step 3: Variants ──
    if "color" in changes or "all" in changes:
        print(f"\n[3] COLOR variants...")
        for name, colors in COLOR_THEMES.items():
            img = compositor.generate(changes={"color": colors})
            save(img, f"color_{name}")

    if "font" in changes or "all" in changes:
        print(f"\n[3] FONT variants...")
        for preset in FONT_PRESETS:
            img = compositor.generate(changes={"font": preset})
            save(img, f"font_{preset}")

    if "text" in changes or "all" in changes:
        print(f"\n[3] TEXT variants...")
        headline_ids = [e["id"] for e in text_elems if e["type"] == "headline"]
        sub_ids = [e["id"] for e in text_elems if e["type"] == "subheadline"]
        price_ids = [e["id"] for e in text_elems if e["type"] == "price"]
        cta_ids = [e["id"] for e in text_elems if e["type"] == "cta_button"]

        overrides = {}
        for eid in headline_ids:
            overrides[eid] = "Heart Health Starts Here"
        for eid in sub_ids:
            overrides[eid] = "Trusted by 10,000+ Customers"
        for eid in price_ids:
            overrides[eid] = "₹499"
        for eid in cta_ids:
            overrides[eid] = "Buy Now"

        if overrides:
            img = compositor.generate(changes={"text": overrides})
            save(img, "text_changed")

    if "ratio" in changes or "all" in changes:
        print(f"\n[3] RATIO variants...")
        for ratio_name in ["1:1", "9:16", "4:5", "16:9"]:
            img = compositor.generate(changes={"ratio": ratio_name})
            save(img, f"ratio_{ratio_name.replace(':', 'x')}")

    if "doctor" in changes or "all" in changes:
        print(f"\n[3] DOCTOR variants...")
        img = compositor.generate(changes={"remove_doctor": True})
        save(img, "no_doctor")

    if "layout" in changes or "all" in changes:
        print(f"\n[3] LAYOUT variants...")
        img = compositor.generate(changes={"layout": "mirror"})
        save(img, "layout_mirror")

    if "combo" in changes or "all" in changes:
        print(f"\n[3] COMBO variants...")

        # Blue + modern font + text change
        headline_id = headline_ids[0] if headline_ids else None
        combo_text = {headline_id: "Ayurvedic Heart Care"} if headline_id else {}
        img = compositor.generate(changes={
            "color": COLOR_THEMES["blue_medical"],
            "font": "modern",
            "text": combo_text,
        })
        save(img, "combo_blue_modern_text")

        # Purple + 9:16 + no doctor
        img = compositor.generate(changes={
            "color": COLOR_THEMES["purple_premium"],
            "ratio": "9:16",
            "remove_doctor": True,
        })
        save(img, "combo_purple_9x16_nodoctor")

        # Dark + bold impact + mirror
        img = compositor.generate(changes={
            "color": COLOR_THEMES["dark_modern"],
            "font": "bold_impact",
            "layout": "mirror",
        })
        save(img, "combo_dark_bold_mirror")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Reference: {reference_path}")
    print(f"  Variants: {len(variants)}")
    for name, path in variants:
        print(f"    {name}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Cost: ~₹0.03 (one Gemini Flash call)")
    print(f"  All {len(variants)} variants = ₹0.00 (pure PIL)")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Test hybrid ad variant pipeline")
    parser.add_argument("--reference", type=str, required=True)
    parser.add_argument("--change", action="append", default=[],
                        choices=["color", "font", "layout", "text", "ratio", "doctor", "combo"])
    parser.add_argument("--all-variants", action="store_true")
    parser.add_argument("--show-analysis", action="store_true")
    parser.add_argument("--cached-analysis", type=str, help="Path to cached analysis JSON (skip Gemini call)")
    args = parser.parse_args()

    if not os.path.exists(args.reference):
        print(f"ERROR: Not found: {args.reference}")
        sys.exit(1)

    changes = args.change or []
    if args.all_variants:
        changes = ["all"]
    run_test(args.reference, changes, args.show_analysis, args.cached_analysis)


if __name__ == "__main__":
    main()
