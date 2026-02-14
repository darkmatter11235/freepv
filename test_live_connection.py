#!/usr/bin/env python3
"""Test FreePVC MCP tools with live FreeCAD connection."""

import sys
sys.path.insert(0, '/home/dark/freepvc/src')

from freepvc.connection import FreePVCConnection

def test_connection():
    print("Testing FreePVC connection...")
    
    # Test with 127.0.0.1
    conn = FreePVCConnection(host="127.0.0.1")
    
    try:
        result = conn.ping()
        print(f"✓ Connection successful: {result}")
        
        # Test creating a project
        code = """
import FreeCAD
doc = FreeCAD.newDocument("TestProject")
doc.Label = "Test Solar Plant"
result = {"name": doc.Name, "label": doc.Label, "objects": len(doc.Objects)}
"""
        result = conn.execute_code(code)
        print(f"✓ Project created: {result}")
        
        # Get active documents
        code = """
import FreeCAD
result = [doc.Name for doc in FreeCAD.listDocuments().values()]
"""
        docs = conn.execute_code(code)
        print(f"✓ Active documents: {docs}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
