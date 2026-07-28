"""Layout engine for automated solar array placement.

This module provides algorithms for efficient array layout generation
with object reuse and terrain-following capabilities.
"""

import math
from typing import List, Optional, Tuple
import numpy as np

from freepvc.models.terrain import TerrainMesh
from freepvc.models.solar_objects import (
    RackConfig,
    TrackerConfig,
    RackPlacement,
    LayoutConfig,
    ArrayLayout,
    RackType,
)


class LayoutEngine:
    """Engine for automated solar array placement with object reuse."""
    
    @staticmethod
    def generate_grid_layout(
        config: LayoutConfig,
        terrain_mesh: Optional[TerrainMesh] = None,
        boundary_polygon: Optional[np.ndarray] = None,
    ) -> ArrayLayout:
        """Generate grid-based array layout with optimized batch terrain queries.
        
        Creates a regular grid of racks following terrain contours.
        Uses efficient object reuse - all racks share the same template.
        OPTIMIZED: Batch terrain queries for 10-100x faster generation!
        
        Args:
            config: Layout configuration with rack template
            terrain_mesh: Optional terrain to follow
            boundary_polygon: Optional boundary polygon for placement area
            
        Returns:
            ArrayLayout with all rack placements
        """
        # Get rack dimensions
        rack_width_m = config.rack_config.rack_width_mm / 1000.0
        rack_length_m = config.rack_config.rack_length_mm / 1000.0
        
        # Calculate grid parameters
        row_spacing_m = config.spacing_m
        
        # Determine layout area
        # If target capacity is specified, calculate estimated area needed
        if config.target_capacity_mw:
            panels_per_rack = config.rack_config.panels_per_row * config.rack_config.rows
            power_per_rack_kw = (panels_per_rack * config.rack_config.panel_spec.power_watts) / 1000.0
            num_racks_needed = int(config.target_capacity_mw * 1000 / power_per_rack_kw)
            racks_per_row = int(num_racks_needed ** 0.5) + 2
            area_width_m = racks_per_row * rack_width_m * 1.2
            area_length_m = racks_per_row * row_spacing_m * 1.2
            
            # Use terrain bounds if available, but limit to estimated area
            if terrain_mesh:
                bounds = terrain_mesh.bounds
                terrain_x_min, terrain_x_max = bounds[0]
                terrain_y_min, terrain_y_max = bounds[1]
                terrain_width_m = (terrain_x_max - terrain_x_min) / 1000.0
                terrain_length_m = (terrain_y_max - terrain_y_min) / 1000.0
                
                # Start from terrain origin but limit extent to estimated area
                x_min, y_min = terrain_x_min, terrain_y_min
                x_max = min(terrain_x_max, terrain_x_min + area_width_m * 1000)
                y_max = min(terrain_y_max, terrain_y_min + area_length_m * 1000)
            else:
                x_min, y_min = 0, 0
                x_max, y_max = area_width_m * 1000, area_length_m * 1000
        elif terrain_mesh:
            # No capacity target - use full terrain bounds
            bounds = terrain_mesh.bounds
            x_min, x_max = bounds[0]
            y_min, y_max = bounds[1]
        else:
            # No terrain, no capacity - use a default 500m × 500m area
            x_min, y_min = 0, 0
            x_max, y_max = 500_000, 500_000
        
        # Convert to meters
        x_min_m, x_max_m = x_min / 1000.0, x_max / 1000.0
        y_min_m, y_max_m = y_min / 1000.0, y_max / 1000.0
        
        # Generate all potential grid positions upfront (vectorized)
        x_positions = np.arange(x_min_m, x_max_m - rack_width_m, rack_width_m)
        y_positions = np.arange(y_min_m, y_max_m - rack_length_m, row_spacing_m)
        xx, yy = np.meshgrid(x_positions, y_positions)
        grid_positions = np.column_stack([xx.ravel(), yy.ravel()])
        
        # Calculate center points for terrain sampling
        center_offsets = np.array([rack_width_m / 2, rack_length_m / 2])
        center_positions = grid_positions + center_offsets
        center_positions_mm = center_positions * 1000
        
        # Batch query terrain if available (MUCH faster!)
        if terrain_mesh:
            from freepvc.engines.terrain_engine import TerrainEngine
            
            # Single batched call for all elevations
            z_mm_array = TerrainEngine.interpolate_elevation(terrain_mesh, center_positions_mm)
            
            # Single batched call for all slopes
            slope_deg_array = TerrainEngine.compute_slopes_at_points(
                terrain_mesh, center_positions_mm, delta=1000.0
            )
            
            # Check if entire rack footprint is within terrain bounds (all 4 corners)
            bounds = terrain_mesh.bounds
            terrain_x_min, terrain_x_max = bounds[0]
            terrain_y_min, terrain_y_max = bounds[1]
            
            # Calculate all 4 corners for each rack position (in mm)
            rack_x_min = grid_positions[:, 0] * 1000  # Left edge
            rack_x_max = (grid_positions[:, 0] + rack_width_m) * 1000  # Right edge
            rack_y_min = grid_positions[:, 1] * 1000  # Bottom edge
            rack_y_max = (grid_positions[:, 1] + rack_length_m) * 1000  # Top edge
            
            # Check if all corners are within terrain bounds
            within_bounds = (
                (rack_x_min >= terrain_x_min) &
                (rack_x_max <= terrain_x_max) &
                (rack_y_min >= terrain_y_min) &
                (rack_y_max <= terrain_y_max)
            )
            
            # Filter by slope AND boundary (vectorized)
            valid_mask = (slope_deg_array <= config.max_slope_deg) & ~np.isnan(z_mm_array) & within_bounds
        else:
            z_mm_array = np.zeros(len(grid_positions))
            slope_deg_array = np.zeros(len(grid_positions))
            valid_mask = np.ones(len(grid_positions), dtype=bool)
        
        # Apply filters
        valid_positions = grid_positions[valid_mask]
        valid_z_mm = z_mm_array[valid_mask]
        valid_slopes = slope_deg_array[valid_mask]
        
        # Apply capacity limit
        panels_per_rack = config.rack_config.panels_per_row * config.rack_config.rows
        power_per_rack_kw = (panels_per_rack * config.rack_config.panel_spec.power_watts) / 1000.0
        
        if config.target_capacity_mw:
            target_capacity_kw = config.target_capacity_mw * 1000
            max_racks = int(np.ceil(target_capacity_kw / power_per_rack_kw))
            valid_positions = valid_positions[:max_racks]
            valid_z_mm = valid_z_mm[:max_racks]
            valid_slopes = valid_slopes[:max_racks]
        
        # Create placements
        placements: List[RackPlacement] = []
        for i, (pos, z_mm, slope) in enumerate(zip(valid_positions, valid_z_mm, valid_slopes)):
            placement = RackPlacement(
                x=pos[0] * 1000,  # mm
                y=pos[1] * 1000,
                z=z_mm,
                rotation_x=0.0,
                rotation_y=0.0,
                rotation_z=0.0,
                terrain_slope_deg=float(slope),
                terrain_aspect_deg=0.0,
                rack_id=f"Rack_{i:04d}",
            )
            placements.append(placement)
        
        layout = ArrayLayout(config=config, placements=placements)
        layout.calculate_statistics()
        
        return layout
    
    @staticmethod
    def generate_terrain_following_layout(
        config: LayoutConfig,
        terrain_mesh: TerrainMesh,
        contour_interval_m: float = 1.0,
    ) -> ArrayLayout:
        """Generate layout that follows terrain contours.
        
        Places racks along elevation contours for better terrain following.
        
        Args:
            config: Layout configuration
            terrain_mesh: Terrain surface to follow
            contour_interval_m: Vertical spacing between contour lines
            
        Returns:
            ArrayLayout with contour-following placements
        """
        # For now, use grid layout with terrain following
        # TODO: Implement true contour-following algorithm
        return LayoutEngine.generate_grid_layout(
            config=config,
            terrain_mesh=terrain_mesh
        )
    
    @staticmethod
    def optimize_spacing_for_gcr(
        rack_config: RackConfig,
        target_gcr: float = 0.4,
    ) -> float:
        """Calculate optimal row spacing for target GCR.
        
        GCR (Ground Coverage Ratio) = panel area / ground area
        
        Args:
            rack_config: Rack configuration
            target_gcr: Target ground coverage ratio (0.3-0.5 typical)
            
        Returns:
            Optimal row spacing in meters
        """
        # Rack area (looking down from above)
        rack_width_m = rack_config.rack_width_mm / 1000.0
        rack_length_m = rack_config.rack_length_mm / 1000.0
        
        # For tilted racks, projected area is reduced
        tilt_rad = math.radians(rack_config.tilt_angle_deg)
        projected_length_m = rack_length_m * math.cos(tilt_rad)
        
        rack_area_m2 = rack_width_m * projected_length_m
        
        # GCR = rack_area / (rack_width * row_spacing)
        # Therefore: row_spacing = rack_area / (rack_width * GCR)
        
        if target_gcr <= 0 or target_gcr > 1:
            raise ValueError("GCR must be between 0 and 1")
        
        spacing_m = rack_area_m2 / (rack_width_m * target_gcr)
        
        return spacing_m
    
    @staticmethod
    def calculate_actual_gcr(
        layout: ArrayLayout
    ) -> float:
        """Calculate actual GCR achieved by layout.
        
        Args:
            layout: Generated array layout
            
        Returns:
            Actual GCR (0-1)
        """
        if layout.ground_area_m2 > 0:
            return layout.panel_area_m2 / layout.ground_area_m2
        return 0.0
    
    @staticmethod
    def _sample_terrain(
        terrain_mesh: TerrainMesh,
        x_mm: float,
        y_mm: float
    ) -> Tuple[float, float, float]:
        """Sample terrain at position and return slope, aspect, elevation.
        
        Args:
            terrain_mesh: Terrain mesh
            x_mm: X coordinate in mm
            y_mm: Y coordinate in mm
            
        Returns:
            Tuple of (slope_deg, aspect_deg, elevation_mm)
        """
        from freepvc.engines.terrain_engine import TerrainEngine
        import numpy as np
        
        # Get elevation
        z_mm = TerrainEngine.interpolate_elevation(terrain_mesh, np.array([x_mm, y_mm]))
        
        # Sample nearby points to calculate slope
        delta = 1000.0  # mm (1 meter for better slope calculation)
        try:
            z_xp = TerrainEngine.interpolate_elevation(terrain_mesh, np.array([x_mm + delta, y_mm]))
            z_xn = TerrainEngine.interpolate_elevation(terrain_mesh, np.array([x_mm - delta, y_mm]))
            z_yp = TerrainEngine.interpolate_elevation(terrain_mesh, np.array([x_mm, y_mm + delta]))
            z_yn = TerrainEngine.interpolate_elevation(terrain_mesh, np.array([x_mm, y_mm - delta]))
            
            # Calculate gradients
            dx = (z_xp - z_xn) / (2 * delta)
            dy = (z_yp - z_yn) / (2 * delta)
            
            # Calculate slope and aspect
            slope_rad = math.atan(math.sqrt(dx**2 + dy**2))
            slope_deg = math.degrees(slope_rad)
            
            if dx != 0 or dy != 0:
                aspect_rad = math.atan2(dy, dx)
                aspect_deg = (90 - math.degrees(aspect_rad)) % 360
            else:
                aspect_deg = 0.0
            
            return slope_deg, aspect_deg, z_mm
        except:
            # If any query fails, return flat
            return 0.0, 0.0, z_mm
    
    @staticmethod
    def create_layout_groups(
        layout: ArrayLayout,
        racks_per_string: int = 10,
    ) -> dict:
        """Group racks into electrical strings for efficient wiring.
        
        Args:
            layout: Generated array layout
            racks_per_string: Number of racks per electrical string
            
        Returns:
            Dictionary mapping string IDs to lists of rack placements
        """
        strings = {}
        
        for i, placement in enumerate(layout.placements):
            string_id = f"String_{i // racks_per_string:04d}"
            
            if string_id not in strings:
                strings[string_id] = []
            
            # Update placement with string assignment
            placement.string_id = string_id
            strings[string_id].append(placement)
        
        return strings
    
    @staticmethod
    def estimate_build_area(
        config: LayoutConfig,
        target_dc_capacity_mw: float
    ) -> Tuple[float, int]:
        """Estimate required site area for target DC capacity.
        
        Args:
            config: Layout configuration
            target_dc_capacity_mw: Target DC capacity in MW
            
        Returns:
            Tuple of (required_area_m2, estimated_rack_count)
        """
        # DC capacity per rack
        dc_per_rack_kw = config.rack_config.dc_capacity_kw
        target_dc_kw = target_dc_capacity_mw * 1000
        
        # Estimated rack count
        rack_count = math.ceil(target_dc_kw / dc_per_rack_kw)
        
        # Calculate area based on GCR
        rack_width_m = config.rack_config.rack_width_mm / 1000.0
        rack_length_m = config.rack_config.rack_length_mm / 1000.0
        
        tilt_rad = math.radians(config.rack_config.tilt_angle_deg)
        projected_length_m = rack_length_m * math.cos(tilt_rad)
        
        rack_area_m2 = rack_width_m * projected_length_m
        total_rack_area_m2 = rack_count * rack_area_m2
        
        # Apply GCR to get total site area
        gcr = config.gcr_target if config.gcr_target > 0 else 0.4
        required_area_m2 = total_rack_area_m2 / gcr
        
        return required_area_m2, rack_count
