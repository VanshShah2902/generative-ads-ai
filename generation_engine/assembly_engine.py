"""
Module for orchestrating the assembly of advertisement visual components.
"""
import os
import shutil
from .product_placer import ProductPlacer
from .person_placer import PersonPlacer
from .ingredient_placer import IngredientPlacer

class AssemblyEngine:
    """Central composition controller that interprets blueprints and coordinates placement."""
    
    def __init__(self):
        self.product_placer = ProductPlacer()
        self.person_placer = PersonPlacer()
        self.ingredient_placer = IngredientPlacer()

    def assemble(self, scene_path: str, payload: dict, anchors: dict) -> str:
        """
        Coordinates the assembly steps based on layout blueprints.
        """
        style = payload.get("creative_style", "product_first")
        print(f"[AssemblyEngine] Starting assembly for creative style: {style}")
        print("Scene used for assembly:", scene_path)
        
        # Style-based routing
        if style == "doctor_first":
            final_scene = self._assemble_doctor_first(scene_path, payload, anchors)
        elif style == "product_first":
            final_scene = self._assemble_product_first(scene_path, payload, anchors)
        elif style == "ingredients_first":
            final_scene = self._assemble_ingredients_first(scene_path, payload, anchors)
        elif style == "solution_first":
            final_scene = self._assemble_solution_first(scene_path, payload, anchors)
        else:
            # Fallback to general order
            final_scene = self._assemble_product_first(scene_path, payload, anchors)
            
        final_dir = "outputs/final_ads"
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, "final_ad.png")
        shutil.copy(final_scene, final_path)
        
        return final_path

    def _get_scale_factor(self, payload: dict) -> float:
        scale_map = {
            "small": 0.2,
            "medium": 0.33,
            "large": 0.45,
            "extra_large": 0.6
        }
        return scale_map.get(payload.get("product_scale", "medium"), 0.33)

    def _assemble_doctor_first(self, scene_path: str, payload: dict, anchors: dict) -> str:
        """doctor_first: Large subject on left, product on right bottom."""
        current_scene = scene_path
        
        # 1. Place Person (Large)
        if "person_anchor" in anchors:
            person_image = payload.get("person_image", "assets/people/person.png")
            current_scene = self.person_placer.place_person(current_scene, person_image, anchors["person_anchor"])
            
        # 2. Place Product (Right-Bottom focus)
        if "product_anchor" in anchors:
            product_image = payload.get("product_image", "assets/products/product.png")
            scale = self._get_scale_factor(payload)
            current_scene = self.product_placer.place_product(current_scene, product_image, anchors["product_anchor"], scale=scale)
            
        # 3. Ingredient Emphasis (Competitor Pattern)
        if payload.get("ingredient_emphasis"):
            current_scene = self.ingredient_placer.place_ingredients(current_scene, anchors.get("product_anchor", (512, 512)), count=3)

        return current_scene

    def _assemble_product_first(self, scene_path: str, payload: dict, anchors: dict) -> str:
        """product_first: Large centered product."""
        current_scene = scene_path
        
        # 1. Place Product (Hero)
        if "product_anchor" in anchors:
            product_image = payload.get("product_image", "assets/products/product.png")
            scale = self._get_scale_factor(payload)
            current_scene = self.product_placer.place_product(current_scene, product_image, anchors["product_anchor"], scale=scale)
            
        # 2. Add some Ingredients for "natural" feel
        current_scene = self.ingredient_placer.place_ingredients(current_scene, anchors.get("product_anchor", (512, 512)), count=3)

        return current_scene

    def _assemble_ingredients_first(self, scene_path: str, payload: dict, anchors: dict) -> str:
        """ingredients_first: Product centered, many ingredients distributed around it."""
        current_scene = scene_path
        
        # 1. Place Product
        if "product_anchor" in anchors:
            product_image = payload.get("product_image", "assets/products/product.png")
            scale = self._get_scale_factor(payload)
            current_scene = self.product_placer.place_product(current_scene, product_image, anchors["product_anchor"], scale=scale)
            
        # 2. Place many ingredients (5)
        current_scene = self.ingredient_placer.place_ingredients(current_scene, anchors.get("product_anchor", (512, 512)), count=5)
        
        return current_scene

    def _assemble_solution_first(self, scene_path: str, payload: dict, anchors: dict) -> str:
        """solution_first: Split composition, person on left, product on right."""
        current_scene = scene_path
        
        # 1. Place Person
        if "person_anchor" in anchors:
            person_image = payload.get("person_image", "assets/people/person.png")
            current_scene = self.person_placer.place_person(current_scene, person_image, anchors["person_anchor"])
            
        # 2. Place Product
        if "product_anchor" in anchors:
            product_image = payload.get("product_image", "assets/products/product.png")
            scale = self._get_scale_factor(payload)
            current_scene = self.product_placer.place_product(current_scene, product_image, anchors["product_anchor"], scale=scale)
            
        # 3. Ingredient Emphasis (Competitor Pattern)
        if payload.get("ingredient_emphasis"):
            current_scene = self.ingredient_placer.place_ingredients(current_scene, anchors.get("product_anchor", (512, 512)), count=3)

        return current_scene
