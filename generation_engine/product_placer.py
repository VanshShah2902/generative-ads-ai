"""
Module for precisely placing product assets onto generated scenes.
"""
import os
import numpy as np
import cv2
from PIL import Image
from utils.compositing_utils import (
    remove_background, scale_asset, match_lighting, composite_with_shadow
)

class ProductPlacer:
    """Handles spatial placement and advanced blending of product images."""
    
    def __init__(self):
        self.output_dir = "outputs/placements"
        os.makedirs(self.output_dir, exist_ok=True)

    def place_product(self, scene_path: str, product_path: str, anchor: tuple, scale: float = 0.33) -> str:
        """
        Places a product image onto a scene with background removal, 
        lighting matching, and soft shadows.
        """
        if not os.path.exists(product_path):
            print(f"[ProductPlacer] Error: Product asset not found at {product_path}")
            return scene_path

        try:
            # 1. Load Images
            scene_img = Image.open(scene_path).convert("RGBA")
            product_img = Image.open(product_path).convert("RGBA")
            
            # 2. Background Removal (if needed)
            product_img = remove_background(product_img)
            
            # 3. Scaling (configurable)
            product_img = scale_asset(product_img, scene_img.size, scale, scale_by='width')
            
            # 4. Lighting Matching
            scene_np = cv2.imread(scene_path)
            product_img = match_lighting(product_img, scene_np, anchor)
            
            # 5. Composite with Shadow
            final_scene = composite_with_shadow(scene_img, product_img, anchor)
            
            # 6. Save result
            output_path = os.path.join(self.output_dir, "scene_with_product.png")
            final_scene.convert("RGB").save(output_path)
            
            print(f"[ProductPlacer] Integrated product saved to {output_path}")
            return output_path

        except Exception as e:
            print(f"[ProductPlacer] Placement failed: {e}")
            return scene_path
