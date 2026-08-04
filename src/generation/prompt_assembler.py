import json
import os

class PromptAssembler:
    def __init__(self, data_dir=".", output_dir="outputs"):
        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def assemble_prompt(self):
        files = {
            "scene": "scene_prompt.json",
            "layout": "layout_spec.json",
            "composition": "composition_spec.json",
            "strategy": "creative_strategy.json"
        }
        
        specs = {}
        for key, filename in files.items():
            path = os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    specs[key] = json.load(f)
            else:
                print(f"Warning: {filename} not found.")
                specs[key] = {}

        # Extract components
        scene_prompt = specs.get("scene", {}).get("scene_prompt", "")
        layout_name = specs.get("layout", {}).get("layout", "")
        comp_style = specs.get("layout", {}).get("composition_style", "")
        visual_focus = specs.get("strategy", {}).get("visual_focus", "")
        
        # 3. Load Anchors (New Step)
        anchor_path = os.path.join(self.data_dir, "layout_anchors.json")
        if not os.path.exists(anchor_path):
            anchor_path = os.path.join(self.data_dir, "data", "layout_anchors.json")
            
        anchor_hints = []
        if os.path.exists(anchor_path):
            with open(anchor_path, "r") as f:
                anchors_data = json.load(f)
                anchors = anchors_data.get("anchors", {})
                for key, val in anchors.items():
                    if val.get("hint"):
                        anchor_hints.append(val["hint"])

        # 4. Build final dense prompt
        # Priority: Scene Base + Layout Composition + Reserved Space Rules + Strategy Context + Anchor Hints
        
        prompt_parts = [scene_prompt]
        
        if comp_style:
            prompt_parts.append(f"{comp_style} composition")
            
        if visual_focus:
            prompt_parts.append(f"{visual_focus} focused aesthetic")
            
        # Add Anchor Hints
        if anchor_hints:
            prompt_parts.extend(anchor_hints)
            
        prompt_parts.append("clean minimal background")
        prompt_parts.append("high resolution advertising photography")

        final_prompt = ", ".join([p for p in prompt_parts if p])
        
        # 5. Save output
        output_path = os.path.join(self.output_dir, "final_prompt.txt")
        with open(output_path, "w") as f:
            f.write(final_prompt)
            
        print(f"Final prompt assembled with anchor hints and saved to {output_path}")
        return final_prompt

if __name__ == "__main__":
    assembler = PromptAssembler()
    assembler.assemble_prompt()
