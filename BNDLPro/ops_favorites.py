"""
Operators for favorites and recent files functionality.
"""

import bpy  # type: ignore
import os
from bpy.types import Operator, Menu  # type: ignore
from bpy.props import StringProperty  # type: ignore
from . import favorites_utils


class BNDL_OT_ToggleFavorite(Operator):
    """Toggle favorite status for the selected .bndl file"""
    bl_idname = "bndl.toggle_favorite"
    bl_label = "Toggle Favorite"
    bl_description = "Add or remove this file from favorites"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to the .bndl file",
        default=""
    )  # type: ignore
    
    def execute(self, context):
        if not self.filepath:
            self.report({'WARNING'}, "No file path provided")
            return {'CANCELLED'}
        
        is_fav = favorites_utils.toggle_favorite(self.filepath)
        filename = os.path.basename(self.filepath)
        
        if is_fav:
            self.report({'INFO'}, f"Added '{filename}' to favorites")
        else:
            self.report({'INFO'}, f"Removed '{filename}' from favorites")
        
        return {'FINISHED'}


class BNDL_OT_ApplyFromPath(Operator):
    """Apply a .bndl file from a given path"""
    bl_idname = "bndl.apply_from_path"
    bl_label = "Apply .bndl"
    bl_description = "Apply a .bndl file to selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to the .bndl file",
        default=""
    )  # type: ignore
    
    def execute(self, context):
        if not self.filepath:
            self.report({'WARNING'}, "No file path provided")
            return {'CANCELLED'}
        
        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, f"File not found: {self.filepath}")
            return {'CANCELLED'}
        
        # Add to recent files
        favorites_utils.add_to_recent_files(self.filepath)
        
        # Call the main replay operator with the file path
        try:
            from .helpers import import_vendor
            if import_vendor("bndl2py_geometry") is None:
                self.report({'ERROR'}, "Add vendor/bndl2py_geometry.py to enable replay.")
                return {'CANCELLED'}
            
            # Use the main replay operator
            result = bpy.ops.bndl.replay_generic('EXEC_DEFAULT', bndl_path=self.filepath)  # type: ignore
            
            if result == {'FINISHED'}:
                filename = os.path.basename(self.filepath)
                self.report({'INFO'}, f"Applied '{filename}' to selection")
            
            return result
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply .bndl: {str(e)}")
            return {'CANCELLED'}


class BNDL_OT_CleanMissingFavorites(Operator):
    """Remove favorites for files that no longer exist"""
    bl_idname = "bndl.clean_missing_favorites"
    bl_label = "Clean Missing Favorites"
    bl_description = "Remove favorite files that no longer exist on disk"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        removed_count = favorites_utils.clean_missing_favorites()
        
        if removed_count > 0:
            self.report({'INFO'}, f"Removed {removed_count} missing favorite(s)")
        else:
            self.report({'INFO'}, "No missing favorites found")
        
        return {'FINISHED'}




class BNDL_MT_QuickAccess(Menu):
    """Context menu for quick access to recent files and favorites"""
    bl_idname = "BNDL_MT_quick_access"
    bl_label = "BNDL Quick Access"
    bl_description = "Recently used files and favorites"
    
    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__package__].preferences  # type: ignore
        
        # Get recent files and favorites
        recent_files = favorites_utils.get_recent_files()
        favorites = favorites_utils.get_favorites()
        
        # RECENT FILES FIRST (at top, most recent first)
        if recent_files:
            layout.label(text=f"Recent Files ({len(recent_files)}):", icon='TIME')  # type: ignore
            for filepath, filename, timestamp in recent_files:
                # Show star icon if it's also a favorite
                icon = 'SOLO_ON' if favorites_utils.is_favorite(filepath) else 'FILE'
                op = layout.operator("bndl.apply_from_path", text=filename, icon=icon)  # type: ignore
                op.filepath = filepath
            
            # Separator between sections if we have both
            if favorites:
                layout.separator()  # type: ignore
        
        # FAVORITES BELOW RECENTS
        if favorites:
            layout.label(text=f"Favorites ({len(favorites)}):", icon='SOLO_ON')  # type: ignore
            for filepath, filename in favorites:
                op = layout.operator("bndl.apply_from_path", text=filename, icon='SOLO_ON')  # type: ignore
                op.filepath = filepath
            layout.separator()  # type: ignore
        
        # No files message
        if not favorites and not recent_files:
            layout.label(text="No recent files or favorites", icon='INFO')  # type: ignore
            layout.separator()  # type: ignore
        
        # Utility options
        layout.operator("bndl.clean_missing_favorites", text="Clean Missing Favorites", icon='TRASH')  # type: ignore


def draw_quick_access_menu(self, context):
    """Add BNDL submenu to 3D View context menu"""
    layout = self.layout
    layout.separator()
    layout.menu("BNDL_MT_quick_access", text="BNDL", icon='NODETREE')


def register():
    """Register operators and menu"""
    bpy.utils.register_class(BNDL_OT_ToggleFavorite)
    bpy.utils.register_class(BNDL_OT_ApplyFromPath)
    bpy.utils.register_class(BNDL_OT_CleanMissingFavorites)
    bpy.utils.register_class(BNDL_MT_QuickAccess)
    
    # Add menu to 3D View context menu
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_quick_access_menu)


def unregister():
    """Unregister operators and menu"""
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_quick_access_menu)
    
    bpy.utils.unregister_class(BNDL_MT_QuickAccess)
    bpy.utils.unregister_class(BNDL_OT_CleanMissingFavorites)
    bpy.utils.unregister_class(BNDL_OT_ApplyFromPath)
    bpy.utils.unregister_class(BNDL_OT_ToggleFavorite)
