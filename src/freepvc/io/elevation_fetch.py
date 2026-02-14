"""Fetch elevation data from online sources using coordinates.

This module provides functions to retrieve terrain elevation data
from various free and commercial elevation APIs.
"""

import asyncio
import aiohttp
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ElevationPoint:
    """Single elevation data point."""
    latitude: float
    longitude: float
    elevation_m: float


class ElevationFetcher:
    """Fetch elevation data from online sources."""
    
    @staticmethod
    async def fetch_open_elevation(
        latitudes: List[float],
        longitudes: List[float],
    ) -> List[ElevationPoint]:
        """Fetch elevation data from Open-Elevation API (free, no API key).
        
        Args:
            latitudes: List of latitude coordinates
            longitudes: List of longitude coordinates
            
        Returns:
            List of elevation points
            
        Raises:
            ValueError: If coordinate lists don't match in length
            RuntimeError: If API request fails
        """
        if len(latitudes) != len(longitudes):
            raise ValueError("Latitude and longitude lists must have same length")
        
        # Open-Elevation API endpoint
        url = "https://api.open-elevation.com/api/v1/lookup"
        
        # Prepare locations payload
        locations = [
            {"latitude": lat, "longitude": lon}
            for lat, lon in zip(latitudes, longitudes)
        ]
        
        # Batch requests in groups of 100 (API limit)
        batch_size = 100
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(locations), batch_size):
                batch = locations[i:i + batch_size]
                payload = {"locations": batch}
                
                try:
                    async with session.post(url, json=payload, timeout=30) as response:
                        if response.status != 200:
                            raise RuntimeError(f"API request failed: {response.status}")
                        
                        data = await response.json()
                        results = data.get("results", [])
                        
                        for result in results:
                            all_results.append(ElevationPoint(
                                latitude=result["latitude"],
                                longitude=result["longitude"],
                                elevation_m=result["elevation"],
                            ))
                
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Timeout fetching elevation data for batch {i//batch_size + 1}")
                except Exception as e:
                    raise RuntimeError(f"Error fetching elevation data: {str(e)}")
        
        return all_results
    
    @staticmethod
    def generate_grid_coordinates(
        center_lat: float,
        center_lon: float,
        width_m: float,
        height_m: float,
        resolution_m: float = 10.0,
    ) -> Tuple[List[float], List[float]]:
        """Generate a grid of coordinates for terrain sampling.
        
        Args:
            center_lat: Center latitude (decimal degrees)
            center_lon: Center longitude (decimal degrees)
            width_m: Grid width in meters (east-west)
            height_m: Grid height in meters (north-south)
            resolution_m: Sampling resolution in meters
            
        Returns:
            Tuple of (latitudes, longitudes) lists
        """
        # Approximate meters to degrees conversion
        # 1 degree latitude ≈ 111,111 meters
        # 1 degree longitude ≈ 111,111 * cos(latitude) meters
        lat_deg_per_m = 1.0 / 111111.0
        lon_deg_per_m = 1.0 / (111111.0 * np.cos(np.radians(center_lat)))
        
        # Calculate grid bounds
        half_width = width_m / 2.0
        half_height = height_m / 2.0
        
        min_lat = center_lat - half_height * lat_deg_per_m
        max_lat = center_lat + half_height * lat_deg_per_m
        min_lon = center_lon - half_width * lon_deg_per_m
        max_lon = center_lon + half_width * lon_deg_per_m
        
        # Generate grid points
        num_lat_points = int(height_m / resolution_m) + 1
        num_lon_points = int(width_m / resolution_m) + 1
        
        lats = np.linspace(min_lat, max_lat, num_lat_points)
        lons = np.linspace(min_lon, max_lon, num_lon_points)
        
        # Create meshgrid
        lat_grid, lon_grid = np.meshgrid(lats, lons, indexing='ij')
        
        # Flatten to lists
        latitudes = lat_grid.flatten().tolist()
        longitudes = lon_grid.flatten().tolist()
        
        return latitudes, longitudes
    
    @staticmethod
    def convert_to_local_coordinates(
        elevation_points: List[ElevationPoint],
        origin_lat: float,
        origin_lon: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert lat/lon/elevation to local XYZ coordinates.
        
        Args:
            elevation_points: List of elevation points
            origin_lat: Origin latitude for local coordinate system
            origin_lon: Origin longitude for local coordinate system
            
        Returns:
            Tuple of (x, y, z) numpy arrays in millimeters
        """
        # Conversion factors
        lat_deg_per_m = 1.0 / 111111.0
        lon_deg_per_m = 1.0 / (111111.0 * np.cos(np.radians(origin_lat)))
        
        # First pass: collect all elevations to find minimum
        elevations = [point.elevation_m for point in elevation_points]
        min_elevation = min(elevations)
        
        x_coords = []
        y_coords = []
        z_coords = []
        
        for point in elevation_points:
            # Calculate offset from origin
            delta_lat = point.latitude - origin_lat
            delta_lon = point.longitude - origin_lon
            
            # Convert to meters
            y_m = delta_lat / lat_deg_per_m
            x_m = delta_lon / lon_deg_per_m
            z_m = point.elevation_m - min_elevation  # Make relative to lowest point
            
            # Convert to millimeters (FreeCAD standard)
            x_coords.append(x_m * 1000.0)
            y_coords.append(y_m * 1000.0)
            z_coords.append(z_m * 1000.0)
        
        return (
            np.array(x_coords),
            np.array(y_coords),
            np.array(z_coords),
        )


async def fetch_terrain_from_coordinates(
    center_lat: float,
    center_lon: float,
    width_m: float = 1000.0,
    height_m: float = 1000.0,
    resolution_m: float = 10.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """High-level function to fetch terrain data from coordinates.
    
    Args:
        center_lat: Center latitude (decimal degrees)
        center_lon: Center longitude (decimal degrees)
        width_m: Area width in meters (default 1km)
        height_m: Area height in meters (default 1km)
        resolution_m: Sampling resolution in meters (default 10m)
        
    Returns:
        Tuple of (x, y, z) arrays in millimeters for FreeCAD
        
    Example:
        >>> x, y, z = await fetch_terrain_from_coordinates(
        ...     center_lat=35.0,
        ...     center_lon=-106.0,
        ...     width_m=500,
        ...     height_m=500,
        ... )
    """
    fetcher = ElevationFetcher()
    
    # Generate grid coordinates
    latitudes, longitudes = fetcher.generate_grid_coordinates(
        center_lat, center_lon, width_m, height_m, resolution_m
    )
    
    # Fetch elevation data
    elevation_points = await fetcher.fetch_open_elevation(latitudes, longitudes)
    
    # Convert to local coordinates
    x, y, z = fetcher.convert_to_local_coordinates(
        elevation_points, center_lat, center_lon
    )
    
    return x, y, z
