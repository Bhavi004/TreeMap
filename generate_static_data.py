"""Generate static JSON data files for GitHub Pages deployment."""
import pandas as pd
import json
import os

os.makedirs('public/data', exist_ok=True)

# Generate tree-data.json (same filtering as api_server.py)
df = pd.read_csv('data/south_delhi/trees.csv')
filtered = df[
    (df['distance_pano'] < 12) & 
    df['distance_pano'].notna() & 
    df['tree_lat'].notna() & 
    df['tree_lng'].notna() & 
    df['pano_id'].notna()
].copy()

result = []
for _, row in filtered.iterrows():
    entry = {
        'tree_lat': round(float(row['tree_lat']), 6),
        'tree_lng': round(float(row['tree_lng']), 6),
        'pano_id': str(row['pano_id']),
        'csv_index': int(row.name),
        'conf': round(float(row['conf']), 3) if pd.notna(row['conf']) else None,
        'image_path': str(row['image_path']) if pd.notna(row['image_path']) else None
    }
    result.append(entry)

with open('public/data/tree-data.json', 'w') as f:
    json.dump(result, f, separators=(',', ':'))

size_mb = os.path.getsize('public/data/tree-data.json') / 1024 / 1024
print(f'tree-data.json: {len(result)} records, {size_mb:.1f} MB')

# Generate streetview-data.json
sv = pd.read_csv('data/south_delhi/panoramas.csv')
sv_filtered = sv[sv['lat'].notna() & sv['lng'].notna() & sv['pano_id'].notna()]
sv_result = []
for _, r in sv_filtered.iterrows():
    sv_result.append({
        'lat': round(float(r['lat']), 6),
        'lng': round(float(r['lng']), 6),
        'pano_id': str(r['pano_id'])
    })

with open('public/data/streetview-data.json', 'w') as f:
    json.dump(sv_result, f, separators=(',', ':'))

size_mb = os.path.getsize('public/data/streetview-data.json') / 1024 / 1024
print(f'streetview-data.json: {len(sv_result)} records, {size_mb:.1f} MB')
