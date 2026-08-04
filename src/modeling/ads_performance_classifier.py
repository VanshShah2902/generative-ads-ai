"""
ads_performance_classifier.py
=============================
Train a stable XGBoost classifier for advertisement creatives to predict CTR class.
Addresses small dataset size by framing as a classification problem and engineering robust features.

Input:
    ads_features.csv

Output:
    creative_performance_model.pkl
    feature_importance.csv
    performance_plots.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_validate
from sklearn.preprocessing import LabelEncoder

# -------------------------------------------------------
# Configuration
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "ads_features.csv")

MODEL_PATH = os.path.join(BASE_DIR, "creative_performance_model.pkl")
IMPORTANCE_PATH = os.path.join(BASE_DIR, "feature_importance.csv")
PLOT_PATH = os.path.join(BASE_DIR, "performance_plots.png")

# -------------------------------------------------------
# Step 1 — Load Dataset
# -------------------------------------------------------
print("Loading dataset from:", DATA_PATH)
df = pd.read_csv(DATA_PATH)
print("Dataset shape:", df.shape)

# -------------------------------------------------------
# Step 2 — Convert CTR to Performance Classes
# -------------------------------------------------------
def categorize_ctr(ctr):
    if ctr < 1:
        return "Low"
    elif ctr < 2:
        return "Medium"
    else:
        return "High"

df["ctr_class"] = df["ctr"].apply(categorize_ctr)

print("\nCTR Class Distribution:")
print(df["ctr_class"].value_counts())

# -------------------------------------------------------
# Step 4 — Feature Engineering
# -------------------------------------------------------
# Create safe features (avoiding division by zero)
df["text_density"] = df["ocr_text_length"] / (df["object_count"] + 1)
df["color_intensity"] = df["dominant_r"] + df["dominant_g"] + df["dominant_b"]
df["brightness_contrast_ratio"] = df["brightness"] / (df["contrast"] + 1)
df["cta_strength"] = df["cta_present"] + df["cta_in_text"]

# -------------------------------------------------------
# Step 3 & 5 — Prevent Leakage & Feature Selection
# -------------------------------------------------------
leakage_cols = [
    "impressions", "clicks", "cpc", "spend", "frequency", "ctr", "ctr_class"
]

weak_features = [
    "right_object", "left_object", "person_present", "object_count"
]

# Identifiers and strings that shouldn't be used as numerical features straight away
identifier_cols = [
    "ad_id", "ad_name", "brand", "image_path", "page_name", "creative_index", "ad_type"
]

cols_to_drop = leakage_cols + weak_features + identifier_cols

# Select final features
feature_cols = [col for col in df.columns if col not in cols_to_drop]

print("\nFinal Features Used (%d):" % len(feature_cols))
print(feature_cols)

X = df[feature_cols].copy()

# Encode target classes (XGBoost expects numeric labels 0, 1, 2)
# We use LabelEncoder and preserve the mapping for future interpretation
le = LabelEncoder()
y = le.fit_transform(df["ctr_class"])

# -------------------------------------------------------
# Step 6 — Train Model
# -------------------------------------------------------
print("\nInitializing XGBoost Classifier...")
model = XGBClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    random_state=42,
    eval_metric="mlogloss"
)

# -------------------------------------------------------
# Step 7 — Cross Validation
# -------------------------------------------------------
print("Running Stratified K-Fold Cross Validation...")
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Evaluate accuracy and weighted F1 (since classes might be imbalanced)
cv_results = cross_validate(
    model, X, y,
    cv=skf,
    scoring=["accuracy", "f1_weighted"]
)

print("\nCross-Validation Results:")
print(f"Mean Accuracy  : {cv_results['test_accuracy'].mean():.4f}  (std: {cv_results['test_accuracy'].std():.4f})")
print(f"Mean F1 (wght) : {cv_results['test_f1_weighted'].mean():.4f}  (std: {cv_results['test_f1_weighted'].std():.4f})")

# Train final model on entire dataset
model.fit(X, y)

# -------------------------------------------------------
# Step 8 — Feature Importance
# -------------------------------------------------------
importance_scores = model.feature_importances_
importance_df = pd.DataFrame({
    "Feature": feature_cols,
    "Importance": importance_scores
}).sort_values(by="Importance", ascending=False)

print("\nTop 10 Features:")
print(importance_df.head(10).to_string(index=False))

importance_df.to_csv(IMPORTANCE_PATH, index=False)

# -------------------------------------------------------
# Step 9 — Visualization
# -------------------------------------------------------
plt.figure(figsize=(15, 5))

# Plot 1: CTR Distribution
plt.subplot(1, 3, 1)
sns.histplot(df["ctr"], bins=20, kde=True, color="skyblue")
plt.title("Continuous CTR Distribution")
plt.xlabel("CTR (%)")

# Plot 2: CTR Class Distribution
plt.subplot(1, 3, 2)
class_counts = df["ctr_class"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
sns.barplot(x=class_counts.index, y=class_counts.values, palette="viridis")
plt.title("CTR Class Distribution")
plt.ylabel("Count")

# Plot 3: Feature Importance
plt.subplot(1, 3, 3)
top_features = importance_df.head(10)
sns.barplot(
    x="Importance",
    y="Feature",
    data=top_features,
    palette="rocket"
)
plt.title("Top 10 Feature Importances (XGBoost)")

plt.tight_layout()
plt.savefig(PLOT_PATH, dpi=150)

# -------------------------------------------------------
# Step 10 — Output & Save Model
# -------------------------------------------------------
# We save both the model and the label encoder so robust predictions can be made later
pipeline_dict = {
    "model": model,
    "label_encoder": le,
    "features": feature_cols
}
joblib.dump(pipeline_dict, MODEL_PATH)

print("\n" + "="*50)
print("✅ Output complete!")
print(f"Model saved to             : {MODEL_PATH}")
print(f"Feature importance saved to: {IMPORTANCE_PATH}")
print(f"Plots saved to             : {PLOT_PATH}")
print("="*50)
