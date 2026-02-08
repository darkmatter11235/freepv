"""FreePVC XML-RPC Server - Runs inside FreeCAD to handle MCP requests.

Based on the pattern from freecad-mcp but extended with solar-specific operations.
"""

import threading
import traceback
from xmlrpc.server import SimpleXMLRPCServer
from queue import Queue

import FreeCAD
import FreeCADGui

# Global server instance and state
_server = None
_server_thread = None
_running = False
_command_queue = Queue()


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
        """Create a fixed-tilt solar rack object.

        Args:
            config: Dictionary with rack configuration

        Returns:
            str: Created object name
        """
        # This will be implemented once we have the FeaturePython objects
        # For now, return a placeholder
        FreeCAD.Console.PrintMessage("create_fixed_rack called with config: {}\n".format(config))
        return "FixedRack_placeholder"

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
        _server.handle_request()


def start_server(host="localhost", port=9876):
    """Start the XML-RPC server in a background thread."""
    global _server_thread, _running

    if _running:
        raise Exception("Server is already running")

    _server_thread = threading.Thread(target=_server_thread_func, args=(host, port), daemon=True)
    _server_thread.start()

    # Start a timer to process queued commands in GUI thread
    from PySide import QtCore

    def process_queue():
        if not _command_queue.empty():
            cmd = _command_queue.get()
            cmd()

    timer = QtCore.QTimer()
    timer.timeout.connect(process_queue)
    timer.start(10)  # Check queue every 10ms

    return True


def stop_server():
    """Stop the XML-RPC server."""
    global _server, _running

    if not _running:
        raise Exception("Server is not running")

    _running = False

    if _server:
        _server.shutdown()
        _server = None

    return True


def is_running():
    """Check if server is running.

    Returns:
        bool: True if server is running
    """
    return _running
