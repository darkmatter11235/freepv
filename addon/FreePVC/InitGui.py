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
        import FreeCAD
        FreeCAD.Console.PrintMessage("FreePVC: Initializing workbench...\n")

        # Import command modules
        try:
            from .commands import cmd_rpc
            FreeCAD.Console.PrintMessage("FreePVC: Commands imported successfully\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"FreePVC: Failed to import commands: {e}\n")
            import traceback
            traceback.print_exc()
            return

        # Register commands
        self.rpc_commands = ["FreePVC_StartRPC", "FreePVC_StopRPC"]

        # Create toolbars
        try:
            self.appendToolbar("MCP Server", self.rpc_commands)
            FreeCAD.Console.PrintMessage(f"FreePVC: Toolbar created with commands: {self.rpc_commands}\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"FreePVC: Failed to create toolbar: {e}\n")

        # Create menus
        try:
            self.appendMenu("&FreePVC", self.rpc_commands)
            FreeCAD.Console.PrintMessage("FreePVC: Menu created\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"FreePVC: Failed to create menu: {e}\n")

        FreeCAD.Console.PrintMessage("FreePVC: Workbench initialized successfully\n")

    def Activated(self):
        """Called when workbench is activated."""
        import FreeCAD
        FreeCAD.Console.PrintMessage("FreePVC: Workbench activated\n")

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
