import json
import os

class CampaignInputProcessor:
    """Converts raw campaign inputs into structured generation parameters."""
    
    def process(self, input_data: dict) -> dict:
        """
        Maps product details to generation payload.
        """
        payload = {
            "product_name": input_data.get("product_name", "Product"),
            "category": input_data.get("category") or input_data.get("product_category", "supplement"),
            "benefits": input_data.get("benefits", []),
            "ingredients": input_data.get("ingredients", []),
            "discount": input_data.get("discount", ""),
            "product_image": input_data.get("product_image"),
            "person_image": input_data.get("person_image"),
            "creative_style": input_data.get("creative_style", "default"),
            "product_position": input_data.get("product_position"),
            "person_position": input_data.get("person_position"),
            "problems": input_data.get("problems", []),
            "solutions": input_data.get("solutions", []),
            "benefit_points": input_data.get("benefit_points", input_data.get("benefits", [])),
            "price": input_data.get("price", ""),
            "offer": input_data.get("offer", ""),
            "brand_name": input_data.get("brand_name", ""),
            "headline": input_data.get("headline", ""),
            "subheadline": input_data.get("subheadline", ""),
            "theme": input_data.get("theme", "KR_2D"),
        }
        
        print(f"[InputProcessor] Generated payload for {payload['product_name']}")
        return payload
