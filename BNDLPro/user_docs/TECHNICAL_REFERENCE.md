# 🏗️ BNDLPro Technical Architecture Reference

> **Complete guide to understanding BNDLPro's internal structure, file organization, and data flow**

---

## 📋 Overview

**BNDLPro** is a Blender addon that exports and imports node trees (Geometry Nodes, Shader/Material Nodes, and Compositor Nodes) to/from a custom `.bndl` text format. This allows sharing, versioning, and reusing complex node setups across projects and between users.

### 💡 Core Concept
Export node trees to human-readable `.bndl` files, then replay them in any Blender scene to recreate the exact node setup, including connections, properties, nested groups, and frame organization.

---

## 📂 File Architecture Reference

### ⚙️ Core Addon Files

> **Foundation files that initialize and configure the addon**

---

#### 📄 `__init__.py`
**WHAT IT DOES:** Main addon entry point. Registers all operators, panels, and preferences with Blender when the addon is enabled.

**WHAT IT USES:**
- `ops_export.py` - Export operators
- `ops_replay.py` - Replay operators  
- `ops_batch_export.py` - Batch export operators
- `ops_favorites.py` - Favorites management
- `ops_docs.py` - Documentation operators
- `ui_panels.py` - UI panel classes
- `prefs.py` - Addon preferences
- `browser.py` - File browser
- `license.py` - License validation
- `i18n_utils.py` - Internationalization

**WHAT USES IT:** Blender's addon system calls `register()` and `unregister()` functions

---

#### `prefs.py`
**WHAT IT DOES:** Defines addon preferences (project directories, export settings, UI options, license keys). Provides the preferences panel in Blender's addon settings.

**WHAT IT USES:**
- `pref_manager.py` - Persistent preference storage
- `license.py` - License validation UI
- `i18n_utils.py` - Translated UI strings

**WHAT USES IT:**
- All operators access preferences via `get_prefs()`
- `ui_panels.py` - Displays preference-dependent UI elements

---

#### `pref_manager.py`
**WHAT IT DOES:** Manages persistent storage of user preferences to JSON files on disk. Handles loading, saving, and migration of preference data.

**WHAT IT USES:**
- Standard Python `json`, `os`, `pathlib` modules

**WHAT USES IT:**
- `prefs.py` - Loads/saves preferences when addon starts/stops

---

### Export System

---

#### `ops_export.py`
**WHAT IT DOES:** Provides export operators that users trigger from the UI. Handles file dialogs, validates selections, and calls appropriate export modules.

**WHAT IT USES:**
- `vendor/export_geometry.py` - Exports Geometry Node trees
- `vendor/export_material.py` - Exports Material/Shader node trees
- `vendor/export_compositor.py` - Exports Compositor node trees
- `vendor/bndl_asset_pack.py` - Optional asset bundling
- `favorites_utils.py` - Adds exported files to favorites
- `i18n_utils.py` - Translated messages
- `progress_utils.py` - Progress tracking

**WHAT USES IT:**
- `ui_panels.py` - Export buttons call these operators
- `__init__.py` - Registers operators

---

#### `ops_batch_export.py`
**WHAT IT DOES:** Batch export operators that export multiple materials or geometry node trees at once from selected objects.

**WHAT IT USES:**
- `vendor/export_material.py` - Exports each material
- `vendor/export_geometry.py` - Exports each geometry node tree
- `vendor/bndl_asset_pack.py` - Optional asset bundling
- `progress_utils.py` - Progress tracking
- `i18n_utils.py` - Translated messages

**WHAT USES IT:**
- `ui_panels.py` - Batch export buttons

---

#### `vendor/export_geometry.py`
**WHAT IT DOES:** Core Geometry Node export logic. Traverses a geometry node tree, analyzes all nodes, sockets, connections, groups, and frames, then generates BNDL text format.

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared export utilities (node type normalization, serialization)
- `vendor/bndl_round.py` - Number formatting

**WHAT USES IT:**
- `ops_export.py` - Single geometry tree export
- `ops_batch_export.py` - Batch geometry export

---

#### `vendor/export_material.py`
**WHAT IT DOES:** Core Material/Shader node export logic. Traverses material node trees and generates BNDL text format with material-specific handling.

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared export utilities
- `vendor/bndl_round.py` - Number formatting

**WHAT USES IT:**
- `ops_export.py` - Single material export
- `ops_batch_export.py` - Batch material export

---

#### `vendor/export_compositor.py`
**WHAT IT DOES:** Core Compositor node export logic. Exports compositor node trees with compositor-specific node handling.

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared export utilities
- `vendor/bndl_round.py` - Number formatting

**WHAT USES IT:**
- `ops_export.py` - Compositor tree export

---

### Replay System

---

#### `ops_replay.py`
**WHAT IT DOES:** Provides replay operators that users trigger from the UI. Reads `.bndl` files, determines tree type, and calls appropriate replay modules to recreate node trees.

**WHAT IT USES:**
- `vendor/replay_geometry.py` - Geometry node replay entry point
- `vendor/replay_material.py` - Material node replay entry point
- `vendor/replay_compositor.py` - Compositor node replay entry point
- `vendor/bndl_asset_pack.py` - Asset unpacking
- `browser.py` - File selection
- `i18n_utils.py` - Translated messages

**WHAT USES IT:**
- `ui_panels.py` - Replay buttons call these operators
- `__init__.py` - Registers operators

---

#### `vendor/replay_geometry.py`
**WHAT IT DOES:** Entry point for geometry node replay. Calls the replay script generator and executes the generated Python code.

**WHAT IT USES:**
- `vendor/bndl2py_geometry.py` - Generates replay Python script from BNDL text

**WHAT USES IT:**
- `ops_replay.py` - When replaying geometry `.bndl` files

---

#### `vendor/replay_material.py`
**WHAT IT DOES:** Entry point for material node replay. Calls the replay script generator and executes the generated Python code.

**WHAT IT USES:**
- `vendor/bndl2py_material.py` - Generates replay Python script from BNDL text

**WHAT USES IT:**
- `ops_replay.py` - When replaying material `.bndl` files

---

#### `vendor/replay_compositor.py`
**WHAT IT DOES:** Entry point for compositor node replay. Calls the replay script generator and executes the generated Python code.

**WHAT IT USES:**
- `vendor/bndl2py_compositor.py` - Generates replay Python script from BNDL text

**WHAT USES IT:**
- `ops_replay.py` - When replaying compositor `.bndl` files

---

#### `vendor/bndl2py_geometry.py`
**WHAT IT DOES:** **Core replay script generator for Geometry Nodes.** Parses BNDL text format into an intermediate representation (IR), then generates a complete Python script that recreates the node tree when executed in Blender. Handles:
- Node creation with correct types
- Socket connections (including field/value detection)
- Property values (including datablocks like Objects, Materials)
- Nested node groups
- Frame organization and parenting
- Simulation/Repeat zone pairing
- Modifier input overrides

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared parsing utilities
- Standard Python `re`, `json`, `math` modules

**WHAT USES IT:**
- `vendor/replay_geometry.py` - Calls `generate_script()` function

---

#### `vendor/bndl2py_material.py`
**WHAT IT DOES:** **Core replay script generator for Material/Shader Nodes.** Parses BNDL text and generates Python replay script for material node trees. Similar to geometry replay but with material-specific handling.

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared parsing utilities
- Standard Python `re`, `json`, `math` modules

**WHAT USES IT:**
- `vendor/replay_material.py` - Calls `generate_script()` function

---

#### `vendor/bndl2py_compositor.py`
**WHAT IT DOES:** **Core replay script generator for Compositor Nodes.** Parses BNDL text and generates Python replay script for compositor node trees.

**WHAT IT USES:**
- `vendor/bndl_common.py` - Shared parsing utilities
- Standard Python `re`, `json`, `math` modules

**WHAT USES IT:**
- `vendor/replay_compositor.py` - Calls `generate_script()` function

---

### Shared Utilities

---

#### `vendor/bndl_common.py`
**WHAT IT DOES:** Shared utility functions used by both export and replay systems. Includes:
- Node type normalization (e.g., "GeometryNodeTransform" → "Transform Geometry")
- Value serialization (vectors, colors, datablocks)
- BNDL header creation
- Tree type detection

**WHAT IT USES:**
- Standard Python modules

**WHAT USES IT:**
- `vendor/export_geometry.py`
- `vendor/export_material.py`
- `vendor/export_compositor.py`
- `vendor/bndl2py_geometry.py`
- `vendor/bndl2py_material.py`
- `vendor/bndl2py_compositor.py`

---

#### `vendor/bndl_round.py`
**WHAT IT DOES:** Number formatting utility that rounds floats to a specified precision while preserving integers. Ensures BNDL files are human-readable without excessive decimal places.

**WHAT IT USES:**
- Standard Python `math` module

**WHAT USES IT:**
- All export modules for formatting numeric values

---

#### `vendor/bndl_asset_pack.py`
**WHAT IT DOES:** Asset bundling system. When exporting, can automatically collect referenced datablocks (Objects, Materials, Images, etc.) and save them alongside the `.bndl` file as:
- `.bndlpack` (custom archive format)
- `.blend` (Blender file with assets)
- Hybrid (both formats)

When replaying, unpacks assets and makes them available.

**WHAT IT USES:**
- Blender's `bpy.data` API
- Standard Python `zipfile`, `json`, `os` modules

**WHAT USES IT:**
- `ops_export.py` - Optional asset packing after export
- `ops_batch_export.py` - Optional asset packing
- `ops_replay.py` - Asset unpacking before replay

---

#### `vendor/replayer_pro.py`
**WHAT IT DOES:** **Stub template for custom replayer implementations.** Provides a framework for advanced users/studios to create custom replay logic without modifying core addon files. Currently contains only template code and documentation.

**WHAT IT USES:**
- None (stub file)

**WHAT USES IT:**
- None (intended for manual customization by advanced users)

---

### UI and User Experience

---

#### `ui_panels.py`
**WHAT IT DOES:** Defines all UI panels that appear in Blender's interface (3D Viewport sidebar, Shader Editor, Compositor, etc.). Provides buttons for export, replay, batch operations, and library browsing.

**WHAT IT USES:**
- All `ops_*.py` operator modules - Calls operators when buttons are clicked
- `prefs.py` - Reads preferences to show/hide features
- `browser.py` - File browser integration
- `i18n_utils.py` - Translated UI labels

**WHAT USES IT:**
- `__init__.py` - Registers panels with Blender

---

#### `browser.py`
**WHAT IT DOES:** File browser system that displays `.bndl` files from configured project directories. Provides search, filtering, favorites, and recent files. Generates file previews and metadata.

**WHAT IT USES:**
- `prefs.py` - Gets project directory paths
- `favorites_utils.py` - Manages favorite files
- `i18n_utils.py` - Translated strings

**WHAT USES IT:**
- `ui_panels.py` - Displays browser in UI
- `ops_replay.py` - File selection for replay

---

#### `favorites_utils.py`
**WHAT IT DOES:** Manages user's favorite `.bndl` files. Stores favorites list persistently and provides add/remove operations.

**WHAT IT USES:**
- Standard Python `json`, `os` modules

**WHAT USES IT:**
- `browser.py` - Displays favorites
- `ops_export.py` - Adds newly exported files to favorites

---

#### `ops_favorites.py`
**WHAT IT DOES:** Operators for managing favorites (add, remove, clear). Triggered from browser UI.

**WHAT IT USES:**
- `favorites_utils.py` - Actual favorites management logic

**WHAT USES IT:**
- `browser.py` - Favorite buttons in file browser

---

#### `ops_docs.py`
**WHAT IT DOES:** Operators that open documentation files or URLs in the user's default browser/text editor.

**WHAT IT USES:**
- Standard Python `webbrowser`, `os` modules
- `user_docs/` directory files

**WHAT USES IT:**
- `ui_panels.py` - Help/documentation buttons

---

### Internationalization and Progress

---

#### `i18n_utils.py`
**WHAT IT DOES:** Internationalization (i18n) system. Loads translations from JSON files and provides functions to get translated strings for UI elements and messages.

**WHAT IT USES:**
- `i18n/bndl_i18n.json` - Translation database
- Blender's translation API

**WHAT USES IT:**
- All UI and operator files for translated strings

---

#### `progress_utils.py`
**WHAT IT DOES:** Progress tracking system for long-running operations (batch export, asset packing). Provides progress bars and status updates in Blender's UI.

**WHAT IT USES:**
- Blender's window manager API

**WHAT USES IT:**
- `ops_batch_export.py` - Batch operation progress
- `vendor/bndl_asset_pack.py` - Asset packing progress

---

### Licensing

---

#### `license.py`
**WHAT IT DOES:** License validation system. Checks license keys, validates studio licenses, and enforces feature restrictions for unlicensed users.

**WHAT IT USES:**
- Standard Python `hashlib`, `json`, `datetime` modules

**WHAT USES IT:**
- `prefs.py` - License key input and validation UI
- `__init__.py` - License check on addon enable

---

#### `generate_license_chunks.py`
**WHAT IT DOES:** Utility script for generating license key chunks. Used during license key generation process.

**WHAT IT USES:**
- Standard Python `hashlib` module

**WHAT USES IT:**
- Manual execution for license generation (not called by addon)

---

#### `helpers.py`
**WHAT IT DOES:** Miscellaneous helper functions used across the addon.

**WHAT IT USES:**
- Standard Python modules

**WHAT USES IT:**
- Various addon modules for utility functions

---

## Data Flow Examples

### Export Flow (Geometry Nodes)
1. User clicks "Export Geometry Nodes" button in `ui_panels.py`
2. `ops_export.py` operator validates selection and opens file dialog
3. User selects save location
4. `ops_export.py` calls `vendor/export_geometry.py`
5. `export_geometry.py` traverses node tree using Blender API
6. Uses `vendor/bndl_common.py` for node type normalization
7. Uses `vendor/bndl_round.py` for number formatting
8. Generates BNDL text and writes to file
9. Optionally calls `vendor/bndl_asset_pack.py` to bundle assets
10. `favorites_utils.py` adds file to favorites
11. Success message displayed via `i18n_utils.py`

### Replay Flow (Geometry Nodes)
1. User selects `.bndl` file in `browser.py`
2. Clicks "Replay" button in `ui_panels.py`
3. `ops_replay.py` operator reads BNDL file
4. Detects tree type from header (GEOMETRY)
5. Calls `vendor/replay_geometry.py`
6. `replay_geometry.py` calls `vendor/bndl2py_geometry.py`
7. `bndl2py_geometry.py` parses BNDL text into IR (Intermediate Representation)
8. Generates complete Python replay script
9. Executes script in Blender's context
10. Script creates nodes, sets properties, makes connections
11. Applies frame parenting and positions
12. Success message displayed

---

## Key Design Patterns

### Separation of Concerns
- **Export modules** only generate BNDL text
- **Replay modules** only parse BNDL and generate Python
- **Operators** handle UI, file I/O, and orchestration
- **Vendor modules** contain core logic, isolated from Blender UI

### Tree-Type Specialization
- Separate export/replay modules for each tree type (Geometry, Material, Compositor)
- Shared utilities in `bndl_common.py` for common operations
- Allows tree-specific optimizations and handling

### Generated Replay Scripts
- BNDL files are parsed into Python scripts at replay time
- Scripts are self-contained and can be saved for debugging
- Allows complex logic (frame positioning, zone pairing) without hardcoding

### Modular Architecture
- Each file has a single, clear responsibility
- Minimal interdependencies between modules
- Easy to maintain, test, and extend

---

## For Developers

### Adding a New Feature
1. **Export enhancement:** Modify appropriate `vendor/export_*.py` file
2. **Replay enhancement:** Modify appropriate `vendor/bndl2py_*.py` file
3. **UI addition:** Add operator to `ops_*.py`, button to `ui_panels.py`
4. **Shared utility:** Add to `vendor/bndl_common.py` or create new utility file

### Testing Changes
1. Export a node tree with your changes
2. Inspect generated `.bndl` file (it's human-readable text)
3. Replay the `.bndl` file in a fresh scene
4. Verify node tree matches original exactly

### File Modification Guidelines
- **Never modify** `vendor/replayer_pro.py` (user customization template)
- **Export modules** should only write BNDL text, not modify Blender data
- **Replay modules** should be idempotent (running twice = same result)
- **Operators** should handle errors gracefully and show user-friendly messages
