import os
import json
import pandas as pd

STORIES_LIBRARY = "output/stories_library.jsonl"
OUTPUT_HYPOTHESES = "output/stories_hypotheses.json"

def analyze_stories():
    if not os.path.exists(STORIES_LIBRARY):
        print("No story library found.")
        return
        
    records = []
    with open(STORIES_LIBRARY, "r") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except: pass
                
    if not records:
        print("No valid story records.")
        return
        
    df = pd.DataFrame(records)
    
    # Analyze by source_album and slot
    if 'reach' in df.columns and 'source_album' in df.columns and 'slot' in df.columns:
        summary = df.groupby(['source_album', 'slot']).agg(
            avg_reach=('reach', 'mean'),
            avg_exits=('exits', 'mean'),
            count=('story_id', 'count')
        ).reset_index()
        
        # Calculate an abstract "score" (reach / (exits+1))
        summary['score'] = summary['avg_reach'] / (summary['avg_exits'] + 1)
        summary = summary.sort_values('score', ascending=False)
        
        out_data = {
            "top_performing_combinations": summary.to_dict(orient='records'),
            "recommendation": "Use this data to favor the best performing album and slot combinations."
        }
        
        with open(OUTPUT_HYPOTHESES, "w") as f:
            json.dump(out_data, f, indent=2)
            
        print(f"Generated story hypotheses: {OUTPUT_HYPOTHESES}")
    else:
        print("Required metrics missing from library.")

if __name__ == "__main__":
    analyze_stories()
