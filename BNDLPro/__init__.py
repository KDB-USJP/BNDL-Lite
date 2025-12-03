# === BNDL LITE CONFIGURATION ===
BNDL_LITE_VERSION = True  # Set to False for Pro version

# Hardcoded Lite license credentials (validated against backend)
LITE_LICENSE_EMAIL = "test@user.com"
LITE_LICENSE_KEY = "12345"
# === END CONFIGURATION ===

bl_info = {
    "name": "BNDL Lite (Materials Only)",
    "author": "Kyōsei Design Bureau",
    "version": (1, 4, 0),
    "blender": (4, 0, 0),
    "location": "N-Panel > BNDL",
    "description": "Export/replay Material node trees to .bndl format",
    "category": "Node",
}

import importlib
import os
import bpy
import bpy.utils.previews
from . import prefs, pref_manager, ui_panels, ops_export, ops_replay, browser, ops_docs, i18n_utils, progress_utils, ops_batch_export, ops_favorites
modules = (i18n_utils, progress_utils, prefs, pref_manager, ui_panels, ops_export, ops_replay, browser, ops_docs, ops_batch_export, ops_favorites)

# Global variable to store icons
custom_icons = None

def register():
    global custom_icons
    
    # Register custom icons
    custom_icons = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__))
    
    # Load icons (use 256px for UI display)
    icon_path = os.path.join(icons_dir, "bndl_icon256px.png")
    if os.path.exists(icon_path):
        custom_icons.load("bndl_logo", icon_path, 'IMAGE')
        print("[BNDL] Custom icon loaded")
    else:
        print(f"[BNDL] Warning: Icon not found at {icon_path}")
    
    # Print version info
    version_str = "BNDL Lite v1.4.0 - Materials Only" if BNDL_LITE_VERSION else "BNDL Pro v1.4.0"
    print(f"[BNDL] {version_str}")
    
    # Register modules
    for m in modules:
        importlib.reload(m)
        if hasattr(m, "register"):
            m.register()
    
    # Load preferences from JSON after all modules are registered
    try:
        prefs_dict, source = pref_manager.load_preferences()
        pref_manager.apply_preferences_to_addon(prefs_dict)
        print(f"[BNDL] Initialized with {source} preferences")
        
        # Auto-validate Lite license on startup
        if BNDL_LITE_VERSION:
            try:
                from . import license as lic
                print("[BNDL Lite] Validating materials-only license...")
                if lic.validate_license_key(LITE_LICENSE_KEY, email=LITE_LICENSE_EMAIL, is_lite=True):
                    print("[BNDL Lite] ✓ Materials export/replay activated")
                else:
                    print("[BNDL Lite] ✗ License validation failed")
            except Exception as e:
                print(f"[BNDL Lite] License error: {e}")
        
        # Restore persistent license status from cache (Pro version)
        elif not BNDL_LITE_VERSION:
            try:
                from . import license as lic
                lic.restore_license_status()
            except Exception as e:
                print(f"[BNDL] Could not restore license status: {e}")
        
        # Silently validate studio license if present (Pro version)
        if source == "STUDIO" and not BNDL_LITE_VERSION:
            try:
                from . import license as lic
                lic.validate_studio_license_silently()
            except Exception as e:
                print(f"[BNDL] Could not validate studio license: {e}")
                
    except Exception as e:
        print(f"[BNDL] Warning: Could not load preferences: {e}")
    
    # Trigger initial library refresh on addon enable
    try:
        # Use a timer to delay refresh until after full registration
        bpy.app.timers.register(lambda: _delayed_initial_refresh(), first_interval=0.1)
    except Exception as e:
        print(f"[BNDL] Could not schedule initial refresh: {e}")

def _delayed_initial_refresh():
    """Delayed refresh after addon registration completes."""
    try:
        from .prefs import get_prefs
        prefs = get_prefs()
        has_dirs = hasattr(prefs, "bndl_directories") and prefs.bndl_directories
        
        if has_dirs:
            bpy.ops.bndl.list_refresh('INVOKE_DEFAULT')  # type: ignore
            print("[BNDL] Library refreshed on addon enable")
    except Exception as e:
        print(f"[BNDL] Initial refresh failed: {e}")
    return None  # Don't repeat the timer

def unregister():
    global custom_icons
    
    # Unregister modules
    for m in reversed(modules):
        if hasattr(m, "unregister"):
            m.unregister()
    
    # Remove custom icons
    if custom_icons:
        bpy.utils.previews.remove(custom_icons)
        custom_icons = None
