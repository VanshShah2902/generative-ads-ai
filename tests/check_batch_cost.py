"""Check exact token usage and cost from batch results."""
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Both batches
batches = [
    ("2-image batch", "batches/h4tjqpfz94fss1upzgy4w8xhj8bjmutzksc5"),
    ("10-image batch", "batches/zfwu0bdcogsyak6yxnopanufagvr3pzvkbso"),
]

for batch_name, batch_id in batches:
    print(f"\n{'='*60}")
    print(f"  {batch_name} ({batch_id})")
    print(f"{'='*60}")

    batch = client.batches.get(name=batch_id)
    total_in = 0
    total_out = 0

    for i, resp in enumerate(batch.dest.inlined_responses):
        u = resp.response.usage_metadata
        print(f"  Image {i+1}: input={u.prompt_token_count}, output={u.candidates_token_count}")

        # Show modality breakdown
        if u.prompt_tokens_details:
            for d in u.prompt_tokens_details:
                print(f"    Input  [{d.modality}]: {d.token_count}")
        if u.candidates_tokens_details:
            for d in u.candidates_tokens_details:
                print(f"    Output [{d.modality}]: {d.token_count}")

        total_in += u.prompt_token_count
        total_out += u.candidates_token_count

    print(f"\n  TOTALS: {total_in} input + {total_out} output")
    print(f"\n  --- Cost estimates ---")
    print(f"  If FULL rate  ($60/1M out): ${total_out * 60 / 1_000_000:.4f} = Rs {total_out * 60 / 1_000_000 * 84:.2f}")
    print(f"  If BATCH 50%  ($30/1M out): ${total_out * 30 / 1_000_000:.4f} = Rs {total_out * 30 / 1_000_000 * 84:.2f}")
    print(f"  Per image (full):  Rs {total_out * 60 / 1_000_000 * 84 / len(batch.dest.inlined_responses):.2f}")
    print(f"  Per image (batch): Rs {total_out * 30 / 1_000_000 * 84 / len(batch.dest.inlined_responses):.2f}")

# Also run a single real-time call to compare token counts
print(f"\n{'='*60}")
print(f"  COMPARISON: Real-time vs Batch token counts")
print(f"{'='*60}")
print(f"  Both use gemini-3.1-flash-image")
print(f"  Output token rate: $60/1M (full) or $30/1M (batch 50% off)")
print(f"\n  When billing updates in 24hrs, compare total spend with:")
print(f"  - If full rate applied to batch: check above 'FULL rate' numbers")
print(f"  - If 50% discount applied: check above 'BATCH 50%' numbers")
