"""FreePVC Connection - Extends freecad-mcp's FreeCADConnection with solar-specific RPC methods."""

import xmlrpc.client
from typing import Any, Dict, List, Optional, Tuple

try:
    from freecad_mcp.server import FreeCADConnection as BaseFreeCADConnection
except ImportError:
    # Fallback if freecad-mcp is not installed
    print("Warning: freecad-mcp not found. Using minimal base class.")

    class BaseFreeCADConnection:
        """Minimal base class if freecad-mcp is not available."""

        RPC_HOST = "127.0.0.1"
        RPC_PORT = 9875

        def __init__(self, host: str = None, port: int = None):
            self.host = host or self.RPC_HOST
            self.port = port or self.RPC_PORT
            self.server = xmlrpc.client.ServerProxy(
                f"http://{self.host}:{self.port}", allow_none=True
            )

        def ping(self) -> str:
            """Test connection to FreeCAD."""
            return self.server.ping()

        def execute_code(self, code: str) -> Any:
            """Execute Python code in FreeCAD."""
            return self.server.execute_code(code)


class FreePVCConnection(BaseFreeCADConnection):
    """Extended FreeCAD connection with solar-specific RPC methods.

    Inherits all base FreeCAD operations from freecad-mcp and adds:
    - Terrain mesh creation and manipulation
    - Solar rack/tracker object creation
    - Array placement operations
    - Heatmap visualization (face colors)
    - Cable path creation
    - Cross-section generation
    """

    # Use different port to avoid conflict with base freecad-mcp
    RPC_PORT = 9876

    def __init__(self, host: str = None, port: int = None):
        """Initialize connection to FreePVC's RPC server on port 9876."""
        super().__init__(host=host, port=port or self.RPC_PORT)

    # Solar-specific RPC methods that will be implemented in the FreeCAD addon

    def create_terrain_mesh(
        self,
        vertices: List[Tuple[float, float, float]],
        triangles: List[Tuple[int, int, int]],
        name: str = "Terrain",
    ) -> str:
        """Create a terrain mesh object in FreeCAD.

        Args:
            vertices: List of (x, y, z) coordinates
            triangles: List of (i, j, k) vertex index triples
            name: Object name

        Returns:
            Object name in FreeCAD document
        """
        return self.server.create_terrain_mesh(vertices, triangles, name)

    def set_face_colors(
        self, obj_name: str, colors: List[Tuple[float, float, float]]
    ) -> bool:
        """Apply per-face colors to a mesh (for heatmap visualization).

        Args:
            obj_name: Name of mesh object
            colors: List of (r, g, b) tuples, one per face (values 0-1)

        Returns:
            Success status
        """
        return self.server.set_face_colors(obj_name, colors)

    def create_fixed_rack(self, config: Dict[str, Any]) -> str:
        """Create a fixed-tilt solar rack object.

        Args:
            config: Dictionary with rack configuration (module size, tilt, etc.)

        Returns:
            Object name
        """
        return self.server.create_fixed_rack(config)

    def create_tracker(self, config: Dict[str, Any]) -> str:
        """Create a single-axis tracker object.

        Args:
            config: Dictionary with tracker configuration

        Returns:
            Object name
        """
        return self.server.create_tracker(config)

    def place_array(
        self,
        base_object: str,
        positions: List[Tuple[float, float, float]],
        rotations: Optional[List[Tuple[float, float, float]]] = None,
    ) -> List[str]:
        """Place an array of objects at specified positions.

        Args:
            base_object: Name of object to array
            positions: List of (x, y, z) positions
            rotations: Optional list of (rx, ry, rz) rotations in degrees

        Returns:
            List of created object names
        """
        return self.server.place_array(base_object, positions, rotations or [])

    def get_terrain_elevation(
        self, terrain_name: str, x: float, y: float
    ) -> Optional[float]:
        """Query terrain elevation at a specific (x, y) point.

        Args:
            terrain_name: Name of terrain object
            x: X coordinate
            y: Y coordinate

        Returns:
            Z elevation at (x, y) or None if outside terrain bounds
        """
        return self.server.get_terrain_elevation(terrain_name, x, y)

    def create_cable_path(
        self,
        points: List[Tuple[float, float, float]],
        diameter: float,
        name: str = "Cable",
    ) -> str:
        """Create a cable path object.

        Args:
            points: List of (x, y, z) path points
            diameter: Cable diameter in mm
            name: Object name

        Returns:
            Object name
        """
        return self.server.create_cable_path(points, diameter, name)

    def create_cross_section(
        self,
        terrain_name: str,
        line_start: Tuple[float, float],
        line_end: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Generate a cross-section profile through terrain.

        Args:
            terrain_name: Name of terrain object
            line_start: (x, y) start point
            line_end: (x, y) end point

        Returns:
            Dictionary with profile data (stations, elevations)
        """
        return self.server.create_cross_section(terrain_name, line_start, line_end)

    def get_object_positions(self, group_name: str) -> List[Tuple[float, float, float]]:
        """Get positions of all objects in a group.

        Args:
            group_name: Name of group object

        Returns:
            List of (x, y, z) positions
        """
        return self.server.get_object_positions(group_name)
