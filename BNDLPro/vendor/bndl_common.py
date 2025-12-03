# bndl_common.py — Shared utilities for multi-tree BNDL support
# Handles common functionality across Geometry, Material, and Compositor exports/replays

import bpy
import re
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any

class TreeType(Enum):
    """Supported node tree types in BNDL format."""
    GEOMETRY = "GEOMETRY"
    MATERIAL = "MATERIAL" 
    COMPOSITOR = "COMPOSITOR"

# BNDL Format Version
BNDL_VERSION = "1.4"  # Updated to support material node groups

# Datablock sentinels (shared across all tree types)
DATABLOCK_SENTINELS = {
    "Material": ("❆", "❆"),
    "Object": ("⊞", "⊞"),
    "Collection": ("✸", "✸"),
    "Image": ("✷", "✷"),
    "Mesh": ("⧉", "⧉"),
    "Curve": ("𝒞", "𝒞"),
    "Text": ("🔤", "🔤"),
    "Armature": ("🦴", "🦴"),
    "Camera": ("📷", "📷"),
    "Light": ("💡", "💡"),
}

def get_addon_preferences():
    """Get BNDL addon preferences, returning None if not found."""
    try:
        import bpy
        return bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    except Exception:
        return None

def format_number(x, ndigits=3):
    """Format a float for BNDL output with at most `ndigits` decimal places.
    Trim trailing zeros and a trailing decimal point. Keep integers stable.
    """
    try:
        f = float(x)
    except Exception:
        return str(x)
    # Use fixed-point with ndigits, then strip trailing zeros
    fmt = f"{f:.{ndigits}f}"
    txt = fmt.rstrip("0").rstrip(".")
    if txt == "-0":
        txt = "0"
    return txt

def generate_random_id(length=6):
    """Generate a random alphanumeric ID for BNDL filenames."""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def detect_tree_type(node_tree) -> TreeType:
    """Detect the type of node tree (Geometry, Material, or Compositor)."""
    if hasattr(node_tree, 'type'):
        if node_tree.type == 'GEOMETRY':
            return TreeType.GEOMETRY
        elif node_tree.type == 'SHADER':
            return TreeType.MATERIAL
        elif node_tree.type == 'COMPOSITING':
            return TreeType.COMPOSITOR
    
    # Fallback: try to detect by context
    if hasattr(bpy.context, 'object') and bpy.context.object:
        if hasattr(bpy.context.object, 'modifiers'):
            return TreeType.GEOMETRY
        elif hasattr(bpy.context.object, 'material_slots'):
            return TreeType.MATERIAL
    
    return TreeType.GEOMETRY  # Default fallback

def get_file_prefix(tree_type: TreeType) -> str:
    """Get the filename prefix for a tree type."""
    prefixes = {
        TreeType.GEOMETRY: "G-",
        TreeType.MATERIAL: "S-",  # S for Shader
        TreeType.COMPOSITOR: "C-"
    }
    return prefixes.get(tree_type, "G-")

def parse_tree_type_header(bndl_content: str) -> Optional[TreeType]:
    """Parse the Tree_Type header from BNDL content."""
    lines = bndl_content.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line.startswith('Tree_Type:'):
            type_str = line.split(':', 1)[1].strip()
            try:
                return TreeType(type_str)
            except ValueError:
                pass
    return None  # No header found or invalid type

def parse_node_tree_name_header(bndl_content: str) -> Optional[str]:
    """Parse the Node_Tree header from BNDL content."""
    lines = bndl_content.split('\n')
    for line in lines[:15]:  # Check first 15 lines
        line = line.strip()
        if line.startswith('# Node_Tree:'):
            name_str = line.split(':', 1)[1].strip()
            return name_str
    return None  # No header found or invalid type

def create_bndl_header(tree_type: TreeType, node_tree_name: str = "", node_count: int = 0) -> str:
    """Create the BNDL header for a file."""
    import datetime
    
    header_lines = [
        f"# BNDL Export v{BNDL_VERSION}",
        f"Tree_Type: {tree_type.value}",
        f"# Blender_Version: {bpy.app.version_string}",
        f"# Export_Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    
    if node_tree_name:
        header_lines.append(f"# Node_Tree: {node_tree_name}")
    
    if node_count > 0:
        header_lines.append(f"# Node_Count: {node_count}")
    
    header_lines.append("")  # Empty line after header
    return '\n'.join(header_lines)

def serialize_datablock_reference(datablock, db_type: str) -> str:
    """Serialize a datablock reference using sentinels."""
    if not datablock:
        return '""'
    
    sentinels = DATABLOCK_SENTINELS.get(db_type, ("❓", "❓"))
    start, end = sentinels
    return f'"{start}{datablock.name}{end}"'

def get_socket_default_value(socket):
    """Get the default value of a node socket, formatted for BNDL."""
    if not hasattr(socket, 'default_value'):
        return None
    
    default = socket.default_value
    
    # Handle different socket types
    if hasattr(socket, 'type'):
        if socket.type in ('VALUE', 'INT', 'FACTOR'):
            return format_number(default)
        elif socket.type == 'BOOLEAN':
            return str(default).lower()
        elif socket.type == 'VECTOR':
            if hasattr(default, '__len__') and len(default) >= 3:
                return f"<{format_number(default[0])}, {format_number(default[1])}, {format_number(default[2])}>"
        elif socket.type in ('RGBA', 'COLOR'):
            if hasattr(default, '__len__') and len(default) >= 3:
                r, g, b = default[0], default[1], default[2]
                a = default[3] if len(default) > 3 else 1.0
                return f"<{format_number(r)}, {format_number(g)}, {format_number(b)}, {format_number(a)}>"
        elif socket.type == 'STRING':
            return f'"{default}"'
    
    # Fallback for unknown types
    return str(default)

def clean_node_name(name: str) -> str:
    """Clean a node name for use in BNDL format."""
    # Remove problematic characters, keep alphanumeric, spaces, dots, underscores
    cleaned = re.sub(r'[^\w\s\.-]', '', name)
    return cleaned.strip()

def get_node_variant(node) -> str:
    """Get the variant string for a node (used in Create statements)."""
    if hasattr(node, 'node_tree') and node.node_tree:
        return node.node_tree.name
    elif hasattr(node, 'operation'):
        return node.operation
    elif hasattr(node, 'mode'):
        return node.mode
    elif hasattr(node, 'blend_type'):
        return node.blend_type
    elif hasattr(node, 'data_type'):
        return node.data_type
    else:
        return ""

def validate_tree_type_compatibility(tree_type: TreeType, node_tree) -> bool:
    """Validate that a node tree is compatible with the specified tree type."""
    detected_type = detect_tree_type(node_tree)
    return detected_type == tree_type

class BNDLExportError(Exception):
    """Exception raised during BNDL export operations."""
    pass

class BNDLImportError(Exception):
    """Exception raised during BNDL import operations."""
    pass

# Socket type mappings (tree-type specific)
GEOMETRY_SOCKET_TYPES = {
    'NodeSocketGeometry': 'GEOMETRY',
    'NodeSocketFloat': 'VALUE',
    'NodeSocketFloatFactor': 'FACTOR',
    'NodeSocketInt': 'INT',
    'NodeSocketBool': 'BOOLEAN',
    'NodeSocketVector': 'VECTOR',
    'NodeSocketColor': 'RGBA',
    'NodeSocketString': 'STRING',
    'NodeSocketMaterial': 'MATERIAL',
    'NodeSocketObject': 'OBJECT',
    'NodeSocketCollection': 'COLLECTION',
    'NodeSocketTexture': 'TEXTURE',
    'NodeSocketImage': 'IMAGE',
}

MATERIAL_SOCKET_TYPES = {
    'NodeSocketShader': 'SHADER',
    'NodeSocketBSDF': 'BSDF',
    'NodeSocketFloat': 'VALUE',
    'NodeSocketFloatFactor': 'FACTOR',
    'NodeSocketColor': 'RGBA',
    'NodeSocketVector': 'VECTOR',
    'NodeSocketString': 'STRING',
    'NodeSocketBool': 'BOOLEAN',
}

COMPOSITOR_SOCKET_TYPES = {
    'NodeSocketColor': 'RGBA',
    'NodeSocketFloat': 'VALUE',
    'NodeSocketFloatFactor': 'FACTOR',
    'NodeSocketInt': 'INT',
    'NodeSocketBool': 'BOOLEAN',
    'NodeSocketVector': 'VECTOR',
    'NodeSocketString': 'STRING',
}

def get_socket_type_mapping(tree_type: TreeType) -> Dict[str, str]:
    """Get the socket type mapping for a specific tree type."""
    mappings = {
        TreeType.GEOMETRY: GEOMETRY_SOCKET_TYPES,
        TreeType.MATERIAL: MATERIAL_SOCKET_TYPES,
        TreeType.COMPOSITOR: COMPOSITOR_SOCKET_TYPES,
    }
    return mappings.get(tree_type, GEOMETRY_SOCKET_TYPES)