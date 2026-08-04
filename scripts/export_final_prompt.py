import os
import json
import sys

# Add the project root to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.campaign_input.input_processor import CampaignInputProcessor
from src.layout.template_selector import TemplateSelector
from src.visual_reasoning.scene_planner import ScenePlanner
from src.prompt_generation.prompt_builder import PromptBuilder

def export_prompt(input_path="inputs/campaigns/arjuna_tea.json"):
    """
    Runs the strategic prompt generation stages and exports the result.
    """
    if not os.path.exists(input_path):
        print(f"Error: Campaign input not found at {input_path}")
        return

    print(f"--- Exporting Final Prompt for: {input_path} ---")

    # 1. Load Raw Campaign Input
    with open(input_path, "r") as f:
        raw_input = json.load(f)

    # 2. Initialize Strategic Modules
    input_proc = CampaignInputProcessor()
    template_sel = TemplateSelector()
    scene_planner = ScenePlanner()
    prompt_builder = PromptBuilder()

    # 3. Run Pipeline Stages
    print("Step 1: Processing campaign input...")
    payload = input_proc.process(raw_input)
    
    print("Step 2: Selecting layout template...")
    payload = template_sel.select_template(payload)
    
    print("Step 3: Planning scene strategy (LLM Reasoning)...")
    payload = scene_planner.plan_scene(payload)
    
    print("Step 4: Building final prompt...")
    prompt = prompt_builder.build_prompt(payload["scene_blueprint"])
    payload["scene_prompt"] = prompt

    # 4. Print results
    print("\n" + "="*50)
    print("GENERATED SCENE PROMPT:")
    print("="*50)
    print(prompt)
    print("="*50 + "\n")

    # 5. Save to file
    output_path = "outputs/final_prompt.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"Prompt successfully exported to: {output_path}")

if __name__ == "__main__":
    # Allow passing input path as argument
    target_input = "inputs/campaigns/arjuna_tea.json"
    if len(sys.argv) > 1:
        target_input = sys.argv[1]
        
    export_prompt(target_input)
