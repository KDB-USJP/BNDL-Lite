# BNDL-Pro Usage Guide

Complete guide to using BNDL-Pro for Geometry Nodes workflow management.

## Table of Contents
1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Exporting Node Trees](#exporting-node-trees)
4. [Replaying Node Trees](#replaying-node-trees)
5. [Asset Bundling](#asset-bundling)
6. [Library Browser](#library-browser)
7. [Preference System](#preference-system)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Requirements
- Blender 4.0 or later
- Python 3.11+ (included with Blender)

### Steps
1. Download or clone the BNDL_pro_2 repository
2. In Blender, go to **Edit → Preferences → Add-ons**
3. Click **Install** and select the BNDL_pro_2 folder
4. Enable the checkbox next to "BNDL Tools (Exporter + Replayer Bridge)"
5. The BNDL panel will appear in the N-Panel (press N in the 3D Viewport)

---

## Quick Start

### Export a Node Tree
1. Select an object with a Geometry Nodes modifier
2. Open the **N-Panel → BNDL tab**
3. Click **Export .bndl**
4. Choose a save location and filename
5. Your node tree is now saved as a .bndl text file!

### Replay a Node Tree
1. Select one or more target objects
2. In the BNDL panel, click **Choose .bndl...**
3. Select your previously exported .bndl file
4. The node tree will be reconstructed and applied to your selected objects

---

## Exporting Node Trees

### Basic Export
The exporter captures:
- All nodes in the Geometry Nodes tree
- Node connections (links)
- Property values and settings
- Group Input/Output interface definitions
- Socket names and default values

### Export with Asset Bundling

**When to use:** When your node tree references external objects, materials, collections, images, meshes, or curves.

**How it works:**
1. Set **Asset Dependency Mode** to **APPEND_ASSETS** in preferences
2. Export your .bndl as normal
3. The exporter will create a matching `.blend` file alongside your `.bndl`
4. The .blend contains all assets referenced by your node tree

**What gets bundled:**
- Objects referenced in Object Info nodes
- Materials referenced in Set Material nodes
- Collections referenced in Collection Info nodes
- Images, Meshes, Curves used in the tree

### Export Best Practices

#### ✅ DO:
- Export from a **clean scene** with only necessary objects
- Remove unused objects before exporting
- Organize assets in collections for clarity
- Use descriptive names for your .bndl files
- Export to a centralized library folder for team sharing

#### ⚠️ AVOID:
- Exporting when objects have complex scene-wide dependencies
- Exporting from scenes with unrelated objects
- Using duplicate object names in your scene

#### 💡 Pro Tip: Clean Export Workflow
1. Duplicate your setup to a fresh .blend file
2. Delete all unneeded objects and hierarchy
3. Verify only essential assets remain
4. Export to .bndl with asset bundling

This ensures clean, portable exports without scene clutter.

---

## Replaying Node Trees

### Direct Load Mode
**Fast but requires existing assets**
1. Select target objects
2. Click **Apply to Selection** (uses last exported .bndl from current session)
   - OR -
   Click **Choose .bndl...** to select a specific file
3. The node tree is applied instantly

**Note:** This mode creates proxy objects if referenced assets don't exist.

### Asset Bundling Mode
**Imports all required assets automatically**

1. Set **Asset Dependency Mode** to **APPEND_ASSETS** in preferences
2. Ensure a matching `.blend` file exists alongside your `.bndl`
3. Click **Apply to Selection** or **Choose .bndl...**
4. Assets will be imported into a `BNDL_Assets` collection
5. The node tree is applied with all assets ready

**Asset Organization:**
- Imported assets go into a **BNDL_Assets** collection
- This collection is automatically hidden from viewport and render
- Assets remain accessible to Geometry Nodes
- The collection is excluded from the view layer (keeps Outliner clean)

### Replay to Multiple Objects
1. Select all target objects (Shift+Click)
2. The active object (last selected) will be processed first
3. All selected objects receive the same node tree

---

## Asset Bundling

### How It Works
Asset bundling solves the "missing datablocks" problem by:
1. **Parsing** the .bndl file for asset references (⊞Objects⊞, ❆Materials❆, etc.)
2. **Filtering** to import only assets used by the node tree
3. **Organizing** imports in a hidden `BNDL_Assets` collection
4. **Configuring** the collection to be excluded from viewport and render

### Asset Reference Sentinels
BNDL uses special Unicode markers to identify asset types:
- `⊞name⊞` - Object
- `❆name❆` - Material
- `✸name✸` - Collection
- `✷name✷` - Image
- `⧉name⧉` - Mesh
- `𝒞name𝒞` - Curve

These are automatically handled by the exporter/replayer.

### Dependency Handling
When you import an Object, Blender automatically brings in its dependencies:
- The object's mesh data
- Assigned materials
- Parent objects (if any)
- Collection membership

This is expected behavior - the addon only requests top-level assets, but Blender ensures completeness.

### BNDL_Assets Collection
After import, the Outliner will show:
```
📁 Scene Collection
  ├─ 🟦 Your Target Objects (with node tree applied)
  └─ 📁 BNDL_Assets (hidden, excluded)
       ├─ 🔶 Referenced Object 1
       ├─ 🔶 Referenced Object 2
       └─ 📁 Sub-collections (if any)
```

The BNDL_Assets collection is configured to:
- ❌ Be excluded from the view layer (unchecked in Outliner)
- 👁️ Hide in viewport (eye icon disabled)
- 📷 Disable in render (camera icon disabled)
- ✅ Remain accessible to Geometry Nodes

---

## Library Browser

### Accessing the Browser
1. Open the **N-Panel → BNDL tab**
2. Expand the **Library** section
3. Select a project from the dropdown

### Organization
- **Projects** are defined in your studio preferences
- Each project can have a different library path
- .bndl files are listed with size and modification date

### Filtering
Use the search box to filter .bndl files by name (case-insensitive).

### Quick Apply
1. Select target objects
2. Select a .bndl from the list
3. Click **Apply to Selection**
4. The tree is instantly applied!

---

## Preference System

### Three-Tier Architecture
BNDL-Pro uses a sophisticated preference system:

1. **Studio Preferences** (Highest Priority)
   - Centralized settings for your studio/team
   - Stored in a shared network location
   - Changes apply to all users instantly
   - No addon redeployment needed

2. **User Preferences** (Medium Priority)
   - Per-user overrides
   - Stored in Blender's user config
   - Allows personal customization

3. **Default Preferences** (Lowest Priority)
   - Built-in fallback values
   - Used when studio/user prefs don't define a value

### Configuring Studio Preferences

#### Step 1: Create studio_prefs.json
```json
{
  "asset_dependency_mode": "APPEND_ASSETS",
  "keep_replay_text": false,
  "projects": [
    {
      "name": "Project Alpha",
      "path": "//server/shared/bndl_library/alpha"
    },
    {
      "name": "Project Beta",
      "path": "//server/shared/bndl_library/beta"
    }
  ]
}
```

#### Step 2: Place on Network Share
Put `studio_prefs.json` on a shared network location:
```
//server/shared/bndl/studio_prefs.json
```

#### Step 3: Configure Pointer (One-time per workstation)
1. Open Blender Preferences → Add-ons → BNDL Tools
2. Enter the network path in **Studio Prefs Path**:
   ```
   //server/shared/bndl/studio_prefs.json
   ```
3. Click **Reload Preferences**

✅ Done! All users now share the same studio settings.

### Available Preferences

| Setting | Options | Description |
|---------|---------|-------------|
| **Asset Dependency Mode** | PROXIES / APPEND_ASSETS | How to handle missing assets |
| **Keep Replay Text** | True / False | Keep generated scripts in Blender Text Editor |
| **Projects** | Array of {name, path} | Library locations for Browser |

### User Overrides
Users can override any setting in their local preferences panel. User settings always take priority over studio settings.

---

## Best Practices

### File Organization
```
your_project/
├─ assets/
│  ├─ source_scenes/     # Original .blend files
│  └─ exports/           # Clean export .blend files
├─ library/
│  ├─ project_name/
│  │  ├─ trees/          # .bndl files
│  │  └─ assets/         # .blend asset bundles
│  └─ shared/            # Studio-wide libraries
```

### Naming Conventions
- **BNDLs:** `BNDL-descriptive_name-HASH.bndl`
- **Assets:** `BNDL-descriptive_name-HASH.blend`
- Use lowercase with underscores
- Include version or iteration info if needed

### Version Control
- ✅ **DO** commit .bndl files to version control (they're text)
- ⚠️ **CONSIDER** committing small .blend asset bundles
- ❌ **AVOID** committing large production .blend files

### Team Workflows

#### Centralized Library
1. Set up shared network storage
2. Configure studio preferences with library path
3. All team members use **Apply to Selection** from Browser
4. Changes to library immediately available to all

#### Individual Contribution
1. Artist creates/modifies node tree
2. Export .bndl with asset bundling
3. Save to shared library location
4. Notify team (or use automated sync)
5. Team members refresh library and apply

---

## Troubleshooting

### "Cannot evaluate node group" Error
**Cause:** Assets not loaded or scene not updated properly.

**Solutions:**
1. Ensure asset bundling is enabled
2. Wait for depsgraph update to complete
3. Check that referenced objects exist in scene
4. Try manual **View Layer Update** (Python: `bpy.context.view_layer.update()`)

### Objects Not Appearing in Outliner
**Cause:** Objects might be in a hidden collection or excluded from view layer.

**Solutions:**
1. Check if BNDL_Assets collection is expanded
2. Enable visibility for BNDL_Assets collection (if needed for inspection)
3. Verify objects exist in `bpy.data.objects` (Outliner → Orphan Data)

### Tree "Flashes" Correct Then Breaks
**Cause:** Assets not fully loaded before tree evaluation.

**Solutions:**
1. Use **APPEND_ASSETS** mode instead of PROXIES
2. Ensure source .blend has no duplicate names
3. Export from a clean scene with minimal dependencies
4. Check console for asset loading messages

### Missing Assets in Imported Tree
**Cause:** Assets weren't bundled or .blend file is missing/outdated.

**Solutions:**
1. Verify matching `.blend` file exists alongside `.bndl`
2. Re-export with asset bundling enabled
3. Check console for "Asset bundling: Appended X asset(s)" message
4. Verify asset names in .bndl match those in .blend

### Preferences Not Loading
**Cause:** Studio prefs path incorrect or file not accessible.

**Solutions:**
1. Check network path in preferences panel
2. Verify `studio_prefs.json` exists and is readable
3. Check JSON syntax (use validator if needed)
4. Click **Reload Preferences** after fixing path
5. Check Blender console for error messages

### Browser Shows No .bndl Files
**Cause:** Project path incorrect or no files exist.

**Solutions:**
1. Verify project path in preferences
2. Ensure .bndl files have correct file extension
3. Check folder permissions (read access required)
4. Refresh by switching projects in dropdown

---

## Advanced Topics

### Custom Replayer Integration
For studios with specialized needs, BNDL-Pro supports custom replay logic through `vendor/replayer_pro.py`. This allows integration with proprietary asset management systems or custom node tree processing.

### Batch Processing
You can script BNDL operations using Blender's Python API:

```python
import bpy
from bpy import context

# Select target objects
for obj in bpy.data.objects:
    if obj.name.startswith("MyPrefix_"):
        obj.select_set(True)

# Apply BNDL
bpy.ops.bndl.replay_to_selected(bndl_path="//library/my_tree.bndl")
```

### Format Details
The .bndl format uses a human-readable text syntax:
- `Create [Type]` - Create a node
- `Set [Node]:` - Set node properties
- `Connect [Output] → [Input]` - Link sockets
- `Declare Inputs/Outputs` - Define group interface

See `.bndl` files for examples.

---

## Getting Help

- **Console Output:** Check Blender's System Console (Window → Toggle System Console)
- **Error Messages:** Look for `[BNDL]` prefixed messages
- **Documentation:** See `docs/` folder for technical details
- **Issues:** File bug reports with console output and .bndl file

---

*Last updated: 2025-11-02*
