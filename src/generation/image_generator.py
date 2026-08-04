import os
import shutil
import cv2
import numpy as np

class ImageGenerator:
    """
    Model-agnostic client for image generation.
    Supports Nano Banana, SDXL, Flux (Mocked for this implementation).
    """
    def __init__(self, output_dir="outputs/scenes"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_scene(self, prompt_path="outputs/final_prompt.txt", model="SDXL"):
        if not os.path.exists(prompt_path):
            print(f"Prompt file {prompt_path} not found.")
            return None

        with open(prompt_path, "r") as f:
            prompt = f.read()

        print(f"Generating scene using {model}...")
        print(f"Prompt: {prompt[:100]}...")

        # MOCK GENERATION: Create a clean background placeholder
        # In a real scenario, this would call an API or load a local model
        width, height = 1024, 1024
        
        # Determine background color based on prompt keywords (heuristic)
        bg_color = (240, 240, 240) # Default light gray
        if "clinic" in prompt.lower():
            bg_color = (255, 250, 245) # Warm sterile white
        elif "nature" in prompt.lower():
            bg_color = (200, 255, 200) # Soft green
        elif "studio" in prompt.lower():
            bg_color = (50, 50, 50) # Dark studio
            
        scene = np.full((height, width, 3), bg_color, dtype=np.uint8)
        
        # Add some "empty space" markers for verification
        cv2.putText(scene, "GENERATED SCENE BACKGROUND", (300, 500), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (150, 150, 150), 2)
        cv2.putText(scene, "Space Reserved for Assets", (350, 550), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)

        output_path = os.path.join(self.output_dir, "generated_scene.png")
        cv2.imwrite(output_path, scene)
        
        print(f"Generated scene saved to {output_path}")
        return output_path

if __name__ == "__main__":
    generator = ImageGenerator()
    generator.generate_scene()
