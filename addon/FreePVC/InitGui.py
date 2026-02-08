"""FreePVC FreeCAD Workbench - GUI initialization."""

import os
import FreeCADGui


class FreePVCWorkbench(FreeCADGui.Workbench):
    """FreePVC workbench for solar plant design."""

    MenuText = "FreePVC"
    ToolTip = "Open-source solar plant design toolkit"
    Icon = os.path.join(os.path.dirname(__file__), "Resources", "icons", "FreePVC.svg")

    def Initialize(self):
        """Initialize the workbench - called when FreeCAD starts."""
        # Import command modules
        from .commands import cmd_rpc

        # Register commands
        self.rpc_commands = ["FreePVC_StartRPC", "FreePVC_StopRPC"]

        # Create toolbars
        self.appendToolbar("MCP Server", self.rpc_commands)

        # Create menus
        self.appendMenu("&FreePVC", self.rpc_commands)

        print("FreePVC workbench initialized")

    def Activated(self):
        """Called when workbench is activated."""
        print("FreePVC workbench activated")

    def Deactivated(self):
        """Called when workbench is deactivated."""
        pass

    def ContextMenu(self, recipient):
        """Define right-click context menu."""
        pass

    def GetClassName(self):
        """Return the C++ class name."""
        return "Gui::PythonWorkbench"


# Register the workbench
FreeCADGui.addWorkbench(FreePVCWorkbench())

print("FreePVC workbench registered")
