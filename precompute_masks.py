"""
Pre-compute mask polygons in normalized panorama coordinates.

This converts RLE-encoded masks into polygon outlines mapped to equirectangular
panorama space, so the browser can draw them without needing pycocotools/opencv.

Output: public/data/masks/<pano_id>.json with structure:
{
  "polygons": [
    { "points": [[x,y],...], "image_path": "...", "highlight": false }
  ]
}
All coordinates are normalized 0-1 (relative to panorama width/height).
"""
import json
import os
import sys
import numpy as np
import cv2
import pycocotools.mask as maskUtils
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

MASK_DIR = Path('data/south_delhi/masks')
OUTPUT_DIR = Path('public/data/masks')
TREES_CSV = Path('data/south_delhi/trees.csv')

# Perspective view parameters (from mask_processor.py)
VIEW_HEIGHT = 720
VIEW_WIDTH = 1024
FOV = 90
# Use a standard panorama size for normalization (the normalized coords are resolution-independent)
PANO_WIDTH = 4096
PANO_HEIGHT = 2048


def map_perspective_to_pano_normalized(x, y, theta, pano_w, pano_h):
    """Map a point from perspective view coords to normalized panorama coords."""
    PHI = 0
    f = 0.5 * VIEW_WIDTH / np.tan(0.5 * FOV / 180.0 * np.pi)
    cx = (VIEW_WIDTH - 1) / 2.0
    cy = (VIEW_HEIGHT - 1) / 2.0

    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], np.float32)
    point = np.array([x, y, 1.0], dtype=np.float32)
    normalized = np.linalg.inv(K) @ point

    y_axis = np.array([0.0, 1.0, 0.0], np.float32)
    x_axis = np.array([1.0, 0.0, 0.0], np.float32)
    R1, _ = cv2.Rodrigues(y_axis * np.radians(theta))
    R2, _ = cv2.Rodrigues(np.dot(R1, x_axis) * np.radians(PHI))
    R = R2 @ R1

    xyz = normalized @ R.T
    lon = np.arctan2(xyz[0], xyz[2])
    hyp = np.sqrt(xyz[0] ** 2 + xyz[2] ** 2)
    lat = np.arctan2(xyz[1], hyp)

    # Normalized 0-1 coordinates
    nx = lon / (2 * np.pi) + 0.5
    ny = lat / np.pi + 0.5
    return nx, ny


def decode_rle_to_polygon(rle_data, orig_shape):
    """Decode RLE mask to polygon points (in perspective view coordinates)."""
    rle = rle_data.copy()
    if isinstance(rle['counts'], str):
        rle['counts'] = rle['counts'].encode('utf-8')
    binary_mask = maskUtils.decode(rle)
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    polygon = largest.squeeze().astype(np.float32)
    if polygon.ndim != 2 or polygon.shape[0] <= 2:
        return None
    # Simplify polygon to reduce point count (epsilon = 2 pixels)
    polygon = cv2.approxPolyDP(polygon.astype(np.float32), 2.0, True).squeeze()
    if polygon.ndim != 2 or polygon.shape[0] <= 2:
        return None
    return polygon


def process_mask_file(args):
    """Process a single mask file and return pre-computed polygon data."""
    mask_path, csv_lookup = args
    try:
        with open(mask_path, 'r') as f:
            mask_data = json.load(f)

        pano_id = mask_data['pano_id']
        polygons = []

        for view_key, trees in mask_data.get('views', {}).items():
            for tree in trees:
                image_path = tree.get('image_path', '')
                csv_key = f"{pano_id}_{image_path}"
                if csv_key not in csv_lookup:
                    continue

                theta = csv_lookup[csv_key]
                mask_data_obj = tree.get('mask_data', {})

                if mask_data_obj.get('encoding') != 'rle' or not mask_data_obj.get('rle'):
                    continue

                orig_shape = mask_data_obj.get('orig_shape', [720, 1024])
                polygon = decode_rle_to_polygon(mask_data_obj['rle'], orig_shape)
                if polygon is None:
                    continue

                # Map each point to normalized panorama coordinates
                pano_points = []
                for pt in polygon:
                    nx, ny = map_perspective_to_pano_normalized(
                        float(pt[0]), float(pt[1]), theta, PANO_WIDTH, PANO_HEIGHT
                    )
                    pano_points.append([round(nx, 5), round(ny, 5)])

                polygons.append({
                    'pts': pano_points,
                    'ip': image_path
                })

        if not polygons:
            return None

        return pano_id, {'polygons': polygons}

    except Exception as e:
        return None


def main():
    print("Loading CSV data...")
    df = pd.read_csv(TREES_CSV)
    # Build lookup: {pano_id}_{image_path} -> theta
    csv_lookup = {}
    for _, row in df.iterrows():
        key = f"{row['pano_id']}_{row['image_path']}"
        csv_lookup[key] = float(row['theta']) if pd.notna(row.get('theta')) else 0.0

    print(f"CSV lookup: {len(csv_lookup)} entries")

    mask_files = list(MASK_DIR.glob('*.json'))
    print(f"Processing {len(mask_files)} mask files...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    written = 0

    # Simple sequential processing (avoids GIL/multiprocessing issues)
    for mf in mask_files:
        processed += 1
        result = process_mask_file((str(mf), csv_lookup))
        if result:
            pano_id, data = result
            out_path = OUTPUT_DIR / f"{pano_id}.json"
            with open(out_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            written += 1
        if processed % 5000 == 0:
            print(f"  {processed}/{len(mask_files)} processed, {written} written...")

    print(f"Done: {written} mask files written to {OUTPUT_DIR}")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob('*.json'))
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
