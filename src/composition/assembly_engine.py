import json
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class AssemblyEngine:
    def __init__(self, data_dir=".", output_dir="outputs/final_ads"):
        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def assemble_ad(self, scene_path="outputs/scenes/generated_scene.png"):
        # Load specifications
        files = {
            "comp": "composition_spec.json",
            "copy": "copy_spec.json",
            "layout": "layout_spec.json",
            "anchors": "layout_anchors.json"
        }
        
        specs = {}
        for key, filename in files.items():
            path = filename if os.path.exists(filename) else os.path.join(self.data_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    specs[key] = json.load(f)
            else:
                specs[key] = {}

        if not os.path.exists(scene_path):
            print(f"Scene image {scene_path} not found.")
            return None

        # Load background scene
        scene = cv2.imread(scene_path)
        scene = cv2.cvtColor(scene, cv2.COLOR_BGR2RGB)
        h, w, _ = scene.shape

        anchors = specs.get("anchors", {}).get("anchors", {})

        # 1. Place Person if required
        person_anchor = anchors.get("person_anchor")
        if person_anchor:
            self._place_asset_at_anchor(scene, "PERSON", person_anchor, (100, 150, 255))

        # 2. Place Product
        product_anchor = anchors.get("product_anchor")
        if product_anchor:
            self._place_asset_at_anchor(scene, "PRODUCT", product_anchor, (255, 150, 150))

        # 3. Add Text Overlay
        pil_img = Image.fromarray(scene)
        draw = ImageDraw.Draw(pil_img)
        
        headline_anchor = anchors.get("headline_anchor", {"position": "top_center"})
        cta_anchor = anchors.get("cta_anchor", {"position": "bottom_center"})
        
        # Calculate coordinates based on anchors
        hx, hy = self._get_anchor_coords(headline_anchor["position"], w, h)
        cx, cy = self._get_anchor_coords(cta_anchor["position"], w, h)

        copy = specs.get("copy", {})
        headline = copy.get("headline", "AD HEADLINE")
        subheadline = copy.get("subheadline", "Ad Subheadline Text")
        cta = copy.get("cta", "LEARN MORE")

        draw.text((hx - 100, hy), headline, fill=(0, 0, 0))
        draw.text((hx - 100, hy + 50), subheadline, fill=(60, 60, 60))
        
        # CTA Button
        draw.rectangle([cx - 100, cy, cx + 100, cy + 50], fill=(0, 120, 215))
        draw.text((cx - 40, cy + 15), cta, fill=(255, 255, 255))

        # Save result
        final_ad = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        output_path = os.path.join(self.output_dir, "final_ad.png")
        cv2.imwrite(output_path, final_ad)
        
        print(f"Final advertisement with anchor alignment saved to {output_path}")
        return output_path

    def _get_anchor_coords(self, position, w, h):
        coords = {"x": w//2, "y": h//2}
        if "top" in position: coords["y"] = 100
        if "bottom" in position: coords["y"] = h - 200
        if "left" in position: coords["x"] = 200
        if "right" in position: coords["x"] = w - 200
        return coords["x"], coords["y"]

    def _place_asset_at_anchor(self, scene, label, anchor, color):
        h, w, _ = scene.shape
        aw, ah = 300, 500
        x, y = self._get_anchor_coords(anchor["position"], w, h)
        
        # Adjust x,y to be top-left of asset instead of center-point of anchor
        x -= aw // 2
        y -= ah // 2
        
        # Constrain to screen
        x = max(10, min(x, w - aw - 10))
        y = max(10, min(y, h - ah - 10))
            
        cv2.rectangle(scene, (x, y), (x+aw, y+ah), color, -1)
        cv2.putText(scene, label, (x+50, y+ah//2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

if __name__ == "__main__":
    engine = AssemblyEngine()
    engine.assemble_ad()
