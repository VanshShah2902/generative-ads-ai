import os
import sys
import json

# Add current directory to path for imports
sys.path.append(os.getcwd())

from generation_engine.layout_engine import LayoutEngine
from utils.io_utils import load_json

def test_layout_engine():
    print("--- Verifying Layout Anchor Engine (Step 1) ---")
    
    payload_path = "inputs/generation_payload.json"
    if not os.path.exists(payload_path):
        print(f"Error: Payload not found at {payload_path}")
        return

    payload = load_json(payload_path)
    engine = LayoutEngine()

    resolutions = [(512, 512), (1024, 1024), (2048, 2048)]

    for res in resolutions:
        print(f"\nTesting Resolution: {res}")
        try:
            anchors = engine.compute_anchors(payload, res)
            print(json.dumps(anchors, indent=4))
        except Exception as e:
            print(f"Error computing anchors: {e}")

def test_layout_overrides():
    print("\n--- Verifying Payload Overrides (Requested Test Case) ---")
    
    engine = LayoutEngine()
    
    override_payload = {
        "scene_prompt": "medical clinic interior, soft daylight lighting, premium advertising photography",
        "product_position": "center",
        "person_position": "right",
        "text_position": "top",
        "headline": "Doctor Recommended Kapiva Shilajit Resin",
        "subheadline": "Science-backed Ayurvedic supplement for modern wellness",
        "cta": "Get Started",
        "creative_style": "doctor_first",
        "layout_cluster": "cluster_3"
    }

    try:
        res = (1024, 1024)
        print(f"Testing Resolution: {res}")
        anchors = engine.compute_anchors(override_payload, res)
        print(json.dumps(anchors, indent=4))
        
        # Verification of specific anchors
        print("\nValidation:")
        print(f"Product Anchor: {anchors['product_anchor']} (Expected: near center x=512)")
        print(f"Person Anchor: {anchors['person_anchor']} (Expected: near right x=819)")
        print(f"Headline Anchor: {anchors['headline_anchor']} (Expected: top_center x=512, y=153)")
        
    except Exception as e:
        print(f"Override test failed: {e}")

from generation_engine.pipeline_runner import AdGenerationPipeline

def test_full_pipeline():
    print("\n--- Verifying End-to-End Pipeline Execution ---")
    pipeline = AdGenerationPipeline()
    # Now passing a raw campaign input instead of a generation payload
    try:
        results = pipeline.run("inputs/campaigns/arjuna_tea.json", num_variations=3)
        print(f"Generated {len(results)} variations.")
        print(f"Top Creative exported to outputs/campaign_results/top_creatives/")
    except Exception as e:
        print(f"Pipeline failed: {e}")

if __name__ == "__main__":
    test_layout_engine()
    test_layout_overrides()
    test_full_pipeline()
