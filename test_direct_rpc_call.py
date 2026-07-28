"""Direct test of create_array_layout with known coordinates."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

# Delete old array
conn.execute_code("""
import FreeCAD
doc = FreeCAD.ActiveDocument
old = doc.getObject("ArrayLayout")
if old:
    doc.removeObject("ArrayLayout")
doc.recompute()
""")

# Create test placements with explicit known values
test_placements = [
    {"x": -109961.5, "y": -109999.9, "z": 4000.0, "name": "TestRack_0"},
    {"x": -78209.5, "y": -109999.9, "z": 4000.0, "name": "TestRack_1"},
    {"x": -46457.5, "y": -109999.9, "z": 4000.0, "name": "TestRack_2"},
]

print("Calling create_array_layout with explicit coordinates:")
for p in test_placements:
    print(f"  {p['name']}: x={p['x']}, y={p['y']}, z={p['z']}")

print("\nInvoking RPC call...")
result = conn.server.create_array_layout("Rack_28x2", test_placements)

print(f"\nResult: {result}")

# Now check what actually got created
check_code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
array = doc.getObject("ArrayLayout")
if array:
    racks = []
    for obj in array.Group[:3]:
        pl = obj.Placement
        racks.append({
            "name": obj.Name,
            "x": pl.Base.x,
            "y": pl.Base.y,
            "z": pl.Base.z,
        })
    result = racks
else:
    result = None
result
"""

actual_positions = conn.execute_code(check_code)

print("\nActual positions in FreeCAD:")
if actual_positions:
    for rack in actual_positions:
        print(f"  {rack['name']}: x={rack['x']:.1f}, y={rack['y']:.1f}, z={rack['z']:.1f}")
    
    print("\n=== COMPARISON ===")
    for i, (expected, actual) in enumerate(zip(test_placements, actual_positions)):
        match = (abs(expected['x'] - actual['x']) < 0.1 and 
                abs(expected['y'] - actual['y']) < 0.1)
        status = "✓ MATCH" if match else "✗ MISMATCH"
        print(f"{status}: Expected ({expected['x']:.1f}, {expected['y']:.1f}), Got ({actual['x']:.1f}, {actual['y']:.1f})")
