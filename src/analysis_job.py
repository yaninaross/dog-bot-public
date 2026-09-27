import os
import json
from collections import defaultdict

def run_analysis():
    """
    Reads the append-only post library.
    Groups posts by tags and computes averages to generate ranked hypotheses.
    """
    library_path = "output/post_library.jsonl"
    if not os.path.exists(library_path):
        print(f"[Analysis Job] No library found at {library_path}")
        return
        
    posts = {}
    
    # Read snapshots, keeping the latest one for each post
    with open(library_path, "r") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                post_id = row["post_id"]
                # Assuming append-only, the last one we see is the latest
                posts[post_id] = row
                
    if not posts:
        print("[Analysis Job] Library is empty.")
        return
        
    print(f"[Analysis Job] Analyzing {len(posts)} unique posts...")
    
    # Group by individual tags
    # Since some fields are single string and some are lists, we'll flatten them into a key
    
    tag_performance = defaultdict(lambda: {"count": 0, "views": 0, "saves": 0, "shares": 0})
    
    for post_id, row in posts.items():
        metrics = row["metrics"]
        tags = row.get("tags", {})
        
        # Flatten tags for grouping
        flat_tags = []
        for key, value in tags.items():
            if key in ["luxury_score", "luxury_signal"]:
                continue # Skip qualitative or continuous
            if isinstance(value, list):
                for v in value:
                    flat_tags.append(f"{key}:{v}")
            else:
                flat_tags.append(f"{key}:{value}")
                
        # Aggregate
        for tag in flat_tags:
            tag_performance[tag]["count"] += 1
            tag_performance[tag]["views"] += metrics.get("views", 0)
            tag_performance[tag]["saves"] += metrics.get("saves", 0)
            tag_performance[tag]["shares"] += metrics.get("shares", 0)
            
    # Compute averages and rank
    hypotheses = []
    h_idx = 1
    
    for tag, data in tag_performance.items():
        count = data["count"]
        if count < 2:
            continue # Need at least 2 posts for a pattern
            
        avg_views = data["views"] / count
        avg_saves = data["saves"] / count
        avg_shares = data["shares"] / count
        
        # Calculate rates based on views to avoid div by zero
        save_rate = (avg_saves / avg_views * 100) if avg_views else 0
        share_rate = (avg_shares / avg_views * 100) if avg_views else 0
        
        hypotheses.append({
            "id": f"H-{h_idx:03d}",
            "tag_combination": tag,
            "n_posts": count,
            "avg_views": round(avg_views, 1),
            "avg_save_rate_pct": round(save_rate, 2),
            "avg_share_rate_pct": round(share_rate, 2)
        })
        h_idx += 1
        
    # Sort by save rate as primary metric for luxury/aspirational content
    hypotheses.sort(key=lambda x: x["avg_save_rate_pct"], reverse=True)
    
    # Save to hypotheses.json
    output_path = "output/hypotheses.json"
    with open(output_path, "w") as f:
        json.dump({"ranked_hypotheses": hypotheses}, f, indent=2)
        
    # Create markdown version for humans
    md_path = "output/hypotheses.md"
    with open(md_path, "w") as f:
        f.write("# Ranked Performance Hypotheses\n\n")
        f.write("| ID | Tag | N | Avg Views | Save Rate | Share Rate |\n")
        f.write("|---|---|---|---|---|---|\n")
        for h in hypotheses[:20]: # Top 20
            f.write(f"| {h['id']} | `{h['tag_combination']}` | {h['n_posts']} | {h['avg_views']} | {h['avg_save_rate_pct']}% | {h['avg_share_rate_pct']}% |\n")
            
    print(f"[Analysis Job] Generated {len(hypotheses)} hypotheses. Saved to {output_path}")

if __name__ == "__main__":
    run_analysis()
