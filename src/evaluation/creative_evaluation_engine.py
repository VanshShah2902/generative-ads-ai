"""
creative_evaluation_engine.py
=============================
Evaluate advertisement creatives using a trained XGBoost performance classifier.

Input:
    ads_features.csv
    creative_performance_model.pkl

Output:
    creative_ranked_ads.csv
"""

import os
import numpy as np
import pandas as pd
import joblib

# -------------------------------------------------------
# Configuration
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "ads_features.csv")
MODEL_PATH = os.path.join(BASE_DIR, "creative_performance_model.pkl")
OUTPUT_PATH = os.path.join(BASE_DIR, "creative_ranked_ads.csv")

# -------------------------------------------------------
# Step 1 — Load Model
# -------------------------------------------------------
print("Loading locally saved creative performance model...")
try:
    pipeline_dict = joblib.load(MODEL_PATH)
    model = pipeline_dict["model"]
    le = pipeline_dict["label_encoder"]
    training_features = pipeline_dict["features"]
except FileNotFoundError:
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Was the training script run?")

# -------------------------------------------------------
# Step 2 — Load Dataset
# -------------------------------------------------------
print("Loading dataset...", DATA_PATH)
df = pd.read_csv(DATA_PATH)

# Preserve identifiers for output
identifiers = df[["ad_id", "ad_name"]].copy() if "ad_name" in df.columns else df[["ad_id"]].copy()

# -------------------------------------------------------
# Step 3 & Prepare Features
# -------------------------------------------------------
# Recreate the engineered features from the training pipeline
if "text_density" not in df.columns:
    df["text_density"] = df["ocr_text_length"] / (df["object_count"] + 1)
if "color_intensity" not in df.columns:
    df["color_intensity"] = df["dominant_r"] + df["dominant_g"] + df["dominant_b"]
if "brightness_contrast_ratio" not in df.columns:
    df["brightness_contrast_ratio"] = df["brightness"] / (df["contrast"] + 1)
if "cta_strength" not in df.columns:
    df["cta_strength"] = df["cta_present"] + df["cta_in_text"]

# Keep only the features used during training to prevent leakage
X = df[training_features].copy()

# -------------------------------------------------------
# Step 4 — Predict Performance Class
# -------------------------------------------------------
print("Predicting performance class...")
pred_encoded = model.predict(X)
pred_classes = le.inverse_transform(pred_encoded)
pred_probs = model.predict_proba(X)

identifiers["predicted_class"] = pred_classes

# Find index mapping for the classes
class_indices = {class_name: idx for idx, class_name in enumerate(le.classes_)}

# -------------------------------------------------------
# Step 5 — Create Creative Score
# -------------------------------------------------------
# Convert predicted class probabilities into a creative score between 0 and 100.
# Low -> 0-40, Medium -> 40-70, High -> 70-100
scores = []
for i, pred_class in enumerate(pred_classes):
    probs = pred_probs[i]
    
    # Extract specific class probabilities
    p_low = probs[class_indices.get("Low", 0)]
    p_med = probs[class_indices.get("Medium", 1)]
    p_high = probs[class_indices.get("High", 2)]
    
    # Scale score intuitively based on the predicted class probability bucket
    if pred_class == "High":
        # Base 70, max 100. Higher P(High) -> higher score.
        # Since it's predicted as high, P(High) is usually >= 0.33
        normalized_p = max(0, (p_high - 0.33) / 0.67) 
        score = 70 + (30 * normalized_p)
    elif pred_class == "Medium":
        # Base 40, max 70
        normalized_p = max(0, (p_med - 0.33) / 0.67)
        score = 40 + (30 * normalized_p)
    else: # Low
        # Base 0, max 40. Higher P(Low) means WORSE performance, so lower score.
        normalized_p = max(0, (p_low - 0.33) / 0.67)
        score = 40 - (40 * normalized_p)
        
    # Add a little boost if secondary probability is high
    if pred_class == "Medium" and p_high > p_low:
        score += 5 * p_high
    elif pred_class == "Low" and p_med > p_low:
        score += 5 * p_med
        
    # Cap between 0 and 100
    score = np.clip(score, 0, 100)
    scores.append(round(score, 2))

identifiers["creative_score"] = scores

# -------------------------------------------------------
# Step 6 — Rank Creatives
# -------------------------------------------------------
ranked_df = identifiers.sort_values(by="creative_score", ascending=False).reset_index(drop=True)

# -------------------------------------------------------
# Step 7 — Generate Insights
# -------------------------------------------------------
print("\n" + "="*50)
print("CREATIVE EVALUATION INSIGHTS")
print("="*50)

# Merge back some original visual features for insight generation
eval_df = ranked_df.merge(df[["ad_id", "brightness", "color_intensity", "text_density"]], on="ad_id", how="left")
eval_df = eval_df.drop_duplicates(subset=["ad_id"])

top_ads = eval_df.head(10)

avg_brightness = top_ads["brightness"].mean()
avg_color_intensity = top_ads["color_intensity"].mean()
avg_text_density = top_ads["text_density"].mean()

print(f"Top 10 Ads - Average Brightness    : {avg_brightness:.2f}")
print(f"Top 10 Ads - Average Color Intensity: {avg_color_intensity:.2f}")
print(f"Top 10 Ads - Average Text Density   : {avg_text_density:.2f}")

print("\nDesign Insights for High Performance:")
if avg_brightness > 120:
    print("- Bright, well-lit visuals are strongly correlated with top performance.")
else:
    print("- Darker, moodier tones appear to work better for your audience.")
    
if avg_text_density < 30:
    print("- Low text density is winning. Keep text sparse and let the imagery speak.")
else:
    print("- High text density is performing well. Your audience responds to information-rich creatives.")

if avg_color_intensity > 300:
    print("- High color intensity works best. Vibrant and colorful imagery captures attention.")
else:
    print("- Muted, softer color palettes are performing well in your top tier.")

print("\n" + "="*50)
print("TOP 10 HIGHEST SCORING CREATIVES")
print("="*50)
print(ranked_df.head(10).to_string(index=False))

# -------------------------------------------------------
# Step 8 — Output
# -------------------------------------------------------
output_cols = ["ad_id", "predicted_class", "creative_score"]
if "ad_name" in ranked_df.columns:
    output_cols.insert(1, "ad_name")

ranked_df[output_cols].to_csv(OUTPUT_PATH, index=False)
print("\nCreative rankings saved to:", OUTPUT_PATH)
