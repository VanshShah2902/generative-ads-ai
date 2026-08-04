"""Quick test: generate 1 variant with ai_compositor."""
import os, sys, json
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))

from src.pipeline.ai_compositor import generate_variant

ref_path = os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 11.png")
analysis_path = os.path.join(BASE, "tests", "variant_results", "analysis_20260727_161416.json")

with open(analysis_path, "r", encoding="utf-8") as f:
    analysis = json.load(f)

changes = {"color": "blue_medical"}
print(f"Reference: {ref_path}")
print(f"Exists: {os.path.exists(ref_path)}")
print(f"Changes: {changes}")
print("Calling Gemini...")

result = generate_variant(ref_path, analysis, changes)
print(f"\nSuccess: {result.get('success')}")
if result.get("success"):
    out = os.path.join(BASE, "tests", "variant_results", "ai_test_blue.png")
    with open(out, "wb") as f:
        f.write(result["output_bytes"])
    print(f"Saved: {out}")
    print(f"Model: {result.get('model')}")
    print(f"Time: {result.get('time_seconds')}s")
else:
    print(f"Error: {result.get('error')}")
