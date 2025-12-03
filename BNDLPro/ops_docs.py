"""
Documentation viewer for BNDL-Pro.
Displays user-facing documentation in a popup window with tab switching.
Uses Blender Text blocks for true scrollable content.
"""

import bpy  # type: ignore
import os
from pathlib import Path

# Global state for current doc (persists across redraws)
_current_doc_index = 0
_doc_text_blocks = {}  # Cache of created text blocks

def get_user_docs_path():
    """Get path to user_docs folder."""
    addon_dir = Path(__file__).parent
    return addon_dir / "user_docs"

def get_doc_files():
    """Get list of essential user-facing documentation files."""
    docs_path = get_user_docs_path()
    if not docs_path.exists():
        return []
    
    # Only include essential user-focused docs (in order of importance)
    essential_docs = [
        ("README.md", "Welcome"),
        ("USAGE_GUIDE.md", "Getting Started"),
        ("QUICK_REFERENCE.md", "Quick Reference"),
        ("PREFERENCES.md", "Preferences"),
        ("ASSET_BUNDLING_FEATURE.md", "Asset Bundling"),
        ("STUDIO_LICENSE_SETUP.md", "Studio Licensing"),
    ]
    
    doc_list = []
    for filename, display_name in essential_docs:
        filepath = docs_path / filename
        if filepath.exists():
            doc_list.append((filename.replace('.md', ''), display_name, str(filepath)))
    
    return doc_list

def read_doc_file(filepath):
    """Read and return documentation file content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading documentation: {str(e)}"

def load_doc_to_text_block(name, filepath):
    """Load documentation into a Blender text block for scrollable viewing."""
    global _doc_text_blocks
    
    # Use a consistent naming scheme
    text_name = f"BNDL_DOC_{name}"
    
    # Check if already loaded
    if text_name in bpy.data.texts:
        text_block = bpy.data.texts[text_name]
    else:
        # Create new text block
        text_block = bpy.data.texts.new(text_name)
        text_block.use_fake_user = True  # Keep it around
    
    # Load content
    content = read_doc_file(filepath)
    text_block.clear()
    text_block.write(content)
    
    _doc_text_blocks[name] = text_block
    return text_block

def set_active_doc(index):
    """Set the currently active documentation index."""
    global _current_doc_index
    _current_doc_index = index

def get_active_doc():
    """Get the currently active documentation index."""
    global _current_doc_index
    return _current_doc_index

def cleanup_doc_text_blocks():
    """Remove all documentation text blocks."""
    global _doc_text_blocks
    for name, text_block in _doc_text_blocks.items():
        if text_block and text_block.name in bpy.data.texts:
            bpy.data.texts.remove(text_block)
    _doc_text_blocks.clear()

class BNDL_OT_ShowDocumentation(bpy.types.Operator):
    """Show BNDL-Pro documentation in a scrollable text viewer"""
    bl_idname = "bndl.show_documentation"
    bl_label = "BNDL-Pro Documentation"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Reset to first doc on open
        set_active_doc(0)
        
        # Load all docs into text blocks
        doc_files = get_doc_files()
        for name, display_name, filepath in doc_files:
            load_doc_to_text_block(name, filepath)
        
        return context.window_manager.invoke_props_dialog(self, width=950)  # type: ignore
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False  # type: ignore
        layout.use_property_decorate = False  # type: ignore
        
        # Get available docs
        doc_files = get_doc_files()
        
        if not doc_files:
            layout.label(text="No documentation files found!", icon='ERROR')  # type: ignore
            layout.label(text="Please ensure user_docs folder exists.")  # type: ignore
            return
        
        # Get current active index
        active_idx = get_active_doc()
        
        # Ensure valid index
        if active_idx < 0 or active_idx >= len(doc_files):
            active_idx = 0
            set_active_doc(0)
        
        # Get current doc
        current_name, current_display, current_path = doc_files[active_idx]
        
        # Create main column
        col = layout.column(align=True)  # type: ignore
        
        # Tab row
        tab_row = col.row(align=True)
        tab_row.scale_y = 1.2
        
        for idx, (name, display_name, filepath) in enumerate(doc_files):
            is_active = (idx == active_idx)
            tab_btn = tab_row.operator("bndl.switch_doc", text=display_name, depress=is_active)
            tab_btn.doc_index = idx
        
        col.separator(factor=0.5)
        
        # Get text block for current doc
        text_block = _doc_text_blocks.get(current_name)
        
        if text_block and text_block.name in bpy.data.texts:
            # Create fixed-height box with text preview
            box = col.box()
            text_col = box.column(align=True)
            text_col.scale_y = 0.65
            
            # Display text lines (with fixed height)
            lines = text_block.as_string().split('\n')
            display_lines = 65  # Fixed height
            
            for i in range(display_lines):
                if i < len(lines):
                    line = lines[i]
                    # Basic markdown formatting
                    if line.startswith('# ') and not line.startswith('## '):
                        text_col.label(text=line[2:], icon='BOOKMARKS')
                    elif line.startswith('## '):
                        text_col.label(text=f"  {line[3:]}", icon='THREE_DOTS')
                    elif line.startswith('### '):
                        text_col.label(text=f"    {line[4:]}")
                    elif line.strip().startswith(('- ', '* ')):
                        text_col.label(text=f"  • {line.strip()[2:]}")
                    elif line.strip().startswith('```'):
                        text_col.label(text="")
                    elif line.strip():
                        text_col.label(text=line)
                    else:
                        text_col.label(text="")
                else:
                    text_col.label(text="")
            
            # Show scroll hint if content is longer
            if len(lines) > display_lines:
                col.separator(factor=0.3)
                hint_row = col.row()
                hint_row.alignment = 'CENTER'
                op = hint_row.operator("bndl.open_doc_in_editor", text=f"Open in Text Editor for Full Content ({len(lines)} lines)", icon='TEXT')
                op.doc_name = current_name
        else:
            col.label(text="Error loading documentation", icon='ERROR')


class BNDL_OT_SwitchDoc(bpy.types.Operator):
    """Switch to a different documentation file"""
    bl_idname = "bndl.switch_doc"
    bl_label = "Switch Documentation"
    bl_options = {'INTERNAL'}
    
    doc_index: bpy.props.IntProperty()  # type: ignore
    
    def execute(self, context):
        # Update the global state
        set_active_doc(self.doc_index)
        
        # Force UI refresh by triggering a redraw
        for window in context.window_manager.windows:  # type: ignore
            for area in window.screen.areas:  # type: ignore
                area.tag_redraw()
        
        return {'FINISHED'}


class BNDL_OT_OpenDocInEditor(bpy.types.Operator):
    """Open documentation in Text Editor for full scrollable view"""
    bl_idname = "bndl.open_doc_in_editor"
    bl_label = "Open in Text Editor"
    bl_options = {'INTERNAL'}
    
    doc_name: bpy.props.StringProperty()  # type: ignore
    
    def execute(self, context):
        # Get the text block
        text_block = _doc_text_blocks.get(self.doc_name)
        
        if not text_block or text_block.name not in bpy.data.texts:
            self.report({'ERROR'}, "Documentation not found")
            return {'CANCELLED'}
        
        # Find or create a Text Editor area
        text_area = None
        for area in context.screen.areas:  # type: ignore
            if area.type == 'TEXT_EDITOR':
                text_area = area
                break
        
        if text_area:
            # Use existing Text Editor
            text_area.spaces.active.text = text_block  # type: ignore
            text_area.spaces.active.show_line_numbers = False  # type: ignore
            text_area.spaces.active.show_word_wrap = True  # type: ignore
        else:
            # Try to split current area
            try:
                bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
                new_area = context.screen.areas[-1]  # type: ignore
                new_area.type = 'TEXT_EDITOR'
                new_area.spaces.active.text = text_block  # type: ignore
                new_area.spaces.active.show_line_numbers = False  # type: ignore
                new_area.spaces.active.show_word_wrap = True  # type: ignore
            except:
                # Fallback: just set it in current space if possible
                self.report({'INFO'}, f"Opened {text_block.name} - Switch to Text Editor to view")
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(BNDL_OT_SwitchDoc)
    bpy.utils.register_class(BNDL_OT_OpenDocInEditor)
    bpy.utils.register_class(BNDL_OT_ShowDocumentation)

def unregister():
    cleanup_doc_text_blocks()
    bpy.utils.unregister_class(BNDL_OT_ShowDocumentation)
    bpy.utils.unregister_class(BNDL_OT_OpenDocInEditor)
    bpy.utils.unregister_class(BNDL_OT_SwitchDoc)
