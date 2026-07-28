"""MCP tools for shading analysis.

Exposes shading analysis operations via Model Context Protocol.
"""

from datetime import datetime
from mcp.types import TextContent, ImageContent
from mcp.server.fastmcp import Context
import json

from freepvc.server import mcp
from freepvc.engines.shading_engine import ShadingEngine, AnnualShadingMetrics
from freepvc.models.solar_objects import RackConfig, RackPlacement, PanelSpec


@mcp.tool()
async def analyze_daily_shading(
    date_str: str = "2024-06-21",
    hour_start: int = 6,
    hour_end: int = 18,
    hour_interval: int = 1,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Analyze shading for current array layout at specific date and time range.

    Calculates row-to-row shading throughout the day based on sun position.
    Useful for understanding shading patterns on solstices, equinoxes, or any specific date.

    Args:
        date_str: Date to analyze (YYYY-MM-DD format, e.g., "2024-06-21" for summer solstice)
        hour_start: Start hour for analysis (0-23, default: 6 AM)
        hour_end: End hour for analysis (0-23, default: 6 PM)
        hour_interval: Hour interval for sampling (default: 1 hour)
        ctx: MCP context

    Returns:
        Shading analysis results with hourly breakdown

    Example dates:
        - Summer solstice: 2024-06-21 (longest day, least shading)
        - Winter solstice: 2024-12-21 (shortest day, most shading)
        - Spring equinox: 2024-03-20
        - Fall equinox: 2024-09-22
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Parse date
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # Get project information via RPC
        project_info_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
if doc is None:
    result = {"error": "No active document"}
else:
    # Get project metadata
    result = {
        "latitude": getattr(doc, "Latitude", 37.0),
        "longitude": getattr(doc, "Longitude", -122.0),
        "timezone_offset": getattr(doc, "TimezoneOffset", -8.0),
    }

result
"""
        project_info = connection.execute_python_code(project_info_code)
        
        if "error" in project_info:
            return [TextContent(
                type="text",
                text="Error: No active FreePVC project. Create a project first using create_project."
            )]

        # Get array layout data via RPC
        layout_data_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
result = {"racks": [], "rack_config": None}

# Find ArrayLayout object
array_layout = None
for obj in doc.Objects:
    if hasattr(obj, "TypeId") and "ArrayLayout" in str(obj.TypeId):
        array_layout = obj
        break

if array_layout is not None:
    # Get rack configuration from base rack
    base_rack_name = getattr(array_layout, "BaseRack", None)
    if base_rack_name and hasattr(doc, base_rack_name):
        base_rack = getattr(doc, base_rack_name)
        
        # Extract rack config
        result["rack_config"] = {
            "panels_per_row": getattr(base_rack, "PanelsPerRow", 2),
            "rows": getattr(base_rack, "Rows", 1),
            "tilt_angle_deg": getattr(base_rack, "TiltAngle", 25.0),
            "azimuth_deg": getattr(base_rack, "Azimuth", 180.0),
            "post_height_m": getattr(base_rack, "PostHeight", 2.5) / 1000.0,
            "panel_power_watts": getattr(base_rack, "PanelPower", 550.0),
            "panel_width_mm": getattr(base_rack, "PanelWidth", 1134.0),
            "panel_height_mm": getattr(base_rack, "PanelHeight", 2278.0),
        }
    
    # Get all rack placements
    for obj in doc.Objects:
        if obj.Name.startswith("Rack_Instance_"):
            placement = obj.Placement
            result["racks"].append({
                "id": obj.Name,
                "x": placement.Base.x,
                "y": placement.Base.y,
                "z": placement.Base.z,
                "rotation_z": obj.Placement.Rotation.Angle,
            })

result
"""
        layout_data = connection.execute_python_code(layout_data_code)
        
        if not layout_data.get("rack_config") or not layout_data.get("racks"):
            return [TextContent(
                type="text",
                text="Error: No array layout found. Generate an array layout first using generate_array_layout."
            )]

        # Build rack config and placements
        rack_cfg_data = layout_data["rack_config"]
        panel_spec = PanelSpec(
            width=rack_cfg_data["panel_width_mm"],
            height=rack_cfg_data["panel_height_mm"],
            power_watts=rack_cfg_data["panel_power_watts"],
        )
        
        rack_config = RackConfig(
            panel_spec=panel_spec,
            panels_per_row=rack_cfg_data["panels_per_row"],
            rows=rack_cfg_data["rows"],
            tilt_angle_deg=rack_cfg_data["tilt_angle_deg"],
            azimuth_deg=rack_cfg_data["azimuth_deg"],
            post_height_m=rack_cfg_data["post_height_m"],
        )
        
        rack_placements = [
            RackPlacement(
                x=r["x"],
                y=r["y"],
                z=r["z"],
                rotation_z=r.get("rotation_z", 0.0),
                rack_id=r["id"],
            )
            for r in layout_data["racks"]
        ]

        # Run shading analysis
        results = ShadingEngine.analyze_array_shading(
            rack_config,
            rack_placements,
            project_info["latitude"],
            project_info["longitude"],
            date,
            hour_start,
            hour_end,
            hour_interval,
            project_info.get("timezone_offset", 0.0),
        )

        # Process results
        total_rack_hours = len(rack_placements) * ((hour_end - hour_start) // hour_interval + 1)
        shaded_rack_hours = sum(1 for r in results if r.is_shaded)
        shading_percentage = (shaded_rack_hours / total_rack_hours * 100) if total_rack_hours > 0 else 0.0

        # Group by hour for summary
        hours_summary = {}
        for result in results:
            hour = result.sun_position.datetime.hour
            if hour not in hours_summary:
                hours_summary[hour] = {
                    "sun_altitude": result.sun_position.altitude_deg,
                    "sun_azimuth": result.sun_position.azimuth_deg,
                    "shaded_racks": 0,
                    "total_racks": 0,
                }
            hours_summary[hour]["total_racks"] += 1
            if result.is_shaded:
                hours_summary[hour]["shaded_racks"] += 1

        # Format output
        response = f"""✓ Daily shading analysis complete

**Date:** {date_str}
**Time range:** {hour_start}:00 - {hour_end}:00 (interval: {hour_interval}h)

**Array Configuration:**
- Total racks: {len(rack_placements)}
- Rack size: {rack_config.panels_per_row}×{rack_config.rows} panels
- Tilt: {rack_config.tilt_angle_deg}°
- Azimuth: {rack_config.azimuth_deg}° ({"S" if 170 <= rack_config.azimuth_deg <= 190 else "N" if rack_config.azimuth_deg < 90 or rack_config.azimuth_deg > 270 else "E/W"})

**Overall Shading:**
- Shaded rack-hours: {shaded_rack_hours:,} / {total_rack_hours:,}
- Shading percentage: {shading_percentage:.1f}%
- Availability: {100 - shading_percentage:.1f}%

**Hourly Breakdown:**
"""
        
        for hour in sorted(hours_summary.keys()):
            data = hours_summary[hour]
            shaded_pct = (data["shaded_racks"] / data["total_racks"] * 100) if data["total_racks"] > 0 else 0.0
            sun_alt = data["sun_altitude"]
            sun_az = data["sun_azimuth"]
            
            # Visual indicator
            if shaded_pct < 5:
                indicator = "☀️ "
            elif shaded_pct < 20:
                indicator = "⛅ "
            else:
                indicator = "🌥️ "
            
            response += f"\n{indicator}{hour:02d}:00 - Sun: {sun_alt:5.1f}° alt, {sun_az:5.1f}° az → {data['shaded_racks']}/{data['total_racks']} racks shaded ({shaded_pct:.1f}%)"

        response += f"""

**Key Findings:**
- Shading is typically worst in early morning and late evening (low sun angles)
- Midday hours usually have minimal shading (high sun altitude)
- Winter months will have more shading due to lower sun angles
- Consider increasing row spacing if shading exceeds acceptable levels

**Next steps:**
- Run annual_shading_analysis for full year metrics
- Adjust row spacing if shading is excessive
- Optimize for your specific performance requirements
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error during shading analysis: {str(e)}"
        )]


@mcp.tool()
async def analyze_annual_shading(
    year: int = 2024,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Calculate annual shading metrics for current array layout.

    Samples representative days throughout the year (solstices, equinoxes) and
    estimates annual energy loss from shading. Provides seasonal breakdown.

    Args:
        year: Year for analysis (default: 2024)
        ctx: MCP context

    Returns:
        Annual shading metrics with seasonal breakdown
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Get project information and layout data (same as daily analysis)
        project_info_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
if doc is None:
    result = {"error": "No active document"}
else:
    result = {
        "latitude": getattr(doc, "Latitude", 37.0),
        "longitude": getattr(doc, "Longitude", -122.0),
        "timezone_offset": getattr(doc, "TimezoneOffset", -8.0),
    }

result
"""
        project_info = connection.execute_python_code(project_info_code)
        
        if "error" in project_info:
            return [TextContent(
                type="text",
                text="Error: No active FreePVC project. Create a project first."
            )]

        # Get array layout data (reuse code from daily analysis)
        layout_data_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
result = {"racks": [], "rack_config": None}

array_layout = None
for obj in doc.Objects:
    if hasattr(obj, "TypeId") and "ArrayLayout" in str(obj.TypeId):
        array_layout = obj
        break

if array_layout is not None:
    base_rack_name = getattr(array_layout, "BaseRack", None)
    if base_rack_name and hasattr(doc, base_rack_name):
        base_rack = getattr(doc, base_rack_name)
        
        result["rack_config"] = {
            "panels_per_row": getattr(base_rack, "PanelsPerRow", 2),
            "rows": getattr(base_rack, "Rows", 1),
            "tilt_angle_deg": getattr(base_rack, "TiltAngle", 25.0),
            "azimuth_deg": getattr(base_rack, "Azimuth", 180.0),
            "post_height_m": getattr(base_rack, "PostHeight", 2500.0) / 1000.0,
            "panel_power_watts": getattr(base_rack, "PanelPower", 550.0),
            "panel_width_mm": getattr(base_rack, "PanelWidth", 1134.0),
            "panel_height_mm": getattr(base_rack, "PanelHeight", 2278.0),
        }
    
    for obj in doc.Objects:
        if obj.Name.startswith("Rack_Instance_"):
            placement = obj.Placement
            result["racks"].append({
                "id": obj.Name,
                "x": placement.Base.x,
                "y": placement.Base.y,
                "z": placement.Base.z,
            })

result
"""
        layout_data = connection.execute_python_code(layout_data_code)
        
        if not layout_data.get("rack_config") or not layout_data.get("racks"):
            return [TextContent(
                type="text",
                text="Error: No array layout found. Generate layout first with generate_array_layout."
            )]

        # Build rack config and placements
        rack_cfg_data = layout_data["rack_config"]
        panel_spec = PanelSpec(
            width=rack_cfg_data["panel_width_mm"],
            height=rack_cfg_data["panel_height_mm"],
            power_watts=rack_cfg_data["panel_power_watts"],
        )
        
        rack_config = RackConfig(
            panel_spec=panel_spec,
            panels_per_row=rack_cfg_data["panels_per_row"],
            rows=rack_cfg_data["rows"],
            tilt_angle_deg=rack_cfg_data["tilt_angle_deg"],
            azimuth_deg=rack_cfg_data["azimuth_deg"],
            post_height_m=rack_cfg_data["post_height_m"],
        )
        
        rack_placements = [
            RackPlacement(x=r["x"], y=r["y"], z=r["z"], rack_id=r["id"])
            for r in layout_data["racks"]
        ]

        # Run annual analysis
        metrics = ShadingEngine.calculate_annual_shading_metrics(
            rack_config,
            rack_placements,
            project_info["latitude"],
            project_info["longitude"],
            year,
            project_info.get("timezone_offset", 0.0),
        )

        # Format response
        response = f"""✓ Annual shading analysis complete

**Year:** {year}
**Array:** {len(rack_placements)} racks, {rack_config.panels_per_row}×{rack_config.rows} panels each

**Annual Metrics:**
- Total daylight hours: {metrics.total_daylight_hours:,.0f} hours/year
- Unshaded hours: {metrics.unshaded_hours:,.0f} hours ({metrics.availability_percentage:.1f}%)
- Shaded hours: {metrics.shaded_hours:,.0f} hours ({metrics.shading_percentage:.1f}%)

**Energy Impact:**
- Average shading fraction: {metrics.average_shading_fraction * 100:.2f}%
- Estimated energy loss: {metrics.shading_loss_fraction * 100:.2f}%
- System availability: {(1 - metrics.shading_loss_fraction) * 100:.1f}%

**Seasonal Breakdown:**
- Winter (Dec-Feb): {metrics.winter_shading_fraction * 100:.1f}% shading
- Spring (Mar-May): {metrics.spring_shading_fraction * 100:.1f}% shading
- Summer (Jun-Aug): {metrics.summer_shading_fraction * 100:.1f}% shading
- Fall (Sep-Nov): {metrics.fall_shading_fraction * 100:.1f}% shading

**Interpretation:**
"""
        
        if metrics.shading_loss_fraction < 0.05:
            response += "✅ Excellent - Shading losses are minimal (<5%). Good row spacing!\n"
        elif metrics.shading_loss_fraction < 0.10:
            response += "✓ Good - Shading losses are acceptable (<10%) for most projects.\n"
        elif metrics.shading_loss_fraction < 0.15:
            response += "⚠️  Moderate - Consider increasing row spacing to reduce losses.\n"
        else:
            response += "❌ High - Significant shading losses. Increase row spacing recommended.\n"

        response += f"""
**Recommendations:**
- Winter has highest shading due to low sun angles
- Consider increasing row spacing by 1-2m if losses exceed target
- Use calculate_optimal_spacing tool to find ideal spacing
- Balance energy gains vs. land use efficiency

**Next steps:**
- Adjust row spacing and regenerate layout if needed
- Export to PVsyst/SAM for detailed energy modeling
- Consider seasonal tilt adjustment strategies
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error during annual shading analysis: {str(e)}"
        )]


@mcp.tool()
async def calculate_optimal_spacing(
    target_shading_loss_percent: float = 5.0,
    min_spacing_m: float = 5.0,
    max_spacing_m: float = 20.0,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Calculate optimal row spacing to achieve target shading loss.

    Uses winter solstice sun angle (worst case for shading) to recommend
    row spacing that meets energy production goals while minimizing land use.

    Args:
        target_shading_loss_percent: Target maximum shading loss (%, default: 5.0)
        min_spacing_m: Minimum spacing to consider (meters, default: 5.0)
        max_spacing_m: Maximum spacing to consider (meters, default: 20.0)
        ctx: MCP context

    Returns:
        Recommended spacing with predicted performance
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Get project info and rack config
        project_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
result = {"latitude": 37.0, "rack_config": None}

if doc is not None:
    result["latitude"] = getattr(doc, "Latitude", 37.0)
    
    # Find base rack
    for obj in doc.Objects:
        if obj.Name.startswith("Rack_"):
            result["rack_config"] = {
                "tilt_angle_deg": getattr(obj, "TiltAngle", 25.0),
                "post_height_m": getattr(obj, "PostHeight", 2500.0) / 1000.0,
                "panel_height_mm": getattr(obj, "PanelHeight", 2278.0),
                "panels_per_row": getattr(obj, "PanelsPerRow", 28),
                "rows": getattr(obj, "Rows", 2),
            }
            break

result
"""
        data = connection.execute_python_code(project_code)
        
        if not data.get("rack_config"):
            return [TextContent(
                type="text",
                text="Error: No rack found in project. Create a rack first."
            )]

        # Build minimal rack config for spacing calculation
        rack_cfg = data["rack_config"]
        panel_spec = PanelSpec(height=rack_cfg["panel_height_mm"])
        
        rack_config = RackConfig(
            panel_spec=panel_spec,
            panels_per_row=rack_cfg["panels_per_row"],
            rows=rack_cfg["rows"],
            tilt_angle_deg=rack_cfg["tilt_angle_deg"],
            post_height_m=rack_cfg["post_height_m"],
        )

        # Calculate optimal spacing
        optimal_spacing, predicted_loss = ShadingEngine.calculate_optimal_row_spacing(
            rack_config,
            data["latitude"],
            target_shading_loss_percent,
            min_spacing_m,
            max_spacing_m,
        )

        # Calculate current spacing for comparison
        current_spacing_code = """
import FreeCAD

doc = FreeCAD.ActiveDocument
result = {"current_spacing": None}

# Find ArrayLayout
for obj in doc.Objects:
    if hasattr(obj, "Spacing"):
        result["current_spacing"] = getattr(obj, "Spacing", None) / 1000.0
        break

result
"""
        current_data = connection.execute_python_code(current_spacing_code)
        current_spacing = current_data.get("current_spacing")

        # Format response
        response = f"""✓ Optimal spacing calculation complete

**Target:** ≤{target_shading_loss_percent:.1f}% shading loss

**Site Configuration:**
- Latitude: {data['latitude']:.2f}°
- Rack tilt: {rack_config.tilt_angle_deg}°
- Rack height: {rack_config.post_height_m:.1f}m posts + {rack_config.rack_length_mm/1000:.1f}m panels

**Recommended Spacing:**
- Optimal row spacing: **{optimal_spacing:.1f}m**
- Predicted winter shading loss: {predicted_loss:.1f}%
- Ground Coverage Ratio (GCR): ~{0.35:.2f} (estimated)
"""

        if current_spacing:
            spacing_diff = optimal_spacing - current_spacing
            response += f"\n**Current vs. Recommended:**\n"
            response += f"- Current spacing: {current_spacing:.1f}m\n"
            response += f"- Difference: {spacing_diff:+.1f}m "
            
            if abs(spacing_diff) < 0.5:
                response += "(✓ Current spacing is optimal)\n"
            elif spacing_diff > 0:
                response += "(→ Consider increasing spacing)\n"
            else:
                response += "(→ Could reduce spacing slightly)\n"

        response += f"""
**Trade-offs:**
- Closer spacing (<{optimal_spacing:.0f}m):
  • Higher capacity per acre
  • More shading losses
  • Lower energy yield per panel
  
- Wider spacing (>{optimal_spacing:.0f}m):
  • Less shading, higher energy yield
  • More land required
  • Higher balance-of-system costs

**Next steps:**
- Regenerate layout with recommended spacing: {optimal_spacing:.1f}m
- Run annual_shading_analysis to verify performance
- Balance land costs vs. energy revenue for your project economics
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error calculating optimal spacing: {str(e)}"
        )]
