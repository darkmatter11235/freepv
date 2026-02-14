"""Single-Axis Tracker FeaturePython Object for FreeCAD.

This module defines a parametric single-axis tracker that rotates
to follow the sun throughout the day.
"""

import FreeCAD
import Part
import math


class SingleAxisTracker:
    """Parametric single-axis tracker with rotation.
    
    Trackers rotate around a horizontal torque tube to follow the sun.
    Supports backtracking to avoid self-shading.
    """
    
    def __init__(self, obj):
        """Initialize tracker properties."""
        
        # Panel Template Reference
        obj.addProperty(
            "App::PropertyLink",
            "PanelTemplate",
            "Panel",
            "Reference to shared panel template"
        )
        
        # Array configuration
        obj.addProperty(
            "App::PropertyInteger",
            "PanelsPerTracker",
            "Array",
            "Number of panels along tracker (1-portrait)"
        ).PanelsPerTracker = 28
        
        obj.addProperty(
            "App::PropertyInteger",
            "PanelsHigh",
            "Array",
            "Number of panels vertically (typically 1 or 2)"
        ).PanelsHigh = 1
        
        obj.addProperty(
            "App::PropertyLength",
            "PanelGap",
            "Array",
            "Gap between panels (mm)"
        ).PanelGap = 20.0
        
        # Tracker configuration
        obj.addProperty(
            "App::PropertyAngle",
            "RotationAngle",
            "Tracker",
            "Current rotation angle (±60° typical)"
        ).RotationAngle = 0.0
        
        obj.addProperty(
            "App::PropertyAngle",
            "MaxRotation",
            "Tracker",
            "Maximum rotation angle"
        ).MaxRotation = 60.0
        
        obj.addProperty(
            "App::PropertyBool",
            "BacktrackingEnabled",
            "Tracker",
            "Enable backtracking to avoid self-shading"
        ).BacktrackingEnabled = True
        
        obj.addProperty(
            "App::PropertyAngle",
            "Azimuth",
            "Tracker",
            "Tracker axis azimuth (0=N-S, 90=E-W)"
        ).Azimuth = 0.0
        
        # Mounting configuration
        obj.addProperty(
            "App::PropertyLength",
            "PostHeight",
            "Mounting",
            "Center post height (mm)"
        ).PostHeight = 2500.0
        
        obj.addProperty(
            "App::PropertyLength",
            "GroundClearance",
            "Mounting",
            "Minimum ground clearance at max rotation (mm)"
        ).GroundClearance = 500.0
        
        # Structure
        obj.addProperty(
            "App::PropertyLength",
            "TorqueTubeDiameter",
            "Structure",
            "Torque tube diameter (mm)"
        ).TorqueTubeDiameter = 150.0
        
        obj.addProperty(
            "App::PropertyLength",
            "PostDiameter",
            "Structure",
            "Support post diameter (mm)"
        ).PostDiameter = 200.0
        
        obj.addProperty(
            "App::PropertyInteger",
            "NumPosts",
            "Structure",
            "Number of support posts (typically 1 or 2)"
        ).NumPosts = 1
        
        # Display options
        obj.addProperty(
            "App::PropertyBool",
            "ShowPanels",
            "Display",
            "Show solar panels"
        ).ShowPanels = True
        
        obj.addProperty(
            "App::PropertyBool",
            "ShowTorqueTube",
            "Display",
            "Show torque tube"
        ).ShowTorqueTube = True
        
        obj.addProperty(
            "App::PropertyBool",
            "ShowPosts",
            "Display",
            "Show support posts"
        ).ShowPosts = True
        
        # Calculated properties
        obj.addProperty(
            "App::PropertyInteger",
            "TotalPanels",
            "Calculated",
            "Total number of panels"
        )
        obj.setEditorMode("TotalPanels", 1)  # Read-only
        
        obj.addProperty(
            "App::PropertyFloat",
            "DCCapacity",
            "Calculated",
            "DC capacity (kW)"
        )
        obj.setEditorMode("DCCapacity", 1)  # Read-only
        
        obj.addProperty(
            "App::PropertyLength",
            "TrackerLength",
            "Calculated",
            "Total tracker length (mm)"
        )
        obj.setEditorMode("TrackerLength", 1)  # Read-only
        
        obj.Proxy = self
        self.Type = "SingleAxisTracker"
    
    def execute(self, obj):
        """Generate tracker geometry when properties change."""
        
        # Get panel dimensions
        if obj.PanelTemplate and hasattr(obj.PanelTemplate, "Width"):
            panel_w = obj.PanelTemplate.Width.Value
            panel_h = obj.PanelTemplate.Height.Value
            panel_t = obj.PanelTemplate.Thickness.Value
            panel_power = getattr(obj.PanelTemplate, "PowerWatts", 550.0)
        else:
            panel_w = 1134.0
            panel_h = 2278.0
            panel_t = 35.0
            panel_power = 550.0
        
        # Update calculated properties
        obj.TotalPanels = obj.PanelsPerTracker * obj.PanelsHigh
        obj.DCCapacity = (obj.TotalPanels * panel_power) / 1000.0
        obj.TrackerLength = (
            obj.PanelsPerTracker * panel_w +
            (obj.PanelsPerTracker - 1) * obj.PanelGap.Value
        )
        
        # Clamp rotation angle
        max_rot = obj.MaxRotation
        if obj.RotationAngle > max_rot:
            obj.RotationAngle = max_rot
        elif obj.RotationAngle < -max_rot:
            obj.RotationAngle = -max_rot
        
        # Build compound shape
        shapes = []
        
        # Generate torque tube
        if obj.ShowTorqueTube:
            tube = self._generate_torque_tube(obj, panel_w)
            shapes.append(tube)
        
        # Generate panel array
        if obj.ShowPanels:
            panel_shapes = self._generate_panel_array(
                obj, panel_w, panel_h, panel_t
            )
            shapes.extend(panel_shapes)
        
        # Generate posts
        if obj.ShowPosts:
            post_shapes = self._generate_posts(obj, panel_w)
            shapes.extend(post_shapes)
        
        # Create compound
        if shapes:
            obj.Shape = Part.makeCompound(shapes)
        else:
            obj.Shape = Part.makeBox(100, 100, 100)
    
    def _generate_torque_tube(self, obj, panel_w):
        """Generate rotating torque tube."""
        tracker_length = (
            obj.PanelsPerTracker * panel_w +
            (obj.PanelsPerTracker - 1) * obj.PanelGap.Value
        )
        
        # Create tube along X-axis
        tube = Part.makeCylinder(
            obj.TorqueTubeDiameter.Value / 2,
            tracker_length
        )
        
        # Rotate to align along tracker axis and position at post height
        tube.Placement = FreeCAD.Placement(
            FreeCAD.Vector(0, 0, obj.PostHeight.Value),
            FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90)
        )
        
        return tube
    
    def _generate_panel_array(self, obj, panel_w, panel_h, panel_t):
        """Generate array of rotating panels."""
        shapes = []
        
        # Create base panel shape to reuse
        base_panel = Part.makeBox(panel_w, panel_h, panel_t)
        
        rot_angle = obj.RotationAngle
        
        for col in range(obj.PanelsPerTracker):
            for row in range(obj.PanelsHigh):
                # Calculate position along tracker
                x = col * (panel_w + obj.PanelGap.Value)
                
                # Y offset for multiple rows
                y_offset = row * (panel_h + obj.PanelGap.Value)
                
                # Copy panel shape
                panel = base_panel.copy()
                
                # First translate to position along tracker
                panel.translate(FreeCAD.Vector(
                    x,
                    -panel_h / 2 - y_offset,
                    obj.PostHeight.Value + obj.TorqueTubeDiameter.Value / 2
                ))
                
                # Then rotate around torque tube (X-axis at post height)
                rotation_center = FreeCAD.Vector(
                    x + panel_w / 2,
                    0,
                    obj.PostHeight.Value
                )
                
                # Rotate around tracker axis (X-axis in our case)
                panel.rotate(
                    rotation_center,
                    FreeCAD.Vector(1, 0, 0),
                    rot_angle
                )
                
                shapes.append(panel)
        
        return shapes
    
    def _generate_posts(self, obj, panel_w):
        """Generate support posts."""
        shapes = []
        
        tracker_length = (
            obj.PanelsPerTracker * panel_w +
            (obj.PanelsPerTracker - 1) * obj.PanelGap.Value
        )
        
        if obj.NumPosts == 1:
            # Center post
            post = Part.makeCylinder(
                obj.PostDiameter.Value / 2,
                obj.PostHeight.Value
            )
            post.Placement.Base = FreeCAD.Vector(tracker_length / 2, 0, 0)
            shapes.append(post)
        elif obj.NumPosts >= 2:
            # Multiple posts distributed along tracker
            post_spacing = tracker_length / (obj.NumPosts - 1)
            for i in range(obj.NumPosts):
                x = i * post_spacing if obj.NumPosts > 1 else tracker_length / 2
                post = Part.makeCylinder(
                    obj.PostDiameter.Value / 2,
                    obj.PostHeight.Value
                )
                post.Placement.Base = FreeCAD.Vector(x, 0, 0)
                shapes.append(post)
        
        return shapes
    
    def onChanged(self, obj, prop):
        """Handle property changes."""
        if prop == "PanelTemplate":
            self.execute(obj)
        elif prop == "RotationAngle":
            # Clamp rotation angle
            if hasattr(obj, "MaxRotation"):
                max_rot = obj.MaxRotation
                if obj.RotationAngle > max_rot:
                    obj.RotationAngle = max_rot
                elif obj.RotationAngle < -max_rot:
                    obj.RotationAngle = -max_rot
    
    def __getstate__(self):
        """Serialize object."""
        return self.Type
    
    def __setstate__(self, state):
        """Deserialize object."""
        if state:
            self.Type = state


class ViewProviderSingleAxisTracker:
    """View provider for SingleAxisTracker objects."""
    
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
            "../Resources/icons/tracker.svg"
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


def makeSingleAxisTracker(name="Tracker", panel_template=None):
    """Create a new single-axis tracker object.
    
    Args:
        name: Object name in FreeCAD document
        panel_template: Optional reference to shared panel template
        
    Returns:
        FreeCAD tracker object
    """
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("SolarProject")
    
    obj = doc.addObject("Part::FeaturePython", name)
    SingleAxisTracker(obj)
    
    if panel_template:
        obj.PanelTemplate = panel_template
    
    if FreeCAD.GuiUp:
        ViewProviderSingleAxisTracker(obj.ViewObject)
        obj.ViewObject.ShapeColor = (0.1, 0.3, 0.8)  # Blue for panels
    
    doc.recompute()
    return obj
