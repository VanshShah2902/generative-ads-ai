import os
import cv2
import numpy as np
import joblib
import pandas as pd
from PIL import Image

class CreativeScorer:
    """Evaluates advertisement creatives using a trained performance model."""
    
    def __init__(self, model_path: str = "models/creative_performance_model.pkl"):
        self.model_path = model_path
        self._load_model()
        
    def _load_model(self):
        """Loads the XGBoost performance model and label encoder."""
        if os.path.exists(self.model_path):
            pipeline_dict = joblib.load(self.model_path)
            self.model = pipeline_dict["model"]
            self.le = pipeline_dict["label_encoder"]
            self.training_features = pipeline_dict["features"]
            print(f"[CreativeScorer] Loaded model from {self.model_path}")
        else:
            self.model = None
            print(f"[CreativeScorer] Warning: Model not found at {self.model_path}. Using heuristic scoring.")

    def extract_features(self, image_path: str, payload: dict) -> dict:
        """
        Extracts visual and logical features from the generated creative.
        """
        img = cv2.imread(image_path)
        if img is None:
            return {}
            
        # 1. Visual Features
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # Dominant Colors
        avg_color_per_row = np.average(img, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        dominant_b, dominant_g, dominant_r = avg_color
        
        # 2. Compositional & Text Features (from Payload)
        ocr_text = f"{payload.get('headline', '')} {payload.get('subheadline', '')} {payload.get('cta', '')}"
        ocr_text_length = len(ocr_text)
        ocr_word_count = len(ocr_text.split())
        
        # Heuristics for features used in training
        features = {
            "brightness": brightness,
            "contrast": contrast,
            "dominant_r": dominant_r,
            "dominant_g": dominant_g,
            "dominant_b": dominant_b,
            "ocr_text_length": ocr_text_length,
            "ocr_word_count": ocr_word_count,
            "cta_present": 1 if payload.get("cta") else 0,
            "cta_in_text": 1 if payload.get("cta") else 0,
            "person_present": 1 if payload.get("person_image") else 0,
            "object_count": 2 if payload.get("person_image") else 1, # Product + Person
            "color_variance": np.var(img),
            # Derived features required by the classifier
            "text_density": ocr_text_length / 3.0, # Approximate
            "color_intensity": dominant_r + dominant_g + dominant_b,
            "brightness_contrast_ratio": brightness / (contrast + 1)
        }
        
        return features

    def _is_placeholder_background(self, img) -> bool:
        """Heuristic to detect the mock grey background."""
        if img is None:
            return False
        # Mock uses (240, 240, 240). Check if the average color is very close and variance is low.
        avg_color = np.mean(img, axis=(0, 1))
        variance = np.var(img)
        
        # Check for the specific mock grey (240, 240, 240)
        is_grey = np.all(np.abs(avg_color - 240) < 5)
        # Mock is very uniform
        is_uniform = variance < 100 
        
        return is_grey and is_uniform

    def score(self, image_path: str, payload: dict) -> dict:
        """
        Predicts performance metrics for a creative.
        """
        features = self.extract_features(image_path, payload)
        img = cv2.imread(image_path)
        
        if self.model:
            # Prepare feature vector for XGBoost
            X = pd.DataFrame([features])
            # Ensure all required features are present
            for col in self.training_features:
                if col not in X.columns:
                    X[col] = 0
            
            X = X[self.training_features]
            
            # Predict
            pred_encoded = self.model.predict(X)[0]
            pred_class = self.le.inverse_transform([pred_encoded])[0]
            pred_probs = self.model.predict_proba(X)[0]
            
            # Engagement Score (0-100) based on class probability
            class_map = {c: i for i, c in enumerate(self.le.classes_)}
            p_high = pred_probs[class_map.get("High", 0)]
            p_med = pred_probs[class_map.get("Medium", 0)]
            
            score = 70 * p_high + 50 * p_med + 30 * (1 - p_high - p_med)
        else:
            # Fallback heuristic score
            score = 50 + (features["brightness"] / 255 * 20)
            pred_class = "N/A"

        # Apply Mock Penalty
        if self._is_placeholder_background(img):
            print(f"[CreativeScorer] Placeholder background detected for {os.path.basename(image_path)}. Applying penalty.")
            score -= 50
            
        return {
            "predicted_ctr_class": pred_class,
            "creative_score": round(max(0, score), 2),
            "visual_metrics": {
                "brightness": round(features["brightness"], 2) if "brightness" in features else 0,
                "color_intensity": round(features["color_intensity"], 2) if "color_intensity" in features else 0
            }
        }
