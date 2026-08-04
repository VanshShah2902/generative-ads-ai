import json
import os

class CreativeStrategyEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.frameworks_path = os.path.join(data_dir, "creative_frameworks.json")
        self.frameworks = self._load_frameworks()

    def _load_frameworks(self):
        if os.path.exists(self.frameworks_path):
            with open(self.frameworks_path, "r") as f:
                return json.load(f)
        return {}

    def select_strategy(self, framework_name, product_category, target_audience):
        """
        Selects a strategy based on framework name and context.
        """
        if framework_name in self.frameworks:
            framework = self.frameworks[framework_name]
            strategy = {
                "strategy": framework_name,
                "visual_focus": framework.get("focus", "general"),
                "person_required": framework.get("person_required", False),
                "product_priority": "high" if framework.get("product_scale") == "large" else "medium",
                "text_priority": framework.get("text_priority", "medium"),
                "context": {
                    "product_category": product_category,
                    "target_audience": target_audience
                }
            }
        else:
            # Fallback strategy
            strategy = {
                "strategy": "default",
                "visual_focus": "product",
                "person_required": False,
                "product_priority": "medium",
                "text_priority": "medium",
                "context": {
                    "product_category": product_category,
                    "target_audience": target_audience
                }
            }

        # Save output
        output_path = "creative_strategy.json"
        with open(output_path, "w") as f:
            json.dump(strategy, f, indent=4)
        
        print(f"Creative strategy saved to {output_path}")
        return strategy

if __name__ == "__main__":
    engine = CreativeStrategyEngine()
    # Example usage
    engine.select_strategy("doctor_first", "Health Supplement", "Elderly people")
