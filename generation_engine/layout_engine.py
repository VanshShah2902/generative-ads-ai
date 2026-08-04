"""
Module for computing spatial anchors based on ad layout specifications.
"""
import json
import os

class LayoutEngine:
    """Enforces advertisement design structure using a resolution-independent coordinate system."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to the 'configs' folder in the project root (one level up from this file's directory)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.config_dir = os.path.join(project_root, "configs")
        else:
            self.config_dir = config_dir
            
        self.layout_presets = self._load_config("layout_presets.json")
        self.anchor_map = self._load_config("anchor_map.json")
        
        # Mapping for payload overrides
        self.position_mapping = {
            "left": "left_center",
            "right": "right_center",
            "center": "center",
            "top": "top_center"
        }

    def _load_config(self, filename: str) -> dict:
        """Loads a JSON configuration file from the config directory."""
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file {path} not found.")
        with open(path, "r") as f:
            return json.load(f)

    def compute_anchors(self, payload: dict, image_size: tuple) -> dict:
        """
        Calculates pixel coordinates for all ad elements based on layout presets and payload overrides.
        """
        # Step 1: Load Layout Preset
        # Priority: strategy['cluster_id'] -> payload['layout_cluster'] -> default "cluster_3"
        cluster_id = payload.get("cluster_id", "")

        if cluster_id == "problem_first":
            layout_def = {
                "person_position": "left",
                "product_position": "right",
                "text_position": "top",
                "focus": "problem visualization"
            }
            for k, v in layout_def.items():
                if k not in payload:
                    payload[k] = v

        # Normalize cluster names
        if cluster_id in ["product_first", "solution_first", "doctor_first", "ingredient_first", "problem_first"]:
            # Map to existing layout or define mapping
            cluster_id = "cluster_3"
             
        if not cluster_id or (cluster_id not in self.layout_presets):
            print(f"[LayoutEngine] Cluster '{cluster_id}' not found. Falling back to 'cluster_3'.")
            cluster_id = "cluster_3" # Robust fallback
            
        # Get base anchors from preset
        anchors = self.layout_presets[cluster_id].copy()
        
        # Step 2: Apply Payload Overrides
        anchors = self._apply_payload_overrides(payload, anchors)
        
        # Step 3 & 4: Resolve Semantic Anchors and Convert to Pixel Coordinates
        pixel_anchors = {}
        width, height = image_size
        
        for element_key, semantic_name in anchors.items():
            percent_x, percent_y = self._resolve_semantic_anchor(semantic_name)
            pixel_anchors[element_key] = self._convert_to_coordinates((percent_x, percent_y), image_size)
            
        # Step 5: Generate Derived Anchors (Subheadline)
        if "headline_anchor" in pixel_anchors:
            hx, hy = pixel_anchors["headline_anchor"]
            # Subheadline is 6% of image height below the headline
            pixel_anchors["subheadline_anchor"] = (hx, hy + int(0.06 * height))
            
        # Ensure all required keys are present (defaulting to existing anchors if needed)
        # This keeps the output format consistent as requested.
        required_keys = ["product_anchor", "person_anchor", "headline_anchor", "subheadline_anchor", "cta_anchor"]
        result = {}
        for key in required_keys:
            result[key] = pixel_anchors.get(key) or pixel_anchors.get("product_anchor")
            
        return result

    def _resolve_semantic_anchor(self, anchor_name: str) -> tuple:
        """Converts a semantic name to target percentage coordinates."""
        if anchor_name not in self.anchor_map:
            raise ValueError(f"Unknown semantic anchor: '{anchor_name}'. Check anchor_map.json.")
        return tuple(self.anchor_map[anchor_name])

    def _convert_to_coordinates(self, anchor_percent: tuple, image_size: tuple) -> tuple:
        """Multiplies percentages by image dimensions to get pixel coordinates."""
        px, py = anchor_percent
        width, height = image_size
        return (int(px * width), int(py * height))

    def _apply_payload_overrides(self, payload: dict, anchors: dict) -> dict:
        """Replaces preset anchors with positions specified in the payload or strategy."""
        
        # 1. Competitor Strategy Overrides (High Priority)
        layout_style = payload.get("layout_style")
        if layout_style == "product_center":
            anchors["product_anchor"] = "center"
        elif layout_style == "split_composition":
            anchors["person_anchor"] = "left_center"
            anchors["product_anchor"] = "right_center"
            
        headline_pos = payload.get("headline_position")
        if headline_pos in ["top", "top_center"]:
            anchors["headline_anchor"] = "top_center"

        # 2. explicit payload positions (User Overrides)
        overrides = {
            "product_position": "product_anchor",
            "person_position": "person_anchor",
            "text_position": "headline_anchor"
        }
        
        for payload_key, anchor_key in overrides.items():
            pos_val = payload.get(payload_key)
            if pos_val:
                if pos_val in self.position_mapping:
                    anchors[anchor_key] = self.position_mapping[pos_val]
                
        return anchors
