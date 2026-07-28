"""Complete cleanup and create fresh document."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

# Close current document and create new one
code = """
import FreeCAD

# Close all documents
for doc_name in FreeCAD.listDocuments():
    FreeCAD.closeDocument(doc_name)

# Create fresh document
doc = FreeCAD.newDocument("Miami_Solar_5MW")
doc.Label = "Miami Solar 5MW"

result = {"name": doc.Name, "label": doc.Label}
result
"""

result = conn.execute_code(code)
print(f"✓ Created fresh document: {result['label']}")
print("  All previous documents closed")
print("\nReady for new design!")
