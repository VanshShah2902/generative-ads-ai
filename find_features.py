import pandas as pd
import joblib
import numpy as np

model = joblib.load('Imported_things/layout_model.pkl')
df = pd.read_csv('Imported_things/competitor_features_with_clusters.csv')

centers = model.cluster_centers_

means = df.groupby('layout_cluster').mean(numeric_only=True).sort_index()

best_cols = []
for j in range(8):
    best_col = None
    min_dist = float('inf')
    for col in means.columns:
        # Distance between the feature means across all clusters and the j-th feature of the centroids across all clusters
        dist = np.linalg.norm(means[col].values - centers[:, j])
        if dist < min_dist:
            min_dist = dist
            best_col = col
    best_cols.append(best_col)

print("Features used in order:")
print(best_cols)
