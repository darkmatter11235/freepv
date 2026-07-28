"""Full inspection of current FreeCAD document state."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

code = """
import FreeCAD
doc = FreeCAD.ActiveDocument

result = {
    "doc_name": doc.Name,
    "objects": [],
}

for obj in doc.Objects:
    obj_info = {
        "name": obj.Name,
        "type": obj.TypeId if hasattr(obj, "TypeId") else "Unknown",
        "label": obj.Label,
    }
    
    # Check if it's an ArrayLayout group
    if obj.Name == "ArrayLayout" and hasattr(obj, "Group"):
        obj_info["group_size"] = len(obj.Group)
        if len(obj.Group) > 0:
            first = obj.Group[0]
            obj_info["first_child"] = first.Name
            obj_info["first_child_placement"] = {
                "x": first.Placement.Base.x,
                "y": first.Placement.Base.y,
                "z": first.Placement.Base.z,
            }
    
    result["objects"].append(obj_info)

result
"""

doc_state = conn.execute_code(code)

print(f"FreeCAD Document: {doc_state['doc_name']}")
print(f"\nTotal objects: {len(doc_state['objects'])}")
print("\nObjects found:")
for obj in doc_state['objects']:
    print(f"  - {obj['name']} ({obj['type']}): {obj['label']}")
    if 'group_size' in obj:
        print(f"      └─ Group with {obj['group_size']} children")
        if 'first_child_placement' in obj:
            p = obj['first_child_placement']
            print(f"         First child at: ({p['x']:.1f}, {p['y']:.1f}, {p['z']:.1f})mm")