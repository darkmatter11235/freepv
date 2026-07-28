"""Delete old array and regenerate to see debug output."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

# Delete old ArrayLayout
code_delete = """
import FreeCAD
doc = FreeCAD.ActiveDocument
old_array = doc.getObject("ArrayLayout")
if old_array:
    doc.removeObject("ArrayLayout")
    doc.recompute()
    result = "Deleted old ArrayLayout"
else:
    result = "No ArrayLayout to delete"
result
"""

print(conn.execute_code(code_delete))
print("\nNow trigger new array generation via MCP tool...")
