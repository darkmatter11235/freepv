"""Solar object data models for FreePVC.

This module defines data models for solar components used throughout
the FreePVC system.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class RackType(Enum):
    """Types of solar racking systems."""
    FIXED_TILT = "fixed"
    SINGLE_AXIS_TRACKER = "tracker"
    EAST_WEST = "east_west"
    DUAL_AXIS_TRACKER = "dual_tracker"


class MountingType(Enum):
    """Mounting configuration types."""
    GROUND_MOUNT = "ground"
    CARPORT = "carport"
    ROOFTOP = "rooftop"


@dataclass
class PanelSpec:
    """Solar panel specification (template/prototype)."""
    
    # Physical dimensions (mm)
    width: float = 1134.0  # Standard 1134mm
    height: float = 2278.0  # Standard 2278mm
    thickness: float = 35.0  # ~35mm typical
    
    # Electrical specs
    power_watts: float = 550.0  # Rated power
    voltage_voc: float = 49.5  # Open circuit voltage
    current_isc: float = 13.9  # Short circuit current
    voltage_mpp: float = 41.7  # MPP voltage
    current_mpp: float = 13.2  # MPP current
    
    # Metadata
    manufacturer: str = "Generic"
    model: str = "550W-Mono"
    efficiency: float = 0.21  # 21%
    
    # Visual properties
    color: Tuple[float, float, float] = (0.1, 0.3, 0.8)  # Blue
    frame_color: Tuple[float, float, float] = (0.2, 0.2, 0.2)  # Dark gray
    
    def __post_init__(self):
        """Validate panel specifications."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Panel dimensions must be positive")
        if self.power_watts <= 0:
            raise ValueError("Panel power must be positive")


@dataclass
class RackConfig:
    """Configuration for a solar rack (shared template for many instances)."""
    
    # Panel configuration
    panel_spec: PanelSpec = field(default_factory=PanelSpec)
    panels_per_row: int = 2  # Panels in portrait across
    rows: int = 1  # Number of rows (along slope)
    
    # Mounting configuration
    rack_type: RackType = RackType.FIXED_TILT
    tilt_angle_deg: float = 25.0  # Fixed tilt angle
    azimuth_deg: float = 180.0  # 0=N, 90=E, 180=S, 270=W
    
    # Structure
    post_height_m: float = 2.0  # Post height above terrain
    row_spacing_m: float = 6.0  # N-S spacing between rack rows
    clearance_m: float = 0.5  # Minimum ground clearance
    
    # Post/pile configuration
    post_diameter_mm: float = 100.0
    num_posts: int = 4  # Number of support posts
    
    # Frame configuration
    beam_width_mm: float = 80.0
    beam_height_mm: float = 40.0
    
    @property
    def rack_width_mm(self) -> float:
        """Total rack width (across)."""
        return self.panels_per_row * self.panel_spec.width
    
    @property
    def rack_length_mm(self) -> float:
        """Total rack length (along slope)."""
        return self.rows * self.panel_spec.height
    
    @property
    def total_panels(self) -> int:
        """Total panels per rack instance."""
        return self.panels_per_row * self.rows
    
    @property
    def dc_capacity_kw(self) -> float:
        """DC capacity in kW per rack."""
        return (self.total_panels * self.panel_spec.power_watts) / 1000.0


@dataclass
class TrackerConfig(RackConfig):
    """Configuration for single-axis tracker."""
    
    # Override defaults for trackers
    rack_type: RackType = RackType.SINGLE_AXIS_TRACKER
    
    # Tracker-specific
    max_rotation_deg: float = 60.0  # ±60° typical
    backtracking_enabled: bool = True
    torque_tube_diameter_mm: float = 150.0
    
    # Trackers are typically horizontal (0° tilt)
    tilt_angle_deg: float = 0.0


@dataclass
class RackPlacement:
    """Placement data for a single rack instance.
    
    This is the lightweight data that varies per instance,
    while the RackConfig is shared among many instances.
    """
    
    # Position (mm)
    x: float
    y: float
    z: float
    
    # Rotation (degrees)
    rotation_x: float = 0.0  # Tilt
    rotation_y: float = 0.0  # Bank angle (for terrain following)
    rotation_z: float = 0.0  # Azimuth
    
    # Terrain-following adjustments
    terrain_slope_deg: float = 0.0
    terrain_aspect_deg: float = 0.0
    
    # Metadata
    rack_id: str = ""
    string_id: Optional[str] = None
    inverter_id: Optional[str] = None


@dataclass
class LayoutConfig:
    """Configuration for array layout generation."""
    
    # Rack template
    rack_config: RackConfig
    
    # Layout parameters
    spacing_m: float = 6.0  # Row-to-row spacing
    gcr_target: float = 0.4  # Ground coverage ratio target
    
    # Constraints
    max_slope_deg: float = 20.0  # Maximum buildable slope
    min_clearance_m: float = 0.5  # Minimum ground clearance
    
    # Layout pattern
    azimuth_deg: float = 180.0  # Primary array orientation
    stagger_enabled: bool = False  # Stagger alternating rows
    
    # Terrain following
    follow_contours: bool = True
    adjust_tilt_to_slope: bool = False


@dataclass
class ArrayLayout:
    """Complete array layout result."""
    
    # Configuration used
    config: LayoutConfig
    
    # Generated placements
    placements: List[RackPlacement] = field(default_factory=list)
    
    # Statistics
    total_racks: int = 0
    total_panels: int = 0
    dc_capacity_kw: float = 0.0
    ground_area_m2: float = 0.0
    panel_area_m2: float = 0.0
    gcr_actual: float = 0.0
    
    def calculate_statistics(self):
        """Calculate layout statistics from placements."""
        self.total_racks = len(self.placements)
        self.total_panels = self.total_racks * self.config.rack_config.total_panels
        self.dc_capacity_kw = self.total_racks * self.config.rack_config.dc_capacity_kw
        
        # Calculate areas (simplified - assumes rectangular layout)
        if self.total_racks > 0:
            rack_area = (
                self.config.rack_config.rack_width_mm / 1000.0 *
                self.config.rack_config.rack_length_mm / 1000.0
            )
            self.panel_area_m2 = self.total_racks * rack_area
            
            # Ground area = total racks * spacing * rack_width
            self.ground_area_m2 = (
                self.total_racks *
                self.config.spacing_m *
                (self.config.rack_config.rack_width_mm / 1000.0)
            )
            
            if self.ground_area_m2 > 0:
                self.gcr_actual = self.panel_area_m2 / self.ground_area_m2
