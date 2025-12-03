import bpy  # type: ignore
from bpy.types import Panel  # type: ignore
from .helpers import import_vendor

# Global set to track scenes that have been auto-refreshed (avoids modifying blend data during draw)
_auto_refreshed_scenes = set()

class BNDL_PT_Main(Panel):
    bl_label = "BNDL"
    bl_idname = "BNDL_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BNDL"

    def draw(self, ctx):
        # Translation helper (lazy import to avoid circular dependencies)
        try:
            from . import i18n_utils as i18n
            def _(key, category='UI'):
                if i18n is None:
                    return key
                result = i18n.get_text(category, key)
                return result if result else key
        except:
            def _(key, category='UI'):
                return key
        
        layout = self.layout
        # Replay is always available via tree-type-specific modules
        # (replay_geometry, replay_material, replay_compositor)
        
        # Show hint if list is empty
        prefs = ctx.preferences.addons[__package__].preferences
        has_dirs = hasattr(prefs, "bndl_directories") and prefs.bndl_directories
        scn = ctx.scene
        
        # Check if list is empty
        list_is_empty = not hasattr(scn, "bndl_items") or len(scn.bndl_items) == 0
        
        # Auto-refresh if list is empty but directories are configured
        if list_is_empty and has_dirs:
            try:
                # Only refresh if we haven't already tried for this scene recently
                scene_id = id(scn)
                if scene_id not in _auto_refreshed_scenes:
                    _auto_refreshed_scenes.add(scene_id)
                    # Schedule refresh after draw to avoid modifying data during rendering
                    def delayed_refresh():
                        try:
                            bpy.ops.bndl.list_refresh('EXEC_DEFAULT')  # type: ignore
                            print("[BNDL] Auto-refreshed empty list in UI (delayed)")
                        except Exception as e:
                            print(f"[BNDL] Delayed auto-refresh failed: {e}")
                    bpy.app.timers.register(delayed_refresh, first_interval=0.1)
                    # Re-check if list is now populated (though it won't be immediate)
                    list_is_empty = not hasattr(scn, "bndl_items") or len(scn.bndl_items) == 0
            except Exception as e:
                print(f"[BNDL] Auto-refresh scheduling failed: {e}")

        # Exporter
        box = layout.box()  # type: ignore
        box.label(text=_("Export Node Trees"))
        
        # Check if Lite version (check build configuration)
        import sys
        package_name = __package__.split('.')[0]
        package_module = sys.modules.get(package_name)
        is_lite = getattr(package_module, 'BNDL_LITE_VERSION', False) if package_module else False
        
        # Three export buttons
        row = box.row(align=True)
        # Geometry - disabled in Lite
        if is_lite:
            geo_row = box.row(align=True)
            geo_row.enabled = False
            geo_row.operator("bndl.export_active_tree", icon='GEOMETRY_NODES', text=_("Geometry"))
            # Material - enabled
            mat_row = box.row(align=True)
            mat_row.operator("bndl.export_material", icon='MATERIAL', text=_("Material"))
            # Compositor - disabled in Lite
            comp_row = box.row(align=True)
            comp_row.enabled = False
            comp_row.operator("bndl.export_compositor", icon='NODE_COMPOSITING', text=_("Compositor"))
            # Upgrade message
            info_row = box.row()
            info_row.scale_y = 0.7
            info_row.label(text="Geometry & Compositor require BNDL Pro", icon='INFO')
            upgrade_row = box.row()
            upgrade_row.scale_y = 0.9
            op = upgrade_row.operator("wm.url_open", text="Upgrade to Pro", icon='URL')
            op.url = "https://kyoseigk.gumroad.com"
        else:
            # Pro version - add proper tooltip for Geometry button
            geo_op = row.operator("bndl.export_active_tree", icon='GEOMETRY_NODES', text=_("Geometry"))
            # TODO: Add proper tooltip/description for Geometry export operator
            row.operator("bndl.export_material", icon='MATERIAL', text=_("Material"))
            row.operator("bndl.export_compositor", icon='NODE_COMPOSITING', text=_("Compositor"))
        
        
        # Batch export buttons
        box.separator()
        if is_lite:
            mat_batch_row = box.row(align=True)
            mat_batch_row.operator("bndl.batch_export_materials", icon='MATERIAL', text=_("Batch: Materials"))
            geo_batch_row = box.row(align=True)
            geo_batch_row.enabled = False
            geo_batch_row.operator("bndl.batch_export_selected", icon='GEOMETRY_NODES', text=_("Batch: Geo Nodes"))
        else:
            row = box.row(align=True)
            row.operator("bndl.batch_export_materials", icon='MATERIAL', text=_("Batch: Materials"))
            row.operator("bndl.batch_export_selected", icon='GEOMETRY_NODES', text=_("Batch: Geo Nodes"))
        
        # Show Pro status if asset bundling is enabled
        from . import license as lic
        is_pro = lic.is_pro_version()
        if prefs.asset_dependency_mode == 'APPEND_ASSETS':
            info_row = box.row()
            info_row.scale_y = 0.8
            if is_pro:
                info_row.label(text=_("Asset bundling: Active") + " ✓", icon='CHECKMARK')
            else:
                info_row.alert = True
                info_row.label(text=_("Asset bundling: Pro license required"), icon='LOCKED')

        # Library
        box = layout.box()  # type: ignore
        header_row = box.row()
        header_row.label(text=_("BNDL Library"))
        if not is_pro and hasattr(prefs, "bndl_directories") and len(prefs.bndl_directories) > 1:
            header_row.label(text="[" + _("Pro: Multi-project") + "]", icon='LOCKED')
        
        # Project filter dropdown (always show if multiple directories OR any directories configured)
        if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
            row = box.row()
            row.prop(scn, "bndl_project_filter", text="", icon='FILE_FOLDER')
        
        # Search row
        row = box.row(align=True)
        row.prop(scn, "bndl_search", text="", icon='VIEWZOOM')
        # Clear search button (only show if there's text)
        if scn.bndl_search:
            row.operator("bndl.clear_search", text="", icon='X')
        
        row.operator("bndl.list_refresh", text="", icon='FILE_REFRESH')
        row.operator("bndl.reveal_export_dir", text="", icon='FILE_FOLDER')

        # Type filter toggles
        filter_row = box.row(align=True)
        filter_row.label(text="Show:")
        filter_row.prop(scn, "bndl_show_all_types", text="", icon='CHECKBOX_HLT', toggle=True)
        filter_row.prop(scn, "bndl_show_materials", text="", icon='MATERIAL', toggle=True)
        # Disable Geometry/Compositor filters in Lite
        if is_lite:
            geo_col = filter_row.column(align=True)
            geo_col.enabled = False
            geo_col.prop(scn, "bndl_show_geometry", text="", icon='GEOMETRY_NODES', toggle=True)
            comp_col = filter_row.column(align=True)
            comp_col.enabled = False
            comp_col.prop(scn, "bndl_show_compositor", text="", icon='NODE_COMPOSITING', toggle=True)
        else:
            filter_row.prop(scn, "bndl_show_geometry", text="", icon='GEOMETRY_NODES', toggle=True)
            filter_row.prop(scn, "bndl_show_compositor", text="", icon='NODE_COMPOSITING', toggle=True)

        if not has_dirs:
            warn = box.row()
            warn.alert = True
            warn.label(text=_("Add project directories in Add-on Preferences."))
        elif list_is_empty:
            # Show hint to refresh if list is empty but directories are configured
            hint = box.row()
            hint.label(text=_("↻ Refresh list or choose project to show BNDL files"), icon='INFO')

        # List
        list_row = box.row()
        list_row.template_list(
            "BNDL_UL_bundles", "",  # UIList ID
            scn, "bndl_items",       # Data source
            scn, "bndl_index",       # Active index
            rows=6,
            type='DEFAULT'           # Use default list type
        )
        
        # File operations menu (next to the list)
        list_row.menu("BNDL_MT_file_context_menu", text="", icon='DOWNARROW_HLT')

        # Global replay options
        box.prop(ctx.scene, "bndl_reuse_proxies", text=_("Reuse proxies for missing datablocks"))
        box.prop(ctx.scene, "bndl_create_as_new", text=_("Create as New (unique names)"))

        # Actions
        row = box.row(align=True)
        row.operator("bndl.apply_from_list", icon='PLAY', text=_("Apply to Selection"))

        # ─── REPLAYER SECTION (Pro only) ───
        if not is_lite:
            box = layout.box()  # type: ignore
            box.label(text=_("Direct Replayer"))
            
            # Direct replay button (auto-detect)
            col = box.column(align=True)
            row = col.row()
            row.operator("bndl.replay_generic", icon='PLAY', text=_("Direct Replay"))
        
        # Documentation button
        layout.separator()  # type: ignore
        row = layout.row()  # type: ignore
        row.scale_y = 1.5
        row.operator("bndl.show_documentation", text=_("Documentation"), icon='HELP')


# ─── NODE EDITOR PANELS (Shader, Geometry Nodes, Compositor) ───

class BNDL_PT_ShaderEditor(Panel):
    """BNDL panel for Shader Editor"""
    bl_label = "BNDL"
    bl_idname = "BNDL_PT_shader_editor"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "BNDL"
    
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'  # type: ignore
    
    def draw(self, context):
        # Reuse the main panel draw function
        BNDL_PT_Main.draw(self, context)  # type: ignore


class BNDL_PT_GeometryNodes(Panel):
    """BNDL panel for Geometry Nodes Editor"""
    bl_label = "BNDL"
    bl_idname = "BNDL_PT_geometry_nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "BNDL"
    
    @classmethod
    def poll(cls, context):
        # Hide in Lite version
        from . import __init__ as main
        if hasattr(main, 'BNDL_LITE_VERSION') and main.BNDL_LITE_VERSION:
            return False
        return context.space_data.tree_type == 'GeometryNodeTree'  # type: ignore
    
    def draw(self, context):
        # Reuse the main panel draw function
        BNDL_PT_Main.draw(self, context)  # type: ignore


class BNDL_PT_Compositor(Panel):
    """BNDL panel for Compositor"""
    bl_label = "BNDL"
    bl_idname = "BNDL_PT_compositor"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "BNDL"
    
    @classmethod
    def poll(cls, context):
        # Hide in Lite version
        from . import __init__ as main
        if hasattr(main, 'BNDL_LITE_VERSION') and main.BNDL_LITE_VERSION:
            return False
        return context.space_data.tree_type == 'CompositorNodeTree'  # type: ignore
    
    def draw(self, context):
        # Reuse the main panel draw function
        BNDL_PT_Main.draw(self, context)  # type: ignore


def register():
    bpy.utils.register_class(BNDL_PT_Main)
    bpy.utils.register_class(BNDL_PT_ShaderEditor)
    bpy.utils.register_class(BNDL_PT_GeometryNodes)
    bpy.utils.register_class(BNDL_PT_Compositor)

def unregister():
    bpy.utils.unregister_class(BNDL_PT_Compositor)
    bpy.utils.unregister_class(BNDL_PT_GeometryNodes)
    bpy.utils.unregister_class(BNDL_PT_ShaderEditor)
    bpy.utils.unregister_class(BNDL_PT_Main)
