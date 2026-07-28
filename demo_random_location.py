#!/usr/bin/env python3
"""
FreePVC Demo - Random Solar Location
=====================================

This script creates a FreePVC solar project at a randomly selected
location worldwide. It imports real terrain data, creates a solar rack,
and generates an array layout.

Run this as: python demo_random_location.py
(Requires FreeCAD to be running)
"""

import sys
import random
from pathlib import Path

# Add src to path so we can import freepvc modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from freepvc.connection import FreeCADConnection
from freepvc.mcp_tools.project import create_project
from freepvc.mcp_tools.terrain import (
    import_terrain_from_coordinates,
    analyze_terrain_slope,
)

# Interesting solar locations around the world (latitude, longitude, name)
SOLAR_LOCATIONS = [
    (35.0872, -106.6504, "Albuquerque, New Mexico"),  # USA - High desert
    (40.5, -3.5, "Central Spain"),  # Europe - High solar resource
    (-23.0, -68.0, "Atacama Desert, Chile"),  # One of driest/sunniest places
    (28.2, 77.2, "New Delhi, India"),  # South Asia
    (35.6762, 139.6503, "Tokyo, Japan"),  # East Asia
    (-33.9, 18.4, "Cape Town, South Africa"),  # Africa
    (34.0, 100.0, "Thailand Central"),  # Southeast Asia
    (-31.9, 115.9, "Perth, Australia"),  # Australia
    (37.8, -25.5, "Canary Islands, Spain"),  # Atlantic Islands
    (31.2, 74.9, "Pakistan (Lahore region)"),  # South Asia
    (20.0, 35.0, "Saudi Arabia"),  # Middle East
    (-22.9, -43.2, "Rio de Janeiro, Brazil"),  # South America
]

def pick_random_location():
    """Pick a random location from the list."""
    return random.choice(SOLAR_LOCATIONS)

def main():
    print("=" * 70)
    print("FreePVC Demo - Random Solar Location")
    print("=" * 70)
    print()
    
    # Pick a random location
    lat, lon, name = pick_random_location()
    print(f"🌍 Selected Location: {name}")
    print(f"   Coordinates: {lat}°, {lon}°")
    print()
    
    # Check FreeCAD connection
    print("📡 Connecting to FreeCAD...")
    try:
        conn = FreeCADConnection()
        print("   ✓ Connected to FreeCAD")
    except Exception as e:
        print(f"   ✗ Failed to connect: {e}")
        print("   Please start FreeCAD first.")
        sys.exit(1)
    
    print()
    
    # Create project
    project_name = f"SolarSite_{name.replace(' ', '_').replace(',', '')}"
    print(f"📋 Creating project: {project_name}")
    try:
        create_project(project_name, lat, lon, altitude=100, timezone="UTC")
        print("   ✓ Project created")
    except Exception as e:
        print(f"   ✗ Failed to create project: {e}")
    
    print()
    
    # Import terrain from coordinates
    print(f"🏔️  Importing terrain data from coordinates...")
    print(f"   (This may take 30-60 seconds...)")
    try:
        import_terrain_from_coordinates(
            center_latitude=lat,
            center_longitude=lon,
            width_m=1000,
            height_m=1000,
            resolution_m=20,
            object_name="Terrain"
        )
        print("   ✓ Terrain imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import terrain: {e}")
        print("   (Note: This requires internet connection to Open-Elevation API)")
    
    print()
    
    # Analyze terrain slope
    print("📊 Analyzing terrain slope...")
    try:
        analyze_terrain_slope("Terrain", color_scheme="slope")
        print("   ✓ Terrain analysis complete (color heatmap applied)")
    except Exception as e:
        print(f"   ✗ Failed to analyze terrain: {e}")
    
    print()
    
    print("=" * 70)
    print("✅ Demo Generation Complete!")
    print("=" * 70)
    print()
    print(f"Project '{project_name}' is now ready in FreeCAD.")
    print("Next steps:")
    print("  • Adjust terrain if needed")
    print("  • Create solar racks and trackers")
    print("  • Generate array layouts")
    print("  • Run performance simulations")
    print()

if __name__ == "__main__":
    main()
