"""Reload the RPC server module in FreeCAD."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

code = """
import sys
import importlib

# Reload the rpc_server module
if 'FreePVC.rpc_server.rpc_server' in sys.modules:
    importlib.reload(sys.modules['FreePVC.rpc_server.rpc_server'])
    result = "RPC server module reloaded"
else:
    result = "RPC server module not found in sys.modules"
result
"""

result = conn.execute_code(code)
print(result)
print("\nNow regenerating Seattle array with fixed RPC server...")
