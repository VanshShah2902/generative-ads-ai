import json
from src.llm.groq_client import GroqClient

class ScenePlanner:
    """Uses LLM reasoning (via Groq) to generate a structured scene blueprint."""
    
    def __init__(self):
        self.llm = GroqClient()
    
    def plan_scene(self, payload: dict) -> dict:
        """
        Plans the visual scene blueprint using LLM reasoning.
        """
        category = (payload.get("category") or payload.get("product_category") or "health").lower()
        style = (payload.get("creative_style") or "default").lower()
        audience = payload.get("target_audience") or "general consumers"
        
        product_name = payload.get("product_name", "")
        benefits = ", ".join(payload.get("benefits", []))
        ingredients = ", ".join(payload.get("ingredients", []))
        
        # Positions from TemplateSelector/LayoutEngine
        prod_pos = payload.get("product_position", "center")
        pers_pos = payload.get("person_position", "")
        text_pos = payload.get("text_position", "top")

        # Competitor Intelligence Context
        cluster_id = payload.get("cluster_id", "N/A")
        layout_style = payload.get("layout_style", "N/A")
        product_scale = payload.get("product_scale", "N/A")
        
        prompt = f"""
        Generate a JSON scene blueprint.
        
        CONTEXT {product_name} ({category}), Benefits: {benefits}, Style: {style}.
        CLUSTER: {cluster_id}.
        
        LAYOUT:
        - Product: {prod_pos}
        - Person: {pers_pos if pers_pos else 'None'}
        - Text: {text_pos}
            
        OUTPUT JSON SCHEMA:
        {{
            "environment": "setting description",
            "background_style": "minimal/artistic style",
            "lighting": "lighting setup",
            "camera_style": "macro/eye-level",
            "product_space": "{prod_pos}",
            "person_space": "{pers_pos}",
            "text_space": "{text_pos}",
            "decor_elements": ["prop 1", "prop 2"]
        }}
        Return ONLY valid JSON. Do NOT wrap in markdown or backticks.
        """
        
        print("[Groq] Generating blueprint logic...")
        
        try:
            response = self.llm.generate(prompt)
            
            # Cleaning Response logic requested
            response = response.strip()

            # Remove markdown code blocks
            if response.startswith("```"):
                response = response.split("```")[1]

            # Remove 'json' label if present
            response = response.replace("json", "").strip()

            print("[ScenePlanner] Cleaned Response:", response[:300])

            blueprint = json.loads(response)
            payload["scene_blueprint"] = blueprint
            print(f"[ScenePlanner] LLM-Generated Strategic Blueprint for: {category}")

        except Exception as e:
            print("[ScenePlanner ERROR]:", e)
            print("[ScenePlanner RAW]:", response)
            raise e
            
        return payload
