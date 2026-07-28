"""Test layout engine directly to see what placements it generates."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.models.solar_objects import RackConfig, LayoutConfig, PanelSpec
from freepvc.engines.layout_engine import LayoutEngine
from freepvc.models.terrain import TerrainMesh
from freepvc.connection import FreePVCConnection
import numpy as np

print("Fetching terrain mesh from FreeCAD...")
conn = FreePVCConnection(host="127.0.0.1")

code = """
import FreeCAD
import numpy as np
doc = FreeCAD.ActiveDocument
terrain = doc.getObject("Terrain")
if terrain and hasattr(terrain, "Mesh"):
    mesh = terrain.Mesh
    vertices = []
    for point in mesh.Points:
        vertices.append([point.x, point.y, point.z])
    
    triangles = []
    for facet in mesh.Facets:
        triangles.append(facet.PointIndices)
    
    result = {
        "vertices": vertices,
        "triangles": triangles,
    }
else:
    result = None
result
"""

terrain_data = conn.execute_code(code)

if not terrain_data:
    print("ERROR: Could not fetch terrain")
    sys.exit(1)

vertices = np.array(terrain_data["vertices"], dtype=np.float64)
triangles = np.array(terrain_data["triangles"], dtype=np.int32)
terrain_mesh = TerrainMesh(vertices=vertices, triangles=triangles)

print(f"✓ Loaded terrain: {len(vertices)} vertices, {len(triangles)} triangles")
print(f"  Terrain bounds: X=[{vertices[:, 0].min():.1f}, {vertices[:, 0].max():.1f}]mm")
print(f"                  Y=[{vertices[:, 1].min():.1f}, {vertices[:, 1].max():.1f}]mm")

# Create rack config matching our 28x2 rack
rack_config = RackConfig(
    panel_spec=PanelSpec(power_watts=550),
    panels_per_row=28,
    rows=2,
    tilt_angle_deg=32,
)

layout_config = LayoutConfig(
    rack_config=rack_config,
    spacing_m=9.0,
    gcr_target=0.35,
    max_slope_deg=20.0,
    target_capacity_mw=4.0,
)

print("\nGenerating layout...")
layout = LayoutEngine.generate_grid_layout(layout_config, terrain_mesh)

print(f"✓ Generated {len(layout.placements)} rack placements")
print(f"\nFirst 5 rack placements from LayoutEngine:")
for i in range(min(5, len(layout.placements))):
    p = layout.placements[i]
    print(f"  {p.rack_id}: X={p.x:.1f}mm ({p.x/1000:.1f}m), Y={p.y:.1f}mm ({p.y/1000:.1f}m), Z={p.z:.1f}mm")

print("\n=== COMPARISON ===")
print("Layout Engine says first rack should be at:")
print(f"  X={layout.placements[0].x:.1f}mm ({layout.placements[0].x/1000:.1f}m)")
print(f"  Y={layout.placements[0].y:.1f}mm ({layout.placements[0].y/1000:.1f}m)")
print("\nBut FreeCAD shows first rack at:")
print(f"  X=0.0mm (0.0m)")
print(f"  Y=0.0mm (0.0m)")
print("\nBUG CONFIRMED: Placements are not being passed correctly to FreeCAD!")
