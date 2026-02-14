"""FreePVC XML-RPC Server - Runs inside FreeCAD to handle MCP requests.

Based on the pattern from freecad-mcp but extended with solar-specific operations.
"""

import threading
import traceback
from xmlrpc.server import SimpleXMLRPCServer
from queue import Queue
import sys
import os

import FreeCAD
import FreeCADGui

# Setup addon path for imports
def _setup_addon_path():
    """Get FreePVC addon root directory."""
    # This file is in FreePVC/rpc_server/rpc_server.py
    # Go up two directories to get FreePVC root
    current_file = os.path.abspath(__file__)
    rpc_server_dir = os.path.dirname(current_file)
    freepvc_root = os.path.dirname(rpc_server_dir)
    return freepvc_root

_ADDON_PATH = _setup_addon_path()

# Global server instance and state
_server = None
_server_thread = None
_running = False
_command_queue = Queue()
_timer = None  # Keep reference to timer to prevent garbage collection


def execute_in_gui_thread(func):
    """Decorator to execute RPC methods in FreeCAD's GUI thread."""

    def wrapper(*args, **kwargs):
        result_container = {}

        def execute():
            try:
                result_container["result"] = func(*args, **kwargs)
                result_container["success"] = True
            except Exception as e:
                result_container["error"] = str(e)
                result_container["traceback"] = traceback.format_exc()
                result_container["success"] = False

        # Queue the command for GUI thread execution
        _command_queue.put(execute)

        # Process the queue (this will be handled by a timer in the GUI thread)
        FreeCADGui.updateGui()

        # Wait for result (simplified - in production, use proper synchronization)
        import time

        timeout = 30  # seconds
        elapsed = 0
        while "result" not in result_container and "error" not in result_container:
            time.sleep(0.01)
            elapsed += 0.01
            if elapsed > timeout:
                return {"error": "Command timeout"}

        if result_container.get("success"):
            return result_container["result"]
        else:
            raise Exception(result_container.get("error", "Unknown error"))

    return wrapper


class FreePVCRPCServer:
    """XML-RPC server for FreePVC operations."""

    def __init__(self, host="localhost", port=9876):
        self.host = host
        self.port = port

    # ===== Base FreeCAD Operations (inherited from freecad-mcp pattern) =====

    @execute_in_gui_thread
    def ping(self):
        """Test connection.

        Returns:
            str: "pong"
        """
        return "pong"

    @execute_in_gui_thread
    def execute_code(self, code: str):
        """Execute arbitrary Python code in FreeCAD.

        Args:
            code: Python code to execute

        Returns:
            Result of code execution
        """
        # Execute in FreeCAD's namespace
        local_vars = {
            "FreeCAD": FreeCAD,
            "FreeCADGui": FreeCADGui,
            "App": FreeCAD,
            "Gui": FreeCADGui,
        }

        try:
            # Use exec for statements, eval for expressions
            result = eval(code, globals(), local_vars)
            return result
        except SyntaxError:
            try:
                exec(code, globals(), local_vars)
                return local_vars.get("result", "Executed successfully")
            except Exception as e:
                raise Exception(f"Execution error: {str(e)}")
        except Exception as e:
            raise Exception(f"Execution error: {str(e)}")

    # ===== Solar-Specific Operations =====

    @execute_in_gui_thread
    def create_terrain_mesh(self, vertices, triangles, name="Terrain"):
        """Create a terrain mesh object.

        Args:
            vertices: List of [x, y, z] coordinates
            triangles: List of [i, j, k] vertex indices
            name: Object name

        Returns:
            str: Created object name
        """
        import Mesh

        doc = FreeCAD.ActiveDocument
        if not doc:
            raise Exception("No active document")

        # Create mesh object
        mesh_obj = doc.addObject("Mesh::Feature", name)

        # Build mesh from vertices and faces
        mesh = Mesh.Mesh()
        for tri in triangles:
            if len(tri) != 3:
                continue
            i, j, k = tri
            if i < len(vertices) and j < len(vertices) and k < len(vertices):
                v1 = vertices[i]
                v2 = vertices[j]
                v3 = vertices[k]
                mesh.addFacet(v1[0], v1[1], v1[2], v2[0], v2[1], v2[2], v3[0], v3[1], v3[2])

        mesh_obj.Mesh = mesh
        doc.recompute()

        return name

    @execute_in_gui_thread
    def set_face_colors(self, obj_name, colors):
        """Set per-face colors on a mesh (for heatmaps).

        Args:
            obj_name: Name of mesh object
            colors: List of [r, g, b] tuples (0-1 range)

        Returns:
            bool: Success
        """
        doc = FreeCAD.ActiveDocument
        if not doc:
            raise Exception("No active document")

        obj = doc.getObject(obj_name)
        if not obj:
            raise Exception(f"Object '{obj_name}' not found")

        # Convert to FreeCAD color format and apply
        vp = obj.ViewObject
        if hasattr(vp, "DiffuseColor"):
            # Convert colors to RGBA tuples (add alpha=1.0)
            face_colors = [(r, g, b, 1.0) for r, g, b in colors]
            vp.DiffuseColor = face_colors

        return True

    @execute_in_gui_thread
    def create_fixed_rack(self, config):
        """Create a fixed-tilt solar rack object using FeaturePython.

        Args:
            config: Dictionary with rack configuration
                - panel_template: Optional name of panel template to reference
                - panels_per_row: Number of panels per row
                - rows: Number of rows
                - tilt_angle: Tilt angle in degrees
                - post_height: Post height in mm
                - name: Optional object name

        Returns:
            str: Created object name
        """
        # Import using importlib to load from file path
        import sys
        import os
        import importlib.util
        
        module_path = os.path.join(_ADDON_PATH, 'objects', 'FixedRack.py')
        spec = importlib.util.spec_from_file_location("FixedRack", module_path)
        fixed_rack_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixed_rack_module)
        makeFixedRack = fixed_rack_module.makeFixedRack
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            doc = FreeCAD.newDocument("SolarProject")
        
        name = config.get("name", "FixedRack")
        
        # Get or create panel template
        panel_template = None
        if "panel_template" in config:
            panel_template = doc.getObject(config["panel_template"])
        
        # Create rack object
        rack = makeFixedRack(name, panel_template)
        
        # Set properties from config
        if "panels_per_row" in config:
            rack.PanelsPerRow = config["panels_per_row"]
        if "rows" in config:
            rack.Rows = config["rows"]
        if "tilt_angle" in config:
            rack.TiltAngle = config["tilt_angle"]
        if "post_height" in config:
            rack.PostHeight = config["post_height"]
        if "azimuth" in config:
            rack.Azimuth = config["azimuth"]
        if "row_spacing" in config:
            if hasattr(rack, "RowSpacing"):
                rack.RowSpacing = config["row_spacing"]
        
        # Mark object as needing recomputation after property changes
        rack.touch()
        doc.recompute()
        return rack.Name

    @execute_in_gui_thread
    def create_panel_template(self, config):
        """Create a solar panel template object for reuse.

        Args:
            config: Dictionary with panel configuration
                - width: Panel width in mm
                - height: Panel height in mm
                - thickness: Panel thickness in mm
                - power_watts: Rated power in watts
                - name: Optional object name

        Returns:
            str: Created template name
        """
        # Import using importlib to load from file path
        import sys
        import os
        import importlib.util
        
        module_path = os.path.join(_ADDON_PATH, 'objects', 'SolarPanel.py')
        spec = importlib.util.spec_from_file_location("SolarPanel", module_path)
        solar_panel_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(solar_panel_module)
        makeSolarPanel = solar_panel_module.makeSolarPanel
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            doc = FreeCAD.newDocument("SolarProject")
        
        name = config.get("name", "PanelTemplate")
        panel = makeSolarPanel(name)
        
        # Set properties from config       
        if "width" in config:
            panel.Width = config["width"]
        if "height" in config:
            panel.Height = config["height"]
        if "thickness" in config:
            panel.Thickness = config["thickness"]
        if "power_watts" in config:
            panel.PowerWatts = config["power_watts"]
        if "manufacturer" in config:
            panel.Manufacturer = config["manufacturer"]
        if "model" in config:
            panel.Model = config["model"]
        
        doc.recompute()
        return panel.Name
    
    @execute_in_gui_thread
    def create_tracker(self, config):
        """Create a single-axis tracker object using FeaturePython.

        Args:
            config: Dictionary with tracker configuration
                - panel_template: Optional name of panel template to reference
                - panels_per_tracker: Number of panels along tracker
                - rotation_angle: Current rotation angle in degrees
                - max_rotation: Maximum rotation angle
                - post_height: Center post height in mm
                - name: Optional object name

        Returns:
            str: Created object name
        """
        # Import using importlib to load from file path
        import sys
        import os
        import importlib.util
        
        module_path = os.path.join(_ADDON_PATH, 'objects', 'Tracker.py')
        spec = importlib.util.spec_from_file_location("Tracker", module_path)
        tracker_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tracker_module)
        makeSingleAxisTracker = tracker_module.makeSingleAxisTracker
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            doc = FreeCAD.newDocument("SolarProject")
        
        name = config.get("name", "Tracker")
        
        # Get panel template        
        panel_template = None
        if "panel_template" in config:
            panel_template = doc.getObject(config["panel_template"])
        
        # Create tracker object
        tracker = makeSingleAxisTracker(name, panel_template)
        
        # Set properties from config
        if "panels_per_tracker" in config:
            tracker.PanelsPerTracker = config["panels_per_tracker"]
        if "panels_high" in config:
            tracker.PanelsHigh = config["panels_high"]
        if "rotation_angle" in config:
            tracker.RotationAngle = config["rotation_angle"]
        if "max_rotation" in config:
            tracker.MaxRotation = config["max_rotation"]
        if "post_height" in config:
            tracker.PostHeight = config["post_height"]
        if "azimuth" in config:
            tracker.Azimuth = config["azimuth"]
        
        doc.recompute()
        return tracker.Name
    
    @execute_in_gui_thread
    @execute_in_gui_thread
    def create_array_layout(self, base_object, placements):
        """Create an array of solar objects at specified placements.
        
        Uses efficient object cloning with Links for memory efficiency.
         
        Args:
            base_object: Name of template object to array
            placements: List of dictionaries with placement data
                - x, y, z: Position in mm
                - rotation_x, rotation_y, rotation_z: Rotations in degrees
                - name: Optional name for the instance
        
        Returns:
            dict: Result with created object names and statistics
        """
        import math
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            raise Exception("No active document")
        
        base = doc.getObject(base_object)
        if not base:
            raise Exception(f"Base object '{base_object}' not found")
        
        # Create a group for the array
        array_group = doc.addObject("App::DocumentObjectGroup", "ArrayLayout")
        created_objects = []
        
        for i, placement_data in enumerate(placements):
            # Use App::Link for efficient object reuse
            # Links share geometry but have independent placements
            link_name = placement_data.get("name", f"{base_object}_Instance_{i:04d}")
            link = doc.addObject("App::Link", link_name)
            link.LinkedObject = base
            
            # Set placement
            x = placement_data.get("x", 0.0)
            y = placement_data.get("y", 0.0)
            z = placement_data.get("z", 0.0)
            rx = placement_data.get("rotation_x", 0.0)
            ry = placement_data.get("rotation_y", 0.0)
            rz = placement_data.get("rotation_z", 0.0)
            
            # Create placement
            placement = FreeCAD.Placement()
            placement.Base = FreeCAD.Vector(x, y, z)
            
            # Apply rotations (Z-Y-X order)
            if rz != 0:
                placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), rz)
            if ry != 0:
                placement.Rotation = placement.Rotation * FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), ry)
            if rx != 0:
                placement.Rotation = placement.Rotation * FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), rx)
            
            link.Placement = placement
            array_group.addObject(link)
            created_objects.append(link.Name)
        
        doc.recompute()
        
        return {
            "group_name": array_group.Name,
            "base_object": base_object,
            "instances_created": len(created_objects),
            "instance_names": created_objects[:10],  # First 10 names
            "total_instances": len(created_objects)
        }

    @execute_in_gui_thread
    def get_terrain_elevation(self, terrain_name, x, y):
        """Get terrain elevation at (x, y).

        Args:
            terrain_name: Name of terrain mesh
            x: X coordinate
            y: Y coordinate

        Returns:
            float: Z elevation or None
        """
        doc = FreeCAD.ActiveDocument
        if not doc:
            return None

        terrain = doc.getObject(terrain_name)
        if not terrain or not hasattr(terrain, "Mesh"):
            return None

        # Simplified elevation query - just find nearest vertex for now
        # TODO: Implement proper barycentric interpolation
        mesh = terrain.Mesh
        min_dist = float("inf")
        closest_z = None

        for point in mesh.Points:
            dx = point.x - x
            dy = point.y - y
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                closest_z = point.z

        return closest_z


def _server_thread_func(host, port):
    """Server thread function."""
    global _server, _running

    _server = SimpleXMLRPCServer((host, port), allow_none=True, logRequests=False)

    # Create RPC server instance and register its methods
    rpc = FreePVCRPCServer(host, port)
    _server.register_instance(rpc)

    FreeCAD.Console.PrintMessage(f"FreePVC RPC server listening on {host}:{port}\n")

    _running = True
    while _running:
        try:
            _server.handle_request()
        except Exception as e:
            if _running:
                FreeCAD.Console.PrintError(f"Server error: {e}\n")
            break


def start_server(host="localhost", port=9876):
    """Start the XML-RPC server in a background thread."""
    global _server_thread, _running, _timer

    if _running:
        raise Exception("Server is already running")

    _server_thread = threading.Thread(target=_server_thread_func, args=(host, port), daemon=True)
    _server_thread.start()

    # Start a timer to process queued commands in GUI thread
    try:
        from PySide2 import QtCore
    except ImportError:
        from PySide import QtCore

    def process_queue():
        while not _command_queue.empty():
            cmd = _command_queue.get()
            cmd()

    _timer = QtCore.QTimer()
    _timer.timeout.connect(process_queue)
    _timer.start(10)  # Check queue every 10ms

    FreeCAD.Console.PrintMessage("✓ FreePVC RPC queue processor started\n")

    return True


def stop_server():
    """Stop the XML-RPC server."""
    global _server, _running, _timer, _server_thread

    if not _running:
        raise Exception("Server is not running")

    _running = False

    # Stop the timer first
    if _timer:
        _timer.stop()
        _timer = None

    # Close the server socket to unblock handle_request()
    if _server:
        try:
            _server.server_close()
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Error closing server: {e}\n")
        _server = None

    # Don't join the thread - it's a daemon thread and will exit on its own
    _server_thread = None

    FreeCAD.Console.PrintMessage("✓ FreePVC RPC server stopped\n")
    
    return True


def is_running():
    """Check if server is running.

    Returns:
        bool: True if server is running
    """
    return _running
