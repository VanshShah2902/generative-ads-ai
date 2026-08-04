import json
import os
import shutil
import sys

# Add root to python path to allow imports from src
sys.path.append(os.getcwd())

# Import modular engines
from src.creative_strategy.creative_strategy_engine import CreativeStrategyEngine
from src.layout_engine.layout_engine import LayoutEngine
from src.scene_generation.scene_prompt_generator import ScenePromptGenerator
from src.composition.composition_spec_generator import CompositionSpecGenerator
from src.copy_generation.copy_generator import CopyGenerator
from src.generation.prompt_assembler import PromptAssembler
from src.generation.image_generator import ImageGenerator
from src.composition.assembly_engine import AssemblyEngine

def run_campaign_pipeline():
    variations_path = "data/campaign_variations.json"
    if not os.path.exists(variations_path):
        print(f"Variations file {variations_path} not found.")
        return

    with open(variations_path, "r") as f:
        campaign_data = json.load(f)

    variations = campaign_data.get("variations", [])
    output_base = "outputs/campaign_runs"
    os.makedirs(output_base, exist_ok=True)

    # Initialize engines once
    strategy_engine = CreativeStrategyEngine()
    layout_engine = LayoutEngine()
    scene_spec_gen = ScenePromptGenerator()
    comp_spec_gen = CompositionSpecGenerator()
    copy_gen = CopyGenerator()
    
    prompt_assembler = PromptAssembler()
    image_generator = ImageGenerator()
    assembly_engine = AssemblyEngine()

    print(f"Starting batch generation for campaign: {campaign_data.get('campaign_id')}")

    for var in variations:
        var_id = var["variation_id"]
        print(f"\n>>> Processing variation: {var_id}")
        
        # 1. Spec Generation Stage
        # Strategy
        strategy_engine.select_strategy(
            var["creative_style"], 
            var["product_category"], 
            var["target_audience"]
        )
        
        # Layout
        cluster_id = var["layout_cluster"].replace("cluster_", "")
        layout_engine.generate_spec(cluster_id)
        
        # Scene Spec
        scene_spec_gen.generate_prompt()
        
        # Composition Spec
        comp_spec_gen.generate_spec()
        
        # Copy Generation
        copy_gen.generate_copy(var["product_name"], var["product_category"])
        
        # 2. Image Generation & Assembly Stage
        # Assemble Prompt
        prompt_assembler.assemble_prompt()
        
        # Generate Scene Background
        image_generator.generate_scene()
        
        # Final Assembly
        assembly_engine.assemble_ad()

        # 3. Organize Output
        var_dir = os.path.join(output_base, var_id)
        os.makedirs(var_dir, exist_ok=True)
        
        # Copy results to variation folder
        shutil.copy("outputs/final_ads/final_ad.png", os.path.join(var_dir, "final_ad.png"))
        shutil.copy("outputs/scenes/generated_scene.png", os.path.join(var_dir, "generated_scene.png"))
        shutil.copy("outputs/final_prompt.txt", os.path.join(var_dir, "final_prompt.txt"))
        
        # Save technical specs for future scoring
        shutil.copy("creative_strategy.json", os.path.join(var_dir, "creative_strategy.json"))
        shutil.copy("layout_spec.json", os.path.join(var_dir, "layout_spec.json"))
        shutil.copy("copy_spec.json", os.path.join(var_dir, "copy_spec.json"))
        
        # Also copy the generation_input if it exists (for backward compatibility)
        if os.path.exists("generation_input.json"):
             shutil.copy("generation_input.json", os.path.join(var_dir, "generation_input.json"))

    print(f"\nCampaign batch generation complete. Results saved to {output_base}")

if __name__ == "__main__":
    run_campaign_pipeline()
