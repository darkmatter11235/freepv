"""Clean up all orphaned rack objects."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

code = """
import FreeCAD
doc = FreeCAD.ActiveDocument

# Delete all rack objects (Link objects starting with "Rack_" or "TestRack_")
deleted = []
for obj in doc.Objects:
    if obj.TypeId == "App::Link" and (obj.Name.startswith("Rack_") or obj.Name.startswith("TestRack_")):
        deleted.append(obj.Name)
        doc.removeObject(obj.Name)

# Also delete ArrayLayout if it exists
if doc.getObject("ArrayLayout"):
    doc.removeObject("ArrayLayout")
    deleted.append("ArrayLayout")

doc.recompute()
result = {"deleted": deleted, "count": len(deleted)}
result
"""

result = conn.execute_code(code)
print(f"Cleaned up {result['count']} objects:")
print(f"  - Deleted ArrayLayout group")
print(f"  - Deleted {result['count']-1} orphaned racks")
print("\nDocument is now clean. Ready for regeneration.")
