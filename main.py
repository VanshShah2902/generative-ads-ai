import os
import sys
import argparse
from generation_engine.pipeline_runner import AdGenerationPipeline

# For Windows: ensure UTF-8 output for emojis and special symbols
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="AI Advertisement Generation Pipeline")
    parser.add_argument("--input", type=str, default="inputs/campaigns/arjuna_tea.json", help="Path to campaign input JSON")
    parser.add_argument("--variations", type=int, default=3, help="Number of creative variations to generate")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found at {args.input}")
        sys.exit(1)
        
    print(f"--- Launching Production Pipeline ---")
    print(f"Target: {args.input}")
    print(f"Variations: {args.variations}")
    
    pipeline = AdGenerationPipeline()
    try:
        results = pipeline.run(args.input, num_variations=args.variations)
        print(f"\n--- Pipeline Complete ---")
        print(f"Successfully generated {len(results)} creatives.")
        print(f"Results are available in the outputs/campaigns/ directory.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
