#!/usr/bin/env python3
"""
Test terrain import and analysis without MCP server.
This tests the core terrain functionality directly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from freepvc.io.terrain_import import TerrainImporter
from freepvc.engines.terrain_engine import TerrainEngine

print("=" * 60)
print("Testing FreePVC Terrain Import and Analysis")
print("=" * 60)

# Test 1: Import CSV terrain
print("\n1. Testing CSV import...")
try:
    terrain_data = TerrainImporter.import_csv_points(
        file_path="sample_terrain.csv",
        x_col=0,
        y_col=1,
        z_col=2,
        skip_header=4,  # Skip 3 comment lines + 1 header row
        unit_scale=1000.0,  # Convert meters to mm
    )
    print(f"   ✓ Imported {terrain_data.num_points} points")
    stats = terrain_data.get_statistics()
    print(f"   ✓ Extent: {stats['x_extent_m']:.1f}m × {stats['y_extent_m']:.1f}m")
    print(f"   ✓ Elevation range: {stats['elevation_range_m']:.1f}m")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Generate mesh
print("\n2. Testing mesh generation...")
try:
    mesh = TerrainEngine.create_mesh_from_points(terrain_data)
    print(f"   ✓ Created mesh with {mesh.num_vertices} vertices")
    print(f"   ✓ {mesh.num_faces} triangular faces")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Analyze slope
print("\n3. Testing slope analysis...")
try:
    slope_map = TerrainEngine.analyze_slope(mesh)
    stats = slope_map.get_statistics()
    print(f"   ✓ Mean slope: {stats['mean_slope_deg']:.2f}°")
    print(f"   ✓ Max slope: {stats['max_slope_deg']:.2f}°")
    print(f"   ✓ Buildable area: {stats['buildable_area_pct']:.1f}%")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 4: Query elevation
print("\n4. Testing elevation interpolation...")
try:
    import numpy as np
    # Query elevation at center of site
    query_point = np.array([25000, 25000])  # 25m, 25m in mm
    elevation = TerrainEngine.interpolate_elevation(mesh, query_point)
    print(f"   ✓ Elevation at (25m, 25m): {elevation/1000:.2f}m")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 5: Heatmap colors
print("\n5. Testing heatmap generation...")
try:
    colors = slope_map.compute_heatmap_colors("slope")
    print(f"   ✓ Generated {len(colors)} face colors")
    print(f"   ✓ Color range: [{colors.min():.2f}, {colors.max():.2f}]")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All terrain tests passed!")
print("=" * 60)
print("\nNext steps:")
print("1. Start FreeCAD and open FreePVC workbench")
print("2. Click 'Start RPC Server' button")
print("3. Run: source .venv/bin/activate && python -m freepvc.server")
print("4. Test MCP tools with the sample_terrain.csv file")
