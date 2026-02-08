"""RPC server command - start/stop XML-RPC server for MCP integration."""

import FreeCAD
import FreeCADGui


class StartRPCCommand:
    """Command to start the FreePVC XML-RPC server."""

    def GetResources(self):
        return {
            "Pixmap": "accessories-text-editor",  # Use built-in icon for now
            "MenuText": "Start RPC Server",
            "ToolTip": "Start the FreePVC XML-RPC server on port 9876 for MCP integration",
        }

    def IsActive(self):
        """Always active."""
        return True

    def Activated(self):
        """Start the RPC server."""
        from ..rpc_server import rpc_server

        try:
            rpc_server.start_server()
            FreeCAD.Console.PrintMessage("✓ FreePVC RPC server started on port 9876\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"✗ Failed to start RPC server: {e}\n")


class StopRPCCommand:
    """Command to stop the FreePVC XML-RPC server."""

    def GetResources(self):
        return {
            "Pixmap": "process-stop",  # Use built-in icon for now
            "MenuText": "Stop RPC Server",
            "ToolTip": "Stop the FreePVC XML-RPC server",
        }

    def IsActive(self):
        """Active only if server is running."""
        from ..rpc_server import rpc_server

        return rpc_server.is_running()

    def Activated(self):
        """Stop the RPC server."""
        from ..rpc_server import rpc_server

        try:
            rpc_server.stop_server()
            FreeCAD.Console.PrintMessage("✓ FreePVC RPC server stopped\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"✗ Failed to stop RPC server: {e}\n")


# Register commands
FreeCADGui.addCommand("FreePVC_StartRPC", StartRPCCommand())
FreeCADGui.addCommand("FreePVC_StopRPC", StopRPCCommand())
