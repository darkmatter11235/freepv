"""FreePVC FreeCAD Workbench - GUI initialization."""

import os
import FreeCADGui


class FreePVCWorkbench(FreeCADGui.Workbench):
    """FreePVC workbench for solar plant design."""

    MenuText = "FreePVC"
    ToolTip = "Open-source solar plant design toolkit"

    def __init__(self):
        # Get the addon path - FreeCAD sets this when loading addons
        import sys
        addon_path = None
        for path in sys.path:
            if "FreePVC" in path:
                addon_path = path
                break

        if addon_path:
            self.Icon = os.path.join(addon_path, "Resources", "icons", "FreePVC.svg")
        else:
            # Fallback: try to find it in FreeCAD's Mod directory
            import FreeCAD
            mod_path = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "FreePVC")
            if not os.path.exists(mod_path):
                mod_path = os.path.join(FreeCAD.getHomePath(), "Mod", "FreePVC")
            self.Icon = os.path.join(mod_path, "Resources", "icons", "FreePVC.svg")

        super().__init__()

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
