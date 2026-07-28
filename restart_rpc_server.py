"""Stop and restart RPC server."""
import sys
sys.path.append("/home/dark/freepvc/src")

from freepvc.connection import FreePVCConnection

conn = FreePVCConnection(host="127.0.0.1")

code = """
# Stop the RPC server
from FreePVC.rpc_server import rpc_server as rpc_mod

if rpc_mod._server:
    print("Stopping RPC server...")
    rpc_mod.stop_server()
    
# Then start it again
import time
time.sleep(1)
print("Starting RPC server...")
rpc_mod.start_server()

"RPC server restarted"
"""

try:
    result = conn.execute_code(code)
    print(result)
except Exception as e:
    print(f"Error: {e}")
    print("\nPlease manually restart FreeCAD to load the fixed code.")
