# FreePVC

**Open-source solar plant design toolkit for FreeCAD with MCP integration**

FreePVC is an open-source alternative to PVCase, providing comprehensive tools for designing utility-scale solar power plants. Built on FreeCAD and exposing all operations via MCP (Model Context Protocol), FreePVC enables both traditional CAD workflows and AI-driven design automation.

## Features

### Ground Mount Solar Design (Phase 1 Focus)

- **Terrain Analysis**: Import point clouds, DEMs, contours; generate meshes; slope analysis with heatmaps
- **Layout Generation**: Fixed-tilt racks, single-axis trackers, east-west configurations with automatic terrain following
- **Civil Engineering**: Piling analysis, collision detection, cut/fill earthwork calculations, cross-sections
- **Electrical Design**: String generation, inverter assignment, DC/AC cable routing, loss calculations
- **Shading Analysis**: Inter-row self-shading, obstacle shading, annual loss estimation using pvlib
- **BOM & Reporting**: Automated bill of materials, piling tables, cable schedules, Excel export

### MCP Integration

All operations are exposed as MCP tools, enabling:

- AI-driven design workflows via Claude Desktop or other MCP clients
- Automated design iteration and optimization
- Natural language interface to complex CAD operations

## Architecture

FreePVC consists of three components:

1. **MCP Server** (standalone Python): FastMCP-based server exposing 34+ tools
2. **Computation Engines** (pure Python): Zero-FreeCAD-dependency engines using numpy/scipy/shapely
3. **FreeCAD Workbench**: GUI addon with parametric objects, toolbars, and XML-RPC server

## Installation

### Prerequisites

- FreeCAD 0.19+ (0.21+ recommended)
- Python 3.10+
- pip or uv package manager

### Install FreePVC MCP Server

```bash
pip install freepvc
```

Or with uv:

```bash
uv pip install freepvc
```

### Install FreeCAD Addon

```bash
python scripts/install_addon.py
```

This symlinks the `addon/FreePVC` directory into your FreeCAD `Mod` folder.

## Quick Start

### Using the FreeCAD GUI

1. Open FreeCAD
2. Switch to the FreePVC workbench
3. Click "Start RPC Server" in the MCP Server toolbar
4. Use the Site & Terrain toolbar to import terrain data
5. Use the Layout toolbar to generate solar arrays

### Using MCP (with Claude Desktop)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "freepvc": {
      "command": "freepvc"
    }
  }
}
```

Then ask Claude to design a solar plant:

> "Create a 50 MW fixed-tilt solar project. Import the terrain from terrain.csv, generate a layout with 550W modules at 25-degree tilt, run piling analysis, and export a BOM."

## Demo Scripts

FreePVC includes several demo scripts to showcase different solar array configurations. Run these in FreeCAD's Python console:

### 1. Fixed-Tilt Array Demo

```python
exec(open('/home/dark/freepvc/demo_solar_array.py').read())
```

**Features:**
- 50 solar panels (10×5 grid)
- 25° tilt angle
- Support posts and structural beams
- Ground plane reference

**Output:** 27.5 kW array with 3D visualization

### 2. Single-Axis Tracker Array Demo

```python
exec(open('/home/dark/freepvc/demo_tracker_array.py').read())
```

**Features:**
- 8 tracker rows × 28 panels = 224 total panels
- Rotating torque tubes (N-S axis)
- Variable rotation angles simulating sun tracking
- Center support posts per tracker

**Output:** 123.2 kW tracker array with rotation capability

### 3. East-West Bifacial Array Demo

```python
exec(open('/home/dark/freepvc/demo_east_west.py').read())
```

**Features:**
- 6 paired rows (East + West facing)
- 12 panels per direction = 144 total panels
- Shallow ±15° tilt angles
- Color-coded: Blue (East), Orange (West)

**Output:** 79.2 kW bifacial array optimized for land utilization

**Benefits:** Uniform daily generation, reduced shading losses, lower wind loads

### 4. Terrain-Draped Array Demo

```python
exec(open('/home/dark/freepvc/demo_terrain_draped.py').read())
```

**Features:**
- 48 panels following terrain contours
- Adaptive tilt (15-35°) based on local slope
- Procedural terrain generation with 5° base slope
- Color-coded panels by elevation (blue=low, red=high)

**Output:** 26.4 kW array demonstrating terrain-following capabilities

**Shows:** How panels adapt to variable terrain with constant post heights

### Running the Demos

1. Open FreeCAD
2. Go to **View → Panels → Python console**
3. Copy and paste one of the `exec(open(...))` commands above
4. Explore the 3D view with mouse controls:
   - **Mouse wheel:** Zoom
   - **Middle mouse:** Pan
   - **Right mouse:** Rotate
   - **View → Standard views → Axonometric** for best perspective

## Development

### Setup Development Environment

```bash
git clone https://github.com/freepvc/freepvc.git
cd freepvc
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/install_addon.py
```

### Run Tests

```bash
pytest tests/
```

### Architecture Principles

- **Separation of Concerns**: Computation engines have zero FreeCAD imports
- **Testability**: All algorithms testable without FreeCAD running
- **MCP-First**: Every operation exposed as an MCP tool
- **Parametric Design**: All FreeCAD objects are fully parametric (FeaturePython)

## Project Status

**Current Phase:** Phase 0 - Project Scaffolding ✅

**Roadmap:**

- Phase 1: Terrain Analysis
- Phase 2: Layout Generation
- Phase 3: Civil Analysis
- Phase 4: Electrical Design
- Phase 5: Shading Analysis
- Phase 6: BOM, Reports & Export

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Inspired by PVCase (commercial AutoCAD plugin)
- Built on FreeCAD, the open-source parametric 3D CAD modeler
- References the PVPlant workbench (github.com/JavierBrana/PVPlant) for domain patterns
- Uses the neka-nat/freecad-mcp project as MCP server base pattern

## Support

- Documentation: /docs
- Issues: https://github.com/freepvc/freepvc/issues
- Discussions: https://github.com/freepvc/freepvc/discussions
