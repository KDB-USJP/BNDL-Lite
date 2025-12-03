"""
BNDL Preference Management System

Implements a three-tier preference loading system:
1. Studio Preferences (via studio_prefs_location.json pointer) - Admin-defined defaults
2. User Preferences (bndl_user_prefs.json in Blender config) - User overrides
3. Hardcoded Defaults - Fallback if no JSON files exist

Studio Preferences Architecture:
- studio_prefs_location.json in addon root contains a path/URL to actual studio_prefs.json
- Allows centralized studio preference management without plugin redeployment
- Supports both local paths (//network/share/studio_prefs.json) and file:// URLs

Preference loading order:
- On addon startup: Load studio prefs (if exist) OR user prefs (if exist) OR defaults
- User can save their preferences to user_prefs.json at any time
- User can reset to studio/defaults at any time
"""

import bpy
import json
import os
from pathlib import Path
from typing import Dict, Any, Literal

# ─────────────────────────────────────────────────────────────────
# Preference Schema & Defaults
# ─────────────────────────────────────────────────────────────────

PREF_SCHEMA = {
    "bndl_directories": [],  # List of {"name": str, "directory": str} dicts
    "name_prefix_1": "",
    "name_prefix_2": "",
    "name_suffix_1": "",
    "overall_notes": "",
    "keep_replay_text": False,
    "round_float_precision": True,
    "reuse_proxies": True,  # Scene-level setting, but can have default
    "asset_dependency_mode": "PROXIES",
    # License settings
    "license_email": "",
    "license_key": "",
    "license_validated": False,
}

# ─────────────────────────────────────────────────────────────────
# File Paths
# ─────────────────────────────────────────────────────────────────

def get_addon_root() -> Path:
    """Get the root directory of the BNDL addon."""
    return Path(__file__).parent

def get_studio_prefs_location_path() -> Path:
    """Path to the studio preferences location pointer file in addon root."""
    return get_addon_root() / "studio_prefs_location.json"

def get_studio_prefs_path() -> Path | None:
    """
    Get the actual studio preferences path by reading the location pointer.
    Returns None if pointer doesn't exist or is invalid.
    """
    location_file = get_studio_prefs_location_path()
    
    if not location_file.exists():
        return None
    
    try:
        with open(location_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both "path" and "location" keys
        studio_path = data.get("studio_prefs_path") or data.get("path") or data.get("location")
        
        if not studio_path:
            print("[BNDL] Warning: studio_prefs_location.json missing 'studio_prefs_path' field")
            return None
        
        # Expand Blender's // relative paths
        if studio_path.startswith("//"):
            if bpy.data.filepath:
                blend_dir = Path(bpy.data.filepath).parent
                studio_path = str(blend_dir / studio_path[2:])
            else:
                print("[BNDL] Warning: Cannot resolve '//' path - no .blend file open")
                return None
        
        # Convert to Path and resolve
        resolved = Path(studio_path).expanduser().resolve()
        
        if not resolved.exists():
            print(f"[BNDL] Warning: Studio prefs not found at: {resolved}")
            return None
        
        return resolved
        
    except Exception as e:
        print(f"[BNDL] Error reading studio_prefs_location.json: {e}")
        return None

def get_user_prefs_path() -> Path:
    """User preferences in Blender config directory."""
    config_dir = Path(bpy.utils.user_resource('CONFIG'))
    bndl_config = config_dir / "BNDL"
    bndl_config.mkdir(parents=True, exist_ok=True)
    return bndl_config / "bndl_user_prefs.json"

# ─────────────────────────────────────────────────────────────────
# Preference Loading
# ─────────────────────────────────────────────────────────────────

def load_json_prefs(path: Path) -> Dict[str, Any] | None:
    """Load preferences from JSON file. Returns None if file doesn't exist or is invalid."""
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate that it's a dict
        if not isinstance(data, dict):
            print(f"[BNDL] Warning: {path.name} is not a valid JSON object")
            return None
        
        return data
    except Exception as e:
        print(f"[BNDL] Error loading {path.name}: {e}")
        return None

def get_preference_source() -> Literal["STUDIO", "USER", "DEFAULT"]:
    """Determine which preference source is currently active."""
    if get_studio_prefs_path() is not None:
        return "STUDIO"
    elif get_user_prefs_path().exists():
        return "USER"
    else:
        return "DEFAULT"

def load_preferences() -> tuple[Dict[str, Any], Literal["STUDIO", "USER", "DEFAULT"]]:
    """
    Load preferences with priority based on prefer_user_prefs toggle.
    Returns (prefs_dict, source)
    """
    from .prefs import get_prefs
    
    # Get preference priority setting
    try:
        prefs = get_prefs()
        prefer_user = prefs.prefer_user_prefs if hasattr(prefs, "prefer_user_prefs") else False
    except:
        prefer_user = False
    
    studio_path = get_studio_prefs_path()
    user_path = get_user_prefs_path()
    
    studio_prefs = load_json_prefs(studio_path) if studio_path else None
    user_prefs = load_json_prefs(user_path) if user_path.exists() else None
    
    # Apply priority logic
    if prefer_user and user_prefs is not None:
        # User preference enabled and exists - use user prefs
        result = {**PREF_SCHEMA, **user_prefs}
        print(f"[BNDL] Loaded user preferences (priority) from: {user_path}")
        return result, "USER"
    elif studio_prefs is not None:
        # Studio prefs exist - use them (either no user prefs, or studio has priority)
        result = {**PREF_SCHEMA, **studio_prefs}
        print(f"[BNDL] Loaded studio preferences from: {studio_path}")
        return result, "STUDIO"
    elif user_prefs is not None:
        # No studio prefs, but user prefs exist
        result = {**PREF_SCHEMA, **user_prefs}
        print(f"[BNDL] Loaded user preferences from: {user_path}")
        return result, "USER"
    else:
        # Fallback to defaults
        print("[BNDL] Using default preferences (no studio or user prefs found)")
        return PREF_SCHEMA.copy(), "DEFAULT"

# ─────────────────────────────────────────────────────────────────
# Preference Saving
# ─────────────────────────────────────────────────────────────────

def _normalize_path_for_json(path: str) -> str:
    """Convert backslashes to forward slashes for cross-platform JSON compatibility."""
    return path.replace("\\", "/") if path else path

def save_user_preferences(prefs_dict: Dict[str, Any]) -> bool:
    """
    Save preferences to user_prefs.json.
    Returns True on success, False on failure.
    """
    user_path = get_user_prefs_path()
    
    try:
        # Ensure directory exists
        user_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON with pretty formatting
        with open(user_path, 'w', encoding='utf-8') as f:
            json.dump(prefs_dict, f, indent=2)
        
        print(f"[BNDL] Saved user preferences to: {user_path}")
        return True
    except Exception as e:
        print(f"[BNDL] Error saving user preferences: {e}")
        return False

def collect_current_preferences() -> Dict[str, Any]:
    """Collect current preferences from the addon."""
    from .prefs import get_prefs
    prefs = get_prefs()
    
    # Serialize bndl_directories CollectionProperty to list of dicts
    # Normalize paths to forward slashes for cross-platform compatibility
    directories = []
    if hasattr(prefs, "bndl_directories"):
        for item in prefs.bndl_directories:
            directories.append({
                "name": item.name,
                "directory": _normalize_path_for_json(item.directory)
            })
    
    # Safely get scene-level property (handle restricted contexts)
    reuse_proxies_value = True
    try:
        if hasattr(bpy.context, 'scene') and bpy.context.scene and hasattr(bpy.context.scene, "bndl_reuse_proxies"):
            reuse_proxies_value = bpy.context.scene.bndl_reuse_proxies  # type: ignore
    except (AttributeError, TypeError):
        # Context might be restricted or scene not available
        pass
    
    return {
        "bndl_directories": directories,
        "name_prefix_1": prefs.name_prefix_1,
        "name_prefix_2": prefs.name_prefix_2,
        "name_suffix_1": prefs.name_suffix_1,
        "overall_notes": prefs.overall_notes,
        "keep_replay_text": prefs.keep_replay_text,
        "round_float_precision": prefs.round_float_precision,
        "reuse_proxies": reuse_proxies_value,
        "asset_dependency_mode": prefs.asset_dependency_mode,
        # License settings
        "license_email": prefs.license_email,
        "license_key": prefs.license_key,
        "license_validated": prefs.license_validated,
    }

def apply_preferences_to_addon(prefs_dict: Dict[str, Any]) -> None:
    """Apply preference values to the addon preferences."""
    from .prefs import get_prefs
    prefs = get_prefs()
    
    # Apply bndl_directories (deserialize list of dicts to CollectionProperty)
    if "bndl_directories" in prefs_dict and hasattr(prefs, "bndl_directories"):
        prefs.bndl_directories.clear()
        for item_dict in prefs_dict["bndl_directories"]:
            if isinstance(item_dict, dict) and "name" in item_dict and "directory" in item_dict:
                item = prefs.bndl_directories.add()
                item.name = item_dict["name"]
                item.directory = item_dict["directory"]
    
    # Apply other preferences
    if "name_prefix_1" in prefs_dict:
        prefs.name_prefix_1 = prefs_dict["name_prefix_1"]
    if "name_prefix_2" in prefs_dict:
        prefs.name_prefix_2 = prefs_dict["name_prefix_2"]
    if "name_suffix_1" in prefs_dict:
        prefs.name_suffix_1 = prefs_dict["name_suffix_1"]
    if "overall_notes" in prefs_dict:
        prefs.overall_notes = prefs_dict["overall_notes"]
    if "keep_replay_text" in prefs_dict:
        prefs.keep_replay_text = prefs_dict["keep_replay_text"]
    if "round_float_precision" in prefs_dict:
        prefs.round_float_precision = prefs_dict["round_float_precision"]
    if "asset_dependency_mode" in prefs_dict:
        prefs.asset_dependency_mode = prefs_dict["asset_dependency_mode"]
    
    # Apply license settings
    if "license_email" in prefs_dict:
        prefs.license_email = prefs_dict["license_email"]
    if "license_key" in prefs_dict:
        prefs.license_key = prefs_dict["license_key"]
    if "license_validated" in prefs_dict:
        prefs.license_validated = prefs_dict["license_validated"]
    
    # Scene-level property (safely handle restricted contexts)
    if "reuse_proxies" in prefs_dict:
        try:
            if hasattr(bpy.context, 'scene') and bpy.context.scene and hasattr(bpy.context.scene, "bndl_reuse_proxies"):
                bpy.context.scene.bndl_reuse_proxies = prefs_dict["reuse_proxies"]  # type: ignore
        except (AttributeError, TypeError):
            # Context might be restricted or scene not available - skip silently
            pass

# ─────────────────────────────────────────────────────────────────
# Operators
# ─────────────────────────────────────────────────────────────────

class BNDL_OT_SaveUserPreferences(bpy.types.Operator):
    """Save current preferences to user preferences JSON file. Will prompt for confirmation if file already exists."""
    bl_idname = "bndl.save_user_preferences"
    bl_label = "Save User Preferences"
    bl_options = {"REGISTER"}
    
    def invoke(self, context, event):
        # Check if user preferences file already exists
        user_path = get_user_prefs_path()
        if user_path.exists():
            return context.window_manager.invoke_confirm(self, event)  # type: ignore[attr-defined]
        else:
            # No existing file, proceed directly
            return self.execute(context)
    
    def execute(self, context):
        prefs_dict = collect_current_preferences()
        success = save_user_preferences(prefs_dict)
        
        if success:
            self.report({'INFO'}, f"Saved user preferences to: {get_user_prefs_path()}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to save user preferences. Check console for details.")
            return {'CANCELLED'}

class BNDL_OT_ResetToStudioDefaults(bpy.types.Operator):
    """Reset preferences to studio defaults (or hardcoded defaults if no studio prefs exist). Will prompt for confirmation when studio preferences are available."""
    bl_idname = "bndl.reset_to_studio_defaults"
    bl_label = "Reset to Studio/Defaults"
    bl_options = {"REGISTER"}
    
    def invoke(self, context, event):
        # Check if studio preferences exist
        studio_path = get_studio_prefs_path()
        if studio_path is not None:
            return context.window_manager.invoke_confirm(self, event)  # type: ignore[attr-defined]
        else:
            # No studio prefs, show info and proceed
            self.report({'INFO'}, "No studio preferences located. Resetting to hardcoded defaults.")
            return self.execute(context)
    
    def execute(self, context):
        # Load fresh preferences (ignoring user prefs)
        studio_path = get_studio_prefs_path()
        if studio_path is not None:
            studio_prefs = load_json_prefs(studio_path)
            if studio_prefs is not None:
                prefs_dict = {**PREF_SCHEMA, **studio_prefs}
                source = "studio defaults"
            else:
                prefs_dict = PREF_SCHEMA.copy()
                source = "hardcoded defaults (studio prefs invalid)"
        else:
            prefs_dict = PREF_SCHEMA.copy()
            source = "hardcoded defaults"
        
        apply_preferences_to_addon(prefs_dict)
        self.report({'INFO'}, f"Reset preferences to {source}")
        return {'FINISHED'}

class BNDL_OT_DeleteUserPreferences(bpy.types.Operator):
    """Delete user preferences JSON file and reset to studio/defaults"""
    bl_idname = "bndl.delete_user_preferences"
    bl_label = "Delete User Preferences"
    bl_options = {"REGISTER"}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)  # type: ignore[attr-defined]
    
    def execute(self, context):
        user_path = get_user_prefs_path()
        
        if not user_path.exists():
            self.report({'WARNING'}, "No user preferences file to delete")
            return {'CANCELLED'}
        
        try:
            user_path.unlink()
            self.report({'INFO'}, f"Deleted user preferences: {user_path}")
            
            # Reset to studio/defaults
            bpy.ops.bndl.reset_to_studio_defaults()  # type: ignore
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete user preferences: {e}")
            return {'CANCELLED'}

class BNDL_OT_ReloadPreferences(bpy.types.Operator):
    """Reload preferences from JSON files (respects preference priority toggle)"""
    bl_idname = "bndl.reload_preferences"
    bl_label = "Reload Preferences"
    bl_description = "Reload preferences from studio/user JSON files based on current priority setting"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        try:
            prefs_dict, source = load_preferences()
            apply_preferences_to_addon(prefs_dict)
            
            source_names = {
                "STUDIO": "studio preferences",
                "USER": "user preferences",
                "DEFAULT": "default preferences"
            }
            self.report({'INFO'}, f"Reloaded {source_names[source]}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reload preferences: {e}")
            return {'CANCELLED'}

# ─────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────

def register():
    bpy.utils.register_class(BNDL_OT_SaveUserPreferences)
    bpy.utils.register_class(BNDL_OT_ResetToStudioDefaults)
    bpy.utils.register_class(BNDL_OT_DeleteUserPreferences)
    bpy.utils.register_class(BNDL_OT_ReloadPreferences)

def unregister():
    bpy.utils.unregister_class(BNDL_OT_ReloadPreferences)
    bpy.utils.unregister_class(BNDL_OT_DeleteUserPreferences)
    bpy.utils.unregister_class(BNDL_OT_ResetToStudioDefaults)
    bpy.utils.unregister_class(BNDL_OT_SaveUserPreferences)
