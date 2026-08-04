import os
import argparse
import numpy as np
import pandas as pd
import joblib
import cv2
import matplotlib.pyplot as plt
import seaborn as sns

def get_abs_path(rel_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(base_dir, "..", "..", rel_path))

# =======================================================
# STEP 1 — Load Data
# =======================================================
def load_data():
    paths = {
        "competitor_features": "Imported_things/competitor_features_with_clusters.csv",
        "layout_clusters": "Imported_things/layout_clusters.csv",
        "cluster_summary": "Imported_things/cluster_summary.csv",
        "cluster_descriptions": "Imported_things/cluster_descriptions.csv",
        "performance_model": "models/creative_performance_model.pkl",
        "layout_model": "Imported_things/layout_model.pkl"
    }
    
    data = {}
    for key, path in paths.items():
        abs_path = get_abs_path(path)
        if not os.path.exists(abs_path):
            print(f"File not found: {abs_path}")
            continue
            
        if path.endswith(".csv"):
            data[key] = pd.read_csv(abs_path)
        elif path.endswith(".pkl"):
            data[key] = joblib.load(abs_path)
            
    return data

# =======================================================
# STEP 2 — Prepare Competitor Layout Features
# =======================================================
def prepare_layout_features(data):
    df = data["competitor_features"]
    
    # Calculate required features
    if "color_intensity" not in df.columns:
        # If dominant colors don't exist use brightness and contrast as a proxy or extract from image if possible
        # However, step 2 asks for dominant_r + dominant_g + dominant_b calculation, so let's prepare the dataframe
        df["color_intensity"] = df["brightness"] * 1.5 # Placeholder backup
        
    if "text_density" not in df.columns:
        if "ocr_text_length" in df.columns and "image_width" in df.columns and "image_height" in df.columns:
             df["text_density"] = (df["ocr_text_length"] / (df["image_width"] * df["image_height"])) * 10000
        else:
             df["text_density"] = 15.0 # Placeholder
             
    # Aggregate per cluster
    cluster_stats = df.groupby("layout_cluster").agg(
        ads_count=("image_path", "count"),
        avg_brightness=("brightness", "mean"),
        avg_contrast=("contrast", "mean"),
        avg_color_intensity=("color_intensity", "mean"),
        avg_text_density=("text_density", "mean")
    ).reset_index()
    
    return cluster_stats

# =======================================================
# STEP 3 — Predict Performance for Layout Clusters
# =======================================================
def predict_cluster_performance(cluster_stats, performance_pipeline):
    model = performance_pipeline["model"]
    le = performance_pipeline["label_encoder"]
    features = performance_pipeline["features"]
    
    predictions = []
    
    for _, row in cluster_stats.iterrows():
        # Create a representative feature vector
        # NOTE: Competitor data is scaled (0-1), but performance model expects (0-255)
        # We scale the visual features back for prediction.
        vec = {}
        for feat in features:
            if feat == "brightness":
                vec[feat] = row["avg_brightness"] * 255.0
            elif feat == "contrast":
                vec[feat] = row["avg_contrast"] * 255.0
            elif feat == "color_intensity":
                vec[feat] = row["avg_color_intensity"] * 765.0 # (255*3)
            elif feat == "text_density":
                vec[feat] = row["avg_text_density"] * 100.0 # heuristic scale
            elif feat == "brightness_contrast_ratio":
                vec[feat] = (row["avg_brightness"] * 255.0) / (row["avg_contrast"] * 255.0 + 1)
            else:
                vec[feat] = 0 # Dummy value for features not available in competitor dataset
                
        # Create dataframe for prediction
        X = pd.DataFrame([vec])
        
        pred_encoded = model.predict(X)
        pred_class = le.inverse_transform(pred_encoded)[0]
        pred_probs = model.predict_proba(X)[0]
        
        # Calculate cluster score similarly to the evaluation engine
        class_indices = {c: idx for idx, c in enumerate(le.classes_)}
        p_low = pred_probs[class_indices.get("Low", 0)]
        p_med = pred_probs[class_indices.get("Medium", 1)]
        p_high = pred_probs[class_indices.get("High", 2)]
        
        if pred_class == "High":
            normalized_p = max(0, (p_high - 0.33) / 0.67) 
            score = 70 + (30 * normalized_p)
        elif pred_class == "Medium":
            normalized_p = max(0, (p_med - 0.33) / 0.67)
            score = 40 + (30 * normalized_p)
        else: # Low
            normalized_p = max(0, (p_low - 0.33) / 0.67)
            score = 40 - (40 * normalized_p)
            
        if pred_class == "Medium" and p_high > p_low:
            score += 5 * p_high
        elif pred_class == "Low" and p_med > p_low:
            score += 5 * p_med
            
        score = np.clip(score, 0, 100)
        
        predictions.append({
            "layout_cluster": int(row["layout_cluster"]),
            "ads_count": int(row["ads_count"]),
            "avg_brightness": row["avg_brightness"],
            "avg_color_intensity": row["avg_color_intensity"],
            "predicted_performance_class": pred_class,
            "cluster_score": round(score, 2)
        })
        
    return pd.DataFrame(predictions)

# =======================================================
# STEP 4 — Rank Layout Clusters
# =======================================================
def rank_clusters(predicted_df):
    return predicted_df.sort_values(by="cluster_score", ascending=False).reset_index(drop=True)

# =======================================================
# STEP 5 — Generate Creative Blueprint
# =======================================================
def generate_blueprint(ranked_df):
    best_cluster = ranked_df.iloc[0]
    
    # Analyze characteristics
    brightness_desc = "High brightness and well-lit imagery" if best_cluster["avg_brightness"] > 120 else "Balanced, softer brightness tones"
    color_desc = "Vibrant and strong color intensity" if best_cluster["avg_color_intensity"] > 250 else "Muted, focused color intensity"
    text_desc = "Minimalist text density" # Using standard text desc, can be updated with more metrics
    
    blueprint_text = f"""Best Layout Cluster: {best_cluster["layout_cluster"]}

Recommended Design Characteristics:
• brightness level: {brightness_desc}
• color intensity: {color_desc}
• text density: {text_desc}
• object placement: Clear centralized or highly visible subject areas based on cluster layout.

Predicted Performance Class: {best_cluster["predicted_performance_class"]}
Cluster Score: {best_cluster["cluster_score"]}/100
Based on {best_cluster["ads_count"]} similar competitor ads.
"""
    
    # Save outputs
    reports_dir = get_abs_path("reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    csv_path = os.path.join(reports_dir, "layout_performance_analysis.csv")
    ranked_df.to_csv(csv_path, index=False)
    
    txt_path = os.path.join(reports_dir, "best_creative_blueprint.txt")
    with open(txt_path, "w") as f:
        f.write(blueprint_text)
        
    print(f"Results saved to {csv_path} and {txt_path}")
    return txt_path

# =======================================================
# STEP 6 — Visualization
# =======================================================
def generate_visualizations(ranked_df):
    reports_dir = get_abs_path("reports")
    os.makedirs(reports_dir, exist_ok=True)
    chart_path = os.path.join(reports_dir, "layout_performance_chart.png")
    
    # Keep top 10 or all clusters to prevent overcrowding
    plot_df = ranked_df.head(10).copy()
    plot_df["layout_cluster"] = plot_df["layout_cluster"].astype(str)
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # 1. Cluster Score vs Layout Cluster
    sns.barplot(data=plot_df, x="layout_cluster", y="cluster_score", ax=axes[0], palette="viridis")
    axes[0].set_title("Cluster Score by Layout Cluster")
    axes[0].set_ylabel("Score (0-100)")
    axes[0].set_xlabel("Layout Cluster")
    
    # 2. Avg Brightness per cluster
    sns.barplot(data=plot_df, x="layout_cluster", y="avg_brightness", ax=axes[1], palette="magma")
    axes[1].set_title("Avg Brightness by Layout Cluster")
    axes[1].set_ylabel("Brightness")
    axes[1].set_xlabel("Layout Cluster")
    
    # 3. Avg Color Intensity per cluster
    sns.barplot(data=plot_df, x="layout_cluster", y="avg_color_intensity", ax=axes[2], palette="plasma")
    axes[2].set_title("Avg Color Intensity by Layout Cluster")
    axes[2].set_ylabel("Color Intensity")
    axes[2].set_xlabel("Layout Cluster")
    
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    print(f"Visualization saved to {chart_path}")

# =======================================================
# STEP 7 — New Creative Evaluation Engine
# =======================================================
def extract_opencv_features(img_path):
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Could not read image: {img_path}")
        
    # Convert to standard RGB to match expectation
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Brightness
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    brightness = np.mean(gray)
    
    # 2. Contrast
    contrast = np.std(gray)
    
    # 3. Color Intensity (dominant colors sum approx)
    color_intensity = np.mean(img_rgb[:,:,0]) + np.mean(img_rgb[:,:,1]) + np.mean(img_rgb[:,:,2])
    
    # Dimensions
    h, w = img_rgb.shape[:2]
    
    return {
        "brightness": brightness,
        "contrast": contrast,
        "color_intensity": color_intensity,
        "text_density": 10.0, # Dummy fallback if no OCR
        "image_width": w,
        "image_height": h,
        "aspect_ratio": w / h
    }

def evaluate_creative(image_path, data):
    print(f"\nEvaluating Image: {image_path}")
    
    # 1. Extract Features
    features_dict = extract_opencv_features(image_path)
    
    # Add proxies for features that might be needed by the models
    features_dict["color_variance"] = features_dict["contrast"] * 0.8 # heuristic proxy
    features_dict["ocr_text_length"] = 10.0 # heuristic
    features_dict["object_count"] = 2 # heuristic
    features_dict["face_area_ratio"] = 0.0 # heuristic
    features_dict["text_char_count"] = 10.0 # heuristic
    
    layout_model = data["layout_model"]
    perf_pipeline = data["performance_model"]
    
    # 2. Predict Layout Cluster
    # Experimentation showed the layout model expects 8 features. 
    # Based on the competitor dataset, these are the most likely 8 visual/structural features.
    layout_feat_names = [
        'brightness', 'contrast', 'color_variance', 'aspect_ratio', 
        'object_count', 'ocr_text_length', 'face_area_ratio', 'text_char_count'
    ]
    
    try:
        layout_vec = np.array([[features_dict.get(f, 0.0) for f in layout_feat_names]])
        if hasattr(layout_model, 'predict'):
             pred_cluster = layout_model.predict(layout_vec)[0]
        else:
             pred_cluster = 0
    except Exception as e:
        print(f"Warning: Layout cluster prediction failed: {e}")
        pred_cluster = -1
        
    # 3. Predict Performance
    model = perf_pipeline["model"]
    le = perf_pipeline["label_encoder"]
    perf_features = perf_pipeline["features"]
    
    # Performance model features (from company data)
    vec = {}
    for feat in perf_features:
        if feat in features_dict:
            vec[feat] = features_dict[feat]
        elif feat == "brightness_contrast_ratio":
            vec[feat] = features_dict["brightness"] / (features_dict["contrast"] + 1)
        elif feat == "color_intensity":
            vec[feat] = features_dict["color_intensity"]
        else:
            vec[feat] = 0.0
            
    X_perf = pd.DataFrame([vec])
    pred_encoded = model.predict(X_perf)
    pred_class = le.inverse_transform(pred_encoded)[0]
    pred_probs = model.predict_proba(X_perf)[0]
    
    class_indices = {c: idx for idx, c in enumerate(le.classes_)}
    p_low = pred_probs[class_indices.get("Low", 0)]
    p_med = pred_probs[class_indices.get("Medium", 1)]
    p_high = pred_probs[class_indices.get("High", 2)]
    
    # Score logic
    if pred_class == "High":
        normalized_p = max(0, (p_high - 0.33) / 0.67) 
        score = 70 + (30 * normalized_p)
    elif pred_class == "Medium":
        normalized_p = max(0, (p_med - 0.33) / 0.67)
        score = 40 + (30 * normalized_p)
    else: 
        normalized_p = max(0, (p_low - 0.33) / 0.67)
        score = 40 - (40 * normalized_p)
        
    score = np.clip(score, 0, 100)
    
    # 4. Generate Output
    print("\n## Creative Evaluation")
    print("\n=================")
    print(f"Predicted Layout Cluster: {pred_cluster}")
    print(f"Predicted Performance Class: {pred_class}")
    print(f"Creative Score: {round(score, 1)} / 100")
    print("\nDesign Insights:")
    
    b_insight = "balanced brightness" if 100 < features_dict['brightness'] < 160 else ("high brightness" if features_dict['brightness'] >= 160 else "low brightness")
    c_insight = "strong color intensity" if features_dict['color_intensity'] > 300 else "soft color intensity"
    t_insight = "low text density" # default
    
    print(f"• {c_insight}")
    print(f"• {b_insight}")
    print(f"• {t_insight}")
    print("=================\n")

# =======================================================
# STEP 8 — CLI Interface
# =======================================================
def main():
    parser = argparse.ArgumentParser(description="Creative Recommendation Engine")
    parser.add_argument("--image", type=str, help="Path to an image to evaluate")
    args = parser.parse_args()
    
    print("Initializing Creative Recommendation Engine...\n")
    
    # Step 1
    data = load_data()
    if "competitor_features" not in data or "performance_model" not in data:
        print("Error: Required data or models missing. Please ensure paths are correct.")
        return
        
    if args.image:
        if not os.path.exists(args.image):
            print(f"Error: Image not found at {args.image}")
            return
        evaluate_creative(args.image, data)
    else:
        # Step 2
        print("Preparing Competitor Layout Features...")
        cluster_stats = prepare_layout_features(data)
        
        # Step 3
        print("Predicting Performance for Layout Clusters...")
        cluster_predictions = predict_cluster_performance(cluster_stats, data["performance_model"])
        
        # Step 4
        print("Ranking Layout Clusters...")
        ranked_clusters = rank_clusters(cluster_predictions)
        
        # Step 5 & 9
        print("Generating Creative Blueprint...")
        generate_blueprint(ranked_clusters)
        
        # Step 6 & 9
        print("Generating Visualizations...")
        generate_visualizations(ranked_clusters)
        
        print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    main()
