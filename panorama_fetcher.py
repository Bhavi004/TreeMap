#!/usr/bin/env python3
"""
Panorama Fetching Module

This module handles all panorama fetching operations including
Street View API calls and image processing.
"""

import asyncio
import aiohttp
import numpy as np
import cv2
import logging
import io
import requests
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import pandas as pd
from pathlib import Path

from utils import fetch_pano_by_id, get_perspective

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PanoramaFetcher:
    """Handles all panorama fetching operations."""
    
    def __init__(self, max_concurrent: int = 4):
        """
        Initialize the panorama fetcher.
        
        Args:
            max_concurrent: Maximum number of concurrent panorama fetches
        """
        self.max_concurrent = max_concurrent
    
    def calculate_centered_theta(self, image_x: float, panorama_width: int) -> float:
        """
        Calculate the theta angle needed to center the view on the given image_x coordinate.
        
        Args:
            image_x: Target x coordinate in the panorama (0 to panorama_width)
            panorama_width: Width of the full panorama
            
        Returns:
            theta: Horizontal angle in degrees to center the view
        """
        # Convert image_x to normalized coordinate (0-1)
        norm_x = image_x / panorama_width
        
        # Convert to longitude in equirectangular projection (-π to π)
        lon = (norm_x - 0.5) * 2 * np.pi
        
        # Convert to theta angle (horizontal rotation in degrees)
        theta = np.degrees(lon)
        
        # Normalize to [-180, 180] range
        theta = ((theta + 180) % 360) - 180
        
        logger.debug(f"🎯 Centering view at x={image_x} -> θ={theta:.2f}°")
        return theta
    
    def create_centered_view(self, panorama_image: np.ndarray, image_x: float,
                            panorama_width: int, panorama_height: int, 
                            view_width: int, view_height: int, FOV: int) -> np.ndarray:
        """
        Create a perspective view centered on the given image_x coordinate.
        
        Args:
            panorama_image: Full panorama image array
            image_x: Target x coordinate to center on
            panorama_width, panorama_height: Panorama dimensions
            view_width, view_height: Desired view dimensions
            FOV: Field of view in degrees
            
        Returns:
            perspective_view: Generated perspective view
        """
        # Calculate theta angle to center the view on image_x
        theta = self.calculate_centered_theta(image_x, panorama_width)
        
        # Create perspective view using existing unwrap function
        perspective_view = get_perspective(
            panorama_image, FOV, theta, 0,  # PHI = 0 (no vertical tilt)
            view_height, view_width, panorama_height, panorama_width,
        )
        
        return perspective_view
    
    async def fetch_panorama_async(self, pano_id: str, session: aiohttp.ClientSession) -> Tuple[Optional[Any], Optional[np.ndarray]]:
        """
        Fetch panorama data asynchronously.
        
        Args:
            pano_id: Panorama ID to fetch
            session: aiohttp ClientSession for HTTP requests
            
        Returns:
            Tuple of (panorama_metadata, panorama_image_array)
        """
        return await fetch_pano_by_id(pano_id, session)
    
    def fetch_panorama_sync(self, pano_id: str) -> Optional[Image.Image]:
        """
        Fetch the original panorama image for a given pano_id by downloading tiles
        directly from Google's tile servers.
        
        Args:
            pano_id: Panorama ID to fetch
            
        Returns:
            Panorama image as PIL Image or None if failed
        """
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # Use zoom level 3: 8 tiles wide x 4 tiles tall, each 512x512
            # Result: 4096 x 2048 equirectangular panorama
            zoom = 3
            tiles_x = 2 ** zoom  # 8
            tiles_y = 2 ** (zoom - 1)  # 4
            tile_size = 512
            
            logger.info(f"Fetching panorama {pano_id} at zoom {zoom} ({tiles_x}x{tiles_y} tiles)")
            
            def fetch_tile(x, y):
                url = f'https://cbk0.google.com/cbk?output=tile&panoid={pano_id}&zoom={zoom}&x={x}&y={y}'
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200 and len(r.content) > 2000:
                        tile = Image.open(io.BytesIO(r.content))
                        if tile.mode != 'RGB':
                            tile = tile.convert('RGB')
                        return (x, y, tile)
                except Exception as e:
                    logger.warning(f"Failed to fetch tile ({x},{y}) for {pano_id}: {e}")
                return (x, y, None)
            
            # Download all tiles concurrently
            panorama = Image.new('RGB', (tiles_x * tile_size, tiles_y * tile_size))
            valid_tiles = 0
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fetch_tile, x, y) for y in range(tiles_y) for x in range(tiles_x)]
                for future in as_completed(futures):
                    x, y, tile = future.result()
                    if tile is not None:
                        panorama.paste(tile, (x * tile_size, y * tile_size))
                        valid_tiles += 1
            
            if valid_tiles == 0:
                logger.warning(f"No valid tiles found for panorama {pano_id}")
                return None
            
            logger.info(f"Successfully fetched panorama {pano_id}: {valid_tiles}/{tiles_x * tiles_y} tiles")
            return panorama
                
        except Exception as e:
            logger.error(f"Error fetching panorama {pano_id}: {e}")
            return None
    
    async def generate_centered_view_for_row(self, row: pd.Series, session: aiohttp.ClientSession,
                                           output_dir: str = "data/views") -> Optional[Dict[str, Any]]:
        """
        Generate a centered view for a specific CSV row.
        
        Args:
            row: Pandas Series representing a single CSV row
            session: aiohttp ClientSession for HTTP requests
            output_dir: Directory to save the output
            
        Returns:
            Dictionary with result information or None if failed
        """
        try:
            pano_id = row['pano_id']
            image_x = row['image_x']
            image_y = row['image_y']
            image_path = row['image_path']
            
            logger.info(f"🔄 Generating centered view for {pano_id} - {Path(image_path).name}")
            
            # Fetch panorama data
            pano, panorama_image = await self.fetch_panorama_async(pano_id, session)
            
            if pano is None or panorama_image is None:
                logger.warning(f"⚠️ Failed to fetch panorama: {pano_id}")
                return None
            
            # Get panorama dimensions
            panorama_height, panorama_width = panorama_image.shape[:2]
            
            # Create centered view with fixed dimensions 1024x720
            centered_view = self.create_centered_view(
                panorama_image, image_x,
                panorama_width, panorama_height,
                1024, 720, 90
            )
            
            # Convert BGR to RGB for encoding
            centered_view_rgb = cv2.cvtColor(centered_view, cv2.COLOR_BGR2RGB)

            # Encode image as JPEG bytes (no disk write, no extra deps)
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            success, enc = cv2.imencode('.jpg', centered_view_rgb, encode_params)
            if not success:
                logger.error("❌ Failed to JPEG-encode centered view in memory")
                return None
            image_data = enc.tobytes()
            
            result = {
                'pano_id': pano_id,
                'image_data': image_data,
                'original_image_path': image_path,
                'tree_lat': row['tree_lat'],
                'tree_lng': row['tree_lng'],
                'stview_lat': row['stview_lat'],
                'stview_lng': row['stview_lng'],
                'image_x': image_x,
                'image_y': image_y,
                'conf': row['conf']
            }
            
            logger.info(f"✅ Created centered view in memory for {pano_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating centered view for {row.get('image_path', 'unknown')}: {str(e)}")
            return None
