import json
import os
import shutil

# Import modular engines
from src.creative_strategy.creative_strategy_engine import CreativeStrategyEngine
from src.layout_engine.layout_engine import LayoutEngine
from src.scene_generation.scene_prompt_generator import ScenePromptGenerator
from src.composition.composition_spec_generator import CompositionSpecGenerator
from src.copy_generation.copy_generator import CopyGenerator
from src.generation_interface.generation_payload_builder import GenerationPayloadBuilder
from src.prompt_generation.prompt_generator import generate_prompt_from_variation

def run_batch_generation():
    variations_path = "data/campaign_variations.json"
    if not os.path.exists(variations_path):
        print("Campaign variations file not found.")
        return

    with open(variations_path, "r") as f:
        campaign_data = json.load(f)

    variations = campaign_data.get("variations", [])
    output_base = "outputs/campaign_runs"
    os.makedirs(output_base, exist_ok=True)

    # Initialize engines
    strategy_engine = CreativeStrategyEngine()
    layout_engine = LayoutEngine()
    scene_gen = ScenePromptGenerator()
    comp_gen = CompositionSpecGenerator()
    copy_gen = CopyGenerator()
    payload_builder = GenerationPayloadBuilder()

    print(f"Starting batch generation for campaign: {campaign_data.get('campaign_id')}")

    for var in variations:
        var_id = var["variation_id"]
        print(f"Processing {var_id}...")
        
        # 1. Strategy
        strategy_engine.select_strategy(
            var["creative_style"], 
            var["product_category"], 
            var["target_audience"]
        )
        
        # 2. Layout
        cluster_id = var["layout_cluster"].replace("cluster_", "")
        layout_engine.generate_spec(cluster_id)
        
        # 3. Scene Prompt
        scene_gen.generate_prompt()
        
        # 4. Composition
        comp_gen.generate_spec()
        
        # 5. Copy
        copy_gen.generate_copy(var["product_name"], var["product_category"])
        
        # 6. Final Payload
        payload = payload_builder.build_payload()
        
        # Add metadata for scoring (Step 7)
        payload["variation_id"] = var_id
        payload["creative_style"] = var["creative_style"]
        payload["layout_cluster"] = var["layout_cluster"]
        payload["person_type"] = var["person_type"]
        
        # Save payload again with metadata
        with open("generation_input.json", "w") as f:
            json.dump(payload, f, indent=4)
            
        # 7. Backward Compatibility: Generate structured_prompt.json using legacy generator
        # This fulfills Step 5 and 6 requirements
        structured_prompt = generate_prompt_from_variation(var)

        # 8. Organize Folders
        var_dir = os.path.join(output_base, var_id)
        os.makedirs(var_dir, exist_ok=True)
        
        # Move inputs to variation folder
        shutil.copy("generation_input.json", os.path.join(var_dir, "generation_input.json"))
        shutil.copy("structured_prompt.json", os.path.join(var_dir, "structured_prompt.json"))
        
        # Optionally copy other specs for debugging
        shutil.copy("creative_strategy.json", os.path.join(var_dir, "creative_strategy.json"))
        shutil.copy("layout_spec.json", os.path.join(var_dir, "layout_spec.json"))

    print(f"Batch generation complete. Results saved in {output_base}")

if __name__ == "__main__":
    run_batch_generation()
