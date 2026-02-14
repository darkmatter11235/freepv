"""Terrain data models for FreePVC.

This module defines dataclasses for representing terrain data,
including point clouds, meshes, and slope analysis results.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np
from enum import Enum


class TerrainSource(Enum):
    """Source type for terrain data."""
    CSV_POINTS = "csv_points"
    DEM_ASCII = "dem_ascii"
    DXF_CONTOURS = "dxf_contours"
    SURVEYED_POINTS = "surveyed_points"


@dataclass
class TerrainData:
    """Raw terrain input data (point cloud).

    Represents the initial terrain data before mesh generation.
    Coordinates are in millimeters to match FreeCAD units.
    """

    points: np.ndarray  # Nx3 array of [x, y, z] coordinates (mm)
    source: TerrainSource
    source_file: Optional[str] = None
    coordinate_system: str = "local"  # or "WGS84", "UTM", etc.
    metadata: dict = field(default_factory=dict)

    @property
    def num_points(self) -> int:
        """Number of terrain points."""
        return len(self.points)

    @property
    def bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """Bounding box as ((x_min, x_max), (y_min, y_max), (z_min, z_max))."""
        if len(self.points) == 0:
            return ((0, 0), (0, 0), (0, 0))

        mins = self.points.min(axis=0)
        maxs = self.points.max(axis=0)
        return ((mins[0], maxs[0]), (mins[1], maxs[1]), (mins[2], maxs[2]))

    @property
    def elevation_range(self) -> Tuple[float, float]:
        """Min and max elevation (z coordinate) in mm."""
        z_coords = self.points[:, 2]
        return (float(z_coords.min()), float(z_coords.max()))

    def get_statistics(self) -> dict:
        """Get statistical summary of terrain data."""
        x, y, z = self.points[:, 0], self.points[:, 1], self.points[:, 2]

        return {
            "num_points": self.num_points,
            "bounds": self.bounds,
            "x_extent_m": (x.max() - x.min()) / 1000,
            "y_extent_m": (y.max() - y.min()) / 1000,
            "elevation_range_m": (z.max() - z.min()) / 1000,
            "mean_elevation_mm": float(z.mean()),
            "std_elevation_mm": float(z.std()),
        }


@dataclass
class TerrainMesh:
    """Triangulated terrain mesh generated from point cloud.

    Represents a Delaunay triangulation of the terrain surface.
    """

    vertices: np.ndarray  # Nx3 array of vertex coordinates (mm)
    triangles: np.ndarray  # Mx3 array of triangle vertex indices
    source_data: Optional[TerrainData] = None

    # Derived properties
    face_normals: Optional[np.ndarray] = None  # Mx3 array of face normal vectors
    vertex_normals: Optional[np.ndarray] = None  # Nx3 array of vertex normal vectors

    @property
    def num_vertices(self) -> int:
        """Number of mesh vertices."""
        return len(self.vertices)

    @property
    def num_faces(self) -> int:
        """Number of triangular faces."""
        return len(self.triangles)

    @property
    def bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """Bounding box as ((x_min, x_max), (y_min, y_max), (z_min, z_max))."""
        mins = self.vertices.min(axis=0)
        maxs = self.vertices.max(axis=0)
        return ((mins[0], maxs[0]), (mins[1], maxs[1]), (mins[2], maxs[2]))

    def compute_face_normals(self) -> np.ndarray:
        """Compute normal vectors for all faces."""
        if self.face_normals is not None:
            return self.face_normals

        # Get triangle vertices
        v0 = self.vertices[self.triangles[:, 0]]
        v1 = self.vertices[self.triangles[:, 1]]
        v2 = self.vertices[self.triangles[:, 2]]

        # Compute edge vectors
        edge1 = v1 - v0
        edge2 = v2 - v0

        # Cross product gives normal
        normals = np.cross(edge1, edge2)

        # Normalize
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        lengths = np.where(lengths == 0, 1, lengths)  # Avoid division by zero
        normals = normals / lengths

        self.face_normals = normals
        return normals

    def compute_vertex_normals(self) -> np.ndarray:
        """Compute normal vectors for all vertices (averaged from adjacent faces)."""
        if self.vertex_normals is not None:
            return self.vertex_normals

        # First compute face normals
        face_normals = self.compute_face_normals()

        # Initialize vertex normals
        vertex_normals = np.zeros((self.num_vertices, 3))

        # Accumulate face normals at each vertex
        for i, tri in enumerate(self.triangles):
            for vertex_idx in tri:
                vertex_normals[vertex_idx] += face_normals[i]

        # Normalize
        lengths = np.linalg.norm(vertex_normals, axis=1, keepdims=True)
        lengths = np.where(lengths == 0, 1, lengths)
        vertex_normals = vertex_normals / lengths

        self.vertex_normals = vertex_normals
        return vertex_normals


@dataclass
class SlopeMap:
    """Slope analysis results for terrain mesh.

    Stores slope, aspect, and derived classifications for each face or vertex.
    """

    mesh: TerrainMesh

    # Per-face values
    face_slopes: np.ndarray  # Slope angle in degrees for each face
    face_aspects: np.ndarray  # Aspect angle (0-360°, 0=North) for each face

    # Per-vertex values (interpolated from faces)
    vertex_slopes: Optional[np.ndarray] = None
    vertex_aspects: Optional[np.ndarray] = None

    # Classification thresholds (degrees)
    slope_threshold_low: float = 5.0   # Gentle slope
    slope_threshold_mid: float = 15.0  # Moderate slope
    slope_threshold_high: float = 25.0 # Steep slope

    @property
    def max_slope(self) -> float:
        """Maximum slope in degrees."""
        return float(self.face_slopes.max())

    @property
    def mean_slope(self) -> float:
        """Mean slope in degrees."""
        return float(self.face_slopes.mean())

    def classify_slopes(self) -> np.ndarray:
        """Classify slopes into categories: 0=flat, 1=gentle, 2=moderate, 3=steep, 4=very steep.

        Returns:
            Array of integers 0-4 for each face
        """
        classification = np.zeros(len(self.face_slopes), dtype=int)

        classification[self.face_slopes >= self.slope_threshold_low] = 1
        classification[self.face_slopes >= self.slope_threshold_mid] = 2
        classification[self.face_slopes >= self.slope_threshold_high] = 3
        classification[self.face_slopes >= 35.0] = 4

        return classification

    def get_buildable_faces(self, max_slope: float = 20.0) -> np.ndarray:
        """Get indices of faces suitable for panel placement (slope below threshold).

        Args:
            max_slope: Maximum buildable slope in degrees

        Returns:
            Array of face indices
        """
        return np.where(self.face_slopes <= max_slope)[0]

    def compute_heatmap_colors(self, scheme: str = "slope") -> np.ndarray:
        """Generate RGB colors for visualization.

        Args:
            scheme: Color scheme - "slope" (green to red), "aspect" (compass directions)

        Returns:
            Nx3 array of RGB values (0-1 range)
        """
        colors = np.zeros((len(self.face_slopes), 3))

        if scheme == "slope":
            # Green (flat) -> Yellow (moderate) -> Red (steep)
            # Normalize slopes to 0-1 range (0-45 degrees)
            normalized = np.clip(self.face_slopes / 45.0, 0, 1)

            colors[:, 0] = normalized  # Red increases with slope
            colors[:, 1] = 1.0 - normalized * 0.5  # Green decreases
            colors[:, 2] = 0.1  # Keep blue low

        elif scheme == "aspect":
            # Color by compass direction
            # North=Blue, East=Red, South=Yellow, West=Green
            normalized_aspect = self.face_aspects / 360.0

            # Use HSV-like mapping
            hue_to_rgb = lambda h: (
                max(0, min(1, abs(h * 6 - 3) - 1)),  # R
                max(0, min(1, 2 - abs(h * 6 - 2))),  # G
                max(0, min(1, 2 - abs(h * 6 - 4))),  # B
            )

            for i, aspect in enumerate(normalized_aspect):
                colors[i] = hue_to_rgb(aspect)

        return colors

    def get_statistics(self) -> dict:
        """Get statistical summary of slope analysis."""
        classification = self.classify_slopes()

        return {
            "mean_slope_deg": float(self.mean_slope),
            "max_slope_deg": float(self.max_slope),
            "min_slope_deg": float(self.face_slopes.min()),
            "std_slope_deg": float(self.face_slopes.std()),
            "num_flat": int((classification == 0).sum()),
            "num_gentle": int((classification == 1).sum()),
            "num_moderate": int((classification == 2).sum()),
            "num_steep": int((classification == 3).sum()),
            "num_very_steep": int((classification == 4).sum()),
            "buildable_area_pct": float(len(self.get_buildable_faces()) / len(self.face_slopes) * 100),
        }


@dataclass
class ContourLine:
    """Single elevation contour line.

    Represents a polyline at constant elevation.
    """

    elevation: float  # Elevation in mm
    points: np.ndarray  # Nx2 array of [x, y] coordinates (mm)
    is_closed: bool = False

    @property
    def length(self) -> float:
        """Total length of contour line in mm."""
        if len(self.points) < 2:
            return 0.0

        # Calculate distances between consecutive points
        diffs = np.diff(self.points, axis=0)
        distances = np.linalg.norm(diffs, axis=1)
        return float(distances.sum())


@dataclass
class ContourSet:
    """Collection of contour lines at different elevations.

    Generated from terrain mesh for visualization.
    """

    contours: List[ContourLine]
    interval: float  # Elevation interval between contours (mm)
    mesh: Optional[TerrainMesh] = None

    @property
    def num_contours(self) -> int:
        """Number of contour lines."""
        return len(self.contours)

    @property
    def elevation_range(self) -> Tuple[float, float]:
        """Min and max elevation of contours."""
        if not self.contours:
            return (0.0, 0.0)
        elevations = [c.elevation for c in self.contours]
        return (min(elevations), max(elevations))

    def get_contour_at_elevation(self, elevation: float, tolerance: float = 1.0) -> Optional[ContourLine]:
        """Find contour line closest to specified elevation.

        Args:
            elevation: Target elevation in mm
            tolerance: Maximum elevation difference in mm

        Returns:
            ContourLine or None if not found
        """
        for contour in self.contours:
            if abs(contour.elevation - elevation) <= tolerance:
                return contour
        return None
