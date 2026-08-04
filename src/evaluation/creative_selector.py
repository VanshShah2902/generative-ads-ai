import os
import shutil
import json
from typing import List, Dict

class CreativeSelector:
    """Ranks generated creatives and exports the top performers."""
    
    def select_best_creatives(self, creatives: List[Dict], top_k: int = 1) -> str:
        """
        Ranks creatives by their score and saves the best ones.
        
        Args:
            creatives (List[Dict]): List of dicts with {path, score, detail}.
            top_k (int): Number of top creatives to select.
            
        Returns:
            str: Path to the campaign results folder.
        """
        print("Creative scores:", creatives)
        # Sort by creative_score descending
        ranked = sorted(creatives, key=lambda x: x["score"], reverse=True)
        top_list = ranked[:top_k]
        
        # Setup Campaign Results Folder
        results_dir = os.path.join("outputs", "campaign_results")
        top_dir = os.path.join(results_dir, "top_creatives")
        os.makedirs(top_dir, exist_ok=True)
        
        best_paths = []
        for i, creative in enumerate(top_list):
            src_path = creative["path"]
            filename = f"best_ad_{i+1:02d}.png"
            dest_path = os.path.join(top_dir, filename)
            
            shutil.copy(src_path, dest_path)
            best_paths.append(dest_path)
            print(f"[CreativeSelector] Exported best ad {i+1} (Score: {creative['score']}) to {dest_path}")
            
        # Generate Performance Report
        report_path = os.path.join(results_dir, "performance_report.json")
        with open(report_path, "w") as f:
            json.dump({
                "campaign_id": os.path.basename(os.path.dirname(top_list[0]["path"])),
                "total_variants": len(creatives),
                "top_score": float(top_list[0]["score"]),
                "ranking": [
                    {
                        "variation": os.path.basename(c["path"]),
                        "cluster_id": c.get("cluster_id", "unknown"),
                        "score": float(c["score"]),
                        "class": str(c["detail"].get("predicted_ctr_class"))
                    } for c in ranked
                ]
            }, f, indent=4)
            
        print(f"[CreativeSelector] Performance report saved to {report_path}")
        return results_dir
