"""Debug the layout engine bounds calculation."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.models.solar_objects import RackConfig, LayoutConfig, PanelSpec
import numpy as np

# Simulate the layout config for 4MW system
panels_per_row = 28
rows = 2
panels_per_rack = panels_per_row * rows  # 56
power_per_rack_kw = (panels_per_rack * 550) / 1000.0  # 30.8 kW

target_capacity_mw = 4.0
num_racks_needed = int(target_capacity_mw * 1000 / power_per_rack_kw)
print(f"Racks needed: {num_racks_needed}")

racks_per_row = int(num_racks_needed ** 0.5) + 2
print(f"Racks per row: {racks_per_row}")

# Rack dimensions (estimate based on 28x2 panels at 1.134m x 2.278m each)
panel_width_mm = 1134
panel_height_mm = 2278
rack_width_mm = panels_per_row * panel_width_mm  # 28 * 1134 = 31752 mm
rack_length_mm = rows * panel_height_mm  # 2 * 2278 = 4556 mm

print(f"Rack width: {rack_width_mm}mm = {rack_width_mm/1000}m")
print(f"Rack length: {rack_length_mm}mm = {rack_length_mm/1000}m")

rack_width_m = rack_width_mm / 1000.0
spacing_m = 9.0

area_width_m = racks_per_row * rack_width_m * 1.2
area_length_m = racks_per_row * spacing_m * 1.2

print(f"\nEstimated area needed:")
print(f"  Width: {area_width_m:.1f}m")
print(f"  Length: {area_length_m:.1f}m")

# Terrain bounds (from diagnostic output)
terrain_x_min = -109961.5  # mm
terrain_x_max = 109961.5   # mm
terrain_y_min = -109999.9  # mm
terrain_y_max = 109999.9   # mm

print(f"\nTerrain bounds:")
print(f"  X: {terrain_x_min:.1f}mm to {terrain_x_max:.1f}mm ({terrain_x_min/1000:.1f}m to {terrain_x_max/1000:.1f}m)")
print(f"  Y: {terrain_y_min:.1f}mm to {terrain_y_max:.1f}mm ({terrain_y_min/1000:.1f}m to {terrain_y_max/1000:.1f}m)")

# Layout engine calculation (from line 69-71)
x_min = terrain_x_min
y_min = terrain_y_min
x_max = min(terrain_x_max, terrain_x_min + area_width_m * 1000)
y_max = min(terrain_y_max, terrain_y_min + area_length_m * 1000)

print(f"\nLayout bounds after min() calculation:")
print(f"  x_min: {x_min:.1f}mm ({x_min/1000:.1f}m)")
print(f"  x_max: {x_max:.1f}mm ({x_max/1000:.1f}m)")
print(f"  y_min: {y_min:.1f}mm ({y_min/1000:.1f}m)")
print(f"  y_max: {y_max:.1f}mm ({y_max/1000:.1f}m)")

# Convert to meters (line 89-90)
x_min_m = x_min / 1000.0
x_max_m = x_max / 1000.0
y_min_m = y_min / 1000.0
y_max_m = y_max / 1000.0

print(f"\nLayout bounds in meters:")
print(f"  x_min_m: {x_min_m:.1f}m")
print(f"  x_max_m: {x_max_m:.1f}m")
print(f"  y_min_m: {y_min_m:.1f}m")
print(f"  y_max_m: {y_max_m:.1f}m")

# Generate grid positions (line 93-94)
x_positions = np.arange(x_min_m, x_max_m - rack_width_m, rack_width_m)
y_positions = np.arange(y_min_m, y_max_m - 4.556, spacing_m)  # rack_length = 4.556m

print(f"\nFirst 5 X positions: {x_positions[:5]}")
print(f"First 5 Y positions: {y_positions[:5]}")

print(f"\nExpected first rack position:")
print(f"  X: {x_positions[0] * 1000:.1f}mm ({x_positions[0]:.1f}m)")
print(f"  Y: {y_positions[0] * 1000:.1f}mm ({y_positions[0]:.1f}m)")

print(f"\nACTUAL first rack position from FreeCAD: X=0.0mm, Y=0.0mm")
print(f"\nDISCREPANCY DETECTED! Layout engine should produce {x_positions[0]:.1f}m but FreeCAD shows 0.0m")
