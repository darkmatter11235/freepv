"""
FreePVC Demo - East-West Bifacial Array
========================================

This script creates an east-west bifacial solar array configuration.
Panels face both east and west in paired rows to capture morning and evening sun.

Instructions:
Run in FreeCAD's Python console:
    exec(open('/home/dark/freepvc/demo_east_west.py').read())
"""

import FreeCAD
import Part
import math

# Create a new document
doc = FreeCAD.newDocument("EastWestDemo")
FreeCAD.setActiveDocument("EastWestDemo")

print("=" * 60)
print("Creating East-West Bifacial Array")
print("=" * 60)

# ===== Configuration =====
# Solar panel dimensions (in mm)
panel_width = 1134     # ~1.13 meters
panel_height = 2278    # ~2.28 meters
panel_thickness = 35   # ~35 mm

# Array configuration
panels_per_row = 12    # Panels per row (E or W facing)
num_paired_rows = 6    # Number of paired rows (each pair has E+W)
row_spacing = 6000     # N-S spacing between paired rows (mm)
tilt_angle = 15        # Shallow tilt for E-W (degrees)
ew_separation = 500    # Gap between E and W rows in pair (mm)

# Post configuration
post_height = 1500     # Lower posts for E-W
post_diameter = 100    # Post diameter (mm)

print(f"Configuration:")
print(f"  Paired rows: {num_paired_rows}")
print(f"  Panels per direction: {panels_per_row}")
print(f"  Total panels: {num_paired_rows * panels_per_row * 2}")
print(f"  Tilt angle: ±{tilt_angle}°")
print()

# ===== Helper Functions =====

def create_ew_row(row_id, y_offset, facing_east=True):
    """Create a single row of panels (either east or west facing)."""

    direction = "East" if facing_east else "West"
    row_group = doc.addObject("App::DocumentObjectGroup", f"Row_{row_id:02d}_{direction}")

    # Determine tilt direction
    rotation_angle = tilt_angle if facing_east else -tilt_angle

    # Create panels
    panels = []
    for i in range(panels_per_row):
        panel = doc.addObject("Part::Box", f"Panel_{row_id:02d}_{direction}_{i:02d}")
        panel.Length = panel_width
        panel.Width = panel_height
        panel.Height = panel_thickness

        # Position panel
        x_pos = i * (panel_width + 20)  # 20mm gap between panels
        panel.Placement.Base = FreeCAD.Vector(x_pos, y_offset, post_height)

        # Tilt panel (rotate around X-axis)
        panel.Placement.Rotation = FreeCAD.Rotation(
            FreeCAD.Vector(1, 0, 0),
            rotation_angle
        )

        # Color coding: Blue for east, orange for west (bifacial)
        if facing_east:
            panel.ViewObject.ShapeColor = (0.1, 0.3, 0.8)  # Blue (morning)
        else:
            panel.ViewObject.ShapeColor = (0.9, 0.5, 0.1)  # Orange (evening)

        panels.append(panel)
        row_group.addObject(panel)

    # Create support posts (every 4 panels)
    for i in range(0, panels_per_row + 1, 4):
        x_pos = i * (panel_width + 20) if i < panels_per_row else (panels_per_row - 1) * (panel_width + 20)

        post = doc.addObject("Part::Cylinder", f"Post_{row_id:02d}_{direction}_{i:02d}")
        post.Radius = post_diameter / 2
        post.Height = post_height
        post.Placement.Base = FreeCAD.Vector(x_pos + panel_width / 2, y_offset, 0)
        post.ViewObject.ShapeColor = (0.6, 0.6, 0.6)  # Gray
        row_group.addObject(post)

    return row_group

# ===== Create the Array =====

array_group = doc.addObject("App::DocumentObjectGroup", "EastWestArray")

print("Creating east-west paired rows...")

rows = []
for pair_idx in range(num_paired_rows):
    y_base = pair_idx * row_spacing

    # Create east-facing row
    y_east = y_base - ew_separation / 2
    east_row = create_ew_row(pair_idx * 2 + 1, y_east, facing_east=True)
    rows.append(east_row)
    array_group.addObject(east_row)

    # Create west-facing row
    y_west = y_base + ew_separation / 2
    west_row = create_ew_row(pair_idx * 2 + 2, y_west, facing_east=False)
    rows.append(west_row)
    array_group.addObject(west_row)

    print(f"  ✓ Pair {pair_idx + 1}: East + West rows ({panels_per_row * 2} panels)")

print(f"\n✓ Created {num_paired_rows} paired rows ({len(rows)} total rows)")

# Add ground plane for reference
print("Adding ground plane...")
ground = doc.addObject("Part::Plane", "Ground")
ground.Length = panels_per_row * (panel_width + 20) + 1000
ground.Width = (num_paired_rows * row_spacing) + 1000
ground.Placement.Base = FreeCAD.Vector(-500, -500, -10)
ground.ViewObject.ShapeColor = (0.4, 0.3, 0.2)  # Brown
ground.ViewObject.Transparency = 50

# Recompute the document
doc.recompute()

# Set view
FreeCADGui.ActiveDocument.ActiveView.viewAxonometric()
FreeCADGui.SendMsgToActiveView("ViewFit")

# Print summary
print()
print("=" * 60)
print("East-West Bifacial Array Created Successfully!")
print("=" * 60)
print(f"Paired rows: {num_paired_rows}")
print(f"Total rows: {len(rows)}")
print(f"Total panels: {num_paired_rows * panels_per_row * 2}")
total_power = num_paired_rows * panels_per_row * 2 * 550
print(f"Total DC capacity: {total_power}W = {total_power / 1000:.1f}kW")
print(f"Array footprint: {panels_per_row * (panel_width + 20) / 1000:.1f}m x {num_paired_rows * row_spacing / 1000:.1f}m")
print()
print("Features:")
print("  ✓ East-West bifacial configuration")
print("  ✓ Blue panels face East (morning sun)")
print("  ✓ Orange panels face West (evening sun)")
print(f"  ✓ Shallow tilt: ±{tilt_angle}°")
print(f"  ✓ Row separation: {ew_separation}mm")
print()
print("Benefits of E-W configuration:")
print("  • More uniform daily generation (morning + evening peaks)")
print("  • Better land utilization (narrower N-S pitch)")
print("  • Reduced row-to-row shading losses")
print("  • Lower wind loads due to shallow tilt")
print("  • Bifacial gain from ground reflection")
print("=" * 60)

print("\n✓ Demo complete! Explore the 3D view!")
print("  - Notice the color coding: Blue (East) vs Orange (West)")
print("  - Observe the shallow tilt angles (±15°)")
print("  - See how paired rows are closely spaced")
print("  - This configuration works great for bifacial modules!")
