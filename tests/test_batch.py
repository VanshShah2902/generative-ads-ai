"""Test: Batch API with gemini-3.1-flash-image — 50% cheaper."""
import os, sys, json, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))

from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Load reference image
ref_path = os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 11.png")
with open(ref_path, "rb") as f:
    img_data = f.read()
image_part = types.Part.from_bytes(data=img_data, mime_type="image/png")

# Build 2 simple requests to test batch
prompts = [
    "Edit this advertisement image. Change the color scheme to clinical blue, cool blue tones. Primary: #1a5276, Secondary: #85c1e9. Keep everything else the same.",
    "Edit this advertisement image. Change the color scheme to energetic red, warm red tones. Primary: #922b21, Secondary: #f1948a. Keep everything else the same.",
]

inline_requests = []
for prompt in prompts:
    inline_requests.append({
        "contents": [{
            "parts": [
                {"text": "REFERENCE AD IMAGE — edit this image:"},
                {"inline_data": {"mime_type": "image/png", "data": __import__("base64").b64encode(img_data).decode()}},
                {"text": prompt},
            ],
            "role": "user",
        }],
        "config": {
            "response_modalities": ["IMAGE", "TEXT"],
        },
    })

print(f"Submitting batch of {len(inline_requests)} requests...")
print("This will cost ~50% less than real-time API calls.")
print()

# User approved this test run

try:
    batch_job = client.batches.create(
        model="models/gemini-3.1-flash-image",
        src=inline_requests,
        config={"display_name": "ad-variant-test"},
    )
    print(f"Batch created: {batch_job.name}")
    print(f"State: {batch_job.state}")

    # Poll for completion
    print("\nWaiting for batch to complete...")
    while True:
        batch_job = client.batches.get(name=batch_job.name)
        print(f"  State: {batch_job.state}")
        if batch_job.state in ("JOB_STATE_SUCCEEDED", "COMPLETED", "STATE_SUCCEEDED"):
            break
        if batch_job.state in ("JOB_STATE_FAILED", "FAILED", "STATE_FAILED"):
            print(f"Batch failed!")
            print(batch_job)
            sys.exit(1)
        time.sleep(10)

    print("\nBatch completed! Fetching results...")
    print(batch_job)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
