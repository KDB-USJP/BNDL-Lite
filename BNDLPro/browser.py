# bndl_addon/browser.py
import os
import bpy
from bpy.types import PropertyGroup, Operator, UIList
from bpy.props import CollectionProperty, StringProperty, IntProperty, EnumProperty, BoolProperty
from .prefs import get_prefs
from .helpers import reveal_in_explorer, import_vendor

# ---------- Data Model ----------

class BNDL_Item(PropertyGroup):
    display_name: StringProperty(name="Name")
    abs_path: StringProperty(name="Path")

# ---------- Scene State ----------

def _ensure_scene_props():
    scn = bpy.context.scene
    if "bndl_items" not in scn:
        scn["bndl_items"] = []
    return scn

def _on_search_update(self, context):
    """Callback when search text changes - trigger UI redraw."""
    # Just tag for redraw - no operator call needed
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def _on_project_filter_update(self, context):
    """Callback when project filter changes - need to reload from different directory."""
    bpy.ops.bndl.list_refresh('EXEC_DEFAULT')

def _on_filter_update(self, context):
    """Callback when type filter toggles change - update master state and trigger UI redraw."""
    # Update master filter state based on individual toggles
    _update_master_filter_state(context)
    
    # Trigger UI redraw
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def _on_master_filter_update(self, context):
    """Callback when master filter toggle changes - set all individual toggles."""
    master_state = getattr(context.scene, "bndl_show_all_types", True)
    
    # Set all individual toggles to match master state
    context.scene.bndl_show_materials = master_state
    context.scene.bndl_show_geometry = master_state
    context.scene.bndl_show_compositor = master_state
    
    # Trigger UI redraw
    _on_filter_update(self, context)

def _update_master_filter_state(context):
    """Update master filter state based on individual toggles."""
    materials = getattr(context.scene, "bndl_show_materials", True)
    geometry = getattr(context.scene, "bndl_show_geometry", True)
    compositor = getattr(context.scene, "bndl_show_compositor", True)
    
    # Master is on if all individual toggles are on
    master_state = materials and geometry and compositor
    
    # Update master toggle without triggering callback
    if hasattr(context.scene, "bndl_show_all_types"):
        context.scene["bndl_show_all_types"] = master_state

def _initial_refresh_handler(scene):
    """Load handler to auto-refresh list on file load."""
    # Trigger one refresh if directory is configured
    try:
        from .prefs import get_prefs
        prefs = get_prefs()
        has_dirs = hasattr(prefs, "bndl_directories") and prefs.bndl_directories
        
        if has_dirs and scene:
            # Check if list is empty or not initialized
            if not hasattr(scene, "bndl_items") or len(scene.bndl_items) == 0:
                # Use a timer to defer refresh until UI is ready
                bpy.app.timers.register(lambda: _deferred_refresh(), first_interval=0.1)
                print("[BNDL] Scheduled auto-refresh for library")
    except Exception as e:
        print(f"[BNDL] Could not schedule auto-refresh: {e}")

def _deferred_refresh():
    """Deferred refresh function executed via timer."""
    try:
        bpy.ops.bndl.list_refresh('EXEC_DEFAULT')
        print("[BNDL] Auto-refreshed library")
    except Exception as e:
        print(f"[BNDL] Auto-refresh failed: {e}")
    return None  # Don't repeat timer

def _get_project_filter_items(self, context):
    """Generate dynamic enum items for project filter dropdown."""
    items = [('ALL', "All Projects", "Show .bndl files from all configured directories", 'WORLD', 0)]
    
    prefs = get_prefs()
    if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
        for idx, item in enumerate(prefs.bndl_directories, start=1):
            if item.name and item.directory:
                items.append((item.name, item.name, f"Show .bndl files from {item.directory}", 'FILE_FOLDER', idx))
    
    return items

def _list_bndl_files(root_dir: str, search: str, recursive: bool = True):
    """Yield (name, abs_path) for *.bndl in root_dir.
    If recursive=True, searches subdirectories as well.
    NOTE: search parameter is no longer used - filtering now happens in UIList.filter_items()"""
    if not root_dir or not os.path.isdir(root_dir):
        return []
    try:
        entries = []
        
        if recursive:
            # Walk through all subdirectories
            for dirpath, dirnames, filenames in os.walk(root_dir):
                for fn in filenames:
                    if not fn.lower().endswith(".bndl"):
                        continue
                    # No longer filter by search here - UIList handles it
                    p = os.path.join(dirpath, fn)
                    
                    # Create relative display name showing subdirectory structure
                    rel_path = os.path.relpath(p, root_dir)
                    display_name = rel_path.replace(os.sep, ' / ')
                    
                    entries.append((display_name, p))
        else:
            # Original non-recursive behavior
            for fn in os.listdir(root_dir):
                if not fn.lower().endswith(".bndl"):
                    continue
                # No longer filter by search here - UIList handles it
                p = os.path.join(root_dir, fn)
                entries.append((fn, p))
        
        entries.sort(key=lambda t: t[0].lower())
        return entries
    except Exception:
        return []

# ---------- Operators ----------

class BNDL_OT_ListRefresh(Operator):
    bl_idname = "bndl.list_refresh"
    bl_label  = "Refresh BNDL List"
    bl_options = {"INTERNAL"}

    def execute(self, ctx):
        scn = ctx.scene
        prefs = get_prefs()
        
        # Determine which directories to search
        project_filter = scn.bndl_project_filter if hasattr(scn, "bndl_project_filter") else "ALL"
        
        # Get directory list from preferences
        root_dirs = []
        if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
            if project_filter == "ALL":
                root_dirs = [bpy.path.abspath(item.directory) for item in prefs.bndl_directories if item.directory]
            else:
                # Filter by specific project
                for item in prefs.bndl_directories:
                    if item.name == project_filter and item.directory:
                        root_dirs = [bpy.path.abspath(item.directory)]
                        break
        
        # Validate directories - filter out empty strings and non-existent paths
        valid_dirs = [d for d in root_dirs if d and os.path.isdir(d)]
        
        if not valid_dirs:
            # Check if project filter is active but directory doesn't exist
            if project_filter != "ALL":
                self.report({'WARNING'}, f"Directory not found for project '{project_filter}'. Check preferences.")
            else:
                self.report({'ERROR'}, "No project directories configured. Add directories in Preferences > BNDL Tools.")
            if hasattr(scn, "bndl_items"):
                scn.bndl_items.clear()
                scn.bndl_index = 0
            return {"CANCELLED"}
        
        # No longer pass search parameter - filtering happens in UIList
        search = ""  # Keep for potential future use, but UIList handles filtering now
        
        # Collect items from all valid directories
        all_items = []
        for root_dir in valid_dirs:
            items = _list_bndl_files(root_dir, search, recursive=True)
            all_items.extend(items)
        
        # Remove duplicates based on abs_path
        seen_paths = set()
        unique_items = []
        for item in all_items:
            if item[1] not in seen_paths:
                seen_paths.add(item[1])
                unique_items.append(item)
        
        unique_items.sort(key=lambda t: t[0].lower())

        scn.bndl_items.clear()
        for name, path in unique_items:
            it = scn.bndl_items.add()
            it.display_name = name
            it.abs_path = path
        scn.bndl_index = min(scn.bndl_index, max(0, len(scn.bndl_items)-1))
        return {"FINISHED"}

class BNDL_OT_RevealDir(Operator):
    bl_idname = "bndl.reveal_export_dir"
    bl_label  = "Open Export Folder"
    bl_options = {"INTERNAL"}

    def execute(self, ctx):
        prefs = get_prefs()
        scn = ctx.scene
        
        # Get the currently filtered project
        project_filter = scn.bndl_project_filter if hasattr(scn, "bndl_project_filter") else "ALL"
        
        # Find the directory to open
        root = ""
        if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
            if project_filter == "ALL" and prefs.bndl_directories:
                # Open the first project directory if showing all
                root = bpy.path.abspath(prefs.bndl_directories[0].directory)
            else:
                # Open the filtered project's directory
                for item in prefs.bndl_directories:
                    if item.name == project_filter:
                        root = bpy.path.abspath(item.directory)
                        break
        
        if not root:
            self.report({'WARNING'}, "No project directory configured.")
            return {"CANCELLED"}
        
        reveal_in_explorer(root if root else "")
        return {"FINISHED"}

class BNDL_OT_ClearSearch(Operator):
    bl_idname = "bndl.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear search filter and show all files"
    bl_options = {"INTERNAL"}
    
    def execute(self, ctx):
        ctx.scene.bndl_search = ""
        # No refresh needed - UIList will automatically update via filter_items()
        return {"FINISHED"}

# ---------- Context Menu Operators ----------

class BNDL_OT_DeleteFile(Operator):
    bl_idname = "bndl.delete_file"
    bl_label = "Delete File"
    bl_description = "Delete the selected .bndl file from disk"
    bl_options = {"REGISTER", "UNDO"}
    
    filepath: StringProperty(name="File Path")
    
    def invoke(self, context, event):
        # Show confirmation dialog
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, ctx):
        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
        
        try:
            # Get base filename without extension
            base_path = os.path.splitext(self.filepath)[0]
            dirname = os.path.dirname(self.filepath)
            
            # Track what files we delete
            deleted_files = []
            
            # Delete the main .bndl file
            os.remove(self.filepath)
            deleted_files.append(os.path.basename(self.filepath))
            
            # Look for and delete associated .blend file
            blend_path = base_path + ".blend"
            if os.path.exists(blend_path):
                os.remove(blend_path)
                deleted_files.append(os.path.basename(blend_path))
            
            # Look for and delete associated .bndlpack file
            bndlpack_path = base_path + ".bndlpack"
            if os.path.exists(bndlpack_path):
                os.remove(bndlpack_path)
                deleted_files.append(os.path.basename(bndlpack_path))
            
            # Report what was deleted
            if len(deleted_files) == 1:
                self.report({'INFO'}, f"Deleted: {deleted_files[0]}")
            else:
                self.report({'INFO'}, f"Deleted: {', '.join(deleted_files)}")
            
            # Refresh the list
            bpy.ops.bndl.list_refresh('EXEC_DEFAULT')
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete file: {e}")
            return {'CANCELLED'}

class BNDL_OT_ToggleFavoriteContext(Operator):
    bl_idname = "bndl.toggle_favorite_context"
    bl_label = "Toggle Favorite"
    bl_description = "Add or remove this file from favorites"
    bl_options = {"INTERNAL"}
    
    filepath: StringProperty(name="File Path")
    
    def execute(self, ctx):
        from . import favorites_utils
        
        if not self.filepath:
            return {'CANCELLED'}
        
        try:
            if favorites_utils.is_favorite(self.filepath):
                favorites_utils.toggle_favorite(self.filepath)  # This will remove it
                self.report({'INFO'}, "Removed from favorites")
            else:
                favorites_utils.toggle_favorite(self.filepath)  # This will add it
                self.report({'INFO'}, "Added to favorites")
            
            # Trigger UI redraw to update star icons
            for window in ctx.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                        
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to toggle favorite: {e}")
            return {'CANCELLED'}

class BNDL_OT_OpenInFilesystem(Operator):
    bl_idname = "bndl.open_in_filesystem"
    bl_label = "Open in File Explorer"
    bl_description = "Open the file location in your system's file explorer"
    bl_options = {"INTERNAL"}
    
    filepath: StringProperty(name="File Path")
    
    def execute(self, ctx):
        if not self.filepath:
            return {'CANCELLED'}
        
        try:
            # Get directory containing the file
            directory = os.path.dirname(self.filepath)
            reveal_in_explorer(directory)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open file location: {e}")
            return {'CANCELLED'}

# ---------- Context Menu ----------

class BNDL_MT_FileContextMenu(bpy.types.Menu):
    bl_label = "BNDL File Options"
    bl_idname = "BNDL_MT_file_context_menu"
    
    def draw(self, context):
        layout = self.layout
        
        # Get the active item from the scene
        scene = context.scene
        if not hasattr(scene, "bndl_items") or not hasattr(scene, "bndl_index"):
            return
            
        active_index = scene.bndl_index
        if active_index < 0 or active_index >= len(scene.bndl_items):
            return
            
        item = scene.bndl_items[active_index]
        
        # Apply to selection (existing functionality)
        layout.operator("bndl.apply_from_list", icon='PLAY', text="Apply to Selection")
        layout.separator()
        
        # Favorite toggle
        from . import favorites_utils
        is_fav = favorites_utils.is_favorite(item.abs_path)
        fav_op = layout.operator("bndl.toggle_favorite_context", 
                                icon='SOLO_ON' if is_fav else 'SOLO_OFF',
                                text="Remove from Favorites" if is_fav else "Add to Favorites")
        fav_op.filepath = item.abs_path
        
        # Open in filesystem
        open_op = layout.operator("bndl.open_in_filesystem", icon='FILE_FOLDER', text="Open in File Explorer")
        open_op.filepath = item.abs_path
        
        layout.separator()
        
        # Delete with confirmation (only if allowed by preferences)
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
            if prefs.allow_file_delete:
                del_op = layout.operator("bndl.delete_file", icon='TRASH', text="Delete File")
                del_op.filepath = item.abs_path
        except:
            pass  # Silently fail if preferences access fails

# This wraps the existing apply operator with the currently selected list item.
class BNDL_OT_ApplyFromList(Operator):
    bl_idname = "bndl.apply_from_list"
    bl_label  = "Apply Selected .bndl"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, ctx):
        from . import favorites_utils
        
        scn = ctx.scene
        if not scn.bndl_items or scn.bndl_index < 0 or scn.bndl_index >= len(scn.bndl_items):
            self.report({'ERROR'}, "No .bndl selected.")
            return {'CANCELLED'}

        if import_vendor("bndl2py_geometry") is None:
            self.report({'ERROR'}, "Add vendor/bndl2py_geometry.py to enable replay.")
            return {'CANCELLED'}

        path = scn.bndl_items[scn.bndl_index].abs_path
        
        # Track this file in recent files
        try:
            favorites_utils.add_to_recent_files(path)
        except Exception as e:
            print(f"[BNDL] Could not add to recent files: {e}")
        
        try:
            # Use the main replay operator
            result = bpy.ops.bndl.replay_generic('EXEC_DEFAULT', bndl_path=path)  # type: ignore
            return result
        except Exception as e:
            self.report({'ERROR'}, f"Replay op failed: {e}")
            return {'CANCELLED'}

# ---------- UI List ----------
class BNDL_UL_Bundles(UIList):
    bl_idname = "BNDL_UL_bundles"

    def draw_item(self, ctx, layout, data, item, icon, active_data, active_propname, index):
        from . import favorites_utils
        
        # Use split layout to control proportions
        split = layout.split(factor=0.08, align=True)  # Star gets ~8% of width
        
        # Left side: Favorite star button
        left = split.row(align=True)
        is_fav = favorites_utils.is_favorite(item.abs_path)
        fav_icon = 'SOLO_ON' if is_fav else 'SOLO_OFF'
        fav_op = left.operator("bndl.toggle_favorite", text="", icon=fav_icon, emboss=False)
        fav_op.filepath = item.abs_path
        
        # Right side: Filename (left-aligned)
        right = split.row(align=True)
        right.alignment = 'LEFT'
        right.label(text=item.display_name)
    
    def filter_items(self, context, data, propname):
        """Filter items based on search text and type toggles - passive filtering (no UI rebuild).
        This handles BOTH our custom search box AND the built-in UIList filter box."""
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list
        
        # Get search string from our custom property (top search box)
        custom_search = context.scene.bndl_search.strip().lower() if hasattr(context.scene, "bndl_search") else ""
        
        # Get search string from built-in UIList filter (bottom search box)
        # The built-in filter is stored in self.filter_name
        builtin_search = self.filter_name.strip().lower() if hasattr(self, "filter_name") and self.filter_name else ""
        
        # Get type filter toggles
        show_materials = getattr(context.scene, "bndl_show_materials", True)
        show_geometry = getattr(context.scene, "bndl_show_geometry", True)
        show_compositor = getattr(context.scene, "bndl_show_compositor", True)
        
        # Combine both searches (both must match if both are active)
        has_custom = bool(custom_search)
        has_builtin = bool(builtin_search)
        has_type_filters = not (show_materials and show_geometry and show_compositor)
        
        # Initialize filter flags (all visible by default)
        flt_flags = [self.bitflag_filter_item] * len(items)
        flt_neworder = []
        
        # Apply filtering if any filters are active
        if has_custom or has_builtin or has_type_filters:
            for i, item in enumerate(items):
                name = item.display_name.lower()
                
                # Item must match both searches if both are active
                matches = True
                if has_custom and custom_search not in name:
                    matches = False
                if has_builtin and builtin_search not in name:
                    matches = False
                
                # Apply type filtering
                if has_type_filters:
                    # Apply type filters based on file prefix
                    if name.startswith('s-') and not show_materials:  # Changed from 'm-' to 's-' for shader/material files
                        matches = False
                    elif name.startswith('g-') and not show_geometry:
                        matches = False
                    elif name.startswith('c-') and not show_compositor:
                        matches = False
                    elif not (name.startswith('s-') or name.startswith('g-') or name.startswith('c-')):
                        # Files without prefixes are shown by default (as requested)
                        pass
                
                if not matches:
                    flt_flags[i] = 0  # Hide this item (remove filter flag)
        
        return flt_flags, flt_neworder

def _addon_load_refresh():
    """Refresh function executed on addon registration (not just file load)."""
    try:
        print("[BNDL] Starting addon load refresh...")
        
        # Only refresh if directories are configured and list is empty
        from .prefs import get_prefs
        prefs = get_prefs()
        has_dirs = hasattr(prefs, "bndl_directories") and prefs.bndl_directories
        
        print(f"[BNDL] Has directories configured: {has_dirs}")
        
        if has_dirs:
            # Get current scene
            scene = bpy.context.scene if bpy.context else None
            print(f"[BNDL] Context exists: {bpy.context is not None}")
            print(f"[BNDL] Scene exists: {scene is not None}")
            
            if scene:
                has_items = hasattr(scene, "bndl_items")
                items_empty = len(scene.bndl_items) == 0 if has_items else True
                print(f"[BNDL] Scene has bndl_items: {has_items}")
                print(f"[BNDL] Items are empty: {items_empty}")
                
                if has_items and items_empty:
                    print("[BNDL] Executing list refresh...")
                    result = bpy.ops.bndl.list_refresh('EXEC_DEFAULT')
                    print(f"[BNDL] Refresh result: {result}")
                    print(f"[BNDL] Items after refresh: {len(scene.bndl_items)}")
                    print("[BNDL] Auto-refreshed library on addon load")
                else:
                    print("[BNDL] Skipping refresh - items not empty or bndl_items not initialized")
            else:
                print("[BNDL] Skipping refresh - no scene available")
        else:
            print("[BNDL] Skipping refresh - no directories configured")
    except Exception as e:
        print(f"[BNDL] Addon load refresh failed: {e}")
        import traceback
        traceback.print_exc()

# ---------- Registration ----------

classes = (
    BNDL_Item,
    BNDL_OT_ListRefresh,
    BNDL_OT_RevealDir,
    BNDL_OT_ClearSearch,
    BNDL_OT_ApplyFromList,
    BNDL_OT_DeleteFile,
    BNDL_OT_ToggleFavoriteContext,
    BNDL_OT_OpenInFilesystem,
    BNDL_MT_FileContextMenu,
    BNDL_UL_Bundles,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.bndl_items = CollectionProperty(type=BNDL_Item)
    bpy.types.Scene.bndl_index = IntProperty(default=0)
    bpy.types.Scene.bndl_search = StringProperty(
        name="Search", 
        default="",
        description="Filter .bndl files by name (type to filter - no refresh needed)",
        update=_on_search_update
    )
    bpy.types.Scene.bndl_project_filter = EnumProperty(
        name="Project",
        items=_get_project_filter_items,
        update=_on_project_filter_update,
        description="Filter by project directory"
    )
    
    # Type filter toggles - default to False for Geometry/Compositor in Lite
    # Check if Lite version
    import sys
    package_name = __package__.split('.')[0]
    package_module = sys.modules.get(package_name)
    is_lite = getattr(package_module, 'BNDL_LITE_VERSION', False) if package_module else False
    
    bpy.types.Scene.bndl_show_materials = BoolProperty(
        name="Show Materials",
        default=True,
        description="Show/Hide Shader/Material BNDLs (S- prefix)",
        update=_on_filter_update
    )
    bpy.types.Scene.bndl_show_geometry = BoolProperty(
        name="Show Geometry Nodes", 
        default=False if is_lite else True,  # Default to False in Lite
        description="Show/Hide Geometry Node BNDLs (G- prefix)",
        update=_on_filter_update
    )
    bpy.types.Scene.bndl_show_compositor = BoolProperty(
        name="Show Compositor",
        default=False if is_lite else True,  # Default to False in Lite
        description="Show/Hide Compositor BNDLs (C- prefix)",
        update=_on_filter_update
    )
    
    bpy.types.Scene.bndl_show_all_types = BoolProperty(
        name="Show All Types",
        description="Master toggle to show/hide all BNDL file types (Materials, Geometry, Compositor)",
        default=True,
        update=_on_master_filter_update
    )
    
    # Register load handler for initial refresh
    if _initial_refresh_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_initial_refresh_handler)
    
    # Note: Auto-refresh now happens in UI draw() method when panel is first displayed

def unregister():
    # Remove load handler
    if _initial_refresh_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_initial_refresh_handler)
    
    for attr in ("bndl_items", "bndl_index", "bndl_search", "bndl_project_filter", "bndl_show_materials", "bndl_show_geometry", "bndl_show_compositor", "bndl_show_all_types"):
        if hasattr(bpy.types.Scene, attr):
            delattr(bpy.types.Scene, attr)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
