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
        """Generate grid-based array layout.
        
        Creates a regular grid of racks following terrain contours.
        Uses efficient object reuse - all racks share the same template.
        
        Args:
            config: Layout configuration with rack template
            terrain_mesh: Optional terrain to follow
            boundary_polygon: Optional boundary polygon for placement area
            
        Returns:
            ArrayLayout with all rack placements
        """
        placements: List[RackPlacement] = []
        
        # Get rack dimensions
        rack_width_m = config.rack_config.rack_width_mm / 1000.0
        rack_length_m = config.rack_config.rack_length_mm / 1000.0
        
        # Calculate grid parameters
        row_spacing_m = config.spacing_m
        
        # Determine layout area
        if terrain_mesh:
            # Use terrain bounds
            bounds = terrain_mesh.bounds
            x_min, x_max = bounds[0]
            y_min, y_max = bounds[1]
        elif config.target_capacity_mw:
            # Calculate compact area based on target capacity
            # Estimate number of racks needed
            panels_per_rack = config.rack_config.panels_per_row * config.rack_config.rows
            power_per_rack_kw = (panels_per_rack * config.rack_config.panel_spec.power_watts) / 1000.0
            num_racks_needed = int(config.target_capacity_mw * 1000 / power_per_rack_kw)
            
            # Estimate grid size (roughly square layout)
            racks_per_row = int(num_racks_needed ** 0.5) + 2  # Add buffer
            
            # Calculate area needed
            rack_width_m = config.rack_config.rack_width_mm / 1000.0
            rack_length_m = config.rack_config.rack_length_mm / 1000.0
            
            area_width_m = racks_per_row * rack_width_m * 1.2
            area_length_m = racks_per_row * row_spacing_m * 1.2
            
            x_min, y_min = 0, 0
            x_max, y_max = area_width_m * 1000, area_length_m * 1000  # Convert to mm
        else:
            # Default to moderate area (1km x 1km)
            x_min, y_min = 0, 0
            x_max, y_max = 1_000_000, 1_000_000  # mm (1km x 1km)
        
        # Convert to meters for calculations
        x_min_m, x_max_m = x_min / 1000.0, x_max / 1000.0
        y_min_m, y_max_m = y_min / 1000.0, y_max / 1000.0
        
        # Generate grid of positions
        rack_id = 0
        y_pos = y_min_m
        
        # Calculate per-rack capacity for target capacity checking
        panels_per_rack = config.rack_config.panels_per_row * config.rack_config.rows
        power_per_rack_kw = (panels_per_rack * config.rack_config.panel_spec.power_watts) / 1000.0
        target_capacity_kw = config.target_capacity_mw * 1000 if config.target_capacity_mw else None
        current_capacity_kw = 0.0
        
        while y_pos + rack_length_m < y_max_m:
            x_pos = x_min_m
            
            while x_pos + rack_width_m < x_max_m:
                # Check if we've reached target capacity
                if target_capacity_kw and current_capacity_kw >= target_capacity_kw:
                    break
                    
                # Check terrain constraints if available
                if terrain_mesh:
                    # Sample terrain slope at rack center
                    x_center_mm = (x_pos + rack_width_m / 2) * 1000
                    y_center_mm = (y_pos + rack_length_m / 2) * 1000
                    
                    try:
                        slope, aspect, z_mm = LayoutEngine._sample_terrain(
                            terrain_mesh,
                            x_center_mm,
                            y_center_mm
                        )
                        
                        # Skip if slope too steep
                        if slope > config.max_slope_deg:
                            x_pos += rack_width_m
                            continue
                        
                        z_m = z_mm / 1000.0
                    except:
                        # If terrain query fails, skip this position
                        x_pos += rack_width_m
                        continue
                else:
                    slope, aspect, z_m = 0.0, 0.0, 0.0
                
                # Create placement
                placement = RackPlacement(
                    x=x_pos * 1000,  # Convert back to mm
                    y=y_pos * 1000,
                    z=z_m * 1000,
                    rotation_x=0.0,  # Tilt is built into rack geometry
                    rotation_y=0.0,  # Could adjust based on terrain
                    rotation_z=0.0,  # Azimuth is built into rack geometry
                    terrain_slope_deg=slope,
                    terrain_aspect_deg=aspect,
                    rack_id=f"Rack_{rack_id:04d}",
                )
                
                placements.append(placement)
                rack_id += 1
                current_capacity_kw += power_per_rack_kw
                
                x_pos += rack_width_m
            
            # Check if we've reached target capacity (break outer loop too)
            if target_capacity_kw and current_capacity_kw >= target_capacity_kw:
                break
                
            y_pos += row_spacing_m
        
        # Create layout result
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
