import bpy, os, importlib, random, string  # type: ignore
from bpy.types import Operator  # type: ignore
from bpy.props import StringProperty, EnumProperty, BoolProperty  # type: ignore
from .prefs import get_prefs
from .helpers import reveal_in_explorer, import_vendor
from .vendor.bndl_common import TreeType, get_file_prefix

def _active_gn_tree_name(ob: bpy.types.Object | None) -> str | None:
    """Return the active Geometry Nodes tree name on the object, if any."""
    if not ob:
        return None
    mod = getattr(ob, "modifiers", None)
    if not mod:
        return None
    # Prefer the active modifier if it’s a GN modifier
    act_mod = ob.modifiers.get(ob.modifiers.active.name) if getattr(ob.modifiers, "active", None) else None  # type: ignore
    candidates = [act_mod] + list(ob.modifiers) if act_mod else list(ob.modifiers)
    for m in candidates:
        if getattr(m, "type", "") == 'NODES' and getattr(m, "node_group", None):
            return m.node_group.name  # type: ignore
    return None

def _rand_tag(k: int = 6) -> str:
    """6-char uppercase/digit suffix to guarantee uniqueness."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(k))

def _notes_block(*chunks: str) -> str:
    """Return a semicolon-prefixed notes block composed from multiple chunks."""
    lines_accum = []
    for notes in chunks:
        if not notes or not notes.strip():
            continue
        lines_accum.extend([ln.rstrip() for ln in notes.splitlines()])
    if not lines_accum:
        return ""
    out = ["; --- NOTES ---"]
    out += [f"; {ln}" if ln else ";" for ln in lines_accum]
    out += ["; --- END NOTES ---", ""]
    return "\n".join(out)

def _get_compositor_scene_items(self, context):
    """Get list of scenes with compositor setups for dropdown."""
    items = []
    
    for scene in bpy.data.scenes:
        if scene.use_nodes and scene.node_tree and scene.node_tree.nodes:  # type: ignore
            # Check if there are meaningful nodes (not just default)
            meaningful_nodes = [n for n in scene.node_tree.nodes  # type: ignore
                              if n.type not in {'COMPOSITE', 'R_LAYERS'} or len(scene.node_tree.nodes) > 2]  # type: ignore
            if meaningful_nodes or len(scene.node_tree.nodes) > 2:  # type: ignore
                items.append((scene.name, scene.name, f"Export compositor from scene '{scene.name}'"))
    
    if not items:
        items.append(("NONE", "No Compositor Setups", "No scenes with compositor setups found"))
    
    return items

def _get_export_project_items(self, context):
    """Generate dynamic enum items for export project dropdown."""
    items = [('NONE', "Select a Project", "Choose which project directory to export to", 'ERROR', 0)]
    
    prefs = get_prefs()
    if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
        for idx, item in enumerate(prefs.bndl_directories, start=1):
            if item.name and item.directory:
                items.append((item.name, item.name, f"Export to {item.directory}", 'FILE_FOLDER', idx))
    
    return items

def _on_export_project_update(self, context):
    """Callback when export project selection changes - auto-fill output directory."""
    if self.export_project == "NONE":
        self.output_dir = ""
        return
    
    prefs = get_prefs()
    if hasattr(prefs, "bndl_directories"):
        for item in prefs.bndl_directories:
            if item.name == self.export_project:
                self.output_dir = item.directory
                break



class BNDL_OT_Export(Operator):
    bl_idname = "bndl.export_active_tree"
    bl_label  = "Export .bndl"
    bl_description = "Upgrade to BNDL Pro for Geometry Nodes export"
    bl_options = {"REGISTER", "UNDO"}

    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to",
        update=_on_export_project_update
    )

    output_dir: StringProperty(  # type: ignore
        name="Output Directory",
        subtype="DIR_PATH",
        description="Where the exporter writes the .bndl file (auto-filled from project selection)",
        default=""
    )

    notes: StringProperty(  # type: ignore
        name="Notes",
        description="Freeform notes stored as ';' comment lines in the .bndl",
        default=""
    )


    def invoke(self, ctx, evt):
        prefs = get_prefs()
        
        # Remember last selected project (stored in scene)
        last_project = ctx.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        
        # Check if last project still exists in preferences
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
            # Auto-fill output_dir from selected project
            for item in prefs.bndl_directories:
                if item.name == last_project:
                    self.output_dir = item.directory
                    break
        else:
            self.export_project = "NONE"
            self.output_dir = ""
        
        return ctx.window_manager.invoke_props_dialog(self, width=520)  # type: ignore

    def draw(self, ctx):
        col = self.layout.column(align=True)  # type: ignore
        
        # Project selection dropdown
        col.prop(self, "export_project", text="Project")
        
        # Show warning if no project selected
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        
        # Output directory (read-only display, auto-filled from project)
        col.prop(self, "output_dir", text="Output Directory")
        
        col.separator()
        row = col.row()
        row.scale_y = 1.6
        row.prop(self, "notes", text="Notes")

    def execute(self, ctx):
        prefs = get_prefs()
        
        # Validate project selection
        if self.export_project == "NONE":
            self.report({'ERROR'}, "Please select a project directory to export to.")
            return {'CANCELLED'}
        
        # Get directory from selected project
        outdir = ""
        if hasattr(prefs, "bndl_directories"):
            for item in prefs.bndl_directories:
                if item.name == self.export_project:
                    outdir = item.directory
                    break
        
        if not outdir:
            self.report({'ERROR'}, f"Project '{self.export_project}' has no directory configured.")
            return {'CANCELLED'}
        
        # Remember this selection for next time
        ctx.scene["_bndl_last_export_project"] = self.export_project
        
        outdir = os.path.abspath(bpy.path.abspath(outdir)) if outdir else ""
        if outdir and not os.path.isdir(outdir):
            try:
                os.makedirs(outdir, exist_ok=True)
            except Exception as e:
                self.report({'ERROR'}, f"Cannot create output dir: {e}")
                return {'CANCELLED'}

        exp = import_vendor("export_geometry")  # Updated to use new geometry exporter
        if exp is None:
            self.report({'ERROR'}, "export_geometry.py not found under bndl_addon/vendor/")
            return {'CANCELLED'}

        # ---- Build unique names (file + text block) ---------------------------------
        ob = ctx.active_object
        base = _active_gn_tree_name(ob) or (ob.name if ob else "BNDL")
        
        # Affixes from prefs
        p = get_prefs()
        pre1 = (p.name_prefix_1.strip() + "_") if p.name_prefix_1.strip() else ""
        pre2 = (p.name_prefix_2.strip() + "_") if p.name_prefix_2.strip() else ""
        suf1 = ("_" + p.name_suffix_1.strip()) if p.name_suffix_1.strip() else ""

        tag = _rand_tag(6)

        prefix = get_file_prefix(TreeType.GEOMETRY)  # "G-"

        textblock_name = f"BNDL_Export-{pre1}{pre2}{base}-{tag}{suf1}.txt"
        outfile_name   = f"{prefix}{pre1}{pre2}{base}-{tag}{suf1}.bndl"
        outfile_path   = os.path.join(outdir, outfile_name) if outdir else ""


        outfile_path   = os.path.join(outdir, outfile_name) if outdir else ""

        # ---- Configure exporter globals if present ----------------------------------
        try:
            if hasattr(exp, "WRITE_FILE_PATH"):
                exp.WRITE_FILE_PATH = outfile_path  # exporter may honor this  # type: ignore
            if hasattr(exp, "TEXT_BLOCK_NAME"):
                exp.TEXT_BLOCK_NAME = textblock_name  # exporter will create/overwrite this Text  # type: ignore

            # Run exporter script
            importlib.reload(exp)

            # ---- Resolve content and ensure external file exists --------------------
            # 1) If the exporter already wrote the file, we're done.
            wrote_file = bool(outfile_path and os.path.isfile(outfile_path))
            # If a file exists and user provided notes, prepend them
            if wrote_file and (get_prefs().overall_notes.strip() or (self.notes and self.notes.strip())):

                try:
                    with open(outfile_path, "r", encoding="utf-8") as f:
                        original = f.read()
                    notes_hdr = _notes_block(get_prefs().overall_notes, self.notes)
                    with open(outfile_path, "w", encoding="utf-8") as f:
                        f.write(notes_hdr + original)
                    # Also try to update an export Text block, if present
                    maybe_txt = bpy.data.texts.get(textblock_name) or bpy.data.texts.get(getattr(exp, "TEXT_BLOCK_NAME", "BNDL_Export"))
                    if maybe_txt:
                        maybe_txt.clear()
                        maybe_txt.write(notes_hdr + original)
                except Exception as _e:
                    # Non-fatal: keep exporting even if annotate failed
                    print("[BNDL] Failed to prepend notes to existing file:", _e)


            # 2) If not, try to pull from the Text block and write it ourselves.
            if not wrote_file:
                txt = bpy.data.texts.get(textblock_name)
                # Fallback to common legacy name if needed
                if txt is None:
                    legacy = getattr(exp, "TEXT_BLOCK_NAME", "BNDL_Export")
                    txt = bpy.data.texts.get(legacy)
                if txt is None:
                    self.report({'ERROR'}, "Export ran but produced neither a file nor a Text block.")
                    return {'CANCELLED'}

                content = txt.as_string() if hasattr(txt, "as_string") else ""
                prefs_notes = get_prefs().overall_notes
                notes_hdr = _notes_block(prefs_notes, self.notes)
                payload = notes_hdr + (content if content.endswith("\n") else content + "\n")

                # Ensure we have an output path
                if not outfile_path:
                    self.report({'WARNING'}, "No output folder configured; writing .bndl next to the .blend file.")
                    blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
                    outfile_path = os.path.join(blend_dir, outfile_name)

                with open(outfile_path, "w", encoding="utf-8") as f:
                    f.write(payload)
                wrote_file = True
                try:
                    if txt and notes_hdr:
                        txt.clear()
                        txt.write(payload)
                except Exception:
                    pass

            # 3) Rename the Text block to our canonical name if exporter used a legacy one
            if textblock_name not in bpy.data.texts and bpy.data.texts:
                # If a different export Text exists, rename it to our canonical textblock_name
                maybe = bpy.data.texts.get(getattr(exp, "TEXT_BLOCK_NAME", "BNDL_Export"))
                if maybe and maybe.name != textblock_name:
                    maybe.name = textblock_name

            # ---- Finalize -----------------------------------------------------------
            if wrote_file:
                self.report({'INFO'}, f"Exported: {outfile_path}")
                
                # ---- Asset bundling (Task 5) ----------------------------------------
                # Check if asset_dependency_mode == 'APPEND_ASSETS' and save .blend
                # Pro feature: Only bundle assets if licensed
                
                if prefs.asset_dependency_mode == 'APPEND_ASSETS':
                    # >>> ANTI-CRACK: Multi-layer license validation for asset export <<<
                    # Inline check #1: Import license module with alias
                    from . import license as lic_mod
                    
                    # Inline check #2: Validate platform config exists (obfuscated get_runtime_key)
                    runtime_cfg = lic_mod._get_platform_config()
                    if not runtime_cfg:
                        self.report({'WARNING'}, "Asset bundling requires BNDL-Pro license. Skipping asset export.")
                    else:
                        # Inline check #3: Ensure addon compatibility (obfuscated is_pro_version)
                        if not lic_mod._check_addon_compatibility():
                            self.report({'WARNING'}, "Asset bundling requires BNDL-Pro license. Skipping asset export.")
                        else:
                            try:
                                # Inline check #4: Re-verify integrity mid-operation (obfuscated _validate_runtime_key)
                                if not lic_mod._verify_addon_integrity():
                                    self.report({'WARNING'}, "License validation failed during asset bundling.")
                                else:
                                    # Read the generated .bndl text
                                    with open(outfile_path, "r", encoding="utf-8") as f:
                                        bndl_text = f.read()
                                    
                                    # Collect referenced assets
                                    asset_dict = exp.collect_referenced_assets(bndl_text)
                                    
                                    # Generate matching .blend filename
                                    blend_path = outfile_path.rsplit('.', 1)[0] + '.blend'
                                    
                                    # Save assets to .blend
                                    success, msg, count = exp.save_assets_to_blend(asset_dict, blend_path)
                                    
                                    if success:
                                        self.report({'INFO'}, f"Asset bundling: {msg}")
                                    else:
                                        self.report({'WARNING'}, f"Asset bundling: {msg}")
                            
                            except Exception as ex:
                                self.report({'WARNING'}, f"Asset bundling failed: {ex}")
                    # >>> END ANTI-CRACK <<<
                # ---------------------------------------------------------------------
                
                # ---- Image/Texture Asset Packing -----------------------------------
                # Pack images/videos referenced by texture nodes
                if prefs.pack_assets_on_export:
                    try:
                        from .vendor import bndl_asset_pack
                        
                        # Determine format from preferences
                        format_map = {
                            'BNDLPACK': 'bndlpack',
                            'BLEND': 'blend',
                            'HYBRID': 'hybrid'
                        }
                        pack_format = format_map.get(prefs.asset_pack_format, 'bndlpack')
                        
                        # Pack assets
                        pack_path = bndl_asset_pack.auto_pack_assets_for_bndl(
                            bndl_path=outfile_path,
                            tree_type='GEOMETRY',
                            source_object=ob,
                            pack_format=pack_format
                        )
                        
                        if pack_path:
                            if pack_format == 'hybrid':
                                self.report({'INFO'}, f"Created asset packs: .bndlpack + _assets.blend")
                            else:
                                pack_name = os.path.basename(pack_path)
                                self.report({'INFO'}, f"Packed assets to {pack_name}")
                    except Exception as e:
                        print(f"[BNDL] Asset packing failed: {e}")
                        # Don't fail the whole export if asset packing fails
                # ---------------------------------------------------------------------
                
                reveal_in_explorer(os.path.dirname(outfile_path))
            else:
                self.report({'INFO'}, f"Exported to Text: {textblock_name}")
            try:
                bpy.ops.bndl.list_refresh()  # type: ignore
            except Exception:
                pass
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}


# ---------- New Multi-Tree Export Operators ----------

class BNDL_OT_ExportMaterial(Operator):
    """Export Material/Shader nodes to .bndl format"""
    bl_idname = "bndl.export_material"
    bl_label = "Export Material Shader"
    bl_options = {"REGISTER", "UNDO"}

    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to",
        update=_on_export_project_update
    )

    output_dir: StringProperty(  # type: ignore
        name="Output Directory",
        subtype="DIR_PATH",
        description="Where the exporter writes the .bndl file",
        default=""
    )

    notes: StringProperty(  # type: ignore
        name="Notes",
        description="Freeform notes for the material export",
        default=""
    )

    def invoke(self, context, event):
        # Check if object has materials
        obj = context.active_object
        if not obj or not hasattr(obj, 'material_slots') or not obj.material_slots:
            self.report({'ERROR'}, "No materials found. Select an object with materials.")
            return {'CANCELLED'}

        # Auto-fill project like geometry exporter
        prefs = get_prefs()
        last_project = context.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
            for item in prefs.bndl_directories:
                if item.name == last_project:
                    self.output_dir = item.directory
                    break
        
        return context.window_manager.invoke_props_dialog(self, width=520)  # type: ignore

    def draw(self, context):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "export_project", text="Project")
        
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        col.prop(self, "output_dir", text="Output Directory")
        col.separator()
        
        row = col.row()
        row.scale_y = 1.6
        row.prop(self, "notes", text="Notes")

    def execute(self, context):
        if self.export_project == "NONE":
            self.report({'ERROR'}, "Please select a project directory.")
            return {'CANCELLED'}
        
        # Get export directory
        prefs = get_prefs()
        outdir = ""
        if hasattr(prefs, "bndl_directories"):
            for item in prefs.bndl_directories:
                if item.name == self.export_project:
                    outdir = item.directory
                    break
        
        if not outdir:
            self.report({'ERROR'}, f"Project '{self.export_project}' has no directory.")
            return {'CANCELLED'}
        
        outdir = os.path.abspath(bpy.path.abspath(outdir))
        os.makedirs(outdir, exist_ok=True)
        
        try:
            # Import material exporter
            exp_mat = import_vendor("export_material")
            if exp_mat is None:
                self.report({'ERROR'}, "export_material.py not found")
                return {'CANCELLED'}
            
            # Get active material
            obj = context.active_object
            material = obj.material_slots[obj.active_material_index].material if obj.material_slots else None  # type: ignore
            if not material:
                self.report({'ERROR'}, "No active material found")
                return {'CANCELLED'}
            
            # Generate filename with S- prefix
            base = material.name
            p = get_prefs()
            pre1 = (p.name_prefix_1.strip() + "_") if p.name_prefix_1.strip() else ""
            pre2 = (p.name_prefix_2.strip() + "_") if p.name_prefix_2.strip() else ""
            suf1 = ("_" + p.name_suffix_1.strip()) if p.name_suffix_1.strip() else ""
            
            tag = _rand_tag(6)
            prefix = get_file_prefix(TreeType.MATERIAL)  # "S-"
            
            outfile_name = f"{prefix}{pre1}{pre2}{base}-{tag}{suf1}.bndl"
            outfile_path = os.path.join(outdir, outfile_name)
            
            # Configure exporter
            exp_mat.WRITE_FILE_PATH = outfile_path  # type: ignore
            exp_mat.TEXT_BLOCK_NAME = f"BNDL_Material_Export-{base}-{tag}"  # type: ignore
            
            # Run export
            importlib.reload(exp_mat)
            bndl_text = exp_mat.export_active_material_to_bndl_text()
            
            # Add notes if provided and write file
            if self.notes.strip() or prefs.overall_notes.strip():
                notes_block = _notes_block(prefs.overall_notes, self.notes)
                final_content = notes_block + bndl_text
            else:
                final_content = bndl_text
            
            # Always write the file
            with open(outfile_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            self.report({'INFO'}, f"Exported material '{material.name}' to {outfile_name}")
            
            # Pack assets if enabled in preferences
            prefs = get_prefs()
            if prefs.pack_assets_on_export:
                try:
                    from .vendor import bndl_asset_pack
                    
                    # Determine format from preferences
                    format_map = {
                        'BNDLPACK': 'bndlpack',
                        'BLEND': 'blend',
                        'HYBRID': 'hybrid'
                    }
                    pack_format = format_map.get(prefs.asset_pack_format, 'bndlpack')
                    
                    # Pack assets
                    pack_path = bndl_asset_pack.auto_pack_assets_for_bndl(
                        bndl_path=outfile_path,
                        tree_type='MATERIAL',
                        source_material=material,
                        pack_format=pack_format
                    )
                    
                    if pack_path:
                        if pack_format == 'hybrid':
                            self.report({'INFO'}, f"Created asset packs: .bndlpack + _assets.blend")
                        else:
                            pack_name = os.path.basename(pack_path)
                            self.report({'INFO'}, f"Packed assets to {pack_name}")
                except Exception as e:
                    print(f"[BNDL] Asset packing failed: {e}")
                    # Don't fail the whole export if asset packing fails
            
            # Remember project selection
            context.scene["_bndl_last_export_project"] = self.export_project  # type: ignore
            
            # Refresh library
            try:
                bpy.ops.bndl.list_refresh()  # type: ignore
            except:
                pass
            
            reveal_in_explorer(os.path.dirname(outfile_path))
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Material export failed: {e}")
            return {'CANCELLED'}


class BNDL_OT_ExportCompositor(Operator):
    """Export Compositor nodes to .bndl format"""
    bl_idname = "bndl.export_compositor"
    bl_label = "Export Compositor"
    bl_description = "Upgrade to BNDL Pro for Compositor export"
    bl_options = {"REGISTER", "UNDO"}

    target_scene: EnumProperty(  # type: ignore
        name="Target Scene",
        items=_get_compositor_scene_items,
        description="Select which scene's compositor to export"
    )

    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to",
        update=_on_export_project_update
    )

    output_dir: StringProperty(  # type: ignore
        name="Output Directory",
        subtype="DIR_PATH",
        description="Where the exporter writes the .bndl file",
        default=""
    )

    notes: StringProperty(  # type: ignore
        name="Notes",
        description="Freeform notes for the compositor export",
        default=""
    )

    def invoke(self, context, event):
        # Set default scene to current scene if it has compositor enabled
        if context.scene.use_nodes and context.scene.node_tree:  # type: ignore
            self.target_scene = context.scene.name  # type: ignore
        
        # Check if any scenes have compositor enabled
        compositor_scenes = [scene for scene in bpy.data.scenes 
                           if scene.use_nodes and scene.node_tree and scene.node_tree.nodes]  # type: ignore
        if not compositor_scenes:
            self.report({'ERROR'}, "No scenes with compositor setups found. Enable 'Use Nodes' in Compositor.")
            return {'CANCELLED'}

        # Auto-fill project
        prefs = get_prefs()
        last_project = context.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
            for item in prefs.bndl_directories:
                if item.name == last_project:
                    self.output_dir = item.directory
                    break
        
        return context.window_manager.invoke_props_dialog(self, width=520)  # type: ignore

    def draw(self, context):
        col = self.layout.column(align=True)  # type: ignore
        col.prop(self, "export_project", text="Project")
        
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        col.prop(self, "output_dir", text="Output Directory")
        col.separator()
        
        row = col.row()
        row.scale_y = 1.6
        row.prop(self, "notes", text="Notes")

    def execute(self, context):
        if self.export_project == "NONE":
            self.report({'ERROR'}, "Please select a project directory.")
            return {'CANCELLED'}
        
        # Get export directory
        prefs = get_prefs()
        outdir = ""
        if hasattr(prefs, "bndl_directories"):
            for item in prefs.bndl_directories:
                if item.name == self.export_project:
                    outdir = item.directory
                    break
        
        if not outdir:
            self.report({'ERROR'}, f"Project '{self.export_project}' has no directory.")
            return {'CANCELLED'}
        
        outdir = os.path.abspath(bpy.path.abspath(outdir))
        os.makedirs(outdir, exist_ok=True)
        
        try:
            # Validate target scene
            target_scene = bpy.data.scenes.get(self.target_scene)
            if not target_scene:
                self.report({'ERROR'}, f"Target scene '{self.target_scene}' not found")
                return {'CANCELLED'}
            
            if not target_scene.use_nodes or not target_scene.node_tree:  # type: ignore
                self.report({'ERROR'}, f"Scene '{self.target_scene}' has no compositor setup")
                return {'CANCELLED'}
            
            # Import compositor exporter
            exp_comp = import_vendor("export_compositor")
            if exp_comp is None:
                self.report({'ERROR'}, "export_compositor.py not found")
                return {'CANCELLED'}
            
            # Generate filename with C- prefix using target scene name
            scene_name = target_scene.name
            base = f"Compositor_{scene_name}"
            p = get_prefs()
            pre1 = (p.name_prefix_1.strip() + "_") if p.name_prefix_1.strip() else ""
            pre2 = (p.name_prefix_2.strip() + "_") if p.name_prefix_2.strip() else ""
            suf1 = ("_" + p.name_suffix_1.strip()) if p.name_suffix_1.strip() else ""
            
            tag = _rand_tag(6)
            prefix = get_file_prefix(TreeType.COMPOSITOR)  # "C-"
            
            outfile_name = f"{prefix}{pre1}{pre2}{base}-{tag}{suf1}.bndl"
            outfile_path = os.path.join(outdir, outfile_name)
            
            # Configure exporter
            exp_comp.WRITE_FILE_PATH = outfile_path  # type: ignore
            exp_comp.TEXT_BLOCK_NAME = f"BNDL_Compositor_Export-{scene_name}-{tag}"  # type: ignore
            
            # Run export
            importlib.reload(exp_comp)
            bndl_text = exp_comp.export_compositor_to_bndl_text()
            
            # Add notes if provided and write file
            if self.notes.strip() or prefs.overall_notes.strip():
                notes_block = _notes_block(prefs.overall_notes, self.notes)
                final_content = notes_block + bndl_text
            else:
                final_content = bndl_text
            
            # Always write the file
            with open(outfile_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            self.report({'INFO'}, f"Exported compositor to {outfile_name}")
            
            # Pack assets if enabled in preferences
            prefs = get_prefs()
            if prefs.pack_assets_on_export:
                try:
                    from .vendor import bndl_asset_pack
                    
                    # Determine format from preferences
                    format_map = {
                        'BNDLPACK': 'bndlpack',
                        'BLEND': 'blend',
                        'HYBRID': 'hybrid'
                    }
                    pack_format = format_map.get(prefs.asset_pack_format, 'bndlpack')
                    
                    # Pack assets
                    pack_path = bndl_asset_pack.auto_pack_assets_for_bndl(
                        bndl_path=outfile_path,
                        tree_type='COMPOSITOR',
                        source_scene=target_scene,
                        pack_format=pack_format
                    )
                    
                    if pack_path:
                        if pack_format == 'hybrid':
                            self.report({'INFO'}, f"Created asset packs: .bndlpack + _assets.blend")
                        else:
                            pack_name = os.path.basename(pack_path)
                            self.report({'INFO'}, f"Packed assets to {pack_name}")
                except Exception as e:
                    print(f"[BNDL] Asset packing failed: {e}")
                    # Don't fail the whole export if asset packing fails
            
            # Remember project selection
            context.scene["_bndl_last_export_project"] = self.export_project  # type: ignore
            
            # Refresh library
            try:
                bpy.ops.bndl.list_refresh()  # type: ignore
            except:
                pass
            
            reveal_in_explorer(os.path.dirname(outfile_path))
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Compositor export failed: {e}")
            return {'CANCELLED'}


class BNDL_OT_ExportGeometryAndMaterial(Operator):
    """Export both Geometry and Material nodes from the active object"""
    bl_idname = "bndl.export_geometry_and_material"
    bl_label = "Export Geometry + Material"
    bl_options = {"REGISTER", "UNDO"}

    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to",
        update=_on_export_project_update
    )

    output_dir: StringProperty(  # type: ignore
        name="Output Directory",
        subtype="DIR_PATH",
        description="Where the exporter writes the .bndl files",
        default=""
    )

    notes: StringProperty(  # type: ignore
        name="Notes",
        description="Freeform notes for both exports",
        default=""
    )

    def invoke(self, context, event):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object selected.")
            return {'CANCELLED'}

        # Check for geometry nodes
        has_geo = any(m.type == 'NODES' and m.node_group for m in getattr(obj, 'modifiers', []))
        # Check for materials
        has_mat = hasattr(obj, 'material_slots') and obj.material_slots and any(
            slot.material and slot.material.use_nodes for slot in obj.material_slots
        )

        if not has_geo and not has_mat:
            self.report({'ERROR'}, "Object has no geometry nodes or materials with shader nodes.")
            return {'CANCELLED'}

        if not has_geo:
            self.report({'ERROR'}, "Object has no geometry nodes modifier.")
            return {'CANCELLED'}

        if not has_mat:
            self.report({'ERROR'}, "Object has no materials with shader nodes.")
            return {'CANCELLED'}

        # Auto-fill project
        prefs = get_prefs()
        last_project = context.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
            for item in prefs.bndl_directories:
                if item.name == last_project:
                    self.output_dir = item.directory
                    break
        
        return context.window_manager.invoke_props_dialog(self, width=520)  # type: ignore

    def draw(self, context):
        col = self.layout.column(align=True)  # type: ignore
        col.label(text="Export both Geometry and Material nodes", icon='INFO')
        col.separator()
        
        col.prop(self, "export_project", text="Project")
        
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        col.prop(self, "output_dir", text="Output Directory")
        col.separator()
        
        row = col.row()
        row.scale_y = 1.6
        row.prop(self, "notes", text="Notes")

    def execute(self, context):
        if self.export_project == "NONE":
            self.report({'ERROR'}, "Please select a project directory.")
            return {'CANCELLED'}

        exported_files = []
        
        try:
            # Export Geometry first
            bpy.ops.bndl.export_active_tree(  # type: ignore
                'EXEC_DEFAULT',
                export_project=self.export_project,
                notes=self.notes
            )
            
            # Export Material
            bpy.ops.bndl.export_material(  # type: ignore
                'EXEC_DEFAULT', 
                export_project=self.export_project,
                notes=self.notes
            )
            
            self.report({'INFO'}, "Exported both Geometry and Material nodes successfully")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Combined export failed: {e}")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(BNDL_OT_Export)
    bpy.utils.register_class(BNDL_OT_ExportMaterial)
    bpy.utils.register_class(BNDL_OT_ExportCompositor)
    bpy.utils.register_class(BNDL_OT_ExportGeometryAndMaterial)

def unregister():
    bpy.utils.unregister_class(BNDL_OT_ExportGeometryAndMaterial)
    bpy.utils.unregister_class(BNDL_OT_ExportCompositor)
    bpy.utils.unregister_class(BNDL_OT_ExportMaterial)
    bpy.utils.unregister_class(BNDL_OT_Export)
