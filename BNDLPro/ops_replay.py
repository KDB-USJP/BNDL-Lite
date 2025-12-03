# ops_replay.py — Dedicated replay operators for each tree type
# Separate operators for Geometry, Material, and Compositor replay

import bpy, os, zipfile, tempfile, shutil  # type: ignore
from bpy.types import Operator  # type: ignore
from bpy.props import StringProperty, EnumProperty, BoolProperty  # type: ignore
from .helpers import import_vendor
from .prefs import get_prefs
from .vendor.bndl_common import TreeType, parse_tree_type_header


# ============================================================================
# Asset Import Helpers (for APPEND_ASSETS mode)
# ============================================================================

def _extract_asset_refs_from_bndl(bndl_text: str) -> dict:
    """
    Parse .bndl text to find all asset references (⊞Object⊞, ❆Material❆, etc.)
    Returns dict mapping datablock type to set of names, e.g.:
    {'objects': {'GLX_Star', 'GLX_Core'}, 'materials': {'MatGlow'}}
    """
    import re
    
    # Sentinel patterns for each datablock type
    patterns = {
        'objects': r'⊞([^⊞]+)⊞',      # ⊞name⊞
        'materials': r'❆([^❆]+)❆',    # ❆name❆
        'collections': r'✸([^✸]+)✸',  # ✸name✸
        'images': r'✷([^✷]+)✷',       # ✷name✷
        'meshes': r'⧉([^⧉]+)⧉',       # ⧉name⧉
        'curves': r'𝒞([^𝒞]+)𝒞',       # 𝒞name𝒞
    }
    
    refs = {}
    for db_type, pattern in patterns.items():
        matches = re.findall(pattern, bndl_text)
        if matches:
            refs[db_type] = set(matches)
    
    return refs


def _append_assets_from_blend(blend_path: str, asset_filter: dict = None) -> tuple:
    """
    Append datablocks from a .blend file into the current scene.
    Returns (success: bool, message: str)
    
    Used for APPEND_ASSETS mode to bring in referenced Objects, Materials,
    Collections, Images, Meshes, Curves before replaying the node tree.
    
    If asset_filter is provided, only append assets whose names are in the filter.
    Otherwise, append ALL assets from the .blend file.
    """
    try:
        if not os.path.isfile(blend_path):
            return (False, f".blend file not found: {blend_path}")
        
        # Track what we append for reporting
        appended = []
        
        # Map of datablock types to bpy.data collections
        db_types = {
            'objects': bpy.data.objects,
            'materials': bpy.data.materials,
            'collections': bpy.data.collections,
            'images': bpy.data.images,
            'meshes': bpy.data.meshes,
            'curves': bpy.data.curves,
        }
        
        # Track object and collection names to link to scene after append
        obj_names_to_link = []
        coll_names_to_link = []
        
        # Append datablocks (link=False means append, not link)
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            # Append all available datablocks of each type (filtered if requested)
            for attr_name in db_types.keys():
                if hasattr(data_from, attr_name):
                    src_list = getattr(data_from, attr_name, [])
                    
                    # Filter to only referenced assets if filter provided
                    if asset_filter and attr_name in asset_filter:
                        filter_set = asset_filter[attr_name]
                        src_list = [name for name in src_list if name in filter_set]
                    
                    if src_list:
                        setattr(data_to, attr_name, src_list)
                        appended.extend([(attr_name.rstrip('s').title(), n) for n in src_list])
                        
                        # Capture names for scene linking (must do inside context)
                        if attr_name == 'objects':
                            obj_names_to_link.extend(src_list)
                        elif attr_name == 'collections':
                            coll_names_to_link.extend(src_list)
        
        print(f"[BNDL] Captured {len(obj_names_to_link)} object(s) and {len(coll_names_to_link)} collection(s) for linking")
        
        # Now link appended objects and collections to a dedicated collection
        # This keeps the Outliner organized and prevents top-level clutter
        scene_collection = bpy.context.scene.collection
        
        # Create or get the BNDL_Assets collection (unique name to avoid conflicts)
        bndl_coll_name = "BNDL_Assets"
        bndl_assets_coll = bpy.data.collections.get(bndl_coll_name)
        if bndl_assets_coll is None:
            bndl_assets_coll = bpy.data.collections.new(bndl_coll_name)
            scene_collection.children.link(bndl_assets_coll)
            print(f"[BNDL] Created {bndl_coll_name} collection")
        else:
            # Ensure it's linked to scene (might exist but not be linked)
            if bndl_coll_name not in scene_collection.children:
                scene_collection.children.link(bndl_assets_coll)
            print(f"[BNDL] Using existing {bndl_coll_name} collection")
        
        # Configure collection to be hidden (assets are for GN reference only)
        # Exclude from view layer so it doesn't render or clutter viewport
        try:
            layer_collection = bpy.context.view_layer.layer_collection.children.get(bndl_coll_name)
            if layer_collection:
                layer_collection.exclude = True  # Exclude from view layer (unchecks in outliner)
            
            # Set collection visibility flags
            bndl_assets_coll.hide_viewport = True    # Hide in viewport
            bndl_assets_coll.hide_render = True      # Disable in render
            print(f"[BNDL] Configured {bndl_coll_name} as hidden (GN reference only)")
        except Exception as e:
            print(f"[BNDL] Warning: Could not configure collection visibility: {e}")
        
        # Link objects to BNDL_Assets collection (not scene root)
        linked_objects = 0
        for obj_name in obj_names_to_link:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                try:
                    # Check if already linked to this collection
                    if obj.name not in bndl_assets_coll.objects:
                        bndl_assets_coll.objects.link(obj)
                        linked_objects += 1
                except Exception as e:
                    print(f"[BNDL] Warning: Could not link object {obj_name}: {e}")
        
        if linked_objects > 0:
            print(f"[BNDL] Linked {linked_objects} object(s) to {bndl_coll_name}")
        elif obj_names_to_link and linked_objects == 0:
            # Objects might already be organized in collections from source .blend
            print(f"[BNDL] Objects already linked to collections (from source .blend)")
        
        # Link sub-collections to BNDL_Assets collection (not scene root)
        # Skip any collection that has the same name as our container to avoid recursion
        linked_collections = 0
        for coll_name in coll_names_to_link:
            # Don't try to link our own collection to itself
            if coll_name == bndl_coll_name:
                print(f"[BNDL] Skipping self-reference: {coll_name}")
                continue
                
            coll = bpy.data.collections.get(coll_name)
            if coll:
                try:
                    # Check if already linked to this collection
                    if coll.name not in bndl_assets_coll.children:
                        bndl_assets_coll.children.link(coll)
                        linked_collections += 1
                except Exception as e:
                    print(f"[BNDL] Warning: Could not link collection {coll_name}: {e}")
        
        if linked_collections > 0:
            print(f"[BNDL] Linked {linked_collections} sub-collection(s) to {bndl_coll_name}")
        
        if appended:
            summary = f"Appended {len(appended)} asset(s) from {os.path.basename(blend_path)}"
            return (True, summary)
        else:
            return (True, f"No assets found in {os.path.basename(blend_path)}")
    
    except Exception as ex:
        return (False, f"Failed to append assets: {ex}")


def _get_scene_items(self, context):
    """Get list of scenes for compositor replay targeting."""
    items = []
    for scene in bpy.data.scenes:
        items.append((scene.name, scene.name, f"Apply to scene '{scene.name}'"))
    return items


class BNDL_OT_ReplayGeometry(Operator):
    """Replay Geometry .bndl files to selected objects"""
    bl_idname = "bndl.replay_geometry"
    bl_label = "Replay Geometry .bndl"
    bl_options = {"REGISTER", "UNDO"}

    bndl_path: StringProperty(
        name="Geometry BNDL File",
        subtype="FILE_PATH",
        description="Path to a .bndl file with Tree_Type: GEOMETRY",
        default=""
    )  # type: ignore

    def invoke(self, ctx, evt):
        if self.bndl_path and self.bndl_path.strip():
            return self.execute(ctx)
        wm = ctx.window_manager
        return wm.invoke_props_dialog(self, width=600)

    def draw(self, ctx):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "bndl_path")

    def execute(self, ctx):
        # Check if this is Lite version - show friendly popup
        import sys
        package_name = __package__.split('.')[0]
        package_module = sys.modules.get(package_name)
        is_lite = getattr(package_module, 'BNDL_LITE_VERSION', False) if package_module else False
        
        if is_lite:
            def draw_upgrade_popup(self, context):
                layout = self.layout
                layout.label(text="Geometry and Compositor BNDLs are in the Pro version only", icon='ERROR')
                layout.separator()
                layout.label(text="Upgrade to replay all tree types")
                layout.separator()
                op = layout.operator("wm.url_open", text="Upgrade to Pro ($20)", icon='URL')
                op.url = "https://kyoseigk.gumroad.com"
            
            ctx.window_manager.popup_menu(draw_upgrade_popup, title="BNDL Pro Required", icon='INFO')
            return {'CANCELLED'}
        
        path = bpy.path.abspath(self.bndl_path.strip())
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Choose a valid .bndl file.")
            return {'CANCELLED'}

        # Validate it's a geometry file by checking Tree_Type header
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            tree_type = parse_tree_type_header(content)
            
            if tree_type is None:
                # No header found, assume it's an old geometry file
                print("[BNDL] No Tree_Type header found, assuming GEOMETRY (legacy file)")
            elif tree_type != TreeType.GEOMETRY:
                self.report({'ERROR'}, f"This .bndl has Tree_Type: {tree_type.value}. Use the {tree_type.value.title()} replay button instead.")
                return {'CANCELLED'}
        except Exception as e:
            print(f"[BNDL] Could not validate file type: {e}")
            # Continue anyway for legacy files

        # Check for selected objects
        if not ctx.selected_objects:
            self.report({'ERROR'}, "Select at least one object for geometry replay")
            return {'CANCELLED'}

        try:
            # ====================================================================
            # Asset Bundling: Handle assets based on user preference
            # ====================================================================
            prefs = get_prefs()
            assets_loaded = False
            
            # Check asset dependency mode setting
            if prefs.asset_dependency_mode == 'APPEND_ASSETS':
                # APPEND_ASSETS: Import actual datablocks from .blend file
                # >>> ANTI-CRACK: Multi-layer license validation for asset import <<<
                # Inline check #1: Import and validate license with different alias
                from . import license as lic_validation
                rt_key = lic_validation._get_platform_config()
                
                if not rt_key:
                    print("[BNDL] Asset bundling requires BNDL-Pro license. Skipping asset import.")
                    print("[BNDL] Falling back to PROXIES mode (placeholder creation).")
                else:
                    # Inline check #2: Double-verify addon compatibility (different from export)
                    if not lic_validation._check_addon_compatibility():
                        print("[BNDL] License validation failed. Skipping asset import.")
                        print("[BNDL] Falling back to PROXIES mode (placeholder creation).")
                    else:
                        # Look for matching .blend file
                        blend_path = os.path.splitext(path)[0] + '.blend'
                        if os.path.isfile(blend_path):
                            print(f"[BNDL] Asset bundling: Found {os.path.basename(blend_path)}")
                            
                            # Extract asset references from .bndl to filter what we append
                            asset_refs = _extract_asset_refs_from_bndl(content)
                            if asset_refs:
                                total_refs = sum(len(names) for names in asset_refs.values())
                                print(f"[BNDL] Asset bundling: Found {total_refs} asset reference(s) in .bndl")
                                for db_type, names in asset_refs.items():
                                    print(f"[BNDL]   - {db_type}: {', '.join(sorted(names))}")
                            else:
                                print(f"[BNDL] Asset bundling: No asset references found, will append all")
                            
                            success, msg = _append_assets_from_blend(blend_path, asset_filter=asset_refs)
                            if success:
                                print(f"[BNDL] Asset bundling: {msg}")
                                assets_loaded = True
                                
                                # Force depsgraph update so appended objects are fully realized
                                print("[BNDL] Forcing depsgraph update...")
                                bpy.context.view_layer.update()
                            else:
                                print(f"[BNDL] Asset bundling WARNING: {msg}")
                                print("[BNDL] Falling back to PROXIES mode (placeholder creation)")
                        else:
                            print(f"[BNDL] Asset bundling: No matching .blend found at {blend_path}")
                            print("[BNDL] Falling back to PROXIES mode (placeholder creation)")
                # >>> END ANTI-CRACK <<<
            
            elif prefs.asset_dependency_mode == 'PROXIES':
                # PROXIES: Create placeholder objects/materials (default behavior)
                print("[BNDL] Asset mode: PROXIES (placeholders will be created for missing datablocks)")
            
            elif prefs.asset_dependency_mode == 'NONE':
                # NONE: Don't create anything, just node tree
                print("[BNDL] Asset mode: NONE (no asset dependencies will be created)")
            
            # Also try to unpack images (works in all modes)
            if prefs.asset_dependency_mode != 'NONE':
                try:
                    from .vendor.bndl_asset_pack import auto_unpack_assets_for_bndl
                    unpacked_images = auto_unpack_assets_for_bndl(path)
                    if unpacked_images:
                        print(f"[BNDL] Loaded {len(unpacked_images)} image(s) from asset pack")
                except Exception as e:
                    print(f"[BNDL] Image unpacking failed (non-fatal): {e}")
            
            # ====================================================================
            # Generate and execute replay script
            # ====================================================================
            
            # Use dedicated geometry replay system
            from .vendor.replay_geometry import GeometryReplay
            script = GeometryReplay.generate_script(content)
            
            # Save script to text block if preference enabled
            if prefs.keep_replay_text:
                text_name = "BNDL_Geometry_Replay"
                if text_name in bpy.data.texts:
                    bpy.data.texts.remove(bpy.data.texts[text_name])
                text_block = bpy.data.texts.new(text_name)
                text_block.write(script)
                print(f"[BNDL] Generated script saved to Text Editor as '{text_name}'")
            
            # Execute the generated script with selected objects and create_as_new flag
            script_globals = {
                "__name__": "__bndl_replay__",
                "bpy": bpy,
                "BNDL_TARGET_OBJECTS": list(ctx.selected_objects),
                "BNDL_CREATE_AS_NEW": ctx.scene.bndl_create_as_new
            }
            exec(script, script_globals)

            
            self.report({'INFO'}, f"Applied geometry nodes to {len(ctx.selected_objects)} object(s)")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Geometry replay failed: {e}")
            return {'CANCELLED'}


class BNDL_OT_ReplayMaterial(Operator):
    """Replay Material .bndl files to selected objects"""
    bl_idname = "bndl.replay_material"
    bl_label = "Replay Material .bndl"
    bl_options = {"REGISTER", "UNDO"}

    bndl_path: StringProperty(
        name="Material BNDL File",
        subtype="FILE_PATH",
        description="Path to a .bndl file with Tree_Type: MATERIAL",
        default=""
    )  # type: ignore

    def invoke(self, ctx, evt):
        if self.bndl_path and self.bndl_path.strip():
            return self.execute(ctx)
        wm = ctx.window_manager
        return wm.invoke_props_dialog(self, width=600)

    def draw(self, ctx):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "bndl_path")

    def execute(self, ctx):
        path = bpy.path.abspath(self.bndl_path.strip())
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Choose a valid .bndl file.")
            return {'CANCELLED'}

        # Validate it's a material file by checking Tree_Type header
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            tree_type = parse_tree_type_header(content)
            
            if tree_type is None:
                self.report({'ERROR'}, "This .bndl file has no Tree_Type header. Cannot determine if it's a material file.")
                return {'CANCELLED'}
            elif tree_type != TreeType.MATERIAL:
                self.report({'ERROR'}, f"This .bndl has Tree_Type: {tree_type.value}. Use the {tree_type.value.title()} replay button instead.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Could not read .bndl file: {e}")
            return {'CANCELLED'}

        # Check for selected objects that can have materials
        suitable_objects = [obj for obj in ctx.selected_objects 
                          if obj and (hasattr(obj.data, 'materials') or 
                                    obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'})]
        
        if not suitable_objects:
            self.report({'ERROR'}, "Select objects that can have materials (meshes, curves, etc.)")
            return {'CANCELLED'}

        try:
            # Auto-unpack assets if available
            try:
                from .vendor.bndl_asset_pack import auto_unpack_assets_for_bndl
                unpacked_images = auto_unpack_assets_for_bndl(path)
                if unpacked_images:
                    print(f"[BNDL] Loaded {len(unpacked_images)} images from asset pack")
            except Exception as e:
                print(f"[BNDL] Asset unpacking failed (non-fatal): {e}")
            
            # Use dedicated material replay system
            from .vendor.replay_material import MaterialReplay
            script = MaterialReplay.generate_script(content)
            
            # Save script to text block if preference enabled
            prefs = get_prefs()
            if prefs.keep_replay_text:
                text_name = "BNDL_Material_Replay"
                if text_name in bpy.data.texts:
                    bpy.data.texts.remove(bpy.data.texts[text_name])
                text_block = bpy.data.texts.new(text_name)
                text_block.write(script)
                print(f"[BNDL] Generated script saved to Text Editor as '{text_name}'")
            
            # Execute the generated script with selected objects and create_as_new flag
            script_globals = {
                "__name__": "__main__",
                "bpy": bpy,
                "BNDL_TARGET_OBJECTS": list(suitable_objects),
                "BNDL_CREATE_AS_NEW": ctx.scene.bndl_create_as_new
            }
            exec(script, script_globals)
            
            self.report({'INFO'}, f"Applied material nodes to {len(suitable_objects)} object(s)")
            return {'FINISHED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Material replay failed: {e}")
            return {'CANCELLED'}


class BNDL_OT_ReplayCompositor(Operator):
    """Replay Compositor .bndl files to scene"""
    bl_idname = "bndl.replay_compositor"
    bl_label = "Replay Compositor .bndl"
    bl_options = {"REGISTER", "UNDO"}

    bndl_path: StringProperty(
        name="Compositor BNDL File",
        subtype="FILE_PATH",
        description="Path to a .bndl file with Tree_Type: COMPOSITOR",
        default=""
    )  # type: ignore

    target_scene: EnumProperty(
        name="Target Scene",
        items=_get_scene_items,
        description="Scene to apply compositor setup to"
    )  # type: ignore

    def invoke(self, ctx, evt):
        # Set default scene to current
        self.target_scene = ctx.scene.name
        
        if self.bndl_path and self.bndl_path.strip():
            return self.execute(ctx)
        wm = ctx.window_manager
        return wm.invoke_props_dialog(self, width=600)

    def draw(self, ctx):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "bndl_path")
        
        if len(bpy.data.scenes) > 1:
            col.separator()
            col.prop(self, "target_scene", text="Target Scene")

    def execute(self, ctx):
        # Check if this is Lite version - show friendly popup
        import sys
        package_name = __package__.split('.')[0]
        package_module = sys.modules.get(package_name)
        is_lite = getattr(package_module, 'BNDL_LITE_VERSION', False) if package_module else False
        
        if is_lite:
            def draw_upgrade_popup(self, context):
                layout = self.layout
                layout.label(text="Geometry and Compositor BNDLs are in the Pro version only", icon='ERROR')
                layout.separator()
                layout.label(text="Upgrade to replay all tree types")
                layout.separator()
                op = layout.operator("wm.url_open", text="Upgrade to Pro ($20)", icon='URL')
                op.url = "https://kyoseigk.gumroad.com"
            
            ctx.window_manager.popup_menu(draw_upgrade_popup, title="BNDL Pro Required", icon='INFO')
            return {'CANCELLED'}
        
        path = bpy.path.abspath(self.bndl_path.strip())
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Choose a valid .bndl file.")
            return {'CANCELLED'}

        # Validate it's a compositor file by checking Tree_Type header
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            tree_type = parse_tree_type_header(content)
            
            if tree_type is None:
                self.report({'ERROR'}, "This .bndl file has no Tree_Type header. Cannot determine if it's a compositor file.")
                return {'CANCELLED'}
            elif tree_type != TreeType.COMPOSITOR:
                self.report({'ERROR'}, f"This .bndl has Tree_Type: {tree_type.value}. Use the {tree_type.value.title()} replay button instead.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Could not read .bndl file: {e}")
            return {'CANCELLED'}

        # Validate target scene
        target_scene = bpy.data.scenes.get(self.target_scene)
        if not target_scene:
            self.report({'ERROR'}, f"Target scene '{self.target_scene}' not found")
            return {'CANCELLED'}

        try:
            # Auto-unpack assets if available
            try:
                from .vendor.bndl_asset_pack import auto_unpack_assets_for_bndl
                unpacked_images = auto_unpack_assets_for_bndl(path)
                if unpacked_images:
                    print(f"[BNDL] Loaded {len(unpacked_images)} images from asset pack")
            except Exception as e:
                print(f"[BNDL] Asset unpacking failed (non-fatal): {e}")
            
            # Use dedicated compositor replay system
            from .vendor.replay_compositor import CompositorReplay
            
            # Temporarily switch context to target scene for compositor operations
            original_scene = ctx.scene
            try:
                # Set the target scene as active
                ctx.window.scene = target_scene
                
                script = CompositorReplay.generate_script(content)
                
                # Save script to text block if preference enabled
                prefs = get_prefs()
                if prefs.keep_replay_text:
                    text_name = "BNDL_Compositor_Replay"
                    if text_name in bpy.data.texts:
                        bpy.data.texts.remove(bpy.data.texts[text_name])
                    text_block = bpy.data.texts.new(text_name)
                    text_block.write(script)
                    print(f"[BNDL] Generated script saved to Text Editor as '{text_name}'")
                
                # Execute the generated script
                exec(script, {"__name__": "__main__", "bpy": bpy})
                
                self.report({'INFO'}, f"Applied compositor nodes to scene '{self.target_scene}'")
                return {'FINISHED'}
            finally:
                # Restore original scene
                ctx.window.scene = original_scene
                
        except Exception as e:
            self.report({'ERROR'}, f"Compositor replay failed: {e}")
            return {'CANCELLED'}


# Legacy replay operator (restored for UI compatibility)
class BNDL_OT_ReplayGeneric(Operator):
    """Generic replay operator that auto-detects tree type"""
    bl_idname = "bndl.replay_generic"
    bl_label = "Replay .bndl (Auto-detect)"
    bl_options = {"REGISTER", "UNDO"}

    bndl_path: StringProperty(
        name="BNDL File",
        subtype="FILE_PATH",
        description="Path to any .bndl file (auto-detects type)",
        default=""
    )  # type: ignore

    def invoke(self, ctx, evt):
        if self.bndl_path and self.bndl_path.strip():
            return self.execute(ctx)
        wm = ctx.window_manager
        return wm.invoke_props_dialog(self, width=600)

    def draw(self, ctx):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "bndl_path")

    def execute(self, ctx):
        path = bpy.path.abspath(self.bndl_path.strip())
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Choose a valid .bndl file.")
            return {'CANCELLED'}

        # Detect tree type and call appropriate operator
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            tree_type = parse_tree_type_header(content)
            
            if not tree_type:
                tree_type = TreeType.GEOMETRY  # Default to geometry for old files
            
            # Call the appropriate specialized operator
            if tree_type == TreeType.GEOMETRY:
                bpy.ops.bndl.replay_geometry('INVOKE_DEFAULT', bndl_path=path)  # type: ignore
            elif tree_type == TreeType.MATERIAL:
                bpy.ops.bndl.replay_material('INVOKE_DEFAULT', bndl_path=path)  # type: ignore
            elif tree_type == TreeType.COMPOSITOR:
                bpy.ops.bndl.replay_compositor('INVOKE_DEFAULT', bndl_path=path)  # type: ignore
            else:
                self.report({'ERROR'}, f"Unsupported tree type: {tree_type}")
                return {'CANCELLED'}
                
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Auto-detection failed: {e}")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(BNDL_OT_ReplayGeometry)
    bpy.utils.register_class(BNDL_OT_ReplayMaterial)
    bpy.utils.register_class(BNDL_OT_ReplayCompositor)
    bpy.utils.register_class(BNDL_OT_ReplayGeneric)
    
    # Register properties used in UI
    bpy.types.Scene.bndl_reuse_proxies = BoolProperty(
        name="Reuse Proxies",
        description="Reuse existing proxy objects/materials if found",
        default=True
    )
    bpy.types.Scene.bndl_create_as_new = BoolProperty(
        name="Create as New",
        description="Create new datablocks with unique names instead of overwriting",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(BNDL_OT_ReplayGeometry)
    bpy.utils.unregister_class(BNDL_OT_ReplayMaterial)
    bpy.utils.unregister_class(BNDL_OT_ReplayCompositor)
    bpy.utils.unregister_class(BNDL_OT_ReplayGeneric)
    
    if hasattr(bpy.types.Scene, "bndl_reuse_proxies"):
        del bpy.types.Scene.bndl_reuse_proxies
    if hasattr(bpy.types.Scene, "bndl_create_as_new"):
        del bpy.types.Scene.bndl_create_as_new