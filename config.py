#!/usr/bin/env python3
"""
Configuration file for Tree Map application.

This file contains all configuration settings including:
- Current active area/city
- Data paths
- API settings
- Processing parameters
"""

import os
from pathlib import Path

# ============================================================================
# AREA/CITY CONFIGURATION
# ============================================================================

# Current active area - Change this to switch between different areas
CURRENT_AREA = "south_delhi"

# Available areas configuration
AREAS = {
    "south_delhi": {
        "name": "South Delhi",
        "description": "Tree inventory data for South Delhi region",
        "enabled": True,
    },
    "chandigarh": {
        "name": "Chandigarh",
        "description": "Tree inventory data for Chandigarh region",
        "enabled": True,
    },
    # Add more areas as they become available:
    # "north_delhi": {
    #     "name": "North Delhi",
    #     "description": "Tree inventory data for North Delhi region",
    #     "enabled": True,
    # },
    # "central_delhi": {
    #     "name": "Central Delhi",
    #     "description": "Tree inventory data for Central Delhi region",
    #     "enabled": True,
    # },
}

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Base directory paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

def get_area_path(area_name: str = None) -> Path:
    """
    Get the data directory path for a specific area.
    
    Args:
        area_name: Name of the area. If None, uses CURRENT_AREA.
    
    Returns:
        Path object pointing to the area's data directory
    """
    if area_name is None:
        area_name = CURRENT_AREA
    return DATA_DIR / area_name

def get_trees_csv_path(area_name: str = None) -> Path:
    """Get the path to the trees CSV file for the specified area."""
    return get_area_path(area_name) / "trees.csv"

def get_panoramas_csv_path(area_name: str = None) -> Path:
    """Get the path to the panoramas CSV file for the specified area."""
    return get_area_path(area_name) / "panoramas.csv"

def get_masks_dir_path(area_name: str = None) -> Path:
    """Get the path to the masks directory for the specified area."""
    return get_area_path(area_name) / "masks"

def get_mask_file_path(pano_id: str, area_name: str = None) -> Path:
    """Get the path to a specific mask file."""
    return get_masks_dir_path(area_name) / f"{pano_id}_masks.json"

# ============================================================================
# API CONFIGURATION
# ============================================================================

# API Server settings
API_HOST = "0.0.0.0"
API_PORT = int(os.environ.get("PORT", 5001))
API_DEBUG = False

# CORS settings
CORS_ENABLED = True

# Processing settings
MAX_CONCURRENT_REQUESTS = 4
THREAD_POOL_WORKERS = 4

# ============================================================================
# DATA FILTERING CONFIGURATION
# ============================================================================

# Tree filtering parameters
MAX_DISTANCE_FROM_PANORAMA = 12  # meters
MIN_CONFIDENCE_SCORE = 0.0  # minimum confidence for tree detection

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Output directory for API-generated views
API_VIEWS_DIR = BASE_DIR / "data" / "api_views"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_area(area_name: str = None) -> bool:
    """
    Validate that an area exists and is enabled.
    
    Args:
        area_name: Name of the area to validate. If None, validates CURRENT_AREA.
    
    Returns:
        True if area is valid and enabled, False otherwise
    """
    if area_name is None:
        area_name = CURRENT_AREA
    
    if area_name not in AREAS:
        return False
    
    if not AREAS[area_name].get("enabled", False):
        return False
    
    # Check if data directory exists
    area_path = get_area_path(area_name)
    if not area_path.exists():
        return False
    
    # Check if required files exist
    if not get_trees_csv_path(area_name).exists():
        return False
    
    if not get_panoramas_csv_path(area_name).exists():
        return False
    
    if not get_masks_dir_path(area_name).exists():
        return False
    
    return True

def get_area_info(area_name: str = None) -> dict:
    """
    Get information about an area.
    
    Args:
        area_name: Name of the area. If None, uses CURRENT_AREA.
    
    Returns:
        Dictionary with area information
    """
    if area_name is None:
        area_name = CURRENT_AREA
    
    if area_name not in AREAS:
        return {}
    
    info = AREAS[area_name].copy()
    info["area_name"] = area_name
    info["valid"] = validate_area(area_name)
    info["paths"] = {
        "area_dir": str(get_area_path(area_name)),
        "trees_csv": str(get_trees_csv_path(area_name)),
        "panoramas_csv": str(get_panoramas_csv_path(area_name)),
        "masks_dir": str(get_masks_dir_path(area_name)),
    }
    
    return info

def list_available_areas() -> list:
    """
    List all available and enabled areas.
    
    Returns:
        List of area names that are enabled
    """
    return [
        area_name 
        for area_name, config in AREAS.items() 
        if config.get("enabled", False)
    ]

# ============================================================================
# STARTUP VALIDATION
# ============================================================================

def validate_config():
    """Validate the configuration on startup."""
    if CURRENT_AREA not in AREAS:
        raise ValueError(
            f"Invalid CURRENT_AREA: '{CURRENT_AREA}'. "
            f"Available areas: {list(AREAS.keys())}"
        )
    
    if not AREAS[CURRENT_AREA].get("enabled", False):
        raise ValueError(
            f"Current area '{CURRENT_AREA}' is not enabled. "
            f"Set 'enabled': True in AREAS configuration."
        )
    
    if not validate_area(CURRENT_AREA):
        raise ValueError(
            f"Current area '{CURRENT_AREA}' is not valid. "
            f"Please check that the data directory and required files exist:\n"
            f"  - {get_area_path()}\n"
            f"  - {get_trees_csv_path()}\n"
            f"  - {get_panoramas_csv_path()}\n"
            f"  - {get_masks_dir_path()}"
        )

# Validate configuration when module is imported
try:
    validate_config()
    print(f"✅ Configuration validated: Using area '{CURRENT_AREA}'")
except ValueError as e:
    print(f"⚠️  Configuration validation failed: {e}")
    raise

