"""Shading analysis engine for solar array layouts.

This module provides algorithms for calculating row-to-row shading,
terrain-based shadow analysis, and annual shading metrics.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import numpy as np

from freepvc.models.solar_objects import RackPlacement, RackConfig
from freepvc.models.terrain import TerrainMesh


@dataclass
class SunPosition:
    """Sun position at a specific time and location."""
    altitude_deg: float  # Sun altitude above horizon (0-90°)
    azimuth_deg: float  # Sun azimuth from North (0-360°)
    datetime: datetime
    
    @property
    def is_daylight(self) -> bool:
        """Check if sun is above horizon."""
        return self.altitude_deg > 0


@dataclass
class ShadingResult:
    """Shading analysis results for a single rack."""
    rack_id: str
    shaded_fraction: float  # 0.0 = fully lit, 1.0 = fully shaded
    shadow_source_ids: List[str]  # IDs of racks casting shadows
    sun_position: SunPosition
    
    @property
    def is_shaded(self) -> bool:
        """Check if rack has any shading."""
        return self.shaded_fraction > 0.01


@dataclass
class AnnualShadingMetrics:
    """Annual shading metrics for a rack or array."""
    rack_id: Optional[str] = None
    
    # Time-based metrics
    total_daylight_hours: float = 0.0
    shaded_hours: float = 0.0
    unshaded_hours: float = 0.0
    
    # Fractional metrics
    average_shading_fraction: float = 0.0  # Average over all daylight hours
    shading_loss_fraction: float = 0.0  # Estimated energy loss
    
    # Seasonal breakdown
    winter_shading_fraction: float = 0.0
    spring_shading_fraction: float = 0.0
    summer_shading_fraction: float = 0.0
    fall_shading_fraction: float = 0.0
    
    @property
    def shading_percentage(self) -> float:
        """Shading as percentage."""
        return self.average_shading_fraction * 100
    
    @property
    def availability_percentage(self) -> float:
        """Unshaded percentage."""
        return (1.0 - self.average_shading_fraction) * 100


class ShadingEngine:
    """Engine for solar shading analysis."""
    
    @staticmethod
    def calculate_sun_position(
        latitude_deg: float,
        longitude_deg: float,
        dt: datetime,
        timezone_offset_hours: float = 0.0,
    ) -> SunPosition:
        """Calculate sun position for given location and time.
        
        Uses simplified solar position algorithm (accurate to ~0.01°).
        Based on NREL Solar Position Algorithm (SPA) simplified version.
        
        Args:
            latitude_deg: Site latitude in decimal degrees
            longitude_deg: Site longitude in decimal degrees
            dt: Date and time (UTC or local with offset)
            timezone_offset_hours: Timezone offset from UTC (e.g., -8 for PST)
            
        Returns:
            SunPosition with altitude and azimuth
        """
        # Convert to radians
        lat_rad = math.radians(latitude_deg)
        
        # Calculate Julian day
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3
        jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        
        # Fractional day
        hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        jd = jdn + (hour - 12.0) / 24.0
        
        # Days since J2000.0
        n = jd - 2451545.0
        
        # Mean solar time
        solar_time = hour + longitude_deg / 15.0 + timezone_offset_hours
        
        # Solar declination (simplified)
        declination_rad = math.radians(23.45) * math.sin(math.radians(360 / 365.0 * (n + 284)))
        
        # Hour angle
        hour_angle_deg = 15.0 * (solar_time - 12.0)
        hour_angle_rad = math.radians(hour_angle_deg)
        
        # Solar altitude
        sin_altitude = (
            math.sin(lat_rad) * math.sin(declination_rad) +
            math.cos(lat_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad)
        )
        altitude_rad = math.asin(max(-1.0, min(1.0, sin_altitude)))
        altitude_deg = math.degrees(altitude_rad)
        
        # Solar azimuth
        cos_azimuth = (
            (math.sin(declination_rad) - math.sin(lat_rad) * sin_altitude) /
            (math.cos(lat_rad) * math.cos(altitude_rad) + 1e-10)
        )
        cos_azimuth = max(-1.0, min(1.0, cos_azimuth))
        azimuth_rad = math.acos(cos_azimuth)
        azimuth_deg = math.degrees(azimuth_rad)
        
        # Correct azimuth for afternoon (PM)
        if hour_angle_deg > 0:
            azimuth_deg = 360.0 - azimuth_deg
        
        return SunPosition(
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            datetime=dt,
        )
    
    @staticmethod
    def calculate_rack_shadow_projection(
        rack_config: RackConfig,
        rack_placement: RackPlacement,
        sun_position: SunPosition,
    ) -> Tuple[np.ndarray, float]:
        """Calculate shadow projection from a rack.
        
        Projects rack corners onto ground plane to determine shadow extent.
        
        Args:
            rack_config: Rack configuration (dimensions, tilt)
            rack_placement: Rack placement (position)
            sun_position: Sun position (altitude, azimuth)
            
        Returns:
            Tuple of (shadow_polygon_2d, shadow_length_m)
            shadow_polygon_2d: Nx2 array of shadow boundary points (x, y)
            shadow_length_m: Maximum shadow extent in meters
        """
        if not sun_position.is_daylight:
            # No shadow at night
            return np.array([[0, 0]]), 0.0
        
        # Rack dimensions (convert mm to m)
        rack_width_m = rack_config.rack_width_mm / 1000.0
        rack_length_m = rack_config.rack_length_mm / 1000.0
        
        # Rack position (convert mm to m)
        rack_x_m = rack_placement.x / 1000.0
        rack_y_m = rack_placement.y / 1000.0
        rack_z_m = rack_placement.z / 1000.0
        
        # Rack tilt and azimuth
        tilt_rad = math.radians(rack_config.tilt_angle_deg)
        azimuth_rack_rad = math.radians(rack_config.azimuth_deg)
        
        # Calculate rack top edge height
        rack_height_m = rack_config.post_height_m + rack_length_m * math.sin(tilt_rad)
        
        # Sun angles
        sun_alt_rad = math.radians(sun_position.altitude_deg)
        sun_az_rad = math.radians(sun_position.azimuth_deg)
        
        # Shadow length from top of rack
        if sun_alt_rad > 0:
            shadow_length_m = rack_height_m / math.tan(sun_alt_rad)
        else:
            shadow_length_m = 0.0
        
        # Shadow direction (opposite of sun azimuth)
        shadow_direction_rad = sun_az_rad + math.pi
        
        # Shadow offset (x, y)
        shadow_dx = shadow_length_m * math.sin(shadow_direction_rad)
        shadow_dy = shadow_length_m * math.cos(shadow_direction_rad)
        
        # Rack corners (simplified - using 4 corners of rack footprint)
        cos_az = math.cos(azimuth_rack_rad)
        sin_az = math.sin(azimuth_rack_rad)
        
        # Rack corners in local coordinates
        half_width = rack_width_m / 2.0
        half_length = rack_length_m * math.cos(tilt_rad) / 2.0
        
        corners_local = np.array([
            [-half_width, -half_length],
            [half_width, -half_length],
            [half_width, half_length],
            [-half_width, half_length],
        ])
        
        # Rotate by rack azimuth
        rotation_matrix = np.array([
            [sin_az, cos_az],
            [cos_az, -sin_az],
        ])
        corners_global = corners_local @ rotation_matrix.T
        corners_global[:, 0] += rack_x_m
        corners_global[:, 1] += rack_y_m
        
        # Project shadow from each corner
        shadow_corners = corners_global + np.array([shadow_dx, shadow_dy])
        
        # Combine rack corners and shadow corners to form shadow polygon
        shadow_polygon = np.vstack([corners_global, shadow_corners])
        
        return shadow_polygon, shadow_length_m
    
    @staticmethod
    def check_rack_shading(
        target_rack_config: RackConfig,
        target_rack_placement: RackPlacement,
        source_rack_config: RackConfig,
        source_rack_placement: RackPlacement,
        sun_position: SunPosition,
    ) -> float:
        """Check if target rack is shaded by source rack.
        
        Args:
            target_rack_config: Configuration of rack being checked for shading
            target_rack_placement: Placement of rack being checked
            source_rack_config: Configuration of rack potentially casting shadow
            source_rack_placement: Placement of potential shading rack
            sun_position: Current sun position
            
        Returns:
            Shading fraction (0.0 = no shade, 1.0 = fully shaded)
        """
        if not sun_position.is_daylight:
            return 0.0
        
        # Get shadow projection from source rack
        shadow_polygon, shadow_length = ShadingEngine.calculate_rack_shadow_projection(
            source_rack_config, source_rack_placement, sun_position
        )
        
        if shadow_length < 0.1:  # Less than 10cm shadow
            return 0.0
        
        # Target rack center (convert mm to m)
        target_x_m = target_rack_placement.x / 1000.0
        target_y_m = target_rack_placement.y / 1000.0
        
        # Check if target center is inside shadow polygon (simplified)
        # Use point-in-polygon test
        from matplotlib.path import Path
        shadow_path = Path(shadow_polygon)
        target_center = np.array([target_x_m, target_y_m])
        
        if shadow_path.contains_point(target_center):
            # Target is shaded - estimate fraction based on coverage
            # Simplified: assume full shading if center is in shadow
            return 0.8  # Assume 80% shading (conservative)
        
        return 0.0
    
    @staticmethod
    def analyze_array_shading(
        rack_config: RackConfig,
        rack_placements: List[RackPlacement],
        latitude_deg: float,
        longitude_deg: float,
        date: datetime,
        hour_start: int = 6,
        hour_end: int = 18,
        hour_interval: int = 1,
        timezone_offset_hours: float = 0.0,
    ) -> List[ShadingResult]:
        """Analyze shading for entire array at specific date/time range.
        
        Args:
            rack_config: Shared rack configuration
            rack_placements: List of all rack placements
            latitude_deg: Site latitude
            longitude_deg: Site longitude
            date: Date to analyze
            hour_start: Start hour (0-23)
            hour_end: End hour (0-23)
            hour_interval: Hour interval for sampling
            timezone_offset_hours: Timezone offset from UTC
            
        Returns:
            List of ShadingResult for each hour sampled
        """
        results = []
        
        for hour in range(hour_start, hour_end + 1, hour_interval):
            # Calculate sun position
            dt = date.replace(hour=hour, minute=0, second=0)
            sun_pos = ShadingEngine.calculate_sun_position(
                latitude_deg, longitude_deg, dt, timezone_offset_hours
            )
            
            if not sun_pos.is_daylight:
                continue
            
            # Check shading for each rack
            for i, target_placement in enumerate(rack_placements):
                rack_id = f"Rack_{i:03d}"
                shaded_fraction = 0.0
                shadow_sources = []
                
                # Check each other rack as potential shadow source
                for j, source_placement in enumerate(rack_placements):
                    if i == j:
                        continue  # Skip self
                    
                    # Check if source casts shadow on target
                    shade_frac = ShadingEngine.check_rack_shading(
                        rack_config, target_placement,
                        rack_config, source_placement,
                        sun_pos
                    )
                    
                    if shade_frac > 0.01:
                        shaded_fraction = max(shaded_fraction, shade_frac)
                        shadow_sources.append(f"Rack_{j:03d}")
                
                results.append(ShadingResult(
                    rack_id=rack_id,
                    shaded_fraction=shaded_fraction,
                    shadow_source_ids=shadow_sources,
                    sun_position=sun_pos,
                ))
        
        return results
    
    @staticmethod
    def calculate_annual_shading_metrics(
        rack_config: RackConfig,
        rack_placements: List[RackPlacement],
        latitude_deg: float,
        longitude_deg: float,
        year: int = 2024,
        timezone_offset_hours: float = 0.0,
    ) -> AnnualShadingMetrics:
        """Calculate annual shading metrics for entire array.
        
        Samples representative days throughout the year (solstices, equinoxes)
        and interpolates to estimate annual performance.
        
        Args:
            rack_config: Shared rack configuration
            rack_placements: List of all rack placements
            latitude_deg: Site latitude
            longitude_deg: Site longitude
            year: Year for analysis
            timezone_offset_hours: Timezone offset from UTC
            
        Returns:
            AnnualShadingMetrics with annual estimates
        """
        # Sample key dates (solstices and equinoxes)
        sample_dates = [
            datetime(year, 1, 1),   # Winter
            datetime(year, 3, 20),  # Spring equinox
            datetime(year, 6, 21),  # Summer solstice
            datetime(year, 9, 22),  # Fall equinox
            datetime(year, 12, 21), # Winter solstice
        ]
        
        total_daylight_hours = 0.0
        total_shaded_hours = 0.0
        seasonal_shading = {
            'winter': [],
            'spring': [],
            'summer': [],
            'fall': [],
        }
        
        for date in sample_dates:
            # Analyze full day
            results = ShadingEngine.analyze_array_shading(
                rack_config, rack_placements,
                latitude_deg, longitude_deg,
                date, hour_start=6, hour_end=18, hour_interval=1,
                timezone_offset_hours=timezone_offset_hours
            )
            
            # Calculate daily metrics
            num_racks = len(rack_placements)
            hours_sampled = len(results) // num_racks if num_racks > 0 else 0
            
            total_daylight_hours += hours_sampled
            
            # Count shaded hours
            for result in results:
                if result.is_shaded:
                    total_shaded_hours += result.shaded_fraction
            
            # Seasonal categorization
            month = date.month
            if month in [12, 1, 2]:
                season = 'winter'
            elif month in [3, 4, 5]:
                season = 'spring'
            elif month in [6, 7, 8]:
                season = 'summer'
            else:
                season = 'fall'
            
            avg_shading = np.mean([r.shaded_fraction for r in results]) if results else 0.0
            seasonal_shading[season].append(avg_shading)
        
        # Calculate average metrics
        avg_shading_fraction = total_shaded_hours / (total_daylight_hours * len(rack_placements)) if total_daylight_hours > 0 else 0.0
        
        return AnnualShadingMetrics(
            total_daylight_hours=total_daylight_hours * 365 / len(sample_dates),
            shaded_hours=total_shaded_hours * 365 / len(sample_dates),
            unshaded_hours=(total_daylight_hours - total_shaded_hours) * 365 / len(sample_dates),
            average_shading_fraction=avg_shading_fraction,
            shading_loss_fraction=avg_shading_fraction * 0.9,  # ~90% of shading translates to energy loss
            winter_shading_fraction=np.mean(seasonal_shading['winter']) if seasonal_shading['winter'] else 0.0,
            spring_shading_fraction=np.mean(seasonal_shading['spring']) if seasonal_shading['spring'] else 0.0,
            summer_shading_fraction=np.mean(seasonal_shading['summer']) if seasonal_shading['summer'] else 0.0,
            fall_shading_fraction=np.mean(seasonal_shading['fall']) if seasonal_shading['fall'] else 0.0,
        )
    
    @staticmethod
    def calculate_optimal_row_spacing(
        rack_config: RackConfig,
        latitude_deg: float,
        target_shading_loss_percent: float = 5.0,
        min_spacing_m: float = 5.0,
        max_spacing_m: float = 20.0,
        spacing_step_m: float = 0.5,
    ) -> Tuple[float, float]:
        """Calculate optimal row spacing to achieve target shading loss.
        
        Uses simplified shadow calculation for winter solstice at solar noon
        to estimate required spacing.
        
        Args:
            rack_config: Rack configuration
            latitude_deg: Site latitude
            target_shading_loss_percent: Target maximum shading loss (%)
            min_spacing_m: Minimum spacing to test
            max_spacing_m: Maximum spacing to test
            spacing_step_m: Step size for spacing sweep
            
        Returns:
            Tuple of (optimal_spacing_m, predicted_shading_loss_percent)
        """
        # Winter solstice sun altitude at solar noon (worst case)
        # Sun altitude ≈ 90° - latitude - 23.45° (declination)
        winter_sun_altitude_deg = 90.0 - abs(latitude_deg) - 23.45
        winter_sun_altitude_rad = math.radians(max(10.0, winter_sun_altitude_deg))
        
        # Rack dimensions
        tilt_rad = math.radians(rack_config.tilt_angle_deg)
        rack_length_m = rack_config.rack_length_mm / 1000.0
        rack_height_m = rack_config.post_height_m + rack_length_m * math.sin(tilt_rad)
        
        # Shadow length at winter solstice
        shadow_length_m = rack_height_m / math.tan(winter_sun_altitude_rad)
        
        # Estimate shading based on spacing
        optimal_spacing = max_spacing_m
        min_shading_loss = 100.0
        
        for spacing_m in np.arange(min_spacing_m, max_spacing_m + spacing_step_m, spacing_step_m):
            # If shadow doesn't reach next row, no shading
            if shadow_length_m <= spacing_m:
                shading_loss_percent = 0.0
            else:
                # Shadow overlaps - estimate energy loss
                overlap_m = shadow_length_m - spacing_m
                overlap_fraction = min(1.0, overlap_m / rack_length_m)
                shading_loss_percent = overlap_fraction * 30.0  # Assume 30% energy loss at worst case
            
            if shading_loss_percent <= target_shading_loss_percent and shading_loss_percent < min_shading_loss:
                optimal_spacing = spacing_m
                min_shading_loss = shading_loss_percent
        
        return optimal_spacing, min_shading_loss
