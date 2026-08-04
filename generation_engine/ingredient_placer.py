"""
Module for placing multiple ingredient assets around the product hero.
"""
import os
import random
import numpy as np
import cv2
from PIL import Image
from utils.compositing_utils import remove_background, scale_asset, composite_with_shadow

class IngredientPlacer:
    """Handles the distribution of ingredient images for ingredient-focused ads."""
    
    def __init__(self):
        self.ingredients_dir = "assets/ingredients"
        self.output_dir = "outputs/placements"
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_available_ingredients(self):
        """Scans the assets directory for ingredient images."""
        if not os.path.exists(self.ingredients_dir):
            return []
        return [
            os.path.join(self.ingredients_dir, f) 
            for f in os.listdir(self.ingredients_dir) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]

    def place_ingredients(self, scene_path: str, product_anchor: tuple, count: int = 4) -> str:
        """
        Distributes a set of ingredient images around the product placement area.
        """
        assets = self._get_available_ingredients()
        if not assets:
            print("[IngredientPlacer] No ingredient assets found. Skipping.")
            return scene_path

        try:
            scene_img = Image.open(scene_path).convert("RGBA")
            w, h = scene_img.size
            px, py = product_anchor
            
            # Select random assets
            selected_assets = random.sample(assets, min(count, len(assets)))
            
            for i, asset_path in enumerate(selected_assets):
                print(f"[IngredientPlacer] Placing ingredient: {os.path.basename(asset_path)}")
                ing_img = Image.open(asset_path).convert("RGBA")
                ing_img = remove_background(ing_img)
                
                # Scale appropriately (randomly 10-15% of scene width)
                scale_factor = random.uniform(0.1, 0.15)
                ing_img = scale_asset(ing_img, (w, h), scale_factor, scale_by='width')
                
                # Rotate for organic feel
                ing_img = ing_img.rotate(random.uniform(-30, 30), expand=True)
                
                # Determine placement (around the product anchor)
                # Use a circular/distribution logic
                angle = (2 * np.pi * i) / count
                radius = 200 + random.uniform(-50, 50) # Distance from product
                offset_x = int(radius * np.cos(angle))
                offset_y = int(radius * np.sin(angle))
                
                target_pos = (
                    max(50, min(w-100, px + offset_x)),
                    max(50, min(h-100, py + offset_y))
                )
                
                # Composite
                scene_img = composite_with_shadow(scene_img, ing_img, target_pos)

            output_path = os.path.join(self.output_dir, "scene_with_ingredients.png")
            scene_img.convert("RGB").save(output_path)
            return output_path

        except Exception as e:
            print(f"[IngredientPlacer] Error placing ingredients: {e}")
            return scene_path
