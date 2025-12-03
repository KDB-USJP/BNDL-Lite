# Asset Bundling Feature - Implementation Summary

## Overview
The BNDL addon now supports bundling referenced assets (Objects, Materials, Collections, Images, Meshes, Curves) alongside .bndl files. This makes BNDL exports self-contained and portable.

## How It Works

### Three Modes
Users can choose how asset dependencies are handled via **Preferences → Asset Dependencies**:

1. **NONE** (🚫)
   - No asset dependencies are included
   - Only the node tree structure is exported/imported
   - Use when you only need the node graph logic

2. **PROXIES** (👻) - *Default*
   - Current behavior: Create placeholder objects/materials by name
   - No actual asset data is transferred
   - Maintains compatibility with existing workflows

3. **BUNDLE ASSETS** (📦) - *New*
   - Exports referenced assets to matching .blend file
   - Imports assets during replay before building node tree
   - Self-contained, portable exports

### File Pairing Convention
When `BUNDLE ASSETS` mode is enabled:
- Export creates two files:
  - `example-DFGTS.bndl` (node tree description)
  - `example-DFGTS.blend` (referenced asset datablocks)
- Import automatically detects and loads matching .blend file
- Fallback to PROXIES mode if .blend not found

## Implementation Details

### Export Side (Tasks 3-5)

#### 1. Asset Collection (`vendor/exportbndl.py`)
```python
def collect_referenced_assets(bndl_text):
    """Parse BNDL text for sentinel-wrapped datablock references.
    Returns dict mapping datablock type → set of names.
    """
```
- Parses generated .bndl text using regex patterns
- Extracts datablock names from sentinel markers:
  - `⊞name⊞` → Object
  - `❆name❆` → Material
  - `✸name✸` → Collection
  - `✷name✷` → Image
  - `⧉name⧉` → Mesh
  - `𝒞name𝒞` → Curve
- Handles escaped sentinels (doubled within names)
- Returns dict: `{'Object': {'Cube', 'Sphere'}, 'Material': {'red'}, ...}`

#### 2. Asset Saving (`vendor/exportbndl.py`)
```python
def save_assets_to_blend(asset_dict, blend_filepath):
    """Save referenced datablocks to a .blend file using bpy.data.libraries.write()"""
```
- Maps asset dict keys to `bpy.data` collections
- Collects actual datablock objects that exist
- Uses `bpy.data.libraries.write(filepath, datablocks, compress=True)`
- Reports missing assets as warnings
- Returns `(success: bool, message: str, count: int)`

#### 3. Integration (`ops_export.py`)
```python
if prefs.asset_dependency_mode == 'APPEND_ASSETS':
    # Read generated .bndl text
    # Collect referenced assets
    # Generate matching .blend filename
    # Save assets to .blend
    # Report success/warnings to user
```
- Runs after .bndl file is written
- Only executes if preference is set to APPEND_ASSETS
- Generates .blend filename from .bndl path (same base name)
- Reports results via `self.report({'INFO'}, ...)`

### Import Side (Tasks 6-8)

#### 1. Asset Appending Helper (`ops_replay.py`)
```python
def _append_assets_from_blend(blend_path: str) -> tuple[bool, str]:
    """Append datablocks from .blend into current scene using bpy.data.libraries.load()"""
```
- Uses context manager: `with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):`
- `link=False` means append (make local), not link (reference)
- Appends all available datablocks of each type
- Tracks appended items for reporting
- Returns `(success: bool, message: str)`

#### 2. Detection & Integration (`ops_replay.py`)
```python
def _delayed_execute():
    """Stage 1: Execute the generated code"""
    # Check preference mode
    if prefs.asset_dependency_mode == 'APPEND_ASSETS':
        # Look for matching .blend file
        blend_path = os.path.splitext(bndl_path)[0] + '.blend'
        if os.path.isfile(blend_path):
            # Append assets before code execution
            success, msg = _append_assets_from_blend(blend_path)
        else:
            # Fallback to PROXIES mode with warning
```
- Runs in Stage 1 of 4-stage timer execution
- Appends assets **before** generated script runs
- Ensures datablocks are available when node tree references them
- Falls back to PROXIES mode if .blend not found

## Workflow Examples

### Scenario 1: Export with Asset Bundling
1. User sets Preferences → Asset Dependencies → **Bundle Assets**
2. Selects object with Geometry Nodes modifier
3. Runs `bndl.export_active_tree` operator
4. Addon:
   - Exports node tree to `example-DFGTS.bndl`
   - Parses .bndl for asset references
   - Collects actual datablocks (Objects, Materials, etc.)
   - Saves to `example-DFGTS.blend` using `bpy.data.libraries.write()`
   - Reports: *"Exported: .../example-DFGTS.bndl"*
   - Reports: *"Asset bundling: Saved 5 asset(s) to example-DFGTS.blend"*

### Scenario 2: Import with Asset Bundling
1. User receives `example-DFGTS.bndl` + `example-DFGTS.blend` (paired files)
2. Opens their Blender project
3. Runs `bndl.replay_to_selected` operator on .bndl file
4. Addon:
   - Detects matching `example-DFGTS.blend`
   - Appends assets using `bpy.data.libraries.load()` (Stage 1)
   - Generates Python script from .bndl
   - Executes script to rebuild node tree (Stage 2-3)
   - Assigns to selected objects (Stage 4)
   - Console: *"[BNDL] Asset bundling: Appended 5 asset(s) from example-DFGTS.blend"*

### Scenario 3: Fallback when .blend Missing
1. User only receives `example-DFGTS.bndl` (no matching .blend)
2. Runs replay operator
3. Addon:
   - Looks for `example-DFGTS.blend` → not found
   - Prints: *"[BNDL] Asset bundling: No matching .blend found, falling back to PROXIES mode"*
   - Creates placeholder objects/materials by name (existing proxy behavior)
   - Node tree replays successfully with proxies

## Code Locations

### Files Modified
- `prefs.py` - Added `asset_dependency_mode` EnumProperty
- `pref_manager.py` - Added to schema, collect, and apply functions
- `vendor/exportbndl.py` - Added collection and saving functions
- `ops_export.py` - Added integration in execute() method
- `ops_replay.py` - Added append helper and integration in _delayed_execute()

### Key Functions
**Export:**
- `vendor/exportbndl.py::collect_referenced_assets(bndl_text)` - Parse sentinels
- `vendor/exportbndl.py::save_assets_to_blend(asset_dict, blend_filepath)` - Write .blend
- `ops_export.py::BNDL_OT_Export.execute()` - Integration point

**Import:**
- `ops_replay.py::_append_assets_from_blend(blend_path)` - Load .blend
- `ops_replay.py::_apply_with_bndl2py()` → `_delayed_execute()` - Integration point

## Testing Checklist (Task 9)

### Test Plan
- [ ] **NONE mode**: No proxies created, no .blend exported
- [ ] **PROXIES mode**: Existing behavior unchanged (proxies created by name)
- [ ] **BUNDLE ASSETS mode**: 
  - [ ] Export creates matching .blend file
  - [ ] Import appends assets from .blend
  - [ ] Console reports asset count
  - [ ] Node tree references work correctly
- [ ] **Fallback behavior**:
  - [ ] Missing .blend triggers fallback to PROXIES
  - [ ] Warning message displayed in console
  - [ ] Replay completes successfully with proxies
- [ ] **Name conflicts**:
  - [ ] Multiple materials named "red" (one in scene, one in .blend)
  - [ ] Verify Blender's append renaming (red.001) works correctly
  - [ ] Node tree uses appended version (or proxy if append fails)

### Test Files
Recommended test cases:
1. Simple cube with single material
2. Complex setup with Object Info → Set Material (multiple assets)
3. Collection instances (nested collections)
4. Image textures (Image type datablocks)
5. Mesh/Curve geometry datablocks

## Benefits

### For Users
- **Portability**: Share .bndl + .blend as a self-contained package
- **Reliability**: No missing asset references when replaying
- **Flexibility**: Three modes for different use cases
- **Backward Compatible**: Default PROXIES mode preserves existing workflows

### For Teams/Studios
- **Studio Defaults**: Set APPEND_ASSETS in studio_prefs.json
- **Asset Management**: Track dependencies via bundled .blend files
- **Version Control**: Both text (.bndl) and binary (.blend) can be versioned
- **Onboarding**: New users receive complete, working setups

## Technical Notes

### Blender API Usage
- **bpy.data.libraries.write()**: Saves datablocks to external .blend
  - `compress=True` for smaller files
  - Accepts set/list of datablock objects
  - Creates new file or overwrites existing

- **bpy.data.libraries.load()**: Appends datablocks from external .blend
  - Context manager pattern: `with ... as (data_from, data_to):`
  - `link=False` means append (local copies)
  - `link=True` would create linked library references

### Sentinel Escaping
- Datablock names containing sentinels are escaped by doubling
- Example: Object named "⊞Test" → exported as `⊞⊞⊞Test⊞`
- Parser un-escapes: `⊞⊞` → `⊞`
- Prevents parsing ambiguity

### Performance
- Export: Minimal overhead (regex + one bpy.data.libraries.write() call)
- Import: Append happens in Stage 1, doesn't block UI
- File sizes: .blend files compressed by default

## Future Enhancements (Optional)

### Possible Improvements
1. **Selective Append**: UI to choose which assets to include
2. **Asset Packing**: Pack images into .blend automatically
3. **Dependency Graph**: Show asset tree in UI before export
4. **Library Linking**: Option to link instead of append
5. **Asset Browser Integration**: Use Blender 3.0+ asset system
6. **Conflict Resolution**: UI for handling name conflicts
7. **Incremental Bundling**: Only update changed assets

### Community Requests
- Monitor GitHub issues for user feedback
- Track which mode is most commonly used
- Consider A/B testing defaults (PROXIES vs. APPEND_ASSETS)

## Changelog

### Version 1.0 (November 2025)
- ✅ Added three-way asset dependency toggle
- ✅ Implemented asset collection via sentinel parsing
- ✅ Implemented .blend export with bpy.data.libraries.write()
- ✅ Implemented .blend import with bpy.data.libraries.load()
- ✅ Integrated into export/import operators
- ✅ Added console logging for asset operations
- ✅ Fallback to PROXIES mode when .blend missing

---

**Status**: Implementation complete (Tasks 1-8). Ready for testing (Task 9).

**Related Files**: See `.github/copilot-instructions.md` for overall project context.
