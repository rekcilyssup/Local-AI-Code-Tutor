import os
import sys
from pathlib import Path

# Add project root to python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.chroma_client import get_global_collection
import pandas as pd

def migrate_parquet():
    file_path = "../Dataset/train-00000-of-00001-b894c52e31287062.parquet"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print("Loading Parquet file...")
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Failed to read parquet: {e}")
        return

    # Sort by upvotes if available to get the best solutions
    if 'upvotes' in df.columns:
        df['upvotes'] = pd.to_numeric(df['upvotes'], errors='coerce').fillna(0)
        df = df.sort_values(by='upvotes', ascending=False)
    
    # Dedup by slug to get the best solution per unique problem
    if 'slug' in df.columns:
        df = df.drop_duplicates(subset=['slug'])

    # Limit removed: we will embed the full dataset (1 unique solution per problem).
    # Since we deduped by slug, we'll embed approx ~2500 unique problems.
    # df = df.head(...)
    
    collection = get_global_collection()
    
    docs = []
    metadatas = []
    ids = []
    
    print(f"Ingesting ALL {len(df)} highly-reviewed global solutions into ChromaDB (this may take a few minutes)...")
    count = 0
    for idx, row in df.iterrows():
        code = str(row.get('python_solutions', ''))
        if not code or len(code) < 10:
            continue
            
        slug = str(row.get('slug', 'unknown'))
        difficulty = str(row.get('difficulty', 'Unknown'))
        
        docs.append(code)
        metadatas.append({
            "titleSlug": slug,
            "lang": "python3",
            "statusDisplay": "Accepted",
            "difficulty": difficulty,
            "rag_source": "global"
        })
        ids.append(f"global_{slug}_{idx}")
        count += 1
        
        if len(docs) >= 100:
            # Batch add forces embeddings computation
            collection.add(documents=docs, metadatas=metadatas, ids=ids)
            print(f"Inserted {count} solutions...")
            docs, metadatas, ids = [], [], []
            
    if docs:
        collection.add(documents=docs, metadatas=metadatas, ids=ids)
        print(f"Inserted {count} solutions...")
        
    print(f"\nDone! Successfully stored {count} unique problem solutions.")
    print("You can now toggle to 'Global Dataset' in your UI!")

if __name__ == "__main__":
    migrate_parquet()
