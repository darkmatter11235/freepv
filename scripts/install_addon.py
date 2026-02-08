#!/usr/bin/env python3
"""Install FreePVC addon into FreeCAD's Mod directory via symlink."""

import os
import platform
import sys
from pathlib import Path


def get_freecad_mod_dir():
    """Get the FreeCAD Mod directory path based on OS."""
    system = platform.system()

    if system == "Linux":
        # Try common Linux paths
        paths = [
            Path.home() / ".local/share/FreeCAD/Mod",
            Path.home() / ".FreeCAD/Mod",
            Path("/usr/share/freecad/Mod"),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            Path.home() / "Library/Application Support/FreeCAD/Mod",
            Path.home() / "Library/Preferences/FreeCAD/Mod",
        ]
    elif system == "Windows":
        paths = [
            Path(os.environ.get("APPDATA", "")) / "FreeCAD/Mod",
            Path.home() / "AppData/Roaming/FreeCAD/Mod",
        ]
    else:
        print(f"Unsupported operating system: {system}")
        return None

    # Find the first existing path
    for path in paths:
        if path.exists():
            return path

    # If none exist, create the first one
    mod_dir = paths[0]
    mod_dir.mkdir(parents=True, exist_ok=True)
    return mod_dir


def install_addon():
    """Install the FreePVC addon by creating a symlink."""
    # Get the addon source directory
    addon_src = Path(__file__).parent.parent / "addon" / "FreePVC"
    addon_src = addon_src.resolve()

    if not addon_src.exists():
        print(f"✗ Error: Addon source directory not found: {addon_src}")
        return False

    # Get the FreeCAD Mod directory
    mod_dir = get_freecad_mod_dir()
    if not mod_dir:
        print("✗ Error: Could not find or create FreeCAD Mod directory")
        return False

    print(f"FreeCAD Mod directory: {mod_dir}")
    print(f"FreePVC source: {addon_src}")

    # Create symlink
    symlink_target = mod_dir / "FreePVC"

    # Remove existing symlink/directory if it exists
    if symlink_target.exists() or symlink_target.is_symlink():
        print(f"Removing existing installation at {symlink_target}")
        if symlink_target.is_symlink():
            symlink_target.unlink()
        else:
            import shutil

            shutil.rmtree(symlink_target)

    try:
        # Create symlink
        symlink_target.symlink_to(addon_src, target_is_directory=True)
        print(f"✓ Successfully created symlink: {symlink_target} -> {addon_src}")
        print("\nFreePVC addon installed!")
        print("\nNext steps:")
        print("1. (Re)start FreeCAD")
        print("2. Switch to the 'FreePVC' workbench")
        print("3. Click 'Start RPC Server' in the toolbar")
        print("4. Run 'freepvc' MCP server to connect")
        return True

    except OSError as e:
        print(f"✗ Error creating symlink: {e}")
        if platform.system() == "Windows":
            print("\nOn Windows, you may need to:")
            print("- Run this script as Administrator, or")
            print("- Enable Developer Mode in Windows Settings")
        return False


if __name__ == "__main__":
    success = install_addon()
    sys.exit(0 if success else 1)
