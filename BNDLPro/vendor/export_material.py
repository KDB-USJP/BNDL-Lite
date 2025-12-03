# export_material.py — BNDL v1.3 Material/Shader Node Exporter
# Exports Material/Shader Node trees to .bndl format with Tree_Type header

import bpy, re
from collections import defaultdict
from .bndl_common import (
    TreeType, BNDL_VERSION, create_bndl_header, get_addon_preferences,
    format_number, generate_random_id, get_file_prefix, DATABLOCK_SENTINELS,
    BNDLExportError, clean_node_name, get_node_variant, serialize_datablock_reference,
    get_socket_default_value, MATERIAL_SOCKET_TYPES
)

try:
    from . import bndl_round
except ImportError:
    bndl_round = None

# ============= CONFIG =============
WRITE_FILE_PATH = ""  # e.g. r"H:\Exports\my_material.bndl" or "" to skip writing
TEXT_BLOCK_NAME = "BNDL_Material_Export"
TREE_TYPE = TreeType.MATERIAL  # This exporter handles Material/Shader nodes only
# ==================================

# ---------- Material-Specific Utilities ----------

def get_material_output_node(material):
    """Find the Material Output node in a material."""
    if not material or not material.node_tree:
        return None
    
    for node in material.node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL':
            return node
    return None

def get_active_material_from_object():
    """Get the active material from the currently selected object."""
    obj = bpy.context.view_layer.objects.active
    if not obj:
        return None
    
    if hasattr(obj, 'material_slots') and obj.material_slots:
        mat_index = obj.active_material_index
        if 0 <= mat_index < len(obj.material_slots):
            return obj.material_slots[mat_index].material
    
    return None

def serialize_material_socket_value(socket):
    """Serialize a material socket default value for BNDL."""
    if not hasattr(socket, 'default_value'):
        return None
    
    default = socket.default_value
    socket_type = getattr(socket, 'type', 'VALUE')
    
    # Material-specific socket types
    if socket_type == 'SHADER':
        return '"SHADER"'  # Shader connections don't have default values
    elif socket_type == 'RGBA':
        if hasattr(default, '__len__') and len(default) >= 3:
            r, g, b = default[0], default[1], default[2]
            a = default[3] if len(default) > 3 else 1.0
            return f"<{format_number(r)}, {format_number(g)}, {format_number(b)}, {format_number(a)}>"
    elif socket_type == 'VECTOR':
        if hasattr(default, '__len__') and len(default) >= 3:
            return f"<{format_number(default[0])}, {format_number(default[1])}, {format_number(default[2])}>"
    elif socket_type in ('VALUE', 'FACTOR'):
        return format_number(default)
    elif socket_type == 'BOOLEAN':
        return str(default).lower()
    elif socket_type == 'STRING':
        return f'"{default}"'
    
    # Fallback
    return str(default)

# ---------- Material Tree Export Logic ----------

class _MaterialTreeExport:
    """Export a material node tree to BNDL format."""
    
    def __init__(self, material):
        self.material = material
        self.tree = material.node_tree
        self.lines_groups = []
        self.lines_top = []
        self.node_instances = {}  # node -> instance name
        self.instance_counter = 1
        self._visited_groups = set()  # Track visited groups for depth-first export
        
    def _get_node_instance(self, node):
        """Get or create instance name for a node."""
        if node not in self.node_instances:
            clean_name = clean_node_name(node.name or node.bl_idname)
            self.node_instances[node] = f"{clean_name}#{self.instance_counter}"
            self.instance_counter += 1
        return self.node_instances[node]
    
    def _export_create_statements(self):
        """Export Create statements for all nodes."""
        for node in self.tree.nodes:
            if node.type == 'REROUTE':
                continue
                
            # Skip Group Input/Output nodes - they are created automatically during replay
            if node.bl_idname in ('NodeGroupInput', 'NodeGroupOutput'):
                continue
                
            instance = self._get_node_instance(node)
            node_type = node.bl_idname
            variant = get_node_variant(node)
            
            if variant:
                self.lines_top.append(f'Create  {node_type}  "{instance}"  "{variant}"')
            else:
                self.lines_top.append(f'Create  {node_type}  "{instance}"')

            # Add Rename statement if node has a custom label (especially for frames)
            if node.label:
                inst_num = instance.split('#')[1] if '#' in instance else '1'
                node_name = instance.split('#')[0] if '#' in instance else instance
                self.lines_top.append(f'Rename  [ {node_name} #{inst_num} ] to ~ {node.label} ~')

    def _export_set_statements(self):
        """Export Set statements for node properties."""
        for node in self.tree.nodes:
            if node.type == 'REROUTE':  # Only skip REROUTE, export FRAME locations!
                continue
            
            # Skip Group Input/Output nodes
            if node.bl_idname in ('NodeGroupInput', 'NodeGroupOutput'):
                continue
            
            instance = self._get_node_instance(node)
            set_entries = []
            
            # Export input socket default values
            for input_socket in node.inputs:
                if not input_socket.is_linked:  # Only export unconnected inputs
                    default_val = serialize_material_socket_value(input_socket)
                    if default_val is not None:
                        socket_name = input_socket.name
                        set_entries.append(f'    "{socket_name}" to {default_val}')
            
            # Export node-specific properties
            self._export_node_properties(node, set_entries)
            
            if set_entries:
                self.lines_top.append(f'Set  [ {instance} ]')
                self.lines_top.extend(set_entries)
    
    def _export_node_properties(self, node, set_entries):
        """Export node-specific properties based on node type."""
        # Handle common material node properties
        
        if node.type == 'BSDF_PRINCIPLED':
            # Principled BSDF specific properties (most are handled by inputs)
            pass
        elif node.type == 'MIX_SHADER':
            if hasattr(node, 'blend_type'):
                set_entries.append(f'    "blend_type" to "©{node.blend_type}©"')
        elif node.type == 'MIX_RGB':
            if hasattr(node, 'data_type'):
                set_entries.insert(0, f'    "data_type" to "©{node.data_type}©"')
            if hasattr(node, 'blend_type'):
                set_entries.append(f'    "blend_type" to "©{node.blend_type}©"')
            if hasattr(node, 'use_clamp'):
                set_entries.append(f'    "use_clamp" to {str(node.use_clamp).lower()}')
        elif hasattr(node, 'data_type'):
            # ShaderNodeMix data type (Float, Vector, Color) - set FIRST
            set_entries.insert(0, f'    "data_type" to "©{node.data_type}©"')
        elif node.type == 'TEX_IMAGE':
            if node.image:
                img_ref = serialize_datablock_reference(node.image, 'Image')
                set_entries.append(f'    "image" to {img_ref}')
            if hasattr(node, 'interpolation'):
                set_entries.append(f'    "interpolation" to "©{node.interpolation}©"')
        elif node.type == 'TEX_NOISE':
            if hasattr(node, 'noise_dimensions'):
                set_entries.append(f'    "noise_dimensions" to "©{node.noise_dimensions}©"')
        elif node.type == 'MAPPING':
            if hasattr(node, 'vector_type'):
                set_entries.append(f'    "vector_type" to "©{node.vector_type}©"')
        elif node.type == 'TEX_COORD':
            # Texture Coordinate node - no special properties
            pass
        
        # SPECIAL: Curve Mapping data (for nodes like RGB Curves, Color Ramp, etc.)
        if hasattr(node, "mapping") and hasattr(node.mapping, "curves"):
            # This node has curve mapping data
            for curve_idx, curve in enumerate(node.mapping.curves):
                if hasattr(curve, "points"):
                    for point_idx, point in enumerate(curve.points):
                        if hasattr(point, "location") and hasattr(point, "handle_type"):
                            # Serialize as: mapping.curve[0].points[0] = X,Y,HANDLE_TYPE
                            x, y = point.location
                            handle_type = point.handle_type
                            key = f"mapping.curve[{curve_idx}].points[{point_idx}]"
                            value = f"<{x},{y},{handle_type}>"
                            set_entries.append(f'    "{key}" to {value}')
        
        # Handle mute state (for all nodes)
        if hasattr(node, 'mute'):
            set_entries.append(f'    "mute" to {str(node.mute).lower()}')
        
        # Export node color if custom color is set
        if hasattr(node, 'use_custom_color') and node.use_custom_color:
            if hasattr(node, 'color'):
                r, g, b = node.color
                set_entries.append(f'    "use_custom_color" to true')
                set_entries.append(f'    "color" to <{format_number(r)}, {format_number(g)}, {format_number(b)}>')
        
        # Handle location (for all nodes)
        if hasattr(node, 'location'):
            x, y = node.location
            # For frames with parents, convert absolute position to relative
            if node.type == 'FRAME' and hasattr(node, 'parent') and node.parent:
                # Recursively subtract parent locations to get relative position
                current_parent = node.parent
                while current_parent:
                    px, py = current_parent.location if hasattr(current_parent, 'location') else (0, 0)
                    x -= px  # SUBTRACT, not add!
                    y -= py  # SUBTRACT, not add!
                    current_parent = current_parent.parent if hasattr(current_parent, 'parent') else None
            set_entries.append(f'    "location" to <{format_number(x)}, {format_number(y)}>')
    
    def _export_connect_statements(self):
        """Export Connect statements for node links."""
        for link in self.tree.links:
            from_node = link.from_node
            to_node = link.to_node
            
            if from_node.type in ('FRAME', 'REROUTE') or to_node.type in ('FRAME', 'REROUTE'):
                continue
            
            # Skip connections involving Group Input/Output nodes
            if (from_node.bl_idname in ('NodeGroupInput', 'NodeGroupOutput') or 
                to_node.bl_idname in ('NodeGroupInput', 'NodeGroupOutput')):
                continue
            
            from_instance = self._get_node_instance(from_node)
            to_instance = self._get_node_instance(to_node)
            
            # Handle duplicate socket names by adding [n] suffix
            from_socket = self._get_socket_display_name(from_node.outputs, link.from_socket)
            to_socket = self._get_socket_display_name(to_node.inputs, link.to_socket)
            
            self.lines_top.append(f'Connect  "{from_instance}"  "{from_socket}"  to  "{to_instance}"  "{to_socket}"')

    def _export_frame_parenting(self):
        """Export Parent statements for frames."""
        for node in self.tree.nodes:
            if node.type == 'REROUTE':
                continue
            if hasattr(node, 'parent') and node.parent and node.parent.type == 'FRAME':
                child_instance = self._get_node_instance(node)
                parent_instance = self._get_node_instance(node.parent)
                self.lines_top.append(f'Parent [ {child_instance} ] to [ {parent_instance} ]')

    def _get_socket_display_name(self, socket_collection, target_socket):
        """Get display name for a socket, adding [n] suffix if name is duplicated."""
        base_name = target_socket.name
        
        # Count sockets with the same name and find which index this socket is
        same_name_sockets = [s for s in socket_collection if s.name == base_name]
        
        # If only one socket with this name, return the base name
        if len(same_name_sockets) == 1:
            return base_name
        
        # Multiple sockets with same name - find the index (1-based)
        for i, sock in enumerate(same_name_sockets, start=1):
            if sock == target_socket:
                return f"{base_name}[{i}]"
        
        # Fallback (should never happen)
        return base_name

    
    def _export_top(self):
        """Export the main material tree."""
        # First, recursively export all child groups (depth-first)
        for n in self.tree.nodes:
            if n.type == 'GROUP' and hasattr(n, 'node_tree') and n.node_tree:
                self._export_group_block(n.node_tree)

        self._export_create_statements()
        self._export_set_statements()
        self._export_connect_statements()
        self._export_frame_parenting()

    def _export_group_block(self, ng):
        """Export a node group block (depth-first)."""
        gname = ng.name
        if gname in self._visited_groups:
            return
        self._visited_groups.add(gname)

        # First, recursively export any child groups
        for n in ng.nodes:
            if n.type == 'GROUP' and hasattr(n, 'node_tree') and n.node_tree:
                self._export_group_block(n.node_tree)

        # Filter out frame nodes
        nodes = [n for n in ng.nodes if n.type != 'REROUTE']
        enum = self._enumerate_nodes(nodes)

        out = [f"START GROUP NAMED {gname}"]

        # Create statements
        for n in nodes:
            typ, nid = enum[n]
            if n.type == 'GROUP':
                ref_name = n.node_tree.name if hasattr(n, 'node_tree') and n.node_tree else "Unnamed"
                out.append(f'Create  [ Group |  | ] ~ {ref_name} ~ #{nid} ; type={n.bl_idname}')
            else:
                variant = get_node_variant(n) or '—'
                friendly = (n.label or "").strip()
                out.append(f'Create  [ {typ} | {variant} | ] ~ {friendly} ~ #{nid} ; type={n.bl_idname}')
            
            # Rename if custom label
            if n.label:
                out.append(f"Rename  [ {typ} #{nid} ] to ~ {n.label} ~")

        # Declare Inputs/Outputs (group interface)
        if hasattr(ng, 'interface') and ng.interface:
            inputs = []
            outputs = []
            
            # Get interface items - ensure unique names by appending numbers to duplicates
            input_counts = {}
            output_counts = {}
            
            for item in ng.interface.items_tree:
                if hasattr(item, 'in_out'):
                    socket_name = getattr(item, 'name', 'Unknown')
                    socket_type = getattr(item, 'socket_type', 'NodeSocketColor')
                    
                    if item.in_out == 'INPUT':
                        count = input_counts.get(socket_name, 0)
                        input_counts[socket_name] = count + 1
                        if count > 0:
                            socket_name = f"{socket_name}.{count}"
                        inputs.append(f"{socket_name}:{socket_type}")
                    elif item.in_out == 'OUTPUT':
                        count = output_counts.get(socket_name, 0)
                        output_counts[socket_name] = count + 1
                        if count > 0:
                            socket_name = f"{socket_name}.{count}"
                        outputs.append(f"{socket_name}:{socket_type}")
            
            if inputs:
                out.append(f"Declare Inputs  [ Group Input ]  ~~ " + " | ".join(inputs))
            if outputs:
                out.append(f"Declare Outputs  [ Group Output ]  ~~ " + " | ".join(outputs))

        # Export node settings
        for n in nodes:
            typ, nid = enum[n]
            set_entries = []
            
            # Export input socket default values
            for input_socket in n.inputs:
                if not input_socket.is_linked:
                    default_val = serialize_material_socket_value(input_socket)
                    if default_val is not None:
                        socket_name = input_socket.name
                        set_entries.append(f'    "{socket_name}" to {default_val}')
            
            # Export node-specific properties
            self._export_node_properties_for_group(n, set_entries)
            
            # Always export location
            if hasattr(n, 'location'):
                x, y = n.location
                set_entries.append(f'    "location" to <{format_number(x)}, {format_number(y)}>')
            
            if set_entries:
                out.append(f'Set  [ {typ} #{nid} ]')
                out.extend(set_entries)

        # Export connections within group
        processed_connections = set()
        
        for link in ng.links:
            from_node = link.from_node
            to_node = link.to_node
            
            # Skip frame nodes
            if from_node.type == 'REROUTE' or to_node.type == 'REROUTE':
                continue
            
            # Walk through reroute chains
            actual_from_socket = self._walk_reroute_chain_backward(link.from_socket)
            actual_to_socket = self._walk_reroute_chain_forward(link.to_socket)
            
            if not actual_from_socket or not actual_to_socket:
                continue
                
            actual_from_node = actual_from_socket.node
            actual_to_node = actual_to_socket.node
            
            # Skip if either end is still a reroute
            if actual_from_node.type == 'REROUTE' or actual_to_node.type == 'REROUTE':
                continue
            
            # Avoid duplicate connections
            connection_key = (actual_from_node, actual_from_socket.name, 
                            actual_to_node, actual_to_socket.name)
            if connection_key in processed_connections:
                continue
            processed_connections.add(connection_key)
            
            from_typ, from_nid = enum.get(actual_from_node, ('Unknown', 0))
            to_typ, to_nid = enum.get(actual_to_node, ('Unknown', 0))
            
            # Handle duplicate socket names by adding [n] suffix
            from_socket_name = self._get_socket_display_name(actual_from_node.outputs, actual_from_socket)
            to_socket_name = self._get_socket_display_name(actual_to_node.inputs, actual_to_socket)
            
            out.append(f'Connect  [ {from_typ} #{from_nid} ]  ○  {from_socket_name}  to  [ {to_typ} #{to_nid} ]  ⦿  {to_socket_name}')

        # Export frame parenting
        for n in nodes:
            if hasattr(n, 'parent') and n.parent and n.parent.type == 'FRAME':
                parent_typ, parent_nid = enum.get(n.parent, ('Unknown', 0))
                child_typ, child_nid = enum.get(n, ('Unknown', 0))
                out.append(f'Parent [ {child_typ} #{child_nid} ] to [ {parent_typ} #{parent_nid} ]')

        out.append(f"END GROUP NAMED {gname}")
        self.lines_groups.extend(out)
        self.lines_groups.append("")  # Empty line after group
                
    def _enumerate_nodes(self, nodes):
        """Create node enumeration similar to main export system."""
        counts = {}
        idx = {}
        for n in nodes:
            # Use custom label if available, otherwise use node name
            display_name = n.label if n.label else (n.name or n.bl_idname)
            clean_name = clean_node_name(display_name)
            counts[clean_name] = counts.get(clean_name, 0) + 1
            idx[n] = (clean_name, counts[clean_name])
        return idx
    
    def run(self):
        """Run the export and return BNDL text."""
        if not self.tree:
            raise BNDLExportError("Material has no node tree")
        
        # Create header
        node_count = len([n for n in self.tree.nodes if not n.type in ('FRAME', 'REROUTE')])
        header = create_bndl_header(TREE_TYPE, self.material.name, node_count)
        
        self.lines_groups = [header, "# === MATERIAL DEFINITIONS ==="]
        self.lines_top = ["# === MATERIAL TREE ==="]
        
        self._export_top()
        
        return "\n".join(self.lines_groups + [""] + self.lines_top) + "\n"

    def _export_node_properties_for_group(self, node, set_entries):
        """Export node-specific properties for group context."""
        # Handle Group nodes
        if node.type == 'GROUP':
            if hasattr(node, 'node_tree') and node.node_tree:
                group_ref = serialize_datablock_reference(node.node_tree, 'NodeTree')
                set_entries.append(f'    "node_tree" to {group_ref}')
        
        # Handle other node types (same as before)
        self._export_node_properties(node, set_entries)
    
    def _walk_reroute_chain_backward(self, socket):
        """Walk backward through reroute nodes to find the actual source socket."""
        current_socket = socket
        visited = set()
        
        while (current_socket and 
               current_socket.node.type == 'REROUTE' and 
               current_socket.node not in visited):
            visited.add(current_socket.node)
            
            # For reroute nodes, find what's connected to their input
            input_socket = current_socket.node.inputs[0] if current_socket.node.inputs else None
            if input_socket and input_socket.is_linked:
                link = input_socket.links[0]
                current_socket = link.from_socket
            else:
                break
        
        return current_socket
    
    def _walk_reroute_chain_forward(self, socket):
        """Walk forward through reroute nodes to find the actual destination socket."""
        current_socket = socket
        visited = set()
        
        while (current_socket and 
               current_socket.node.type == 'REROUTE' and 
               current_socket.node not in visited):
            visited.add(current_socket.node)
            
            # For reroute nodes, find what their output connects to
            output_socket = current_socket.node.outputs[0] if current_socket.node.outputs else None
            if output_socket and output_socket.is_linked:
                # Take the first linked socket (reroutes typically connect to one destination)
                link = output_socket.links[0]
                current_socket = link.to_socket
            else:
                break
        
        return current_socket

# ---------- Main Export Function ----------

def export_active_material_to_bndl_text():
    """Export the active material's shader nodes to BNDL text."""
    material = get_active_material_from_object()
    if not material:
        raise RuntimeError("No active material found. Select an object with a material.")
    
    if not material.use_nodes or not material.node_tree:
        raise RuntimeError(f"Material '{material.name}' does not use shader nodes.")
    
    # Check if material has any nodes
    if not material.node_tree.nodes:
        raise RuntimeError(f"Material '{material.name}' has no shader nodes.")
    
    exp = _MaterialTreeExport(material)
    text = exp.run()
    
    # Round floats if enabled in preferences
    prefs = get_addon_preferences()
    should_round = getattr(prefs, "round_float_precision", True) if prefs else True
    
    if should_round and bndl_round is not None:
        try:
            print("[BNDL] Rounding float precision in output...")
            text = bndl_round.round_floats_in_bndl(text)
        except Exception as ex:
            print(f"[BNDL] Warning: float rounding failed: {ex}")
    
    # Write to Text datablock
    tb = bpy.data.texts.get(TEXT_BLOCK_NAME) or bpy.data.texts.new(TEXT_BLOCK_NAME)
    tb.clear()
    tb.write(text)
    
    # Optional: also dump to file
    if WRITE_FILE_PATH:
        try:
            with open(bpy.path.abspath(WRITE_FILE_PATH), "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print(f"[BNDL] Warning: failed to write file: {e}")
    
    print(f"[BNDL] Exported material '{material.name}' to {TEXT_BLOCK_NAME}")
    return text

# ---------- Convenience Functions ----------

def get_available_materials():
    """Get list of materials with shader nodes from the current object."""
    obj = bpy.context.view_layer.objects.active
    if not obj or not hasattr(obj, 'material_slots'):
        return []
    
    materials = []
    for slot in obj.material_slots:
        if slot.material and slot.material.use_nodes and slot.material.node_tree:
            materials.append(slot.material)
    
    return materials

def export_material_by_name(material_name):
    """Export a specific material by name."""
    material = bpy.data.materials.get(material_name)
    if not material:
        raise RuntimeError(f"Material '{material_name}' not found.")
    
    if not material.use_nodes or not material.node_tree:
        raise RuntimeError(f"Material '{material_name}' does not use shader nodes.")
    
    exp = _MaterialTreeExport(material)
    return exp.run()

def export_material_to_bndl(material):
    """Export a material object to BNDL text."""
    if not material:
        raise RuntimeError("Material is None.")
    
    if not material.use_nodes or not material.node_tree:
        raise RuntimeError(f"Material '{material.name}' does not use shader nodes.")
    
    exp = _MaterialTreeExport(material)
    text = exp.run()
    
    # Round floats if enabled in preferences
    prefs = get_addon_preferences()
    should_round = getattr(prefs, "round_float_precision", True) if prefs else True
    
    if should_round and bndl_round is not None:
        try:
            text = bndl_round.round_floats_in_bndl(text)
        except Exception as ex:
            print(f"[BNDL] Warning: float rounding failed: {ex}")
    
    return text

# For backward compatibility
export_to_bndl_text = export_active_material_to_bndl_text