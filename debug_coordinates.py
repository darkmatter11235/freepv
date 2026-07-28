"""Debug script to check terrain and rack coordinates."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

# Connect to FreeCAD
conn = FreePVCConnection(host="127.0.0.1")

# Get terrain bounds
code_terrain = """
import FreeCAD
doc = FreeCAD.ActiveDocument
terrain = doc.getObject("Terrain")
if terrain and hasattr(terrain, "Mesh"):
    mesh = terrain.Mesh
    bbox = mesh.BoundBox
    result = {
        "x_min": bbox.XMin,
        "x_max": bbox.XMax,
        "y_min": bbox.YMin,
        "y_max": bbox.YMax,
        "z_min": bbox.ZMin,
        "z_max": bbox.ZMax,
    }
else:
    result = None
result
"""

terrain_bounds = conn.execute_code(code_terrain)
print("\n=== TERRAIN BOUNDS ===")
if terrain_bounds:
    for key, value in terrain_bounds.items():
        print(f"{key}: {value:.1f} mm ({value/1000:.1f} m)")
else:
    print("Terrain not found")

# Get first few rack positions
code_racks = """
import FreeCAD
doc = FreeCAD.ActiveDocument
array_layout = doc.getObject("ArrayLayout")
if array_layout:
    racks = array_layout.Group[:5]  # First 5 racks
    result = []
    for rack in racks:
        pl = rack.Placement
        result.append({
            "name": rack.Name,
            "x": pl.Base.x,
            "y": pl.Base.y,
            "z": pl.Base.z,
        })
else:
    result = None
result
"""

rack_positions = conn.execute_code(code_racks)
print("\n=== FIRST 5 RACK POSITIONS ===")
if rack_positions:
    for rack in rack_positions:
        print(f"{rack['name']}: X={rack['x']:.1f}mm ({rack['x']/1000:.1f}m), Y={rack['y']:.1f}mm ({rack['y']/1000:.1f}m), Z={rack['z']:.1f}mm")
else:
    print("No racks found")

print("\n=== ANALYSIS ===")
if terrain_bounds and rack_positions:
    first_rack = rack_positions[0]
    print(f"Terrain X range: {terrain_bounds['x_min']/1000:.1f}m to {terrain_bounds['x_max']/1000:.1f}m")
    print(f"Terrain Y range: {terrain_bounds['y_min']/1000:.1f}m to {terrain_bounds['y_max']/1000:.1f}m")
    print(f"First rack X: {first_rack['x']/1000:.1f}m")
    print(f"First rack Y: {first_rack['y']/1000:.1f}m")
    
    # Check if rack is within terrain bounds
    if (terrain_bounds['x_min'] <= first_rack['x'] <= terrain_bounds['x_max'] and
        terrain_bounds['y_min'] <= first_rack['y'] <= terrain_bounds['y_max']):
        print("✓ First rack is WITHIN terrain bounds")
    else:
        print("✗ First rack is OUTSIDE terrain bounds!")
        print(f"   X offset: {(first_rack['x'] - terrain_bounds['x_min'])/1000:.1f}m from terrain left edge")
        print(f"   Y offset: {(first_rack['y'] - terrain_bounds['y_min'])/1000:.1f}m from terrain bottom edge")
