"""Test gemini-2.5-flash-image for ratio-only change — cheapest model."""
import os, sys, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))

from src.pipeline.ai_compositor import generate_variant
import json

ref = os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 11.png")
analysis_path = os.path.join(BASE, "tests", "variant_results", "analysis_20260727_161416.json")
with open(analysis_path, "r") as f:
    analysis = json.load(f)

changes = {"ratio": "1:1"}

print("Testing gemini-2.5-flash-image for ratio-only change (1:1)...")
print(f"Reference: {os.path.basename(ref)}")
print(f"Expected cost: ~Rs 1.75 (batch would be ~Rs 0.88)")
print()

start = time.time()
result = generate_variant(ref, analysis, changes, allowed_models=["gemini-2.5-flash-image"])
elapsed = time.time() - start

if result.get("success"):
    out_path = os.path.join(BASE, "tests", "variant_results", "flash_ratio_1x1.png")
    with open(out_path, "wb") as f:
        f.write(result["output_bytes"])
    print(f"SUCCESS!")
    print(f"  Model: {result['model']}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Input tokens: {result['input_tokens']}")
    print(f"  Output tokens: {result['output_tokens']}")
    print(f"  Cost: Rs {result['cost_inr']} (${result['cost_usd']})")
    print(f"  Saved to: {out_path}")
else:
    print(f"FAILED: {result['error']}")
    print(f"  Time: {elapsed:.1f}s")
