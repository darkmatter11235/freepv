"""
FreePVC Demo - Simple Solar Panel Array
========================================

This script creates a simple solar panel array in FreeCAD to demonstrate
the basic concepts. Run this in FreeCAD's Python console or save as a macro.

Instructions:
1. Open FreeCAD
2. Go to Macro > Macros... > Create
3. Paste this code and save as "demo_solar_array"
4. Click Execute

Or paste directly into the Python console (View > Panels > Python console)
"""

import FreeCAD
import Part
import math

# Create a new document
doc = FreeCAD.newDocument("SolarArrayDemo")
FreeCAD.setActiveDocument("SolarArrayDemo")

print("=" * 60)
print("Creating Solar Panel Array Demo")
print("=" * 60)

# ===== Configuration =====
# Solar panel dimensions (in mm)
panel_width = 1134     # ~1.13 meters
panel_height = 2278    # ~2.28 meters
panel_thickness = 35   # ~35 mm

# Array configuration
panels_per_row = 10    # Panels across
num_rows = 5           # Rows deep
panel_gap = 20         # Gap between panels (mm)
row_spacing = 6000     # Space between rows (mm)
tilt_angle = 25        # Degrees

# Post configuration
post_height = 2000     # Height of support posts (mm)
post_width = 100       # Post cross-section (mm)

print(f"Configuration:")
print(f"  Array: {panels_per_row} x {num_rows} = {panels_per_row * num_rows} panels")
print(f"  Panel size: {panel_width}mm x {panel_height}mm")
print(f"  Tilt angle: {tilt_angle}°")
print()

# ===== Helper Functions =====

def create_solar_panel(x, y, z, name):
    """Create a single solar panel (blue box)."""
    panel = doc.addObject("Part::Box", name)
    panel.Length = panel_width
    panel.Width = panel_height
    panel.Height = panel_thickness
    panel.Placement.Base = FreeCAD.Vector(x, y, z)

    # Make it blue to look like a solar panel
    panel.ViewObject.ShapeColor = (0.1, 0.3, 0.8)  # Blue

    return panel

def create_support_post(x, y, name):
    """Create a support post (cylinder)."""
    post = doc.addObject("Part::Cylinder", name)
    post.Radius = post_width / 2
    post.Height = post_height
    post.Placement.Base = FreeCAD.Vector(x, y, 0)

    # Make it gray
    post.ViewObject.ShapeColor = (0.7, 0.7, 0.7)  # Gray

    return post

def create_frame_beam(x1, y1, z1, x2, y2, z2, name):
    """Create a structural beam between two points."""
    # Create a line (edge)
    line = Part.makeLine(
        FreeCAD.Vector(x1, y1, z1),
        FreeCAD.Vector(x2, y2, z2)
    )

    # Convert edge to wire, then make pipe (tube)
    wire = Part.Wire([line])
    beam = wire.makePipe(Part.Wire([Part.makeCircle(30)]))

    beam_obj = doc.addObject("Part::Feature", name)
    beam_obj.Shape = beam

    # Make it dark gray
    beam_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.3)

    return beam_obj

# ===== Create the Array =====

# Group to hold everything
array_group = doc.addObject("App::DocumentObjectGroup", "SolarArray")

panels = []
posts = []
beams = []

print("Creating solar panels...")

for row in range(num_rows):
    for col in range(panels_per_row):
        # Calculate position
        x = col * (panel_width + panel_gap)
        y = row * row_spacing
        z = post_height

        # Create panel
        panel_name = f"Panel_R{row+1:02d}_C{col+1:02d}"
        panel = create_solar_panel(x, y, z, panel_name)
        panels.append(panel)
        array_group.addObject(panel)

print(f"  ✓ Created {len(panels)} solar panels")

# Tilt the panels
print(f"Tilting panels to {tilt_angle}°...")
for panel in panels:
    # Rotate around the lower edge (X-axis)
    panel.Placement.Rotation = FreeCAD.Rotation(
        FreeCAD.Vector(1, 0, 0),  # Rotate around X-axis
        tilt_angle
    )

print(f"  ✓ Panels tilted")

# Add support posts at corners of the array
print("Creating support structure...")

# Posts at 4 corners and middle supports
post_positions = [
    (0, 0),  # Front left
    (panels_per_row * (panel_width + panel_gap) - panel_gap, 0),  # Front right
    (0, (num_rows - 1) * row_spacing),  # Back left
    (panels_per_row * (panel_width + panel_gap) - panel_gap, (num_rows - 1) * row_spacing),  # Back right
]

# Add middle posts
for row in range(num_rows):
    mid_x = (panels_per_row * (panel_width + panel_gap)) / 2
    post_positions.append((mid_x, row * row_spacing))

for idx, (x, y) in enumerate(post_positions):
    post = create_support_post(x, y, f"Post_{idx+1:02d}")
    posts.append(post)
    array_group.addObject(post)

print(f"  ✓ Created {len(posts)} support posts")

# Add horizontal beams connecting posts
print("Adding structural beams...")

# Front beam
beam = create_frame_beam(
    post_positions[0][0], post_positions[0][1], post_height,
    post_positions[1][0], post_positions[1][1], post_height,
    "Beam_Front"
)
beams.append(beam)
array_group.addObject(beam)

# Back beam
beam = create_frame_beam(
    post_positions[2][0], post_positions[2][1], post_height,
    post_positions[3][0], post_positions[3][1], post_height,
    "Beam_Back"
)
beams.append(beam)
array_group.addObject(beam)

print(f"  ✓ Created {len(beams)} structural beams")

# Recompute the document
doc.recompute()

# Fit view to show everything
FreeCADGui.ActiveDocument.ActiveView.viewAxonometric()
FreeCADGui.SendMsgToActiveView("ViewFit")

# Print summary
print()
print("=" * 60)
print("Solar Array Created Successfully!")
print("=" * 60)
print(f"Total panels: {len(panels)}")
print(f"Total DC capacity: {len(panels) * 550}W = {len(panels) * 0.55:.1f}kW")
print(f"Array footprint: {panels_per_row * (panel_width + panel_gap) / 1000:.1f}m x {num_rows * row_spacing / 1000:.1f}m")
print(f"Total area: {(panels_per_row * (panel_width + panel_gap) * num_rows * row_spacing) / 1_000_000:.1f} m²")
print()
print("View controls:")
print("  - Mouse wheel: Zoom")
print("  - Middle mouse: Pan")
print("  - Right mouse: Rotate")
print("  - View > Standard views > Axonometric")
print("=" * 60)

# Add project properties
doc.addProperty("App::PropertyString", "ProjectType", "FreePVC")
doc.ProjectType = "Solar Array Demo"

doc.addProperty("App::PropertyInteger", "TotalPanels", "FreePVC")
doc.TotalPanels = len(panels)

doc.addProperty("App::PropertyFloat", "TotalPowerKW", "FreePVC")
doc.TotalPowerKW = len(panels) * 0.55

doc.addProperty("App::PropertyFloat", "TiltAngle", "FreePVC")
doc.TiltAngle = tilt_angle

print("\n✓ Demo complete! You can now:")
print("  1. Rotate the view to see the 3D array")
print("  2. Click on individual panels to select them")
print("  3. File > Save to save the design")
print("  4. File > Export to export as STEP, STL, etc.")
