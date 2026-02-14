"""
FreePVC Demo - Terrain-Draped Solar Array
==========================================

This script creates a solar array that follows terrain contours.
Panels are placed on variable slopes with adaptive tilt angles.

Instructions:
Run in FreeCAD's Python console:
    exec(open('/home/dark/freepvc/demo_terrain_draped.py').read())
"""

import FreeCAD
import Part
import Mesh
import math
import random

# Create a new document
doc = FreeCAD.newDocument("TerrainDrapedDemo")
FreeCAD.setActiveDocument("TerrainDrapedDemo")

print("=" * 60)
print("Creating Terrain-Draped Solar Array")
print("=" * 60)

# ===== Configuration =====
# Solar panel dimensions (in mm)
panel_width = 1134     # ~1.13 meters
panel_height = 2278    # ~2.28 meters
panel_thickness = 35   # ~35 mm

# Array configuration
panels_per_row = 8     # Panels across
num_rows = 6           # Rows deep
panel_gap = 20         # Gap between panels (mm)
row_spacing = 6000     # Space between rows (mm)

# Terrain configuration
terrain_size = 50000   # 50m x 50m terrain
terrain_base_slope = 5 # Base slope in degrees (S to N)
terrain_variation = 1000  # Max height variation (mm)

# Post configuration
post_width = 100       # Post cross-section (mm)

print(f"Configuration:")
print(f"  Array: {panels_per_row} x {num_rows} = {panels_per_row * num_rows} panels")
print(f"  Terrain size: {terrain_size / 1000}m x {terrain_size / 1000}m")
print(f"  Base slope: {terrain_base_slope}°")
print(f"  Height variation: ±{terrain_variation / 1000}m")
print()

# ===== Generate Terrain =====

print("Generating terrain mesh...")

# Create a simple terrain mesh with variable elevation
terrain_points = []
terrain_faces = []

grid_size = 20  # 20x20 grid of terrain points
grid_spacing = terrain_size / (grid_size - 1)

# Generate height map
heights = []
for row in range(grid_size):
    row_heights = []
    for col in range(grid_size):
        # Base slope (north is higher)
        base_height = row * (terrain_size / (grid_size - 1)) * math.tan(math.radians(terrain_base_slope))

        # Add undulation (sine wave pattern)
        wave_x = math.sin(col * math.pi / grid_size * 2) * 300
        wave_y = math.sin(row * math.pi / grid_size * 3) * 200

        # Add random variation
        random_var = random.uniform(-terrain_variation / 4, terrain_variation / 4)

        height = base_height + wave_x + wave_y + random_var
        row_heights.append(height)

    heights.append(row_heights)

# Create terrain vertices
for row in range(grid_size):
    for col in range(grid_size):
        x = col * grid_spacing
        y = row * grid_spacing
        z = heights[row][col]
        terrain_points.append(FreeCAD.Vector(x, y, z))

# Create terrain faces (triangles)
for row in range(grid_size - 1):
    for col in range(grid_size - 1):
        # Each grid square becomes 2 triangles
        i1 = row * grid_size + col
        i2 = row * grid_size + col + 1
        i3 = (row + 1) * grid_size + col
        i4 = (row + 1) * grid_size + col + 1

        terrain_faces.append([i1, i2, i4])
        terrain_faces.append([i1, i4, i3])

# Build the mesh
terrain_mesh = Mesh.Mesh()
terrain_mesh.addFacets([
    [terrain_points[f[0]], terrain_points[f[1]], terrain_points[f[2]]]
    for f in terrain_faces
])

# Create terrain object
terrain = doc.addObject("Mesh::Feature", "Terrain")
terrain.Mesh = terrain_mesh
terrain.ViewObject.ShapeColor = (0.4, 0.3, 0.2)  # Brown

print(f"  ✓ Created terrain mesh with {len(terrain_points)} points")

# ===== Helper Functions =====

def get_terrain_elevation(x, y):
    """Get interpolated terrain elevation at position (x, y)."""
    # Simple bilinear interpolation
    col_f = x / grid_spacing
    row_f = y / grid_spacing

    col = int(col_f)
    row = int(row_f)

    # Clamp to valid range
    col = max(0, min(col, grid_size - 2))
    row = max(0, min(row, grid_size - 2))

    # Fractional parts
    dx = col_f - col
    dy = row_f - row

    # Get 4 corner heights
    h00 = heights[row][col]
    h10 = heights[row][col + 1]
    h01 = heights[row + 1][col]
    h11 = heights[row + 1][col + 1]

    # Bilinear interpolation
    h0 = h00 * (1 - dx) + h10 * dx
    h1 = h01 * (1 - dx) + h11 * dx
    h = h0 * (1 - dy) + h1 * dy

    return h

def get_terrain_slope(x, y):
    """Get terrain slope at position (x, y) in degrees."""
    # Sample elevation at nearby points
    delta = 500  # mm
    z_center = get_terrain_elevation(x, y)
    z_north = get_terrain_elevation(x, y + delta)
    z_east = get_terrain_elevation(x + delta, y)

    # Calculate slope components
    slope_n = (z_north - z_center) / delta
    slope_e = (z_east - z_center) / delta

    # Overall slope magnitude
    slope_rad = math.atan(math.sqrt(slope_n**2 + slope_e**2))
    return math.degrees(slope_rad)

# ===== Create the Array =====

array_group = doc.addObject("App::DocumentObjectGroup", "SolarArray")

panels = []
posts = []

print("Creating terrain-following solar panels...")

for row in range(num_rows):
    for col in range(panels_per_row):
        # Calculate panel center position
        x = 5000 + col * (panel_width + panel_gap)
        y = 5000 + row * row_spacing

        # Get terrain elevation at panel location
        terrain_elev = get_terrain_elevation(x, y)
        terrain_slope = get_terrain_slope(x, y)

        # Post height (constant 2m above terrain)
        post_height = 2000
        panel_z = terrain_elev + post_height

        # Create panel
        panel_name = f"Panel_R{row+1:02d}_C{col+1:02d}"
        panel = doc.addObject("Part::Box", panel_name)
        panel.Length = panel_width
        panel.Width = panel_height
        panel.Height = panel_thickness
        panel.Placement.Base = FreeCAD.Vector(x, y, panel_z)

        # Adaptive tilt: base 25° + compensate for terrain slope
        adaptive_tilt = 25 + terrain_slope / 2
        adaptive_tilt = max(15, min(35, adaptive_tilt))  # Clamp to 15-35°

        # Apply tilt
        panel.Placement.Rotation = FreeCAD.Rotation(
            FreeCAD.Vector(1, 0, 0),
            adaptive_tilt
        )

        # Color code by elevation (blue=low, green=mid, red=high)
        normalized_elev = (terrain_elev - min(min(h) for h in heights)) / (
            max(max(h) for h in heights) - min(min(h) for h in heights)
        )
        r = normalized_elev
        g = 1 - abs(normalized_elev - 0.5) * 2
        b = 1 - normalized_elev
        panel.ViewObject.ShapeColor = (r * 0.5 + 0.2, g * 0.5 + 0.2, b * 0.5 + 0.3)

        panels.append(panel)
        array_group.addObject(panel)

        # Create support post
        post = doc.addObject("Part::Cylinder", f"Post_R{row+1:02d}_C{col+1:02d}")
        post.Radius = post_width / 2
        post.Height = post_height
        post.Placement.Base = FreeCAD.Vector(x, y, terrain_elev)
        post.ViewObject.ShapeColor = (0.6, 0.6, 0.6)  # Gray
        posts.append(post)
        array_group.addObject(post)

print(f"  ✓ Created {len(panels)} panels following terrain")

# Recompute the document
doc.recompute()

# Set view
FreeCADGui.ActiveDocument.ActiveView.viewAxonometric()
FreeCADGui.SendMsgToActiveView("ViewFit")

# Print summary
print()
print("=" * 60)
print("Terrain-Draped Solar Array Created Successfully!")
print("=" * 60)
print(f"Total panels: {len(panels)}")
print(f"Total posts: {len(posts)}")
print(f"Total DC capacity: {len(panels) * 550}W = {len(panels) * 0.55:.1f}kW")
print()
print("Features:")
print("  ✓ Panels follow terrain contours")
print("  ✓ Adaptive tilt based on local slope")
print("  ✓ Constant 2m post height above terrain")
print("  ✓ Color-coded panels by elevation:")
print("    - Blue/Purple: Lower elevation")
print("    - Green: Mid elevation")
print("    - Red/Yellow: Higher elevation")
print()
print("Terrain characteristics:")
print(f"  • Base slope: {terrain_base_slope}° (S to N)")
print(f"  • Undulating surface with sine waves")
print(f"  • Random variation: ±{terrain_variation / 1000}m")
print(f"  • Total elevation change: {(max(max(h) for h in heights) - min(min(h) for h in heights)) / 1000:.1f}m")
print("=" * 60)

print("\n✓ Demo complete! Explore the 3D view!")
print("  - Rotate the view to see how panels follow the terrain")
print("  - Notice the color gradient showing elevation changes")
print("  - Observe varying post heights maintaining constant clearance")
print("  - See how tilt angles adapt to local terrain slope")
