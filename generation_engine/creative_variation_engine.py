import random
from typing import List

class CreativeVariationEngine:
    """Generates multiple creative variations from a base generation payload."""
    
    def generate_variations(self, payload: dict, num_variations: int = 5) -> List[dict]:
        """
        Processes a base payload into multiple diverse variants.
        
        Args:
            payload (dict): The base generation specification.
            num_variations (int): Number of variations to produce.
            
        Returns:
            List[dict]: A list of modified payload dictionaries.
        """
        print(f"[CreativeVariationEngine] Generating {num_variations} variations...")
        
        variations = []
        positions = ["left", "center", "right"]
        
        for i in range(num_variations):
            variant = payload.copy()
            
            # 1. Layout Variation (Cycle through positions)
            variant["product_position"] = positions[i % len(positions)]
            
            # 2. Scene Diversity (Random Seed)
            variant["scene_seed"] = random.randint(0, 2147483647)
            
            # 3. Copy Variation
            original_headline = payload.get("headline", "")
            if i % 3 == 1:
                # Benefit-focused variation
                variant["headline"] = f"Experience the Power of {original_headline.split()[-1]}"
            elif i % 3 == 2:
                # Short/Urgency variation
                variant["headline"] = f"Try {original_headline.split()[-1]} Today!"
            
            variations.append(variant)
            
        return variations
