# FreePVC Development Setup

## Prerequisites

- Python 3.12+
- FreeCAD 0.19+ (0.21+ recommended)
- Git

## Quick Start

### 1. Clone and Setup Virtual Environment

```bash
cd /home/dark/freepvc

# Create virtual environment with Python 3.12
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Install FreeCAD Addon

```bash
# Symlink the FreePVC addon into FreeCAD's Mod directory
python scripts/install_addon.py
```

### 3. Start FreeCAD and RPC Server

1. Launch FreeCAD
2. Switch to the **FreePVC** workbench (from workbench selector)
3. Click **"Start RPC Server"** in the toolbar
4. Server will start on `localhost:9876`

### 4. Run FreePVC MCP Server

In a separate terminal:

```bash
source .venv/bin/activate
freepvc
```

The MCP server will:
- Connect to FreeCAD on port 9876
- Expose solar-specific MCP tools
- Ready for AI agent integration

## Current Status

✅ **Phase 0 Complete** - Project Scaffolding
- Full directory structure
- MCP server with FastMCP + freecad-mcp
- FreeCAD workbench with RPC server
- Project management tools (create_project, get_summary, save_project)
- Python 3.12 environment with all dependencies

## Next Phase: Terrain Analysis

Phase 1 will add:
- Terrain mesh generation from CSV/DEM/DXF
- Slope analysis with heatmaps
- Elevation interpolation
- MCP tools for terrain operations

## Git Commits

```bash
# View project history
git log --oneline

# Current commits:
# 3cda71d Update to Python 3.12 and freecad-mcp dependency
# 612db09 Phase 0: Project scaffolding
```

## Testing the Installation

```python
# Test Python imports
python -c "import freepvc; print(freepvc.__version__)"
# Output: 0.1.0

# Verify freepvc command
which freepvc
# Output: /home/dark/freepvc/.venv/bin/freepvc
```

## MCP Tools Available (Phase 0)

1. **create_project** - Create new solar project with site metadata
2. **get_project_summary** - Get overview of current project
3. **save_project** - Save FreeCAD document

## Dependencies Installed

- **freecad-mcp** 0.1.15 - Base MCP connection to FreeCAD
- **numpy** 2.4.2 - Array mathematics
- **scipy** 1.17.0 - Scientific computing (Delaunay, interpolation)
- **pvlib** 0.15.0 - Solar position calculations
- **shapely** 2.1.2 - 2D geometry operations
- **openpyxl** 3.1.5 - Excel export
- **ezdxf** 1.4.3 - DXF import/export
- **simplekml** 1.3.6 - KML export

Dev dependencies: pytest, pytest-asyncio, pytest-cov, ruff, mypy

## Troubleshooting

### FreeCAD RPC Connection Failed

```
⚠ Warning: Could not connect to FreeCAD
```

**Solution:**
1. Make sure FreeCAD is running
2. Switch to FreePVC workbench
3. Click "Start RPC Server"

### Import Errors

```bash
# Ensure venv is activated
source .venv/bin/activate

# Verify installation
pip list | grep freepvc
```

### FreeCAD Addon Not Showing

```bash
# Re-run installer
python scripts/install_addon.py

# Check symlink
ls -la ~/.local/share/FreeCAD/Mod/FreePVC
```
