"""Fetch batch results and save images."""
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
batch = client.batches.get(name="batches/h4tjqpfz94fss1upzgy4w8xhj8bjmutzksc5")

labels = ["blue_medical", "red_vitality"]
for i, resp in enumerate(batch.dest.inlined_responses):
    for part in resp.response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.mime_type.startswith("image/"):
            out_path = os.path.join(BASE, "tests", "variant_results", f"batch_{labels[i]}.png")
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"Saved: {out_path} ({len(part.inline_data.data)} bytes)")
