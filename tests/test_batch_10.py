"""Batch test: 10 images, 3 references, mixed colors + ratios."""
import os, sys, json, time, base64
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 3 reference images
refs = {
    "static11": os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 11.png"),
    "static7": os.path.join(BASE, "tests", "variant_results", "uploaded_AT Weekly Static 7.png"),
    "14in1": os.path.join(BASE, "tests", "variant_results", "uploaded_AT 14-in-1 Static 35.png"),
}

def load_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

ref_b64 = {k: load_b64(v) for k, v in refs.items()}

# 10 jobs: (label, ref_key, prompt)
jobs = [
    ("static11_blue", "static11",
     "Edit this ad image. Change the color scheme to clinical blue, cool blue tones. Primary: #1a5276, Secondary: #85c1e9. Keep everything else exactly the same."),
    ("static11_purple", "static11",
     "Edit this ad image. Change the color scheme to rich purple, premium luxury, royal purple tones. Primary: #6c3483, Secondary: #c39bd3. Keep everything else exactly the same."),
    ("static11_1x1", "static11",
     "Edit this ad image. Resize/recompose to 1:1 square format (1080x1080). Rearrange layout to fit square. ALL content must be present. No cropping important elements."),
    ("static11_9x16", "static11",
     "Edit this ad image. Resize/recompose to 9:16 vertical portrait format (1080x1920). Stack elements top to bottom. Extend background naturally. ALL content must be present."),
    ("static7_teal", "static7",
     "Edit this ad image. Change the color scheme to fresh teal, natural green-blue, calming aqua tones. Primary: #148f77, Secondary: #76d7c4. Keep everything else exactly the same."),
    ("static7_4x5", "static7",
     "Edit this ad image. Resize/recompose to 4:5 portrait format (1080x1350). Slightly taller than original. ALL content must be present. No cropping important elements."),
    ("static7_9x16", "static7",
     "Edit this ad image. Resize/recompose to 9:16 vertical portrait format (1080x1920). Stack elements top to bottom. Extend background naturally. ALL content must be present."),
    ("14in1_red", "14in1",
     "Edit this ad image. Change the color scheme to energetic red, vitality, warm red tones. Primary: #922b21, Secondary: #f1948a. Keep everything else exactly the same."),
    ("14in1_1x1", "14in1",
     "Edit this ad image. Resize/recompose to 1:1 square format (1080x1080). Rearrange layout to fit square. ALL content must be present. No cropping important elements."),
    ("14in1_9x16", "14in1",
     "Edit this ad image. Resize/recompose to 9:16 vertical portrait format (1080x1920). Stack elements top to bottom. Extend background naturally. ALL content must be present."),
]

inline_requests = []
for label, ref_key, prompt in jobs:
    inline_requests.append({
        "contents": [{
            "parts": [
                {"text": "REFERENCE AD IMAGE — edit this image according to the instructions:"},
                {"inline_data": {"mime_type": "image/png", "data": ref_b64[ref_key]}},
                {"text": prompt},
            ],
            "role": "user",
        }],
        "config": {
            "response_modalities": ["IMAGE", "TEXT"],
            "safety_settings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        },
    })

print(f"Submitting batch of {len(inline_requests)} requests to gemini-3.1-flash-image...")
print(f"3 reference images, mixed color + ratio changes")
print(f"Estimated cost: ~₹45 (batch 50% off)")
print()

start_time = time.time()

try:
    batch_job = client.batches.create(
        model="models/gemini-3.1-flash-image",
        src=inline_requests,
        config={"display_name": "ad-batch-10-test"},
    )
    print(f"Batch created: {batch_job.name}")
    print(f"State: {batch_job.state}")
    print()

    print("Waiting for batch to complete...")
    while True:
        batch_job = client.batches.get(name=batch_job.name)
        elapsed = time.time() - start_time
        print(f"  [{elapsed:.0f}s] State: {batch_job.state}")
        if batch_job.state in ("JOB_STATE_SUCCEEDED", "COMPLETED", "STATE_SUCCEEDED"):
            break
        if batch_job.state in ("JOB_STATE_FAILED", "FAILED", "STATE_FAILED"):
            print(f"Batch FAILED!")
            print(batch_job)
            sys.exit(1)
        time.sleep(15)

    total_time = time.time() - start_time
    print(f"\nBatch completed in {total_time:.0f} seconds ({total_time/60:.1f} min)")

    # Save results
    out_dir = os.path.join(BASE, "tests", "variant_results", "batch_10")
    os.makedirs(out_dir, exist_ok=True)

    success = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for i, resp in enumerate(batch_job.dest.inlined_responses):
        label = jobs[i][0]
        response = resp.response

        # Token usage
        usage = response.usage_metadata
        inp_tokens = usage.prompt_token_count if usage else 0
        out_tokens = usage.candidates_token_count if usage else 0
        total_input_tokens += inp_tokens
        total_output_tokens += out_tokens

        if not response.candidates:
            print(f"  [{label}] FAILED: No candidates")
            failed += 1
            continue

        candidate = response.candidates[0]
        parts = getattr(getattr(candidate, "content", None), "parts", None)
        if not parts:
            print(f"  [{label}] FAILED: No content parts")
            failed += 1
            continue

        saved = False
        for part in parts:
            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
                out_path = os.path.join(out_dir, f"{label}.png")
                with open(out_path, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"  [{label}] OK — {len(part.inline_data.data)} bytes | in:{inp_tokens} out:{out_tokens}")
                success += 1
                saved = True
                break

        if not saved:
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            print(f"  [{label}] FAILED: No image. Text: {' '.join(text_parts)[:200]}")
            failed += 1

    # Cost calculation (batch = 50% off: $30/1M output tokens)
    cost_usd = (total_input_tokens * 0.10 / 1_000_000) + (total_output_tokens * 30 / 1_000_000)
    cost_inr = cost_usd * 84

    print(f"\n{'='*50}")
    print(f"RESULTS: {success}/{len(jobs)} succeeded, {failed} failed")
    print(f"Total time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"Total tokens: {total_input_tokens} input + {total_output_tokens} output")
    print(f"Total cost: ${cost_usd:.4f} (₹{cost_inr:.2f})")
    print(f"Cost per image: ${cost_usd/max(success,1):.4f} (₹{cost_inr/max(success,1):.2f})")
    print(f"Saved to: {out_dir}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
