"""Fixed-Tilt Solar Rack FeaturePython Object for FreeCAD.

This module defines a parametric fixed-tilt rack that can reference
a shared panel template for efficient object reuse.
"""

import FreeCAD
import Part
import math


class FixedRack:
    """Parametric fixed-tilt solar rack with object reuse.
    
    The rack references a shared panel template and creates instances
    efficiently. When the panel template changes, all racks update.
    """
    
    def __init__(self, obj):
        """Initialize fixed rack properties."""
        
        # Panel Template Reference (enables object reuse)
        obj.addProperty(
            "App::PropertyLink",
            "PanelTemplate",
            "Panel",
            "Reference to shared panel template"
        )
        
        # Array configuration
        obj.addProperty(
            "App::PropertyInteger",
            "PanelsPerRow",
            "Array",
            "Number of panels per row (across)"
        )
        obj.PanelsPerRow = 2
        
        obj.addProperty(
            "App::PropertyInteger",
            "Rows",
            "Array",
            "Number of rows (vertically)"
        )
        obj.Rows = 1
        
        obj.addProperty(
            "App::PropertyLength",
            "PanelGap",
            "Array",
            "Gap between panels (mm)"
        )
        obj.PanelGap = 20.0
        
        # Mounting configuration
        obj.addProperty(
            "App::PropertyAngle",
            "TiltAngle",
            "Mounting",
            "Panel tilt angle from horizontal"
        )
        obj.TiltAngle = 25.0
        
        obj.addProperty(
            "App::PropertyAngle",
            "Azimuth",
            "Mounting",
            "Array azimuth (0=N, 90=E, 180=S, 270=W)"
        )
        obj.Azimuth = 180.0
        
        obj.addProperty(
            "App::PropertyLength",
            "PostHeight",
            "Mounting",
            "Support post height (mm)"
        )
        obj.PostHeight = 2000.0
        
        obj.addProperty(
            "App::PropertyLength",
            "GroundClearance",
            "Mounting",
            "Minimum ground clearance (mm)"
        )
        obj.GroundClearance = 500.0
        
        # Structural elements
        obj.addProperty(
            "App::PropertyLength",
            "PostDiameter",
            "Structure",
            "Support post diameter (mm)"
        )
        obj.PostDiameter = 100.0
        
        obj.addProperty(
            "App::PropertyInteger",
            "NumPosts",
            "Structure",
            "Number of support posts"
        )
        obj.NumPosts = 4
        
        obj.addProperty(
            "App::PropertyLength",
            "BeamWidth",
            "Structure",
            "Structural beam width (mm)"
        )
        obj.BeamWidth = 80.0
        
        obj.addProperty(
            "App::PropertyLength",
            "BeamHeight",
            "Structure",
            "Structural beam height (mm)"
        )
        obj.BeamHeight = 40.0
        
        # Display options
        obj.addProperty(
            "App::PropertyBool",
            "ShowPanels",
            "Display",
            "Show solar panels"
        )
        obj.ShowPanels = True
        
        obj.addProperty(
            "App::PropertyBool",
            "ShowStructure",
            "Display",
            "Show support structure"
        )
        obj.ShowStructure = True
        
        obj.addProperty(
            "App::PropertyBool",
            "ShowPosts",
            "Display",
            "Show support posts"
        )
        obj.ShowPosts = True
        
        # Calculated properties
        obj.addProperty(
            "App::PropertyInteger",
            "TotalPanels",
            "Calculated",
            "Total number of panels"
        )
        obj.TotalPanels = 0
        
        obj.addProperty(
            "App::PropertyFloat",
            "DCCapacity",
            "Calculated",
            "DC capacity (kW)"
        )
        obj.DCCapacity = 0.0
        
        obj.Proxy = self
        self.Type = "FixedRack"
    
    def execute(self, obj):
        """Generate rack geometry when properties change."""
        
        # Get panel dimensions from template or use defaults
        if obj.PanelTemplate and hasattr(obj.PanelTemplate, "Width"):
            panel_w = obj.PanelTemplate.Width.Value
            panel_h = obj.PanelTemplate.Height.Value
            panel_t = obj.PanelTemplate.Thickness.Value
            panel_power = getattr(obj.PanelTemplate, "PowerWatts", 550.0)
        else:
            # Default panel dimensions
            panel_w = 1134.0
            panel_h = 2278.0
            panel_t = 35.0
            panel_power = 550.0
        
        # Update calculated properties
        obj.TotalPanels = obj.PanelsPerRow * obj.Rows
        obj.DCCapacity = (obj.TotalPanels * panel_power) / 1000.0
        
        # Build compound shape
        shapes = []
        
        # Generate panel array (as a compound for efficiency)
        if obj.ShowPanels:
            panel_shapes = self._generate_panel_array(
                obj, panel_w, panel_h, panel_t
            )
            shapes.extend(panel_shapes)
        
        # Generate support structure
        if obj.ShowStructure:
            structure_shapes = self._generate_structure(
                obj, panel_w, panel_h
            )
            shapes.extend(structure_shapes)
        
        # Generate posts
        if obj.ShowPosts:
            post_shapes = self._generate_posts(
                obj, panel_w, panel_h
            )
            shapes.extend(post_shapes)
        
        # Create compound
        if shapes:
            obj.Shape = Part.makeCompound(shapes)
        else:
            # Create placeholder box
            obj.Shape = Part.makeBox(100, 100, 100)
    
    def _generate_panel_array(self, obj, panel_w, panel_h, panel_t):
        """Generate array of panels (reusing single panel shape)."""
        shapes = []
        
        # Create ONE panel shape to reuse
        base_panel = Part.makeBox(panel_w, panel_h, panel_t)
        
        tilt_rad = math.radians(obj.TiltAngle)
        
        for row in range(obj.Rows):
            for col in range(obj.PanelsPerRow):
                # Calculate position
                x = col * (panel_w + obj.PanelGap.Value)
                
                # Y offset includes both panel height and gap, projected along slope
                y_flat = row * (panel_h + obj.PanelGap.Value)
                y = y_flat * math.cos(tilt_rad)
                z = obj.PostHeight.Value + y_flat * math.sin(tilt_rad)
                
                # Copy and transform the base panel shape (efficient)
                panel = base_panel.copy()
                panel.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(x, y, z),
                    FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), obj.TiltAngle)
                )
                shapes.append(panel)
        
        return shapes
    
    def _generate_structure(self, obj, panel_w, panel_h):
        """Generate support beams."""
        shapes = []
        
        tilt_rad = math.radians(obj.TiltAngle)
        
        # Calculate rack dimensions
        rack_width = obj.PanelsPerRow * panel_w + (obj.PanelsPerRow - 1) * obj.PanelGap.Value
        rack_length = obj.Rows * panel_h + (obj.Rows - 1) * obj.PanelGap.Value
        
        # Horizontal beams along bottom edge
        beam_length = rack_width
        beam = Part.makeBox(beam_length, obj.BeamWidth.Value, obj.BeamHeight.Value)
        
        # Position beam at base of panels
        beam.Placement = FreeCAD.Placement(
            FreeCAD.Vector(0, -obj.BeamWidth.Value, obj.PostHeight.Value),
            FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), obj.TiltAngle)
        )
        shapes.append(beam)
        
        # Top beam
        y_top = rack_length * math.cos(tilt_rad)
        z_top = obj.PostHeight.Value + rack_length * math.sin(tilt_rad)
        
        beam_top = Part.makeBox(beam_length, obj.BeamWidth.Value, obj.BeamHeight.Value)
        beam_top.Placement = FreeCAD.Placement(
            FreeCAD.Vector(0, y_top, z_top),
            FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), obj.TiltAngle)
        )
        shapes.append(beam_top)
        
        return shapes
    
    def _generate_posts(self, obj, panel_w, panel_h):
        """Generate support posts."""
        shapes = []
        
        rack_width = obj.PanelsPerRow * panel_w + (obj.PanelsPerRow - 1) * obj.PanelGap.Value
        
        # Distribute posts evenly across width
        if obj.NumPosts >= 2:
            post_spacing = rack_width / (obj.NumPosts - 1)
        else:
            post_spacing = 0
        
        for i in range(obj.NumPosts):
            x = i * post_spacing if obj.NumPosts > 1 else rack_width / 2
            
            post = Part.makeCylinder(
                obj.PostDiameter.Value / 2,
                obj.PostHeight.Value
            )
            post.Placement.Base = FreeCAD.Vector(x, 0, 0)
            shapes.append(post)
        
        return shapes
    
    def onChanged(self, obj, prop):
        """Handle property changes."""
        # If panel template changes, trigger rebuild
        if prop == "PanelTemplate":
            self.execute(obj)
    
    def __getstate__(self):
        """Serialize object."""
        return self.Type
    
    def __setstate__(self, state):
        """Deserialize object."""
        if state:
            self.Type = state


class ViewProviderFixedRack:
    """View provider for FixedRack objects."""
    
    def __init__(self, vobj):
        vobj.Proxy = self
    
    def attach(self, vobj):
        """Setup scene sub-graph."""
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
        pass
    
    def getIcon(self):
        """Return icon path."""
        import os
        icon_path = os.path.join(
            os.path.dirname(__file__),
            "../Resources/icons/fixed_rack.svg"
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


def makeFixedRack(name="FixedRack", panel_template=None):
    """Create a new fixed-tilt rack object.
    
    Args:
        name: Object name in FreeCAD document
        panel_template: Optional reference to shared panel template
        
    Returns:
        FreeCAD fixed rack object
    """
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("SolarProject")
    
    obj = doc.addObject("Part::FeaturePython", name)
    FixedRack(obj)
    
    if panel_template:
        obj.PanelTemplate = panel_template
    
    if FreeCAD.GuiUp:
        ViewProviderFixedRack(obj.ViewObject)
        # Set default colors
        obj.ViewObject.ShapeColor = (0.1, 0.3, 0.8)  # Blue for panels
    
    doc.recompute()
    return obj
