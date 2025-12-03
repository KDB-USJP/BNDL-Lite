# bndl_asset_pack.py — Asset packing/unpacking for BNDL files
# Handles images, videos, and other external resources referenced by .bndl files

import bpy
import os
import zipfile
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# ============= ASSET PACK FORMATS =============
# 
# Option 1: .bndlpack (ZIP file)
#   - Simple ZIP container with images + manifest.json
#   - Easy to inspect, portable, works everywhere
#   - Structure:
#     mysetup.bndlpack/
#       manifest.json          # {"version": "1.0", "bndl": "mysetup.bndl", "assets": [...]}
#       images/
#         texture1.png
#         texture2.jpg
#       videos/
#         animation.mp4
#
# Option 2: .blend (Blender file)
#   - Pack images into a minimal .blend file
#   - Blender's native packing system (reliable)
#   - Requires Blender to extract, but integrates perfectly
#   - Name: mysetup_assets.blend
#
# Option 3: Hybrid (both)
#   - Export both .bndlpack and _assets.blend
#   - User chooses which to use based on workflow
#
# ============================================

class AssetPackError(Exception):
    """Exception raised during asset packing/unpacking."""
    pass

# ---------- Asset Discovery ----------

def find_referenced_images(mat: bpy.types.Material) -> Set[bpy.types.Image]:
    """Find all images referenced by a material's node tree."""
    images = set()
    if not mat or not mat.node_tree:
        return images
    
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            images.add(node.image)
        elif node.type == 'GROUP' and node.node_tree:
            # Recursively search node groups
            images.update(_find_images_in_node_tree(node.node_tree))
    
    return images

def _find_images_in_node_tree(tree: bpy.types.NodeTree) -> Set[bpy.types.Image]:
    """Recursively find images in a node tree."""
    images = set()
    if not tree:
        return images
    
    for node in tree.nodes:
        # Check for both compositor IMAGE nodes and shader TEX_IMAGE nodes
        if node.type in ('IMAGE', 'TEX_IMAGE') and hasattr(node, 'image') and node.image:
            images.add(node.image)
        elif hasattr(node, 'node_tree') and node.node_tree:
            images.update(_find_images_in_node_tree(node.node_tree))
    
    return images

def find_referenced_images_compositor(scene: bpy.types.Scene) -> Set[bpy.types.Image]:
    """Find all images referenced by a compositor node tree."""
    images = set()
    if not scene or not scene.node_tree:
        return images
    
    for node in scene.node_tree.nodes:
        if node.type == 'IMAGE' and hasattr(node, 'image') and node.image:
            images.add(node.image)
        elif node.type == 'GROUP' and node.node_tree:
            images.update(_find_images_in_node_tree(node.node_tree))
    
    return images

def find_referenced_images_geometry(modifier: bpy.types.NodesModifier) -> Set[bpy.types.Image]:
    """Find all images referenced by a geometry nodes tree."""
    images = set()
    if not modifier or not modifier.node_group:
        return images
    
    return _find_images_in_node_tree(modifier.node_group)

# ---------- Option 1: .bndlpack (ZIP) ----------

def create_bndlpack(bndl_path: str, output_path: Optional[str] = None, 
                   images: Optional[Set[bpy.types.Image]] = None) -> str:
    """
    Create a .bndlpack file (ZIP) containing images referenced by the .bndl file.
    
    Args:
        bndl_path: Path to the .bndl file
        output_path: Optional custom output path (default: same dir as .bndl with .bndlpack extension)
        images: Optional set of images to pack (if None, auto-detect from context)
    
    Returns:
        Path to created .bndlpack file
    """
    bndl_path = Path(bndl_path)
    
    if output_path is None:
        output_path = bndl_path.with_suffix('.bndlpack')
    else:
        output_path = Path(output_path)
    
    # Auto-detect images if not provided
    if images is None:
        images = set()
        # Try to find images from active material/scene/object
        if bpy.context.active_object and hasattr(bpy.context.active_object, 'active_material'):
            mat = bpy.context.active_object.active_material
            if mat:
                images.update(find_referenced_images(mat))
    
    if not images:
        raise AssetPackError("No images found to pack")
    
    # Create manifest
    manifest = {
        "version": "1.0",
        "bndl_file": bndl_path.name,
        "created_with": f"Blender {bpy.app.version_string}",
        "assets": []
    }
    
    # Create ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add each image
        for img in images:
            if not img.filepath:
                print(f"[BNDL] Warning: Image '{img.name}' has no filepath, skipping")
                continue
            
            # Resolve filepath
            img_path = bpy.path.abspath(img.filepath)
            if not os.path.exists(img_path):
                print(f"[BNDL] Warning: Image file not found: {img_path}")
                continue
            
            # Determine subdir based on type
            file_ext = Path(img_path).suffix.lower()
            if file_ext in ('.mp4', '.avi', '.mov', '.mkv'):
                subdir = 'videos'
            else:
                subdir = 'images'
            
            # Add to ZIP with relative path
            arcname = f"{subdir}/{Path(img_path).name}"
            zf.write(img_path, arcname)
            
            # Add to manifest
            manifest["assets"].append({
                "name": img.name,
                "filename": Path(img_path).name,
                "type": subdir,
                "size": os.path.getsize(img_path)
            })
        
        # Write manifest
        manifest_json = json.dumps(manifest, indent=2)
        zf.writestr('manifest.json', manifest_json)
    
    print(f"[BNDL] Created asset pack: {output_path}")
    print(f"[BNDL] Packed {len(manifest['assets'])} asset(s)")
    return str(output_path)

def extract_bndlpack(pack_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Extract a .bndlpack file and load images into Blender.
    
    Args:
        pack_path: Path to the .bndlpack file
        output_dir: Optional directory to extract to (default: temp dir)
    
    Returns:
        Dict mapping image names to loaded Image datablocks
    """
    pack_path = Path(pack_path)
    
    if output_dir is None:
        # Extract to temp directory next to .blend file or in system temp
        blend_dir = Path(bpy.data.filepath).parent if bpy.data.filepath else Path.home()
        output_dir = blend_dir / f".bndl_cache/{pack_path.stem}"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract ZIP
    with zipfile.ZipFile(pack_path, 'r') as zf:
        zf.extractall(output_dir)
    
    # Read manifest
    manifest_path = output_dir / 'manifest.json'
    if not manifest_path.exists():
        raise AssetPackError("Invalid .bndlpack: missing manifest.json")
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Load images into Blender
    loaded_images = {}
    for asset in manifest.get('assets', []):
        asset_type = asset.get('type', 'images')
        filename = asset.get('filename')
        name = asset.get('name')
        
        if not filename or not name:
            continue
        
        asset_path = output_dir / asset_type / filename
        if not asset_path.exists():
            print(f"[BNDL] Warning: Asset file not found: {asset_path}")
            continue
        
        # Load image
        try:
            # Check if already loaded
            existing = bpy.data.images.get(name)
            if existing:
                print(f"[BNDL] Image '{name}' already loaded, reusing")
                loaded_images[name] = existing
            else:
                img = bpy.data.images.load(str(asset_path))
                img.name = name
                loaded_images[name] = img
                print(f"[BNDL] Loaded image: {name}")
        except Exception as e:
            print(f"[BNDL] Failed to load {name}: {e}")
    
    return loaded_images

# ---------- Option 2: .blend Asset File ----------

def create_blend_asset_pack(bndl_path: str, output_path: Optional[str] = None,
                           images: Optional[Set[bpy.types.Image]] = None) -> str:
    """
    Create a minimal .blend file containing packed images.
    
    Args:
        bndl_path: Path to the .bndl file
        output_path: Optional custom output path (default: bndl_name_assets.blend)
        images: Optional set of images to pack
    
    Returns:
        Path to created .blend file
    """
    bndl_path = Path(bndl_path)
    
    if output_path is None:
        output_path = bndl_path.with_name(f"{bndl_path.stem}_assets.blend")
    else:
        output_path = Path(output_path)
    
    # Auto-detect images if not provided
    if images is None:
        images = set()
        if bpy.context.active_object and hasattr(bpy.context.active_object, 'active_material'):
            mat = bpy.context.active_object.active_material
            if mat:
                images.update(find_referenced_images(mat))
    
    if not images:
        raise AssetPackError("No images found to pack")
    
    # Save current blend state
    current_file = bpy.data.filepath
    
    # Create new blend file
    bpy.ops.wg.read_homefile(use_empty=True)
    
    # Copy images to new file
    copied_images = []
    for img in images:
        if img.filepath:
            img_path = bpy.path.abspath(img.filepath)
            if os.path.exists(img_path):
                try:
                    new_img = bpy.data.images.load(img_path)
                    new_img.name = img.name
                    new_img.pack()  # Pack into .blend file
                    copied_images.append(new_img.name)
                except Exception as e:
                    print(f"[BNDL] Failed to load {img.name}: {e}")
    
    # Save the asset blend file
    bpy.ops.wg.save_as_mainfile(filepath=str(output_path))
    
    print(f"[BNDL] Created asset blend: {output_path}")
    print(f"[BNDL] Packed {len(copied_images)} image(s): {', '.join(copied_images)}")
    
    # Restore original file
    if current_file:
        bpy.ops.wg.open_mainfile(filepath=current_file)
    
    return str(output_path)

def load_blend_asset_pack(pack_path: str) -> Dict[str, bpy.types.Image]:
    """
    Load images from a .blend asset pack file.
    
    Args:
        pack_path: Path to the _assets.blend file
    
    Returns:
        Dict mapping image names to loaded Image datablocks
    """
    pack_path = Path(pack_path)
    
    if not pack_path.exists():
        raise AssetPackError(f"Asset pack not found: {pack_path}")
    
    loaded_images = {}
    
    # Link images from the asset blend file
    with bpy.data.libraries.load(str(pack_path), link=False) as (data_from, data_to):
        # Load all images
        data_to.images = data_from.images
    
    # Unpack images to current file
    for img in data_to.images:
        if img and img.name:
            loaded_images[img.name] = img
            print(f"[BNDL] Loaded image: {img.name}")
    
    return loaded_images

# ---------- Hybrid Export ----------

def create_asset_packs_hybrid(bndl_path: str, images: Optional[Set[bpy.types.Image]] = None) -> Tuple[str, str]:
    """
    Create both .bndlpack (ZIP) and _assets.blend for maximum compatibility.
    
    Returns:
        Tuple of (bndlpack_path, blend_path)
    """
    bndl_path = Path(bndl_path)
    
    # Create both formats
    bndlpack_path = create_bndlpack(str(bndl_path), images=images)
    blend_path = create_blend_asset_pack(str(bndl_path), images=images)
    
    return (bndlpack_path, blend_path)

# ---------- Auto-detection Helper ----------

def auto_pack_assets_for_bndl(bndl_path: str, tree_type: str, 
                              source_material: Optional[bpy.types.Material] = None,
                              source_scene: Optional[bpy.types.Scene] = None,
                              source_object: Optional[bpy.types.Object] = None,
                              pack_format: str = 'bndlpack') -> Optional[str]:
    """
    Automatically detect and pack assets for a .bndl file based on its tree type.
    
    Args:
        bndl_path: Path to the .bndl file
        tree_type: 'MATERIAL', 'COMPOSITOR', or 'GEOMETRY'
        source_material: Source material (for MATERIAL type)
        source_scene: Source scene (for COMPOSITOR type)
        source_object: Source object (for GEOMETRY type)
        pack_format: 'bndlpack', 'blend', or 'hybrid'
    
    Returns:
        Path to created pack file (or primary file if hybrid)
    """
    images = set()
    
    # Detect images based on tree type
    if tree_type == 'MATERIAL' and source_material:
        images = find_referenced_images(source_material)
    elif tree_type == 'COMPOSITOR' and source_scene:
        images = find_referenced_images_compositor(source_scene)
    elif tree_type == 'GEOMETRY' and source_object:
        # Find geometry nodes modifier
        for mod in source_object.modifiers:
            if mod.type == 'NODES':
                images.update(find_referenced_images_geometry(mod))
    
    if not images:
        print("[BNDL] No images found to pack")
        return None
    
    # Create pack based on format
    if pack_format == 'bndlpack':
        return create_bndlpack(bndl_path, images=images)
    elif pack_format == 'blend':
        return create_blend_asset_pack(bndl_path, images=images)
    elif pack_format == 'hybrid':
        pack, blend = create_asset_packs_hybrid(bndl_path, images=images)
        return pack  # Return .bndlpack as primary
    else:
        raise ValueError(f"Unknown pack format: {pack_format}")

# ---------- Unpacking Helper ----------

def auto_unpack_assets_for_bndl(bndl_path: str) -> Dict[str, bpy.types.Image]:
    """
    Automatically find and unpack assets for a .bndl file.
    
    Looks for:
    1. .bndlpack file with same name
    2. _assets.blend file with same stem
    
    Returns:
        Dict of loaded images
    """
    bndl_path = Path(bndl_path)
    
    # Try .bndlpack first
    pack_path = bndl_path.with_suffix('.bndlpack')
    if pack_path.exists():
        print(f"[BNDL] Found asset pack: {pack_path}")
        return extract_bndlpack(str(pack_path))
    
    # Try _assets.blend
    blend_path = bndl_path.with_name(f"{bndl_path.stem}_assets.blend")
    if blend_path.exists():
        print(f"[BNDL] Found asset blend: {blend_path}")
        return load_blend_asset_pack(str(blend_path))
    
    print("[BNDL] No asset pack found")
    return {}

# ---------- Utility Functions ----------

def list_assets_in_pack(pack_path: str) -> List[Dict]:
    """List all assets in a .bndlpack file without extracting."""
    pack_path = Path(pack_path)
    
    with zipfile.ZipFile(pack_path, 'r') as zf:
        manifest_data = zf.read('manifest.json')
        manifest = json.loads(manifest_data)
        return manifest.get('assets', [])

def get_pack_info(pack_path: str) -> Dict:
    """Get metadata about a .bndlpack file."""
    pack_path = Path(pack_path)
    
    with zipfile.ZipFile(pack_path, 'r') as zf:
        manifest_data = zf.read('manifest.json')
        manifest = json.loads(manifest_data)
        
        # Calculate total size
        total_size = sum(zinfo.file_size for zinfo in zf.filelist 
                        if not zinfo.filename.endswith('/'))
        
        return {
            'version': manifest.get('version'),
            'bndl_file': manifest.get('bndl_file'),
            'asset_count': len(manifest.get('assets', [])),
            'total_size': total_size,
            'created_with': manifest.get('created_with')
        }
