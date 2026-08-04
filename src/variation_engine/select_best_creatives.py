import pandas as pd
import os
import shutil
import matplotlib.pyplot as plt

def select_best_creatives(num_top=3):
    scores_path = "outputs/campaign_runs/creative_scores.csv"
    runs_dir = "outputs/campaign_runs"
    best_dir = "outputs/best_creatives"
    
    if not os.path.exists(scores_path):
        print("Creative scores not found.")
        return

    os.makedirs(best_dir, exist_ok=True)
    df = pd.read_csv(scores_path)
    
    # Sort by score descending
    df_sorted = df.sort_values(by="creative_score", ascending=False)
    
    # Select top N
    top_creatives = df_sorted.head(num_top)
    
    print(f"Selecting top {num_top} creatives...")
    for idx, row in top_creatives.iterrows():
        var_id = row["variation_id"]
        src_path = os.path.join(runs_dir, var_id, "final_ad.png")
        dest_path = os.path.join(best_dir, f"top_creative_{var_id}.png")
        
        if os.path.exists(src_path):
            shutil.copy(src_path, dest_path)
            print(f"Copied {var_id} (Score: {row['creative_score']}) to {best_dir}")

    # Visualization: Score Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(df["creative_score"], bins=10, color='skyblue', edgecolor='black')
    plt.title("Distribution of Creative Scores across Campaign Variations")
    plt.xlabel("Creative Score (0-1)")
    plt.ylabel("Frequency")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    vis_path = os.path.join(runs_dir, "creative_score_distribution.png")
    plt.savefig(vis_path)
    print(f"Score distribution chart saved to {vis_path}")

if __name__ == "__main__":
    select_best_creatives(3)
