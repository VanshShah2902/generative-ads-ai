import cv2
import numpy as np
import os

class SceneCritic:
    """Evaluates generated backgrounds using image analysis heuristics."""
    
    def check_scene(self, image_path: str, blueprint: dict) -> dict:
        """
        Runs heuristics to check if the scene is suitable for composition.
        Returns a dict with pass/fail and feedback.
        """
        if not os.path.exists(image_path):
            return {"pass": False, "feedback": "Image file not found"}
            
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return {"pass": False, "feedback": "Failed to load image"}
            
        height, width = img.shape[:2]
        
        # 1. Check for "Empty" Space (Low Entropy/Detail)
        # We look for regions with low edge density or low variance
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        results: dict = {
            "pass": True,
            "feedback": [],
            "metrics": {}
        }
        
        feedback_list: list = results["feedback"]
        metrics_dict: dict = results["metrics"]
        
        # Check Product Space (e.g., if it's "right")
        prod_space = blueprint.get("product_space", "").lower()
        if "right" in prod_space:
            roi = edges[:, int(width*0.6):]
        elif "left" in prod_space:
            roi = edges[:, :int(width*0.4)]
        else: # center
            roi = edges[:, int(width*0.3):int(width*0.7)]
            
        edge_density = float(np.sum(roi) / (roi.size * 255))
        metrics_dict["product_space_edge_density"] = edge_density
        
        if edge_density > 0.15: # Threshold for "too busy"
            results["pass"] = False
            feedback_list.append(f"Product space ({prod_space}) is too busy (density: {edge_density:.2f})")
            
        # 2. Check Brightness Balance
        avg_brightness = float(np.mean(gray))
        metrics_dict["avg_brightness"] = avg_brightness
        
        if avg_brightness < 40: # Too dark
            results["pass"] = False
            feedback_list.append(f"Scene is too dark (avg brightness: {avg_brightness:.1f})")
        elif avg_brightness > 220: # Overexposed
            results["pass"] = False
            feedback_list.append(f"Scene is overexposed (avg brightness: {avg_brightness:.1f})")
            
        if results["pass"]:
            print(f"[SceneCritic] Scene PASSED heuristics (Density: {edge_density:.2f}, Bright: {avg_brightness:.1f})")
        else:
            print(f"[SceneCritic] Scene FAILED: {', '.join(feedback_list)}")
            
        return results
