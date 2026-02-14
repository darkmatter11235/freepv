"""
FreePVC Demo - Single-Axis Tracker Array
=========================================

This script creates a single-axis tracker solar array with rotation capability.
Trackers rotate to follow the sun throughout the day.

Instructions:
Run in FreeCAD's Python console:
    exec(open('/home/dark/freepvc/demo_tracker_array.py').read())
"""

import FreeCAD
import Part
import math

# Create a new document
doc = FreeCAD.newDocument("TrackerArrayDemo")
FreeCAD.setActiveDocument("TrackerArrayDemo")

print("=" * 60)
print("Creating Single-Axis Tracker Array")
print("=" * 60)

# ===== Configuration =====
# Solar panel dimensions (in mm)
panel_width = 1134     # ~1.13 meters
panel_height = 2278    # ~2.28 meters
panel_thickness = 35   # ~35 mm

# Tracker configuration
panels_per_tracker = 28    # Long trackers (1-portrait configuration)
num_trackers = 8           # Number of tracker rows
tracker_spacing = 8000     # N-S spacing between trackers (mm)
max_rotation = 60          # Maximum rotation angle (degrees)
current_angle = 30         # Current tracker angle (can animate this!)

# Torque tube configuration
tube_diameter = 150        # mm
tube_length = panels_per_tracker * panel_width

# Post configuration
post_height = 2500         # Height of center post (mm)
post_diameter = 200        # Post diameter (mm)

print(f"Configuration:")
print(f"  Trackers: {num_trackers} rows")
print(f"  Panels per tracker: {panels_per_tracker}")
print(f"  Total panels: {num_trackers * panels_per_tracker}")
print(f"  Current rotation: {current_angle}°")
print()

# ===== Helper Functions =====

def create_tracker_row(tracker_id, y_offset, rotation_angle):
    """Create a complete tracker row with panels, torque tube, and post."""

    tracker_group = doc.addObject("App::DocumentObjectGroup", f"Tracker_{tracker_id:02d}")

    # 1. Create torque tube (rotating axis)
    tube = doc.addObject("Part::Cylinder", f"TorqueTube_{tracker_id:02d}")
    tube.Radius = tube_diameter / 2
    tube.Height = tube_length
    tube.Placement.Base = FreeCAD.Vector(0, y_offset, post_height)
    tube.Placement.Rotation = FreeCAD.Rotation(
        FreeCAD.Vector(0, 1, 0),  # Rotate around Y-axis (N-S)
        90  # Make it horizontal along X-axis
    )
    tube.ViewObject.ShapeColor = (0.4, 0.4, 0.4)  # Dark gray
    tracker_group.addObject(tube)

    # 2. Create center support post
    post = doc.addObject("Part::Cylinder", f"Post_{tracker_id:02d}")
    post.Radius = post_diameter / 2
    post.Height = post_height
    post.Placement.Base = FreeCAD.Vector(tube_length / 2, y_offset, 0)
    post.ViewObject.ShapeColor = (0.6, 0.6, 0.6)  # Gray
    tracker_group.addObject(post)

    # 3. Create panels on the tracker
    panels = []
    for i in range(panels_per_tracker):
        panel = doc.addObject("Part::Box", f"Panel_{tracker_id:02d}_{i:02d}")
        panel.Length = panel_width
        panel.Width = panel_height
        panel.Height = panel_thickness

        # Position panel along the tracker
        x_pos = i * panel_width
        panel.Placement.Base = FreeCAD.Vector(x_pos, y_offset, post_height)

        # Apply tracker rotation (rotate around the torque tube axis)
        # First rotate to vertical, then apply tracker angle
        panel.Placement.Rotation = FreeCAD.Rotation(
            FreeCAD.Vector(1, 0, 0),  # Rotate around X-axis (torque tube)
            rotation_angle
        )

        # Color: Blue for solar panels
        panel.ViewObject.ShapeColor = (0.1, 0.3, 0.9)
        panels.append(panel)
        tracker_group.addObject(panel)

    return tracker_group

# ===== Create the Tracker Array =====

array_group = doc.addObject("App::DocumentObjectGroup", "TrackerArray")

print("Creating tracker rows...")

trackers = []
for row in range(num_trackers):
    y_offset = row * tracker_spacing

    # Add some variation in rotation (simulating tracking at different times)
    # Central trackers point more directly at sun
    if num_trackers > 1:
        angle_variation = -10 + (row / (num_trackers - 1)) * 20
    else:
        angle_variation = 0

    tracker_angle = current_angle + angle_variation

    tracker = create_tracker_row(row + 1, y_offset, tracker_angle)
    trackers.append(tracker)
    array_group.addObject(tracker)

    print(f"  ✓ Tracker {row + 1}: {panels_per_tracker} panels at {tracker_angle:.1f}°")

print(f"\n✓ Created {len(trackers)} tracker rows")

# Add ground plane for reference
print("Adding ground plane...")
ground = doc.addObject("Part::Plane", "Ground")
ground.Length = tube_length + 1000
ground.Width = (num_trackers * tracker_spacing) + 1000
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
print("Tracker Array Created Successfully!")
print("=" * 60)
print(f"Total trackers: {len(trackers)}")
print(f"Total panels: {num_trackers * panels_per_tracker}")
print(f"Total DC capacity: {num_trackers * panels_per_tracker * 550}W = {num_trackers * panels_per_tracker * 0.55:.1f}kW")
print(f"Array footprint: {tube_length / 1000:.1f}m x {num_trackers * tracker_spacing / 1000:.1f}m")
print()
print("Features:")
print("  ✓ Single-axis N-S tracking")
print("  ✓ Rotation range: ±60°")
print(f"  ✓ Current angle: {current_angle}°")
print()
print("To animate tracker rotation, run:")
print("  for angle in range(-60, 61, 10):")
print("      # Update rotations in FreeCAD")
print("=" * 60)

print("\n✓ Demo complete! Explore the 3D view!")
print("  - Notice how trackers have slightly different angles")
print("  - This simulates different tracking positions throughout the day")
print("  - In reality, all trackers would track together with backtracking logic")
