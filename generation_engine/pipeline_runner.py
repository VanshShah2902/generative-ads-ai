"""
Main orchestration module for the AI Advertisement Generation Pipeline.
"""

from .scene_generator import SceneGenerator
from .layout_engine import LayoutEngine
from .assembly_engine import AssemblyEngine
from .creative_variation_engine import CreativeVariationEngine

from src.campaign_input.input_processor import CampaignInputProcessor
from src.layout.template_selector import TemplateSelector
from src.visual_reasoning.scene_planner import ScenePlanner
from src.visual_reasoning.scene_critic import SceneCritic
from src.prompt_generation.prompt_builder import PromptBuilder
from src.copy_generation.copy_generator import CopyGenerator

from src.evaluation.creative_scorer import CreativeScorer
from src.evaluation.creative_selector import CreativeSelector
from src.creative_strategy.competitor_intelligence import CompetitorIntelligence
from src.creative.creative_strategy import CreativeStrategyBuilder

class AdGenerationPipeline:
    """Orchestrates the factory flow from inputs to scored creatives."""
    
    def __init__(self):
        self.input_proc = CampaignInputProcessor()
        self.template_sel = TemplateSelector()
        self.competitor_intel = CompetitorIntelligence()
        self.scene_planner = ScenePlanner()
        self.prompt_builder = PromptBuilder()
        self.copy_gen = CopyGenerator()
        self.scene_critic = SceneCritic()
        self.scene_gen = SceneGenerator()
        self.layout_eng = LayoutEngine()
        self.assembly_eng = AssemblyEngine()
        self.variation_eng = CreativeVariationEngine()
        self.scorer = CreativeScorer()
        self.selector = CreativeSelector()
        self.creative_strategy = CreativeStrategyBuilder()
        
    def run(self, input_path: str, num_variations: int = 5) -> dict:
        """
        Executes the prompt generation stage of the pipeline.
        Generating multiple variations for each cluster.
        """
        import json
        import os
        import datetime
        
        print(f"--- Starting Creative Factory Pipeline for All Clusters ---")
        
        # 1. Load Raw Campaign Input
        with open(input_path, "r") as f:
            raw_input = json.load(f)
        print(f"Step 1: Campaign input loaded from {input_path}")
        
        # 2. Strategic Processing Chain (Base Setup)
        base_payload = self.input_proc.process(raw_input)
        base_payload = self.template_sel.select_template(base_payload)
        competitor_strategy = self.competitor_intel.analyze(base_payload)
        base_payload.update(competitor_strategy)
        
        # Reason about base scene blueprint (ONCE per campaign)
        base_payload = self.scene_planner.plan_scene(base_payload)

        # Save to memory
        from src.memory.product_memory import ProductMemory
        memory = ProductMemory()
        memory.add_product(base_payload)
        
        # 3. Setup Campaign Output Folders
        prompts_dir = os.path.join("outputs", "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # 4. Load Clusters
        clusters = ["product_first", "solution_first", "doctor_first", "ingredient_first", "problem_first"]
        cluster_prompts = {}
        
        # 5. Process each cluster for prompts
        for cluster_id in clusters:
            try:
                print(f"\n[Pipeline] Generating Prompts for {cluster_id}...")
                
                # Create a localized payload for this cluster
                payload = base_payload.copy()
                payload["cluster_id"] = cluster_id
                
                # GROQ — TEXT INTELLIGENCE
                copy = self.copy_gen.generate_copy(payload)
                payload.update(copy)
                
                strategy = self.creative_strategy.build(payload, cluster_id)
                payload["creative_strategy"] = strategy
                print("[Pipeline] Creative Strategy:", strategy)
                
                # A. Build multiple prompts for this specific cluster
                prompts = self.prompt_builder.build_multiple_prompts(
                    payload,
                    cluster_id=cluster_id,
                    blueprint=payload.get("scene_blueprint"),
                    strategy=payload.get("creative_strategy"),
                    num_variations=num_variations
                )
                cluster_prompts[cluster_id] = prompts
                print(f"[Pipeline] {len(prompts)} prompts generated for {cluster_id}")
                
            except Exception as e:
                print(f"[Pipeline ERROR] Cluster {cluster_id} failed: {e}")
                continue
            
        # 6. Save all generated prompts
        prompts_file = os.path.join(prompts_dir, "cluster_prompts.json")
        with open(prompts_file, "w") as f:
            json.dump(cluster_prompts, f, indent=4)
        print(f"[Pipeline] All cluster prompts saved to {prompts_file}")
            
        print(f"--- Pipeline Prompt Generation Complete ---")
        return cluster_prompts

    def generate_from_selected(self):
        """
        Triggers image generation for currently selected prompts.
        Supports multiple selections per cluster.
        """
        import json
        import os
        
        selected_file = "outputs/prompts/selected_prompts.json"
        if not os.path.exists(selected_file):
            print(f"[Pipeline ERROR] No selected prompts found at {selected_file}")
            return
            
        with open(selected_file, "r") as f:
            selected = json.load(f)
            
        # We need the original campaign input to get image paths
        input_path = "inputs/campaign_input.json"
        if os.path.exists(input_path):
            with open(input_path, "r") as f:
                base_info = json.load(f)
        else:
            base_info = {}

        for cluster, prompts in selected.items():
            if not prompts:
                continue
                
            # Handle both single string (legacy) and list of strings
            if isinstance(prompts, str):
                prompts = [prompts]
                
            for i, prompt in enumerate(prompts):
                # Use a suffix if there are multiple prompts for the same cluster
                suffix = f"_{i+1}" if len(prompts) > 1 else ""
                cluster_display = f"{cluster}{suffix}"
                
                print(f"\n[Pipeline] Generating Final Image for {cluster_display}...")
                
                # Use person image ONLY for doctor_first cluster
                use_person_image = base_info.get("person_image") if cluster == "doctor_first" else None
                
                payload = {
                    "scene_prompt": prompt,
                    "cluster_id": cluster_display,
                    "product_image": base_info.get("product_image"),
                    "person_image": use_person_image
                }
                
                try:
                    # GEMINI — IMAGE GENERATION
                    self.scene_gen.generate_scene(payload)
                except Exception as e:
                    print(f"[Pipeline ERROR] Generation failed for {cluster_display}: {e}")
