"""
Batch export operators for BNDL addon.
Export multiple materials, objects, or scenes at once.
"""

import bpy  # type: ignore
import os
from bpy.types import Operator  # type: ignore
from bpy.props import EnumProperty, BoolProperty, StringProperty  # type: ignore
from .prefs import get_prefs
from .i18n_utils import ui, op, tip, msg, err
from .progress_utils import ProgressTracker


def _get_export_project_items(self, context):
    """Generate dynamic enum items for export project dropdown."""
    items = [('NONE', "Select a Project", "Choose which project directory to export to", 'ERROR', 0)]
    
    prefs = get_prefs()
    if hasattr(prefs, "bndl_directories") and prefs.bndl_directories:
        for idx, item in enumerate(prefs.bndl_directories, start=1):
            if item.name and item.directory:
                items.append((item.name, item.name, f"Export to {item.directory}", 'FILE_FOLDER', idx))
    
    return items


class BNDL_OT_BatchExportMaterials(Operator):
    """Export all materials in the blend file to .bndl files"""
    bl_idname = "bndl.batch_export_materials"
    bl_label = "Batch Export Materials"
    bl_description = "Export all materials (or selected objects' materials) to individual .bndl files"
    bl_options = {'REGISTER', 'UNDO'}
    
    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to"
    )
    
    export_mode: EnumProperty(  # type: ignore
        name="Export Mode",
        description="Which materials to export",
        items=[
            ('ALL', "All Materials", "Export all materials in the blend file", 'MATERIAL', 0),
            ('SELECTED', "Selected Objects", "Export materials from selected objects only", 'RESTRICT_SELECT_OFF', 1),
            ('ACTIVE', "Active Object", "Export materials from active object only", 'OBJECT_DATA', 2),
        ],
        default='SELECTED'
    )
    
    skip_nodes_without_material: BoolProperty(  # type: ignore
        name="Skip Objects Without Materials",
        description="Don't create empty .bndl files for objects without materials",
        default=True
    )
    
    overwrite_existing: BoolProperty(  # type: ignore
        name="Overwrite Existing Files",
        description="Overwrite .bndl files if they already exist",
        default=False
    )
    
    def invoke(self, context, event):
        prefs = get_prefs()
        
        # Remember last selected project
        last_project = context.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
        
        return context.window_manager.invoke_props_dialog(self, width=400)  # type: ignore
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)  # type: ignore
        
        col.prop(self, "export_project", text="Project")
        
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        
        # Export mode selection - make it prominent
        mode_box = col.box()
        mode_box.label(text="Export Mode:")
        mode_box.prop(self, "export_mode", text="")
        
        col.separator()
        col.prop(self, "skip_nodes_without_material")
        col.prop(self, "overwrite_existing")
    
    def execute(self, context):
        print(f"[DEBUG] Batch materials export mode: {self.export_mode}")
        print(f"[DEBUG] Selected objects: {[obj.name for obj in context.selected_objects]}")
        if context.active_object:
            print(f"[DEBUG] Active object: {context.active_object.name}")
        else:
            print(f"[DEBUG] No active object")
        
        # Validate project selection
        if self.export_project == "NONE":
            self.report({'ERROR'}, msg('Select project'))
            return {'CANCELLED'}
        
        # Get output directory
        prefs = get_prefs()
        outdir = ""
        if hasattr(prefs, "bndl_directories"):
            for item in prefs.bndl_directories:
                if item.name == self.export_project:
                    outdir = item.directory
                    break
        
        if not outdir:
            self.report({'ERROR'}, msg('No directory configured', project=self.export_project))
            return {'CANCELLED'}
        
        outdir = os.path.abspath(bpy.path.abspath(outdir))
        if not os.path.isdir(outdir):
            try:
                os.makedirs(outdir, exist_ok=True)
            except Exception as e:
                self.report({'ERROR'}, err('File write error', path=outdir))
                return {'CANCELLED'}
        
        # Collect materials to export
        materials_to_export = []
        
        if self.export_mode == 'ALL':
            materials_to_export = [mat for mat in bpy.data.materials if mat.use_nodes]
            print(f"[DEBUG] ALL mode: collected {len(materials_to_export)} materials")
        
        elif self.export_mode == 'SELECTED':
            print(f"[DEBUG] SELECTED mode: processing {len(context.selected_objects)} selected objects")
            for obj in context.selected_objects:
                print(f"[DEBUG] Processing object: {obj.name} (type: {obj.type})")
                
                # Collect materials from material_slots
                materials_found = []
                if hasattr(obj, 'material_slots'):
                    print(f"[DEBUG] Object {obj.name} has {len(obj.material_slots)} material slots")
                    for slot in obj.material_slots:
                        if slot.material:
                            materials_found.append(slot.material)
                            print(f"[DEBUG] Slot material: {slot.material.name}, use_nodes: {slot.material.use_nodes}")
                
                # Also check obj.data.materials for mesh objects
                if hasattr(obj, 'data') and hasattr(obj.data, 'materials'):
                    print(f"[DEBUG] Object {obj.name} data has {len(obj.data.materials)} materials")  # type: ignore
                    for mat in obj.data.materials:  # type: ignore
                        if mat and mat not in materials_found:
                            materials_found.append(mat)
                            print(f"[DEBUG] Data material: {mat.name}, use_nodes: {mat.use_nodes}")
                
                # Filter for node-based materials
                for mat in materials_found:
                    if mat.use_nodes:
                        if mat not in materials_to_export:
                            materials_to_export.append(mat)
                            print(f"[DEBUG] Added material: {mat.name}")
                        else:
                            print(f"[DEBUG] Material {mat.name} already in list")
                    else:
                        print(f"[DEBUG] Skipping material {mat.name} (no nodes)")
            print(f"[DEBUG] SELECTED mode: collected {len(materials_to_export)} materials total")
        
        elif self.export_mode == 'ACTIVE':
            if context.active_object and hasattr(context.active_object, 'material_slots'):
                print(f"[DEBUG] ACTIVE mode: processing active object {context.active_object.name}")
                for slot in context.active_object.material_slots:
                    if slot.material and slot.material.use_nodes:
                        if slot.material not in materials_to_export:
                            materials_to_export.append(slot.material)
                            print(f"[DEBUG] Added material: {slot.material.name}")
            print(f"[DEBUG] ACTIVE mode: collected {len(materials_to_export)} materials")
        
        print(f"[DEBUG] Final materials to export: {[mat.name for mat in materials_to_export]}")
        print(f"[DEBUG] Total materials found: {len(materials_to_export)}")
        
        if not materials_to_export:
            print("[DEBUG] No materials to export - check if materials have use_nodes=True")
        
        if not materials_to_export:
            self.report({'WARNING'}, msg('No items to export'))
            return {'CANCELLED'}
        
        # Remember project selection
        context.scene["_bndl_last_export_project"] = self.export_project  # type: ignore
        
        # Export with progress tracking
        success_count = 0
        failed_count = 0
        
        with ProgressTracker("Batch exporting materials", total=len(materials_to_export)) as progress:
            for i, mat in enumerate(materials_to_export):
                try:
                    # Generate filename
                    import random, string
                    tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    filename = f"S-{mat.name}-{tag}.bndl"
                    filepath = os.path.join(outdir, filename)
                    
                    # Check if file exists
                    if os.path.exists(filepath) and not self.overwrite_existing:
                        progress.update(i + 1, f"Skipped {mat.name} (file exists)")
                        continue
                    
                    # Export material using vendor/export_material.py
                    from .vendor import export_material
                    content = export_material.export_material_to_bndl(mat)
                    
                    if content:
                        # Write file
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        # Asset packing if enabled
                        if prefs.pack_assets_on_export:
                            try:
                                from .vendor import bndl_asset_pack
                                
                                # Map preference format to function parameter
                                format_map = {
                                    'BNDLPACK': 'bndlpack',
                                    'BLEND': 'blend',
                                    'HYBRID': 'hybrid'
                                }
                                pack_format = format_map.get(prefs.asset_pack_format, 'bndlpack')
                                
                                bndl_asset_pack.auto_pack_assets_for_bndl(
                                    filepath, 
                                    'MATERIAL', 
                                    source_material=mat, 
                                    pack_format=pack_format
                                )
                            except Exception as e:
                                print(f"[BNDL] Asset packing warning for {mat.name}: {e}")
                        
                        success_count += 1
                        progress.update(i + 1, f"Exported {mat.name}")
                    else:
                        failed_count += 1
                        progress.update(i + 1, f"Failed {mat.name}")
                
                except Exception as e:
                    failed_count += 1
                    progress.update(i + 1, f"Error: {mat.name}")
                    print(f"[BNDL] Batch export error for {mat.name}: {e}")
        
        # Report results
        if failed_count == 0:
            self.report({'INFO'}, msg('Batch export complete', count=success_count))
        else:
            self.report({'WARNING'}, msg('Batch export partial', success=success_count, failed=failed_count))
        
        # Refresh library
        try:
            bpy.ops.bndl.list_refresh('EXEC_DEFAULT')  # type: ignore
        except:
            pass
        
        return {'FINISHED'}


class BNDL_OT_BatchExportSelected(Operator):
    """Export selected geometry nodes trees to .bndl files"""
    bl_idname = "bndl.batch_export_selected"
    bl_label = "Batch Export Selected (Geometry)"
    bl_description = "Export geometry node trees from all selected objects to individual .bndl files"
    bl_options = {'REGISTER', 'UNDO'}
    
    export_project: EnumProperty(  # type: ignore
        name="Export to Project",
        items=_get_export_project_items,
        description="Select which project directory to export to"
    )
    
    skip_objects_without_gn: BoolProperty(  # type: ignore
        name="Skip Objects Without Geometry Nodes",
        description="Don't process objects that don't have geometry node modifiers",
        default=True
    )
    
    overwrite_existing: BoolProperty(  # type: ignore
        name="Overwrite Existing Files",
        description="Overwrite .bndl files if they already exist",
        default=False
    )
    
    def invoke(self, context, event):
        prefs = get_prefs()
        
        # Remember last selected project
        last_project = context.scene.get("_bndl_last_export_project", "NONE")  # type: ignore
        valid_projects = {item.name for item in prefs.bndl_directories} if hasattr(prefs, "bndl_directories") else set()
        
        if last_project != "NONE" and last_project in valid_projects:
            self.export_project = last_project
        
        return context.window_manager.invoke_props_dialog(self, width=400)  # type: ignore
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)  # type: ignore
        
        col.prop(self, "export_project", text="Project")
        
        if self.export_project == "NONE":
            warn = col.row()
            warn.alert = True
            warn.label(text="Select a project directory", icon='ERROR')
        
        col.separator()
        col.prop(self, "skip_objects_without_gn")
        col.prop(self, "overwrite_existing")
    
    def execute(self, context):
        # Validate project selection
        if self.export_project == "NONE":
            self.report({'ERROR'}, msg('Select project'))
            return {'CANCELLED'}
        
        # Get output directory
        prefs = get_prefs()
        outdir = ""
        if hasattr(prefs, "bndl_directories"):
            for item in prefs.bndl_directories:
                if item.name == self.export_project:
                    outdir = item.directory
                    break
        
        if not outdir:
            self.report({'ERROR'}, msg('No directory configured', project=self.export_project))
            return {'CANCELLED'}
        
        outdir = os.path.abspath(bpy.path.abspath(outdir))
        if not os.path.isdir(outdir):
            try:
                os.makedirs(outdir, exist_ok=True)
            except Exception as e:
                self.report({'ERROR'}, err('File write error', path=outdir))
                return {'CANCELLED'}
        
        # Collect objects with geometry nodes
        objects_to_export = []
        
        for obj in context.selected_objects:
            # Check for geometry node modifiers
            has_gn = False
            gn_tree = None
            
            if hasattr(obj, 'modifiers'):
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and mod.node_group:  # type: ignore
                        has_gn = True
                        gn_tree = mod.node_group  # type: ignore
                        break
            
            if has_gn or not self.skip_objects_without_gn:
                objects_to_export.append((obj, gn_tree))
        
        if not objects_to_export:
            self.report({'WARNING'}, msg('No items to export'))
            return {'CANCELLED'}
        
        # Remember project selection
        context.scene["_bndl_last_export_project"] = self.export_project  # type: ignore
        
        # Export with progress tracking
        success_count = 0
        failed_count = 0
        
        with ProgressTracker("Batch exporting geometry nodes", total=len(objects_to_export)) as progress:
            for i, (obj, gn_tree) in enumerate(objects_to_export):
                try:
                    if not gn_tree:
                        progress.update(i + 1, f"Skipped {obj.name} (no GN)")
                        continue
                    
                    # Generate filename
                    import random, string
                    tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    filename = f"G-{obj.name}-{tag}.bndl"
                    filepath = os.path.join(outdir, filename)
                    
                    # Check if file exists
                    if os.path.exists(filepath) and not self.overwrite_existing:
                        progress.update(i + 1, f"Skipped {obj.name} (file exists)")
                        continue
                    
                    # Export geometry nodes using vendor/export_geometry.py
                    from .vendor import export_geometry
                    content = export_geometry.export_geometry_nodes_to_bndl(gn_tree)
                    
                    if content:
                        # Write file
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        # Asset packing if enabled
                        if prefs.pack_assets_on_export:
                            try:
                                from .vendor import bndl_asset_pack
                                
                                format_map = {
                                    'BNDLPACK': 'bndlpack',
                                    'BLEND': 'blend',
                                    'HYBRID': 'hybrid'
                                }
                                pack_format = format_map.get(prefs.asset_pack_format, 'bndlpack')
                                
                                bndl_asset_pack.auto_pack_assets_for_bndl(
                                    filepath, 
                                    'GEOMETRY', 
                                    source_object=obj, 
                                    pack_format=pack_format
                                )
                            except Exception as e:
                                print(f"[BNDL] Asset packing warning for {obj.name}: {e}")
                        
                        success_count += 1
                        progress.update(i + 1, f"Exported {obj.name}")
                    else:
                        failed_count += 1
                        progress.update(i + 1, f"Failed {obj.name}")
                
                except Exception as e:
                    failed_count += 1
                    progress.update(i + 1, f"Error: {obj.name}")
                    print(f"[BNDL] Batch export error for {obj.name}: {e}")
        
        # Report results
        if failed_count == 0:
            self.report({'INFO'}, msg('Batch export complete', count=success_count))
        else:
            self.report({'WARNING'}, msg('Batch export partial', success=success_count, failed=failed_count))
        
        # Refresh library
        try:
            bpy.ops.bndl.list_refresh('EXEC_DEFAULT')  # type: ignore
        except:
            pass
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(BNDL_OT_BatchExportMaterials)
    bpy.utils.register_class(BNDL_OT_BatchExportSelected)
    print("[BNDL] Batch export operators registered")


def unregister():
    bpy.utils.unregister_class(BNDL_OT_BatchExportSelected)
    bpy.utils.unregister_class(BNDL_OT_BatchExportMaterials)
