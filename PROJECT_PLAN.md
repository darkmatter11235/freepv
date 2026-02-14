# FreePVC Project Implementation Plan

## Project Overview

FreePVC is an open-source solar plant design toolkit for FreeCAD with MCP integration. This document outlines the implementation roadmap for AI-assisted development via GitHub Copilot agent mode.

**Current Status:** Phase 1 (Terrain Analysis) - 90% Complete
**Next Focus:** Phase 2 (Layout Generation)

---

## ✅ Completed Work

### Phase 0: Project Scaffolding (Complete)
- ✅ Project structure with src/freepvc and addon/FreePVC
- ✅ Python 3.12 environment setup
- ✅ FreeCAD workbench with Start/Stop RPC Server buttons
- ✅ MCP server with FastMCP integration
- ✅ Development tooling (pytest, ruff, mypy)

### Demo Scripts (Complete)
- ✅ `demo_solar_array.py` - 50-panel fixed-tilt array
- ✅ `demo_tracker_array.py` - 8 tracker rows with 224 panels
- ✅ `demo_east_west.py` - East-West bifacial configuration
- ✅ `demo_terrain_draped.py` - Terrain-following array

### Phase 1: Terrain Analysis (90% Complete)
- ✅ Terrain data models (`src/freepvc/models/terrain.py`)
- ✅ Terrain engine with Delaunay triangulation (`src/freepvc/engines/terrain_engine.py`)
- ✅ File import: CSV, DEM ASCII, XYZ (`src/freepvc/io/terrain_import.py`)
- ✅ 4 MCP terrain tools exposed via `src/freepvc/server.py`
- ✅ Slope analysis with heatmap visualization
- ✅ Elevation interpolation
- ✅ 8/8 unit tests passing (`tests/test_terrain_engine.py`)
- ⏳ Contour generation (implemented but needs integration)
- ⏳ Cut/fill volume calculation (implemented but needs testing)

---

## 🎯 Phase 2: Layout Generation (Next)

**Goal:** Create parametric solar rack objects and automated array placement on terrain.

### Task 2.1: FeaturePython Base Classes

**Files to create:**
- `src/freepvc/models/solar_objects.py` - Base classes for solar components
- `addon/FreePVC/objects/SolarRack.py` - FeaturePython object for fixed racks
- `addon/FreePVC/objects/Tracker.py` - FeaturePython object for trackers

**Implementation:**
```python
class SolarRackBase:
    """Base class for parametric solar racks."""
    def __init__(self, obj):
        # Panel dimensions
        obj.addProperty("App::PropertyLength", "PanelWidth", "Panel", "Width of solar panel")
        obj.addProperty("App::PropertyLength", "PanelHeight", "Panel", "Height of solar panel")
        obj.addProperty("App::PropertyInteger", "PanelsPerRow", "Array", "Panels per row")
        obj.addProperty("App::PropertyInteger", "Rows", "Array", "Number of rows")

        # Mounting configuration
        obj.addProperty("App::PropertyAngle", "TiltAngle", "Mounting", "Panel tilt angle")
        obj.addProperty("App::PropertyLength", "PostHeight", "Mounting", "Post height above ground")
        obj.addProperty("App::PropertyLength", "RowSpacing", "Array", "Spacing between rows")

    def execute(self, obj):
        # Generate geometry based on parameters
        pass
```

**Acceptance Criteria:**
- [ ] FeaturePython objects are fully parametric (editable in Properties panel)
- [ ] Changing parameters updates geometry automatically
- [ ] Objects integrate with FreeCAD's Part workbench
- [ ] Icon files created in `addon/FreePVC/Resources/icons/`
- [ ] Unit tests in `tests/test_solar_objects.py`

**References:**
- Existing pattern: Demo scripts (demo_solar_array.py, demo_tracker_array.py)
- FreeCAD docs: https://wiki.freecadweb.org/FeaturePython_Objects

---

### Task 2.2: Array Placement Engine

**Files to create:**
- `src/freepvc/engines/layout_engine.py` - Array placement algorithms
- `src/freepvc/models/layout.py` - Layout configuration models

**Implementation:**
```python
class LayoutEngine:
    """Engine for automated solar array placement."""

    @staticmethod
    def generate_grid_layout(
        terrain_mesh: TerrainMesh,
        rack_config: dict,
        spacing: float,
        azimuth: float = 180.0,
        max_slope: float = 20.0,
    ) -> List[RackPlacement]:
        """Generate grid-based array layout following terrain.

        Args:
            terrain_mesh: Terrain surface to follow
            rack_config: Rack dimensions and configuration
            spacing: North-south row spacing (mm)
            azimuth: Array orientation (0=N, 90=E, 180=S, 270=W)
            max_slope: Maximum buildable slope (degrees)

        Returns:
            List of rack placements with positions and rotations
        """
        # 1. Get buildable faces from terrain (slope <= max_slope)
        # 2. Create grid of potential rack positions
        # 3. For each position, check terrain slope and adjust tilt
        # 4. Generate placement data (x, y, z, rotation)
        pass

    @staticmethod
    def optimize_spacing(
        terrain_mesh: TerrainMesh,
        rack_config: dict,
        gcr_target: float = 0.4,
    ) -> float:
        """Calculate optimal row spacing for target GCR.

        GCR (Ground Coverage Ratio) = panel area / ground area
        """
        pass
```

**Acceptance Criteria:**
- [ ] Generates rack positions following terrain contours
- [ ] Respects slope constraints (skips areas too steep)
- [ ] Optimizes for ground coverage ratio (GCR)
- [ ] Handles azimuth rotation
- [ ] Returns placement data compatible with FreeCAD
- [ ] Unit tests in `tests/test_layout_engine.py`

---

### Task 2.3: MCP Tools for Layout

**Files to modify:**
- `src/freepvc/server.py` - Add 4 new MCP tools

**New MCP Tools:**

```python
@mcp.tool()
async def create_fixed_rack(
    panel_width_m: float = 1.134,
    panel_height_m: float = 2.278,
    panels_per_row: int = 2,
    rows: int = 1,
    tilt_angle_deg: float = 25.0,
    post_height_m: float = 2.0,
    row_spacing_m: float = 6.0,
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Create a fixed-tilt solar rack in FreeCAD.

    Returns: Confirmation with rack details (panel count, DC capacity, etc.)
    """
    pass

@mcp.tool()
async def generate_array_layout(
    terrain_name: str = "Terrain",
    rack_type: str = "fixed",  # "fixed", "tracker", "east_west"
    spacing_m: float = 6.0,
    azimuth_deg: float = 180.0,
    max_slope_deg: float = 20.0,
    gcr_target: float = 0.4,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Generate automated solar array layout on terrain.

    Returns: Summary (total racks, panels, DC capacity, ground area)
    """
    pass

@mcp.tool()
async def calculate_gcr(
    layout_name: str = "ArrayLayout",
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Calculate Ground Coverage Ratio for existing layout.

    Returns: GCR, panel area, ground area, utilization percentage
    """
    pass

@mcp.tool()
async def export_layout_summary(
    layout_name: str = "ArrayLayout",
    output_format: str = "json",  # "json", "csv", "excel"
    file_path: str = None,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Export layout summary to file.

    Returns: File path and summary statistics
    """
    pass
```

**Acceptance Criteria:**
- [ ] All 4 tools registered and discoverable via MCP
- [ ] Tools integrate with layout_engine.py
- [ ] Tools communicate with FreeCAD via RPC
- [ ] Error handling for invalid parameters
- [ ] Detailed response messages with statistics

---

### Task 2.4: FreeCAD GUI Commands

**Files to create:**
- `addon/FreePVC/commands/cmd_layout.py` - Layout toolbar commands

**Commands to implement:**
```python
class CreateFixedRackCommand:
    def GetResources(self):
        return {
            'Pixmap': 'FreePVC_FixedRack.svg',
            'MenuText': 'Create Fixed Rack',
            'ToolTip': 'Create a fixed-tilt solar rack'
        }

    def Activated(self):
        # Show dialog to input parameters
        # Create rack using FeaturePython object
        pass

class GenerateLayoutCommand:
    def GetResources(self):
        return {
            'Pixmap': 'FreePVC_GenerateLayout.svg',
            'MenuText': 'Generate Layout',
            'ToolTip': 'Generate array layout on terrain'
        }

    def Activated(self):
        # Show layout configuration dialog
        # Call layout_engine to generate placements
        # Create rack objects at each position
        pass
```

**Acceptance Criteria:**
- [ ] Commands appear in FreePVC workbench toolbar
- [ ] Dialog boxes for parameter input (Qt UI)
- [ ] Preview mode before final placement
- [ ] Progress bar for large layouts
- [ ] Undo/redo support

---

## 🔮 Phase 3: Civil Analysis

**Goal:** Piling calculations, collision detection, cut/fill earthwork.

### Task 3.1: Piling Analysis

**Files to create:**
- `src/freepvc/engines/piling_engine.py`
- `src/freepvc/models/piling.py`

**Features:**
- Calculate pile depths based on terrain slope
- Detect collisions between piles and terrain
- Generate piling schedule (pile lengths, quantities)
- Export to CSV/Excel

### Task 3.2: Earthwork Calculations

**Files to modify:**
- `src/freepvc/engines/terrain_engine.py` - Enhance cut/fill methods

**Features:**
- Cut/fill volume calculation (already implemented, needs testing)
- Grading plan generation
- Cross-section profiles
- Mass haul diagram

### Task 3.3: MCP Tools for Civil

**New tools:**
- `analyze_piling` - Generate piling analysis
- `calculate_earthwork` - Cut/fill volumes
- `generate_cross_sections` - Terrain cross-sections

---

## 🔌 Phase 4: Electrical Design

**Goal:** String generation, inverter assignment, DC/AC cable routing.

### Task 4.1: Electrical Models

**Files to create:**
- `src/freepvc/models/electrical.py` - String, inverter, cable models
- `src/freepvc/engines/electrical_engine.py` - String generation algorithms

**Features:**
- Automatic string generation (series-connected panels)
- Inverter sizing and assignment
- DC combiner box placement
- String voltage/current calculations using pvlib

### Task 4.2: Cable Routing

**Features:**
- DC cable routing (panels → combiners → inverters)
- AC cable routing (inverters → transformer)
- Cable tray path generation
- Cable schedule (types, lengths, gauges)

### Task 4.3: MCP Tools for Electrical

**New tools:**
- `generate_strings` - Auto-generate panel strings
- `assign_inverters` - Assign strings to inverters
- `calculate_losses` - DC/AC wire losses
- `export_cable_schedule` - BOM for cables

---

## ☀️ Phase 5: Shading Analysis

**Goal:** Inter-row self-shading, obstacle shading, annual loss estimation.

### Task 5.1: Shading Engine

**Files to create:**
- `src/freepvc/engines/shading_engine.py`
- `src/freepvc/models/shading.py`

**Features:**
- Ray-tracing or backtracking algorithm
- Hourly shading simulation using pvlib
- Annual energy loss calculation
- Shading heatmap visualization

### Task 5.2: MCP Tools for Shading

**New tools:**
- `analyze_shading` - Run shading analysis
- `calculate_annual_losses` - Energy loss estimate
- `optimize_row_spacing` - Minimize shading losses

---

## 📊 Phase 6: BOM & Reporting

**Goal:** Automated bill of materials, reports, Excel export.

### Task 6.1: BOM Generation

**Files to create:**
- `src/freepvc/io/bom_export.py`
- `src/freepvc/models/bom.py`

**Features:**
- Count all components (panels, racks, posts, piles, cables, inverters)
- Generate itemized BOM with quantities
- Export to Excel with multiple sheets

### Task 6.2: Report Generation

**Features:**
- Project summary report (PDF via reportlab)
- Site plan drawing (DXF export)
- Piling table, cable schedule
- KML export for Google Earth

### Task 6.3: MCP Tools for Export

**New tools:**
- `generate_bom` - Export BOM to Excel
- `export_drawings` - DXF/DWG export
- `create_project_report` - PDF report

---

## 🧪 Testing Strategy

### Unit Tests
- **Location:** `tests/`
- **Coverage:** All engines (terrain, layout, piling, electrical, shading)
- **Framework:** pytest
- **Target:** 80%+ code coverage

### Integration Tests
- **Location:** `tests/integration/`
- **Scope:** End-to-end workflows (terrain import → layout → BOM)
- **MCP:** Test all MCP tools via mcp.client

### Manual Tests
- **Demo scripts:** Keep updating with new features
- **FreeCAD GUI:** Manual testing of workbench commands

---

## 📝 Documentation

### For Users
- ✅ README.md - Project overview and quick start
- ✅ .vscode/MCP_SETUP.md - MCP configuration guide
- ⏳ docs/USER_GUIDE.md - Complete user documentation
- ⏳ docs/TUTORIALS.md - Step-by-step tutorials

### For Developers
- ⏳ docs/ARCHITECTURE.md - System architecture
- ⏳ docs/API.md - MCP tool reference
- ⏳ docs/CONTRIBUTING.md - Contribution guidelines

---

## 🚀 Implementation Guidelines for AI Agents

### Code Style
- Follow PEP 8 (enforced by ruff)
- Type hints on all functions
- Docstrings in Google format
- Maximum line length: 100 characters

### Existing Patterns to Follow

1. **MCP Tools** (`src/freepvc/server.py`):
```python
@mcp.tool()
async def tool_name(
    param: type,
    ctx: Context = None,
) -> list[TextContent | ImageContent]:
    """Tool description.

    Args:
        param: Parameter description

    Returns:
        Response description
    """
    connection = ctx.request_context.lifespan_context["connection"]

    try:
        # Implementation
        result = connection.some_rpc_method(...)
        response = f"""✓ Success message

**Details:**
- Key: {value}
"""
        return [TextContent(type="text", text=response)]
    except Exception as e:
        return [TextContent(type="text", text=f"✗ Error: {str(e)}")]
```

2. **Engine Classes** (`src/freepvc/engines/`):
```python
class SomeEngine:
    """Engine for some capability."""

    @staticmethod
    def process_something(
        input_data: DataModel,
        param: float,
    ) -> ResultModel:
        """Process something.

        Args:
            input_data: Input data description
            param: Parameter description

        Returns:
            Result description

        Raises:
            ValueError: When validation fails
        """
        # Pure Python logic (no FreeCAD imports)
        pass
```

3. **FeaturePython Objects** (`addon/FreePVC/objects/`):
```python
class SomeObject:
    def __init__(self, obj):
        obj.addProperty("App::PropertyFloat", "PropName", "Group", "Description")
        obj.Proxy = self

    def execute(self, obj):
        # Generate Part geometry
        import Part
        shape = Part.makeBox(obj.PropName, ...)
        obj.Shape = shape
```

### File Organization
```
src/freepvc/
├── models/          # Data models (dataclasses)
├── engines/         # Business logic (pure Python)
├── io/              # File import/export
├── mcp_tools/       # MCP tool modules (DEPRECATED - use server.py)
├── server.py        # MCP server + all tools
└── connection.py    # RPC connection to FreeCAD

addon/FreePVC/
├── objects/         # FeaturePython objects
├── commands/        # GUI commands
├── rpc_server/      # XML-RPC server
├── Resources/icons/ # Icon files
├── Init.py          # Non-GUI initialization
└── InitGui.py       # GUI initialization

tests/
├── test_*.py        # Unit tests
└── integration/     # Integration tests
```

---

## 🎯 Priority Order for Implementation

1. **Phase 2.1** - FeaturePython rack objects (foundation for everything)
2. **Phase 2.2** - Layout engine (automated placement)
3. **Phase 2.3** - MCP layout tools (AI orchestration)
4. **Phase 3.1** - Piling analysis (civil engineering)
5. **Phase 4.1** - Electrical models (string generation)
6. **Phase 5.1** - Shading analysis (performance validation)
7. **Phase 6.1** - BOM generation (deliverables)

---

## 🤖 Agent Mode Execution

When implementing a phase:

1. **Read existing code** to understand patterns:
   - `src/freepvc/server.py` - MCP tool patterns
   - `src/freepvc/engines/terrain_engine.py` - Engine patterns
   - `src/freepvc/models/terrain.py` - Data model patterns

2. **Create files** as specified in task descriptions

3. **Write tests** for all new functionality

4. **Update MCP server** to expose new capabilities

5. **Test integration**:
   - Run unit tests: `pytest tests/`
   - Test MCP tools via GitHub Copilot
   - Verify in FreeCAD GUI

6. **Document** new features in docstrings and user guide

---

## 📌 Notes

- **FreeCAD compatibility:** Target FreeCAD 0.21+ (Ubuntu 24.04 default)
- **Python version:** 3.12+ (required by freecad-mcp)
- **MCP protocol:** Use FastMCP patterns from freecad-mcp
- **Units:** All internal calculations in millimeters (FreeCAD standard)
- **Coordinates:** Right-handed system (X=East, Y=North, Z=Up)

---

## 🔗 External Resources

- FreeCAD Python API: https://wiki.freecadweb.org/Python_scripting_tutorial
- pvlib Documentation: https://pvlib-python.readthedocs.io/
- MCP Specification: https://modelcontextprotocol.io/
- PVCase (commercial reference): https://pvcase.com/

---

**Last Updated:** 2026-02-08
**Status:** Phase 1 Complete, Phase 2 Ready to Start
