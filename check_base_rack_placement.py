"""Check the base rack's placement."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
base_rack = doc.getObject("Rack_28x2")
if base_rack:
    pl = base_rack.Placement
    result = {
        "Base.x": pl.Base.x,
        "Base.y": pl.Base.y,
        "Base.z": pl.Base.z,
        "Has_Rotation": pl.Rotation.Angle != 0,
        "Angle": pl.Rotation.Angle,
    }
else:
    result = None
result
"""

base_placement = conn.execute_code(code)
if base_placement:
    print("Base Rack (Rack_28x2) Placement:")
    for key, value in base_placement.items():
        print(f"  {key}: {value}")
    
    if base_placement["Base.x"] != 0 or base_placement["Base.y"] != 0:
        print("\n⚠️ WARNING: Base rack has non-zero placement!")
        print("This will offset all Link instances!")
else:
    print("Base rack not found")

# Also check the first link's absolute vs relative placement
code2 = """
import FreeCAD
doc = FreeCAD.ActiveDocument
array = doc.getObject("ArrayLayout")
if array and len(array.Group) > 0:
    first_link = array.Group[0]
    result = {
        "link_placement_x": first_link.Placement.Base.x,
        "link_placement_y": first_link.Placement.Base.y,
        "link_placement_z": first_link.Placement.Base.z,
    }
    
    # Check if linked object has placement
    if hasattr(first_link, "LinkedObject"):
        linked = first_link.LinkedObject
        result["linked_object_x"] = linked.Placement.Base.x
        result["linked_object_y"] = linked.Placement.Base.y
        result["linked_object_z"] = linked.Placement.Base.z
else:
    result = None
result
"""

link_info = conn.execute_code(code2)
if link_info:
    print("\nFirst Link (Rack_0000):")
    print(f"  Link.Placement: ({link_info['link_placement_x']:.1f}, {link_info['link_placement_y']:.1f}, {link_info['link_placement_z']:.1f})mm")
    print(f"  LinkedObject.Placement: ({link_info['linked_object_x']:.1f}, {link_info['linked_object_y']:.1f}, {link_info['linked_object_z']:.1f})mm")
    
    total_x = link_info['link_placement_x'] + link_info['linked_object_x']
    total_y = link_info['link_placement_y'] + link_info['linked_object_y']
    print(f"  Combined total: ({total_x:.1f}, {total_y:.1f})mm")
