import os
import json
import pandas as pd
import pickle

class CompetitorIntelligence:
    """
    Analyzes competitor layout trends and determines the optimal strategy 
    for the current ad generation task.
    """
    
    def __init__(self, data_dir="Imported_things"):
        self.data_dir = data_dir
        self.cluster_summary_path = os.path.join(data_dir, "cluster_summary.csv")
        self.cluster_desc_path = os.path.join(data_dir, "cluster_descriptions.csv")
        self.model_path = os.path.join(data_dir, "layout_model.pkl")
        
    def analyze(self, payload: dict) -> dict:
        """
        Determines the competitor-aware strategy based on campaign style 
        and historical cluster performance/frequency.
        """
        print("[CompetitorIntelligence] Analyzing competitor trends...")
        
        # 1. Load Data
        summary_df = self._load_csv(self.cluster_summary_path)
        desc_df = self._load_csv(self.cluster_desc_path)
        
        # 2. Identify Most Frequent Cluster (Global Trend)
        top_cluster = 3 # Default based on previous analysis
        if summary_df is not None:
            top_cluster = int(summary_df.loc[summary_df['ads_count'].idxmax()]['cluster'])
            
        # 3. Match Style to Strategy
        creative_style = payload.get("creative_style", "product_first")
        
        # Mapping implementation
        strategy = self._map_style_to_cluster(creative_style, top_cluster, desc_df)
        
        print(f"[CompetitorIntelligence] Selected Strategy: Cluster {strategy['cluster_id']} ({strategy['layout_style']})")
        return strategy

    def _load_csv(self, path):
        if os.path.exists(path):
            return pd.read_csv(path)
        return None

    def _map_style_to_cluster(self, style: str, top_cluster: int, desc_df: pd.DataFrame) -> dict:
        """
        Heuristic mapping of campaign styles to competitor layout patterns.
        """
        # Default Strategy (Cluster 3 - Product Focused)
        base_strategy = {
            "cluster_id": top_cluster,
            "layout_style": "product_center",
            "ingredient_emphasis": False,
            "headline_position": "top",
            "product_scale": "large"
        }

        if style == "doctor_endorsement" or style == "doctor_first":
            # Target cluster 5 (lifestyle/multiple elements)
            base_strategy.update({
                "cluster_id": 5, 
                "layout_style": "split_composition",
                "product_scale": "medium",
                "headline_position": "top_center"
            })
        elif style == "product_showcase" or style == "product_first":
            base_strategy.update({
                "cluster_id": 3,
                "layout_style": "product_center",
                "product_scale": "extra_large",
                "headline_position": "top"
            })
        elif style == "benefits_grid" or style == "ingredients_first":
            base_strategy.update({
                "cluster_id": 0,
                "layout_style": "distributed_elements",
                "ingredient_emphasis": True,
                "product_scale": "medium",
                "headline_position": "top"
            })
        elif style == "solution_first":
            base_strategy.update({
                "cluster_id": 2,
                "layout_style": "block_grid",
                "headline_position": "top_center",
                "product_scale": "large"
            })

        return base_strategy

if __name__ == "__main__":
    # Test
    ci = CompetitorIntelligence()
    test_payload = {"creative_style": "ingredients_first"}
    print(ci.analyze(test_payload))
