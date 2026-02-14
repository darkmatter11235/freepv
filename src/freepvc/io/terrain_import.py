"""Terrain data import from various file formats.

Supports:
- CSV point clouds (X, Y, Z)
- DEM ASCII grid format
- DXF contour lines (future)
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict
import csv

from freepvc.models.terrain import TerrainData, TerrainSource


class TerrainImporter:
    """Import terrain data from various file formats."""

    @staticmethod
    def import_csv_points(
        file_path: str,
        x_col: int = 0,
        y_col: int = 1,
        z_col: int = 2,
        skip_header: int = 0,
        delimiter: str = ",",
        unit_scale: float = 1.0,
    ) -> TerrainData:
        """Import terrain from CSV point cloud.

        Args:
            file_path: Path to CSV file
            x_col: Column index for X coordinate (0-based)
            y_col: Column index for Y coordinate (0-based)
            z_col: Column index for Z/elevation coordinate (0-based)
            skip_header: Number of header rows to skip
            delimiter: CSV delimiter character
            unit_scale: Multiplier to convert to mm (e.g., 1000.0 for meters)

        Returns:
            TerrainData with point cloud

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty or malformed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        points = []

        with open(file_path, "r") as f:
            reader = csv.reader(f, delimiter=delimiter)

            # Skip header rows
            for _ in range(skip_header):
                next(reader, None)

            # Read data rows
            for row_num, row in enumerate(reader, start=skip_header + 1):
                try:
                    # Extract coordinates
                    x = float(row[x_col]) * unit_scale
                    y = float(row[y_col]) * unit_scale
                    z = float(row[z_col]) * unit_scale
                    points.append([x, y, z])

                except (IndexError, ValueError) as e:
                    raise ValueError(
                        f"Error parsing row {row_num} in {file_path}: {e}"
                    )

        if not points:
            raise ValueError(f"No valid points found in {file_path}")

        points_array = np.array(points, dtype=np.float64)

        return TerrainData(
            points=points_array,
            source=TerrainSource.CSV_POINTS,
            source_file=str(file_path),
            metadata={
                "num_points_imported": len(points),
                "x_col": x_col,
                "y_col": y_col,
                "z_col": z_col,
                "unit_scale": unit_scale,
            },
        )

    @staticmethod
    def import_dem_ascii(
        file_path: str,
        unit_scale: float = 1.0,
    ) -> TerrainData:
        """Import terrain from ASCII DEM grid format.

        Supports the standard ASCII grid format used by GIS software:
        ```
        ncols         100
        nrows         100
        xllcorner     0.0
        yllcorner     0.0
        cellsize      10.0
        NODATA_value  -9999
        <grid data>
        ```

        Args:
            file_path: Path to ASCII DEM file
            unit_scale: Multiplier to convert to mm (e.g., 1000.0 for meters)

        Returns:
            TerrainData with point cloud from grid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is malformed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"DEM file not found: {file_path}")

        # Read header
        header = {}
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line[0].isdigit() and line[0] != "-":
                    # Header line
                    parts = line.split()
                    if len(parts) == 2:
                        key = parts[0].lower()
                        try:
                            value = float(parts[1])
                        except ValueError:
                            value = parts[1]
                        header[key] = value
                else:
                    # Start of data
                    break

        # Validate required headers
        required = ["ncols", "nrows", "xllcorner", "yllcorner", "cellsize"]
        for key in required:
            if key not in header:
                raise ValueError(f"Missing required header: {key}")

        ncols = int(header["ncols"])
        nrows = int(header["nrows"])
        xllcorner = float(header["xllcorner"]) * unit_scale
        yllcorner = float(header["yllcorner"]) * unit_scale
        cellsize = float(header["cellsize"]) * unit_scale
        nodata = float(header.get("nodata_value", -9999))

        # Read grid data
        grid_data = []
        with open(file_path, "r") as f:
            # Skip header lines
            for _ in range(len(header)):
                next(f)

            # Read grid rows
            for line in f:
                line = line.strip()
                if line:
                    row = [float(x) for x in line.split()]
                    grid_data.append(row)

        if len(grid_data) != nrows:
            raise ValueError(
                f"Expected {nrows} rows, got {len(grid_data)}"
            )

        # Convert grid to point cloud
        points = []
        for row_idx, row in enumerate(grid_data):
            if len(row) != ncols:
                raise ValueError(
                    f"Row {row_idx} has {len(row)} columns, expected {ncols}"
                )

            for col_idx, z in enumerate(row):
                if z != nodata:
                    # Calculate coordinates
                    x = xllcorner + col_idx * cellsize
                    y = yllcorner + (nrows - 1 - row_idx) * cellsize  # Y increases upward
                    z_scaled = z * unit_scale

                    points.append([x, y, z_scaled])

        if not points:
            raise ValueError(f"No valid elevation data found in {file_path}")

        points_array = np.array(points, dtype=np.float64)

        return TerrainData(
            points=points_array,
            source=TerrainSource.DEM_ASCII,
            source_file=str(file_path),
            metadata={
                "ncols": ncols,
                "nrows": nrows,
                "xllcorner": xllcorner,
                "yllcorner": yllcorner,
                "cellsize": cellsize,
                "nodata_value": nodata,
                "unit_scale": unit_scale,
                "num_points_imported": len(points),
            },
        )

    @staticmethod
    def import_xyz_text(
        file_path: str,
        delimiter: str = None,
        unit_scale: float = 1.0,
    ) -> TerrainData:
        """Import terrain from simple XYZ text file (space or tab delimited).

        Args:
            file_path: Path to XYZ file
            delimiter: Delimiter (None for whitespace)
            unit_scale: Multiplier to convert to mm

        Returns:
            TerrainData with point cloud
        """
        # Simple wrapper around CSV importer
        if delimiter is None:
            # Read and detect delimiter
            with open(file_path, "r") as f:
                first_line = f.readline().strip()
                if "\t" in first_line:
                    delimiter = "\t"
                else:
                    delimiter = " "

        # Handle multiple spaces as single delimiter
        points = []
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(delimiter) if delimiter != " " else line.split()
                if len(parts) < 3:
                    continue

                try:
                    x = float(parts[0]) * unit_scale
                    y = float(parts[1]) * unit_scale
                    z = float(parts[2]) * unit_scale
                    points.append([x, y, z])
                except (ValueError, IndexError):
                    continue

        if not points:
            raise ValueError(f"No valid points found in {file_path}")

        points_array = np.array(points, dtype=np.float64)

        return TerrainData(
            points=points_array,
            source=TerrainSource.SURVEYED_POINTS,
            source_file=str(file_path),
            metadata={
                "num_points_imported": len(points),
                "unit_scale": unit_scale,
            },
        )

    @staticmethod
    def auto_detect_format(file_path: str) -> str:
        """Auto-detect terrain file format.

        Args:
            file_path: Path to file

        Returns:
            Format string: "csv", "dem_ascii", "xyz", or "unknown"
        """
        file_path = Path(file_path)

        # Check by extension first
        ext = file_path.suffix.lower()
        if ext == ".csv":
            return "csv"
        elif ext in [".asc", ".dem"]:
            return "dem_ascii"
        elif ext in [".xyz", ".txt"]:
            # Could be XYZ or DEM ASCII, check content
            pass

        # Check content
        try:
            with open(file_path, "r") as f:
                first_lines = [next(f).strip() for _ in range(min(10, sum(1 for _ in f)))]

            # Check for DEM ASCII headers
            if any("ncols" in line.lower() or "nrows" in line.lower() for line in first_lines):
                return "dem_ascii"

            # Check for CSV (commas)
            if any("," in line for line in first_lines):
                return "csv"

            # Default to XYZ
            return "xyz"

        except Exception:
            return "unknown"

    @staticmethod
    def import_auto(
        file_path: str,
        unit_scale: float = 1.0,
        **kwargs,
    ) -> TerrainData:
        """Auto-detect format and import terrain data.

        Args:
            file_path: Path to terrain file
            unit_scale: Multiplier to convert to mm
            **kwargs: Additional format-specific arguments

        Returns:
            TerrainData

        Raises:
            ValueError: If format cannot be detected or import fails
        """
        fmt = TerrainImporter.auto_detect_format(file_path)

        if fmt == "csv":
            return TerrainImporter.import_csv_points(file_path, unit_scale=unit_scale, **kwargs)
        elif fmt == "dem_ascii":
            return TerrainImporter.import_dem_ascii(file_path, unit_scale=unit_scale)
        elif fmt == "xyz":
            return TerrainImporter.import_xyz_text(file_path, unit_scale=unit_scale, **kwargs)
        else:
            raise ValueError(f"Unknown terrain file format: {file_path}")


def create_sample_terrain(
    size: float = 50000.0,
    spacing: float = 2000.0,
    slope: float = 5.0,
    roughness: float = 500.0,
) -> TerrainData:
    """Create sample terrain for testing.

    Args:
        size: Terrain extent in mm (default 50m)
        spacing: Point spacing in mm (default 2m)
        slope: Base slope in degrees (default 5°)
        roughness: Random elevation variation in mm (default 0.5m)

    Returns:
        TerrainData with synthetic terrain
    """
    import math
    import random

    points = []

    x = 0.0
    while x <= size:
        y = 0.0
        while y <= size:
            # Base slope (north-south)
            base_z = y * math.tan(math.radians(slope))

            # Add roughness
            z = base_z + random.uniform(-roughness, roughness)

            points.append([x, y, z])
            y += spacing
        x += spacing

    points_array = np.array(points, dtype=np.float64)

    return TerrainData(
        points=points_array,
        source=TerrainSource.SURVEYED_POINTS,
        metadata={"generated": True, "size": size, "spacing": spacing, "slope": slope},
    )
