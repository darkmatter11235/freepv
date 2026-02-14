"""Tests for terrain engine.

Run with: pytest tests/test_terrain_engine.py
"""

import numpy as np
import pytest

from freepvc.models.terrain import TerrainData, TerrainSource
from freepvc.engines.terrain_engine import TerrainEngine
from freepvc.io.terrain_import import create_sample_terrain


def test_create_sample_terrain():
    """Test sample terrain generation."""
    terrain = create_sample_terrain(size=10000, spacing=1000, slope=5.0, roughness=500)

    assert terrain.num_points > 0
    assert terrain.source == TerrainSource.SURVEYED_POINTS
    bounds = terrain.bounds
    assert bounds[0][1] - bounds[0][0] == pytest.approx(10000, abs=1)  # X extent
    assert bounds[1][1] - bounds[1][0] == pytest.approx(10000, abs=1)  # Y extent


def test_mesh_from_points():
    """Test Delaunay mesh generation."""
    terrain = create_sample_terrain(size=5000, spacing=1000, slope=0)

    mesh = TerrainEngine.create_mesh_from_points(terrain)

    assert mesh.num_vertices == terrain.num_points
    assert mesh.num_faces > 0
    assert mesh.face_normals is not None
    assert mesh.vertex_normals is not None


def test_slope_analysis():
    """Test slope and aspect calculation."""
    # Create flat terrain
    flat_terrain = TerrainEngine.create_regular_grid_terrain(
        x_extent=10000,
        y_extent=10000,
        grid_spacing=2000,
        elevation_function=lambda x, y: 0.0,
    )
    flat_mesh = TerrainEngine.create_mesh_from_points(flat_terrain)
    flat_slope = TerrainEngine.analyze_slope(flat_mesh)

    # Flat terrain should have near-zero slopes
    assert flat_slope.mean_slope < 1.0  # Less than 1 degree
    assert flat_slope.max_slope < 2.0

    # Create sloped terrain (5 degrees)
    import math

    sloped_terrain = TerrainEngine.create_regular_grid_terrain(
        x_extent=10000,
        y_extent=10000,
        grid_spacing=2000,
        elevation_function=lambda x, y: y * math.tan(math.radians(5)),
    )
    sloped_mesh = TerrainEngine.create_mesh_from_points(sloped_terrain)
    sloped_slope = TerrainEngine.analyze_slope(sloped_mesh)

    # Sloped terrain should have approx 5 degree slope
    assert sloped_slope.mean_slope == pytest.approx(5.0, abs=0.5)


def test_elevation_interpolation():
    """Test elevation interpolation."""
    import math

    # Create terrain with known slope
    terrain = TerrainEngine.create_regular_grid_terrain(
        x_extent=10000,
        y_extent=10000,
        grid_spacing=1000,
        elevation_function=lambda x, y: y * math.tan(math.radians(10)),
    )
    mesh = TerrainEngine.create_mesh_from_points(terrain)

    # Query elevation at known point
    query_point = np.array([5000, 5000])
    elevation = TerrainEngine.interpolate_elevation(mesh, query_point)

    # At y=5000, with 10 degree slope: z = 5000 * tan(10°)
    expected = 5000 * math.tan(math.radians(10))
    assert elevation == pytest.approx(expected, abs=100)  # Within 100mm


def test_slope_classification():
    """Test slope classification."""
    terrain = create_sample_terrain(size=10000, spacing=1000, slope=15, roughness=1000)
    mesh = TerrainEngine.create_mesh_from_points(terrain)
    slope_map = TerrainEngine.analyze_slope(mesh)

    classification = slope_map.classify_slopes()

    # Should have some variety of slope classes
    assert len(classification) == mesh.num_faces
    assert classification.max() >= 1  # At least some non-flat faces

    stats = slope_map.get_statistics()
    assert "mean_slope_deg" in stats
    assert "buildable_area_pct" in stats


def test_heatmap_colors():
    """Test heatmap color generation."""
    terrain = create_sample_terrain(size=5000, spacing=1000, slope=10, roughness=500)
    mesh = TerrainEngine.create_mesh_from_points(terrain)
    slope_map = TerrainEngine.analyze_slope(mesh)

    # Test slope color scheme
    colors_slope = slope_map.compute_heatmap_colors("slope")
    assert colors_slope.shape == (mesh.num_faces, 3)
    assert colors_slope.min() >= 0.0
    assert colors_slope.max() <= 1.0

    # Test aspect color scheme
    colors_aspect = slope_map.compute_heatmap_colors("aspect")
    assert colors_aspect.shape == (mesh.num_faces, 3)
    assert colors_aspect.min() >= 0.0
    assert colors_aspect.max() <= 1.0


def test_buildable_faces():
    """Test buildable area calculation."""
    # Create steep terrain (30 degrees)
    import math

    steep_terrain = TerrainEngine.create_regular_grid_terrain(
        x_extent=5000,
        y_extent=5000,
        grid_spacing=1000,
        elevation_function=lambda x, y: y * math.tan(math.radians(30)),
    )
    steep_mesh = TerrainEngine.create_mesh_from_points(steep_terrain)
    steep_slope = TerrainEngine.analyze_slope(steep_mesh)

    # Most faces should be too steep for default 20 degree threshold
    buildable = steep_slope.get_buildable_faces(max_slope=20.0)
    assert len(buildable) < steep_mesh.num_faces * 0.5  # Less than 50% buildable


def test_grid_elevation_generation():
    """Test regular grid elevation generation for visualization."""
    terrain = create_sample_terrain(size=10000, spacing=2000, slope=5, roughness=200)
    mesh = TerrainEngine.create_mesh_from_points(terrain)

    x, y, z_grid = TerrainEngine.generate_grid_elevations(mesh, grid_size=20)

    assert len(x) == 20
    assert len(y) == 20
    assert z_grid.shape == (20, 20)
    assert not np.any(np.isnan(z_grid))  # No NaN values within bounds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
