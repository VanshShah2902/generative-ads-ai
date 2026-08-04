class TemplateSelector:
    """Selects layout templates based on creative strategy and assets."""
    
    def select_template(self, payload: dict) -> dict:
        """
        Determines the layout cluster based on creative style.
        """
        style = payload.get("creative_style", "default")
        
        # Mapping styles to clusters
        style_map = {
            "doctor_endorsement": "cluster_3",
            "lifestyle": "cluster_1",
            "minimal_product": "cluster_2", # Assuming a cluster_2 exists or falls back
            "product_showcase": "cluster_3",
            "problem_first": "cluster_problem_first"
        }
        
        cluster = style_map.get(style, "cluster_3")
        payload["layout_cluster"] = cluster
        
        print(f"[TemplateSelector] Style '{style}' mapped to '{cluster}'")
        return payload
