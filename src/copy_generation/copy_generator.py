from src.llm.groq_client import GroqClient
from src.compliance.nmc_filter import sanitise_headline
import json
import re

class CopyGenerator:
    def __init__(self):
        self.llm = GroqClient()

    def generate_copy(self, payload: dict) -> dict:
        product = payload.get("product_name", "")
        benefits = payload.get("benefits", [])
        problems = payload.get("problems", [])
        solutions = payload.get("solutions", [])
        ingredients = payload.get("ingredients", [])
        cluster = payload.get("cluster_id", payload.get("creative_style", ""))

        prompt = f"""
        You are an expert ad copywriter.

        Generate a high-converting advertisement copy.

        PRODUCT: {product}
        BENEFITS: {benefits}
        PROBLEMS: {problems}
        SOLUTIONS: {solutions}
        INGREDIENTS: {ingredients}
        AD TYPE: {cluster}

        NMC COMPLIANCE RULES (MANDATORY — India National Medical Commission guidelines):
        - NEVER use words: cures, treats, heals, eliminates, reverses, miracle, guaranteed, 100% effective
        - NEVER say "prevents [disease]", "cures [disease]", "treats [disease]"
        - NEVER make absolute health outcome promises — use "helps", "supports", "may help", "promotes"
        - NEVER imply the product replaces medical advice or prescription
        - For doctor-endorsed products: say "formulated by" NOT "prescribed by"
        - Health benefits must be qualified: "Supports healthy cholesterol" NOT "Lowers cholesterol"
        - Compliant examples: "Supports Heart Health", "Helps Maintain Healthy Cholesterol", "Formulated for Wellness"
        - Non-compliant (FORBIDDEN): "Cures Heart Disease", "Lowers Cholesterol Guaranteed", "Prescribed by Doctors"

        COPYWRITING RULES:
        - Headline must be short, bold, attention-grabbing
        - Subheadline must support benefits clearly
        - Subheadline must be maximum 6-10 words
        - Must be short, punchy, and benefit-driven
        - Avoid long sentences
        - Avoid generic phrases like "best product"
        - Make it sound like real ad copy
        - Tone depends on AD TYPE:
          - product_first: premium, product-focused tone
          - solution_first: lead with the SOLUTION and positive outcome — use the SOLUTIONS list above as the headline focus. Tone: relieving, hopeful, outcome-forward.
          - doctor_first: authority, trust
          - ingredient_first: natural, purity
          - problem_first: lead with the PROBLEM in the headline — make it feel relatable and urgent, use the PROBLEMS list above. Tone: empathetic, urgent, then pivots to hope.

        OUTPUT JSON:
        {{
            "headline": "...",
            "subheadline": "..."
        }}

        Return ONLY valid JSON. Do NOT include any explanation or text outside JSON. Do NOT wrap in markdown or backticks.
        """

        print("[Groq] Generating prompt + copy...")
        try:
            response = self.llm.generate(prompt)
            
            # Cleaning Response logic
            response = response.strip()

            # Remove markdown code blocks
            if response.startswith("```"):
                response = response.split("```")[1]

            # Remove 'json' label if present
            response = response.replace("json", "").strip()

            print("[CopyGenerator] Cleaned Response:", response[:300])

            copy = json.loads(response)

            # ── NMC compliance pass on generated copy ─────────────────────
            copy["headline"]    = sanitise_headline(copy.get("headline", ""))
            copy["subheadline"] = sanitise_headline(copy.get("subheadline", ""))

            subheadline = copy.get("subheadline", "")

            # Hard truncate if too long
            words = subheadline.split()
            if len(words) > 10:
                subheadline = " ".join(words[:10])
                copy["subheadline"] = subheadline

            return copy
        except Exception as e:
            print("[CopyGenerator ERROR]:", e)
            print("[CopyGenerator RAW]:", response)
            # Fallback (as before but with more logs)
            return {
                "headline": payload.get("product_name", "Premium Product"),
                "subheadline": "Supports your health naturally."
            }
