import bpy  # type: ignore
from bpy.types import AddonPreferences, PropertyGroup  # type: ignore
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty  # type: ignore

class BNDL_DirectoryItem(PropertyGroup):
    """Individual directory entry for multi-project support."""
    name: StringProperty(
        name="Project Name",
        description="Project Name",
        default="Project"
    )  # type: ignore
    directory: StringProperty(
        name="Directory",
        subtype='DIR_PATH',
        description="Directory",
        default=""
    )  # type: ignore
    
    # Per-project export presets (override global settings)
    use_project_presets: BoolProperty(
        name="Use Project-Specific Presets",
        description="Override global export settings with project-specific presets",
        default=False
    )  # type: ignore
    project_prefix_1: StringProperty(
        name="Project Prefix 1",
        description="Project-specific name prefix 1",
        default=""
    )  # type: ignore
    project_prefix_2: StringProperty(
        name="Project Prefix 2", 
        description="Project-specific name prefix 2",
        default=""
    )  # type: ignore
    project_suffix_1: StringProperty(
        name="Project Suffix 1",
        description="Project-specific name suffix 1",
        default=""
    )  # type: ignore
    project_notes: StringProperty(
        name="Project Notes",
        description="Project-specific export notes",
        default=""
    )  # type: ignore


class BNDL_RecentFileItem(PropertyGroup):
    """Recently used .bndl file entry."""
    filepath: StringProperty(
        name="File Path",
        description="Full path to .bndl file",
        default=""
    )  # type: ignore
    filename: StringProperty(
        name="File Name",
        description="Display name of .bndl file",
        default=""
    )  # type: ignore
    timestamp: StringProperty(
        name="Last Used",
        description="Last time this file was used",
        default=""
    )  # type: ignore


class BNDL_FavoriteItem(PropertyGroup):
    """Favorite .bndl file entry."""
    filepath: StringProperty(
        name="File Path",
        description="Full path to favorite .bndl file",
        default=""
    )  # type: ignore
    filename: StringProperty(
        name="File Name",
        description="Display name of favorite file",
        default=""
    )  # type: ignore

class BNDL_AddonPrefs(AddonPreferences):
    bl_idname = __package__  # type: ignore

    # License key (Pro features)
    license_email: StringProperty(
        name="Email",
        description="License email",
        default=""
    )  # type: ignore
    
    license_key: StringProperty(
        name="License Key",
        description="License key",
        default="",
        subtype='PASSWORD'
    )  # type: ignore
    
    license_validated: BoolProperty(
        name="License Validated",
        description="License Validated",
        default=False,
        options={'HIDDEN'}
    )  # type: ignore

    # Preference priority control
    prefer_user_prefs: BoolProperty(
        name="Prefer User Preferences",
        description="Prefer user prefs",
        default=False
    )  # type: ignore

    name_prefix_1: StringProperty(name="Name Prefix 1", default="")  # type: ignore
    name_prefix_2: StringProperty(name="Name Prefix 2", default="")  # type: ignore
    name_suffix_1: StringProperty(name="Name Suffix 1", default="")  # type: ignore
    
    # Multi-project directory support
    bndl_directories: CollectionProperty(
        type=BNDL_DirectoryItem,
        name="BNDL Directories",
        description="BNDL Directories"
    )  # type: ignore
    bndl_directories_index: bpy.props.IntProperty(default=0)  # type: ignore
    
    # Recently used files tracking
    recent_files: CollectionProperty(
        type=BNDL_RecentFileItem,
        name="Recent Files",
        description="Recently used .bndl files"
    )  # type: ignore
    max_recent_files: IntProperty(
        name="Max Recent Files",
        description="Maximum number of recent files to track",
        default=10,
        min=3,
        max=50
    )  # type: ignore
    
    # Favorites system
    favorite_files: CollectionProperty(
        type=BNDL_FavoriteItem,
        name="Favorite Files",
        description="Favorite .bndl files for quick access"
    )  # type: ignore

    overall_notes: StringProperty(
        name="Overall Notes",
        description="Export notes",
        default=""
    )  # type: ignore

    keep_replay_text: BoolProperty(
        name="Keep Replay Text",
        description="Keep replay text",
        default=False
    )  # type: ignore

    round_float_precision: BoolProperty(
        name="Round Float Precision",
        description="Round float precision",
        default=True
    )  # type: ignore
    
    asset_dependency_mode: EnumProperty(
        name="Asset Dependencies",
        description="Asset dependency mode",
        items=[
            ('NONE', "None", "Don't include any asset dependencies - node tree only", 'CANCEL', 0),
            ('PROXIES', "Proxies", "Create placeholder (proxy) objects/materials by name (current behavior)", 'GHOST_ENABLED', 1),
            ('APPEND_ASSETS', "Bundle Assets", "Export referenced assets to matching .blend file and append on import", 'PACKAGE', 2),
        ],
        default='PROXIES'
    )  # type: ignore
    
    # Asset packing for images/textures
    pack_assets_on_export: BoolProperty(
        name="Pack Assets with Export",
        description="Pack assets toggle",
        default=True
    )  # type: ignore
    
    asset_pack_format: EnumProperty(
        name="Asset Pack Format",
        description="Asset pack format",
        items=[
            ('BNDLPACK', ".bndlpack (ZIP)", "ZIP file with images + manifest.json - portable, easy to inspect", 'FILE_ARCHIVE', 0),
            ('BLEND', ".blend Asset File", "Minimal .blend file with packed images - native Blender format", 'FILE_BLEND', 1),
            ('HYBRID', "Both Formats", "Export both .bndlpack and _assets.blend for maximum compatibility", 'DUPLICATE', 2),
        ],
        default='BNDLPACK'
    )  # type: ignore
    
    auto_unpack_assets_on_replay: BoolProperty(
        name="Auto-Unpack Assets on Replay",
        description="Auto-unpack toggle",
        default=True
    )  # type: ignore
    
    # Safety settings for shared environments
    allow_file_delete: BoolProperty(
        name="Allow File Deletion",
        description="Allow users to delete .bndl files from the library browser (disable in shared environments)",
        default=True
    )  # type: ignore


    def draw(self, ctx):
        layout = self.layout
        
        # Import i18n utilities
        try:
            from . import i18n_utils as i18n
        except:
            i18n = None  # Fallback if i18n not available
        
        # Helper function for safe translation
        def _(key, category='UI'):
            if i18n:
                return i18n.get_text(category, key)
            return key
        
        # ========== LICENSE SECTION ==========
        from . import license as lic
        
        # Check if this is Lite version (check build configuration, not runtime license)
        # Import from package namespace to get the constant
        import sys
        package_name = __package__.split('.')[0]
        package_module = sys.modules.get(package_name)
        is_lite = getattr(package_module, 'BNDL_LITE_VERSION', False) if package_module else False
        is_pro = lic.is_pro_version()
        
        # ========== HERO SECTION ==========
        hero_box = layout.box()
        hero_split = hero_box.split(factor=0.2, align=False)
        
        # Left: Logo
        left_col = hero_split.column(align=True)
        try:
            import os
            import bpy
            addon_dir = os.path.dirname(os.path.realpath(__file__))
            hero_path = os.path.join(addon_dir, "hero.png")
            if os.path.exists(hero_path):
                # Load and display hero image
                img = bpy.data.images.load(hero_path, check_existing=True)
                # Ensure preview is generated
                try:
                    img.preview_ensure()
                except Exception:
                    pass
                # Get icon ID from preview
                icon_id = getattr(getattr(img, "preview", None), "icon_id", 0)
                if icon_id:
                    left_col.template_icon(icon_value=icon_id, scale=5.0)
                else:
                    left_col.label(text="BNDL", icon='NODE_MATERIAL')
            else:
                left_col.label(text="BNDL", icon='NODE_MATERIAL')
        except Exception as e:
            # Fallback if image can't be loaded
            left_col.label(text="BNDL", icon='NODE_MATERIAL')

        
        # Right: Description
        right_col = hero_split.column(align=True)
        right_col.label(text="BNDL Lite at a glance:", icon='INFO')
        right_col.label(text="• Export and replay Material node trees to .bndl format")
        right_col.label(text="• Version control friendly, human-readable text format")
        right_col.label(text="• Multi-project browser for quick access")
        right_col.label(text="• Upgrade to Pro for Geometry Nodes and Compositor support")
        
        layout.separator()
        

        if is_lite:
            # Lite version branding
            box = layout.box()
            col = box.column(align=True)
            col.label(text="🎨 BNDL Lite (Materials Only)", icon='MATERIAL')
            col.separator()
            
            # Feature comparison - 2 column layout
            split = col.split(factor=0.5, align=True)
            
            # Left column: Included Features
            left_col = split.column(align=True)
            left_col.label(text="Included Features:", icon='CHECKMARK')
            left_col.label(text="  ✓ Material/Shader export & replay")
            left_col.label(text="  ✓ Frame support")
            left_col.label(text="  ✓ Nested node groups")
            left_col.label(text="  ✓ Version control friendly")
            
            # Right column: Pro Features
            right_col = split.column(align=True)
            right_col.label(text="Pro Features (Upgrade Required):", icon='ERROR')
            right_col.label(text="  ✗ Geometry Nodes export/replay")
            right_col.label(text="  ✗ Compositor Nodes export/replay")
            right_col.label(text="  ✗ Asset bundling (no proxies)")

            col.separator()
            
            # Upgrade CTA
            row = col.row(align=True)
            row.scale_y = 1.5
            op = row.operator("wm.url_open", text="Upgrade to Pro ($20)", icon='FUND')
            op.url = "https://kyoseigk.gumroad.com"
            
            row = col.row(align=True)
            op = row.operator("wm.url_open", text="Bulk Licensing", icon='COMMUNITY')
            op.url = "mailto:contact@kyoseigk.com?subject=BNDL Pro Bulk License Inquiry"
            
            layout.separator()
            # Continue to show project directories and other settings below
        
        # Only show license section for free users (Pro version only, not Lite)
        elif not is_pro:
            box = layout.box()
            box.label(text=_("BNDL Free Version"), icon='INFO')
            box.operator("bndl.show_license_activation", text=_("Enter License Key"), icon='LOCKED')
            layout.separator()
        
        
        # Show settings for all users (Lite and Pro)
        # if is_pro:  # DISABLED: Show settings for Lite users too
        if True:  # Always show settings
            # Preference Management Section
            box = layout.box()
            box.label(text=_("Preference Management"), icon='SETTINGS')
            
            # Show current preference source
            try:
                from . import pref_manager
                source = pref_manager.get_preference_source()
                source_icons = {"STUDIO": "COMMUNITY", "USER": "USER", "DEFAULT": "PREFERENCES"}
                source_labels = {
                    "STUDIO": _("Studio Preferences (admin-defined)"),
                    "USER": _("User Preferences (your saved settings)"),
                    "DEFAULT": _("Default Preferences (hardcoded)")
                }
                
                row = box.row()
                row.label(text=f"{_('Current Source')}: {source_labels[source]}", icon=source_icons[source])  # type: ignore
            except Exception:
                pass
            
            # Preference priority toggle (only show if both studio and user prefs exist)
            studio_exists = pref_manager.get_studio_prefs_path() is not None
            user_exists = pref_manager.get_user_prefs_path().exists()
            
            if studio_exists and user_exists:
                box.separator()
                row = box.row()
                row.prop(self, "prefer_user_prefs", text=_("Prefer User Over Studio"), toggle=True)
                help_row = box.row()
                help_row.scale_y = 0.8
                help_row.label(text=_("Toggle priority help"), icon='INFO')
                
                # Add reload button
                reload_row = box.row()
                reload_row.operator("bndl.reload_preferences", icon='FILE_REFRESH', text=_("Reload Preferences"))
            
            box.separator()
            row = box.row(align=True)
            row.operator("bndl.save_user_preferences", icon='FILE_TICK', text=_("Save User Preferences"))
            row.operator("bndl.reset_to_studio_defaults", icon='LOOP_BACK', text=_("Reset to Studio/Defaults"))
            
            if source == "USER":
                row = box.row()
                row.operator("bndl.delete_user_preferences", icon='TRASH', text=_("Delete User Preferences"))
            
            layout.separator()
            
            # Existing preference controls
            col = layout.column(align=True)
            
            # Multi-project directory management
            box = col.box()
            box.label(text=_("Project Directories"), icon='FILE_FOLDER')
            box.label(text=_("Project directory help"), icon='INFO')
            row = box.row()
            row.template_list("BNDL_UL_directories", "", self, "bndl_directories", self, "bndl_directories_index", rows=3)
            col_ops = row.column(align=True)
            col_ops.operator("bndl.add_directory", icon='ADD', text="")
            col_ops.operator("bndl.remove_directory", icon='REMOVE', text="")
            
            # Show directory path and project presets button for selected project
            if self.bndl_directories and self.bndl_directories_index < len(self.bndl_directories):
                item = self.bndl_directories[self.bndl_directories_index]
                box.prop(item, "directory", text=_("Path"))
                
                # Project presets button
                presets_row = box.row()
                op = presets_row.operator("bndl.edit_project_presets", text=_("Edit Project Presets"), icon='PREFERENCES')
                op.project_index = self.bndl_directories_index
                if item.use_project_presets:
                    presets_row.label(text="✓", icon='CHECKMARK')
            else:
                box.label(text=_("Click + to add first directory"), icon='INFO')
            
            col.separator()
            col.label(text=_("Filename Affixes"))
            grid = col.grid_flow(columns=2, even_columns=True, row_major=True)
            grid.prop(self, "name_prefix_1")
            grid.prop(self, "name_prefix_2")
            grid.prop(self, "name_suffix_1")
            col.separator()
            row = col.row()
            row.scale_y = 1.6
            row.prop(self, "overall_notes")
            col.separator()
            
            # Quick Access Settings
            box = col.box()
            box.label(text=_("Quick Access Settings"), icon='TIME')
            box.prop(self, "max_recent_files", text=_("Max Recent Files"))
            
            # Show recent files and favorites count
            info_row = box.row()
            info_row.label(text=f"{_('Recent Files')}: {len(self.recent_files)}")
            info_row.label(text=f"{_('Favorites')}: {len(self.favorite_files)}")
            
            # Clean missing favorites button
            box.operator("bndl.clean_missing_favorites", text=_("Clean Missing Favorites"), icon='TRASH')
            
            col.separator()
            col.label(text=_("Commercial replayer note"))
            col.separator()
            col.prop(self, "keep_replay_text")
            col.separator()
            col.prop(self, "round_float_precision")
            col.separator()
            
            # Asset dependency mode with Pro licensing
            from . import license as lic
            is_pro = lic.is_pro_version()
            
            row = col.row()
            row.prop(self, "asset_dependency_mode")
            
            # Show lock icon if APPEND_ASSETS selected without license
            if self.asset_dependency_mode == 'APPEND_ASSETS' and not is_pro:
                warn_row = col.row()
                warn_row.alert = True
                warn_row.label(text="⚠ " + _("Asset bundling: Pro license required"), icon='LOCKED')
                col.label(text=_("Fallback to proxies"), icon='INFO')
            
            col.separator()
            
            # Asset packing section
            box = col.box()
            box.label(text=_("Asset Packing (Images/Videos)"), icon='IMAGE_DATA')
            box.prop(self, "pack_assets_on_export", toggle=True)
            
            if self.pack_assets_on_export:
                box.prop(self, "asset_pack_format", text=_("Format"))
                
                # Show info about selected format
                info_row = box.row()
                info_row.scale_y = 0.7
                if self.asset_pack_format == 'BNDLPACK':
                    info_row.label(text=_("Portable ZIP info"), icon='INFO')
                elif self.asset_pack_format == 'BLEND':
                    info_row.label(text=_("Native Blender info"), icon='INFO')
                elif self.asset_pack_format == 'HYBRID':
                    info_row.label(text=_("Hybrid format info"), icon='INFO')
                
                box.prop(self, "auto_unpack_assets_on_replay", toggle=True)

            col.separator()
            
            # Safety settings for shared environments
            box = col.box()
            box.label(text=_("Safety Settings"), icon='LOCKED')
            box.prop(self, "allow_file_delete", text=_("Allow File Deletion"))
            help_row = box.row()
            help_row.scale_y = 0.7
            help_row.label(text=_("Disable in shared environments to prevent accidental file deletion"), icon='INFO')

def get_prefs() -> "BNDL_AddonPrefs":
    return bpy.context.preferences.addons[__package__].preferences  # type: ignore

# Operators for managing directory list
class BNDL_OT_AddDirectory(bpy.types.Operator):
    bl_idname = "bndl.add_directory"
    bl_label = "Add Directory"
    bl_description = "Add a new project directory"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        prefs = get_prefs()
        item = prefs.bndl_directories.add()
        item.name = f"Project {len(prefs.bndl_directories)}"
        prefs.bndl_directories_index = len(prefs.bndl_directories) - 1
        return {'FINISHED'}

class BNDL_OT_RemoveDirectory(bpy.types.Operator):
    bl_idname = "bndl.remove_directory"
    bl_label = "Remove Directory"
    bl_description = "Remove selected project directory"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        prefs = get_prefs()
        if prefs.bndl_directories:
            prefs.bndl_directories.remove(prefs.bndl_directories_index)
            prefs.bndl_directories_index = min(prefs.bndl_directories_index, len(prefs.bndl_directories) - 1)
        return {'FINISHED'}

class BNDL_OT_EditProjectPresets(bpy.types.Operator):
    bl_idname = "bndl.edit_project_presets"
    bl_label = "Edit Project Presets"
    bl_description = "Edit project-specific export presets"
    bl_options = {'INTERNAL'}
    
    project_index: IntProperty()  # type: ignore
    
    def execute(self, context):
        # This is a stub implementation - would open a popup or dialog for editing project presets
        self.report({'INFO'}, f"Edit presets for project {self.project_index} (not implemented)")
        return {'FINISHED'}

class BNDL_OT_ShowLicenseActivation(bpy.types.Operator):
    """Show license activation popup"""
    bl_idname = "bndl.show_license_activation"
    bl_label = "Enter License Key"
    bl_description = "Enter your BNDL-Pro license key to unlock Pro features"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        return context.window_manager.invoke_popup(self)  # type: ignore
    
    def draw(self, context):
        layout = self.layout
        
        # Import i18n utilities
        try:
            from .. import i18n_utils as i18n
        except:
            i18n = None
        
        # Helper function for safe translation
        def _(key, category='UI'):
            if i18n:
                return i18n.get_text(category, key)
            return key
        
        layout.label(text=_("Enter your BNDL-Pro License Key"), icon='LOCKED')
        layout.separator()
        
        prefs = get_prefs()
        
        # Email field (optional, for backdoor licenses)
        layout.prop(prefs, "license_email", text=_("Email (optional)"), icon='USER')
        
        # License key input
        layout.prop(prefs, "license_key", text=_("License Key"))
        
        # Activate button
        row = layout.row()
        row.operator("bndl.validate_license", text=_("Activate License"), icon='CHECKMARK')
        
        layout.separator()
        
        # Show what Pro unlocks
        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text=_("Upgrade to Pro to unlock:"))
        col.label(text="• " + _("Asset bundling feature"))
        col.label(text="• " + _("Multiple directories feature"))
        col.label(text="• " + _("Studio prefs feature"))
        col.label(text="• " + _("Advanced browser feature"))
        col.separator()
        col.label(text=_("Purchase URL"), icon='URL')


class BNDL_OT_ShowLicenseSuccess(bpy.types.Operator):
    """Show license activation success popup"""
    bl_idname = "bndl.show_license_success"
    bl_label = "License Activated!"
    bl_description = "BNDL-Pro license successfully activated"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Import i18n utilities
        try:
            from .. import i18n_utils as i18n
        except:
            i18n = None
        
        # Helper function for safe translation
        def _(key, category='UI'):
            if i18n:
                return i18n.get_text(category, key)
            return key
        
        layout.label(text=_("🎉 Welcome to BNDL-Pro!"), icon='CHECKMARK')
        layout.separator()
        
        col = layout.column(align=True)
        col.label(text=_("Your license has been successfully activated."))
        col.label(text=_("Pro features are now unlocked:"))
        col.separator()
        col.label(text="✓ " + _("Asset bundling enabled"))
        col.label(text="✓ " + _("Multiple project directories"))
        col.label(text="✓ " + _("Studio preference system"))
        col.label(text="✓ " + _("Advanced library browser"))
        
        layout.separator()
        layout.label(text=_("Thank you for supporting BNDL-Pro!"), icon='HEART')


class BNDL_OT_ValidateLicense(bpy.types.Operator):
    """Validate license key and unlock Pro features"""
    bl_idname = "bndl.validate_license"
    bl_label = "Validate License"
    bl_description = "Validate your BNDL-Pro license key with Gumroad"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        from . import license as lic
        prefs = get_prefs()
        
        key = prefs.license_key.strip()
        email = prefs.license_email.strip() if prefs.license_email else None
        
        if not key:
            self.report({'WARNING'}, "Please enter a license key")
            return {'CANCELLED'}
        
        # Check if this is first activation
        was_first_activation = not prefs.license_validated
        
        # Show progress in console
        print("[BNDL] Validating license key...")
        if email:
            print(f"[BNDL] Email provided: {email} (will check backdoor licenses)")
        
        # Pass email for backdoor license checking
        if lic.validate_license_key(key, email=email):
            prefs.license_validated = True
            self.report({'INFO'}, "✓ License activated! Pro features unlocked.")
            
            # Show success popup on first activation
            if was_first_activation:
                bpy.ops.bndl.show_license_success('INVOKE_DEFAULT')  # type: ignore
            
            # Force UI refresh
            for area in context.screen.areas:  # type: ignore
                area.tag_redraw()
        else:
            prefs.license_validated = False
            self.report({'ERROR'}, "Invalid license key. Check Console for details.")
        
        return {'FINISHED'}

class BNDL_UL_Directories(bpy.types.UIList):
    bl_idname = "BNDL_UL_directories"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon='FILE_FOLDER')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='FILE_FOLDER')

def register():
    bpy.utils.register_class(BNDL_RecentFileItem)
    bpy.utils.register_class(BNDL_FavoriteItem)
    bpy.utils.register_class(BNDL_DirectoryItem)
    bpy.utils.register_class(BNDL_OT_AddDirectory)
    bpy.utils.register_class(BNDL_OT_RemoveDirectory)
    bpy.utils.register_class(BNDL_OT_EditProjectPresets)
    bpy.utils.register_class(BNDL_OT_ShowLicenseActivation)
    bpy.utils.register_class(BNDL_OT_ShowLicenseSuccess)
    bpy.utils.register_class(BNDL_OT_ValidateLicense)
    bpy.utils.register_class(BNDL_UL_Directories)
    bpy.utils.register_class(BNDL_AddonPrefs)

def unregister():
    bpy.utils.unregister_class(BNDL_AddonPrefs)
    bpy.utils.unregister_class(BNDL_UL_Directories)
    bpy.utils.unregister_class(BNDL_OT_ValidateLicense)
    bpy.utils.unregister_class(BNDL_OT_ShowLicenseSuccess)
    bpy.utils.unregister_class(BNDL_OT_ShowLicenseActivation)
    bpy.utils.unregister_class(BNDL_OT_EditProjectPresets)
    bpy.utils.unregister_class(BNDL_OT_RemoveDirectory)
    bpy.utils.unregister_class(BNDL_OT_AddDirectory)
    bpy.utils.unregister_class(BNDL_DirectoryItem)
    bpy.utils.unregister_class(BNDL_FavoriteItem)
    bpy.utils.unregister_class(BNDL_RecentFileItem)
