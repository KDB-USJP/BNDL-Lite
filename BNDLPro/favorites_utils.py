"""
Utilities for managing recent files and favorites in BNDL addon.
Provides functions to add/remove files from recent history and favorites list.
"""

import bpy
import os
from datetime import datetime
from typing import Optional


def add_to_recent_files(filepath: str) -> None:
    """
    Add a file to the recent files list.
    
    Args:
        filepath: Full path to the .bndl file
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    # Get filename from path
    filename = os.path.basename(filepath)
    
    # Check if file already exists in recent list
    existing_idx = None
    for i, item in enumerate(prefs.recent_files):
        if item.filepath == filepath:
            existing_idx = i
            break
    
    # Remove if it already exists (we'll add it to the front)
    if existing_idx is not None:
        prefs.recent_files.remove(existing_idx)
    
    # Add to the front of the list
    new_item = prefs.recent_files.add()
    prefs.recent_files.move(len(prefs.recent_files) - 1, 0)
    
    new_item.filepath = filepath
    new_item.filename = filename
    new_item.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Trim list if it exceeds max_recent_files
    while len(prefs.recent_files) > prefs.max_recent_files:
        prefs.recent_files.remove(len(prefs.recent_files) - 1)
    
    print(f"[BNDL Recent] Added: {filename}")


def is_favorite(filepath: str) -> bool:
    """
    Check if a file is in the favorites list.
    
    Args:
        filepath: Full path to the .bndl file
        
    Returns:
        True if file is favorited, False otherwise
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    for item in prefs.favorite_files:
        if item.filepath == filepath:
            return True
    
    return False


def toggle_favorite(filepath: str) -> bool:
    """
    Toggle favorite status for a file.
    
    Args:
        filepath: Full path to the .bndl file
        
    Returns:
        True if file is now favorited, False if unfavorited
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    # Get filename from path
    filename = os.path.basename(filepath)
    
    # Check if already favorited
    for i, item in enumerate(prefs.favorite_files):
        if item.filepath == filepath:
            # Remove from favorites
            prefs.favorite_files.remove(i)
            print(f"[BNDL Favorites] Removed: {filename}")
            return False
    
    # Add to favorites
    new_fav = prefs.favorite_files.add()
    new_fav.filepath = filepath
    new_fav.filename = filename
    print(f"[BNDL Favorites] Added: {filename}")
    return True


def clean_missing_favorites() -> int:
    """
    Remove favorites for files that no longer exist.
    
    Returns:
        Number of favorites removed
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    removed_count = 0
    i = 0
    while i < len(prefs.favorite_files):
        item = prefs.favorite_files[i]
        if not os.path.exists(item.filepath):
            print(f"[BNDL Favorites] Removing missing file: {item.filename}")
            prefs.favorite_files.remove(i)
            removed_count += 1
        else:
            i += 1
    
    return removed_count


def get_recent_files(max_count: Optional[int] = None) -> list:
    """
    Get list of recent files.
    
    Args:
        max_count: Maximum number of files to return (None = all)
        
    Returns:
        List of tuples: (filepath, filename, timestamp)
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    result = []
    count = 0
    for item in prefs.recent_files:
        if max_count and count >= max_count:
            break
        # Only include files that still exist
        if os.path.exists(item.filepath):
            result.append((item.filepath, item.filename, item.timestamp))
            count += 1
    
    return result


def get_favorites() -> list:
    """
    Get list of favorite files.
    
    Returns:
        List of tuples: (filepath, filename)
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    result = []
    for item in prefs.favorite_files:
        # Only include files that still exist
        if os.path.exists(item.filepath):
            result.append((item.filepath, item.filename))
    
    return result


def get_project_export_settings(project_index: int) -> dict:
    """
    Get export settings for a project, with project-specific overrides.
    
    Args:
        project_index: Index of the project in bndl_directories
        
    Returns:
        Dictionary with keys: prefix_1, prefix_2, suffix_1, notes
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    
    # Default to global settings
    settings = {
        'prefix_1': prefs.name_prefix_1,
        'prefix_2': prefs.name_prefix_2,
        'suffix_1': prefs.name_suffix_1,
        'notes': prefs.overall_notes
    }
    
    # Check if we have a valid project with overrides
    if 0 <= project_index < len(prefs.bndl_directories):
        project = prefs.bndl_directories[project_index]
        if project.use_project_presets:
            # Override with project-specific settings
            settings['prefix_1'] = project.project_prefix_1
            settings['prefix_2'] = project.project_prefix_2
            settings['suffix_1'] = project.project_suffix_1
            settings['notes'] = project.project_notes
            print(f"[BNDL Export] Using project-specific presets for: {project.name}")
    
    return settings
