"""
Module for placing person/subject assets onto generated scenes.
"""
import os
import numpy as np
import cv2
from PIL import Image
from utils.compositing_utils import (
    remove_background, scale_asset, match_lighting, composite_with_shadow
)

class PersonPlacer:
    """Handles spatial placement and advanced blending of person assets."""
    
    def __init__(self):
        self.output_dir = "outputs/placements"
        os.makedirs(self.output_dir, exist_ok=True)

    def place_person(self, scene_path: str, person_path: str, anchor: tuple) -> str:
        """
        Places a person asset onto a scene with background removal, 
        adaptive scaling, and shadow synthesis.
        """
        if not os.path.exists(person_path):
            print(f"[PersonPlacer] Error: person asset not found at {person_path}")
            return scene_path

        try:
            # 1. Load Images
            scene_img = Image.open(scene_path).convert("RGBA")
            person_img = Image.open(person_path).convert("RGBA")
            
            # 2. Background Removal
            person_img = remove_background(person_img)
            
            # 3. Scaling (40-45% of scene height)
            person_img = scale_asset(person_img, scene_img.size, 0.42, scale_by='height')
            
            # 4. Lighting Matching
            scene_np = cv2.imread(scene_path)
            person_img = match_lighting(person_img, scene_np, anchor)
            
            # 5. Composite with Shadow
            final_scene = composite_with_shadow(scene_img, person_img, anchor)
            
            # 6. Save result
            output_path = os.path.join(self.output_dir, "scene_with_person.png")
            final_scene.convert("RGB").save(output_path)
            
            print(f"[PersonPlacer] Integrated person saved to {output_path}")
            return output_path

        except Exception as e:
            print(f"[PersonPlacer] Placement failed: {e}")
            return scene_path
