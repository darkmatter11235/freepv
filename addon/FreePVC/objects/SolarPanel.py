"""Solar Panel FeaturePython Object for FreeCAD.

This module defines a parametric solar panel object that serves as
a template/prototype. Multiple rack instances can reference a single
panel template for memory efficiency.
"""

class SolarPanel:
    """Parametric solar panel FeaturePython object.
    
    This acts as a template/prototype that can be shared among
    multiple rack instances for efficient memory use.
    """
    
    def __init__(self, obj):
        """Initialize solar panel properties."""
        
        # Physical dimensions
        obj.addProperty(
            "App::PropertyLength",
            "Width",
            "Dimensions",
            "Panel width (mm)"
        )
        obj.Width = 1134.0
        
        obj.addProperty(
            "App::PropertyLength",
            "Height",
            "Dimensions",
            "Panel height (mm)"
        )
        obj.Height = 2278.0
        
        obj.addProperty(
            "App::PropertyLength",
            "Thickness",
            "Dimensions",
            "Panel thickness (mm)"
        )
        obj.Thickness = 35.0
        
        # Electrical specifications
        obj.addProperty(
            "App::PropertyFloat",
            "PowerWatts",
            "Electrical",
            "Rated power (W)"
        )
        obj.PowerWatts = 550.0
        
        obj.addProperty(
            "App::PropertyFloat",
            "VoltageVoc",
            "Electrical",
            "Open circuit voltage (V)"
        )
        obj.VoltageVoc = 49.5
        
        obj.addProperty(
            "App::PropertyFloat",
            "CurrentIsc",
            "Electrical",
            "Short circuit current (A)"
        )
        obj.CurrentIsc = 13.9
        
        obj.addProperty(
            "App::PropertyFloat",
            "VoltageMpp",
            "Electrical",
            "Maximum power point voltage (V)"
        )
        obj.VoltageMpp = 41.7
        
        obj.addProperty(
            "App::PropertyFloat",
            "CurrentMpp",
            "Electrical",
            "Maximum power point current (A)"
        )
        obj.CurrentMpp = 13.2
        
        obj.addProperty(
            "App::PropertyFloat",
            "Efficiency",
            "Electrical",
            "Panel efficiency (fraction)"
        )
        obj.Efficiency = 0.21
        
        # Metadata
        obj.addProperty(
            "App::PropertyString",
            "Manufacturer",
            "Metadata",
            "Panel manufacturer"
        )
        obj.Manufacturer = "Generic"
        
        obj.addProperty(
            "App::PropertyString",
            "Model",
            "Metadata",
            "Panel model"
        )
        obj.Model = "550W-Mono"
        
        # Visual properties
        obj.addProperty(
            "App::PropertyColor",
            "PanelColor",
            "Display",
            "Panel surface color"
        )
        obj.PanelColor = (0.1, 0.3, 0.8, 1.0)  # Blue
        
        obj.addProperty(
            "App::PropertyColor",
            "FrameColor",
            "Display",
            "Frame color"
        )
        obj.FrameColor = (0.2, 0.2, 0.2, 1.0)  # Dark gray
        
        obj.addProperty(
            "App::PropertyBool",
            "ShowFrame",
            "Display",
            "Show panel frame"
        )
        obj.ShowFrame = True
        
        obj.Proxy = self
        self.Type = "SolarPanel"
    
    def execute(self, obj):
        """Generate panel geometry when properties change."""
        import FreeCAD
        import Part
        
        # Main panel body (blue surface)
        panel_shape = Part.makeBox(
            obj.Width.Value,
            obj.Height.Value,
            obj.Thickness.Value - 5.0  # Slightly thinner
        )
        panel_shape.translate(FreeCAD.Vector(0, 0, 5.0))
        
        if obj.ShowFrame:
            # Create frame around edges (aluminum frame)
            frame_width = 40.0  # mm
            frame_depth = 5.0  # mm
            
            # Bottom frame
            bottom_frame = Part.makeBox(
                obj.Width.Value,
                obj.Height.Value,
                frame_depth
            )
            
            # Combine
            final_shape = panel_shape.fuse(bottom_frame)
        else:
            final_shape = panel_shape
        
        obj.Shape = final_shape
    
    def onChanged(self, obj, prop):
        """Handle property changes."""
        pass
    
    def __getstate__(self):
        """Serialize object for save."""
        return self.Type
    
    def __setstate__(self, state):
        """Deserialize object on load."""
        if state:
            self.Type = state


class ViewProviderSolarPanel:
    """View provider for SolarPanel objects."""
    
    def __init__(self, vobj):
        vobj.Proxy = self
    
    def attach(self, vobj):
        """Setup the scene sub-graph."""
        self.Object = vobj.Object
    
    def updateData(self, obj, prop):
        """Property update handler."""
        return
    
    def getDisplayModes(self, vobj):
        """Return available display modes."""
        return ["Shaded", "Wireframe"]
    
    def getDefaultDisplayMode(self):
        """Return default display mode."""
        return "Shaded"
    
    def setDisplayMode(self, mode):
        """Set display mode."""
        return mode
    
    def onChanged(self, vobj, prop):
        """Handle view property changes."""
        if prop == "PanelColor":
            if hasattr(vobj.Object, "PanelColor"):
                vobj.ShapeColor = vobj.Object.PanelColor
        elif prop == "FrameColor":
            pass  # Could implement separate frame coloring
    
    def getIcon(self):
        """Return icon path."""
        import os
        icon_path = os.path.join(
            os.path.dirname(__file__),
            "../Resources/icons/solar_panel.svg"
        )
        if os.path.exists(icon_path):
            return icon_path
        return None
    
    def __getstate__(self):
        """Serialize view provider."""
        return None
    
    def __setstate__(self, state):
        """Deserialize view provider."""
        return None


def makeSolarPanel(name="SolarPanel"):
    """Create a new solar panel object.
    
    Args:
        name: Object name in FreeCAD document
        
    Returns:
        FreeCAD solar panel object
    """
    import FreeCAD
    
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("SolarProject")
    
    obj = doc.addObject("Part::FeaturePython", name)
    SolarPanel(obj)
    
    if FreeCAD.GuiUp:
        ViewProviderSolarPanel(obj.ViewObject)
    
    doc.recompute()
    return obj
