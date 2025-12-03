# 🧩 BNDL File Format — *Release 1.3 (Multi-Domain)*

> **BNDL** ("Bundle") is a human-readable serialization of Blender node trees.  
> It enables round-tripping node graphs — export, version-control, diff, and replay — while preserving structure, values, frames, and user overrides.

## 1. Purpose
BNDL provides a **plain-text representation** of Blender node trees for **Geometry Nodes**, **Shader/Material Nodes**, and **Compositor Nodes** in Blender 4.x.  
It's designed for:
- Pipeline automation: generate procedural assets or templates via Python.  
- Version control: track node graph changes in Git or similar tools.  
- Cross-team exchange: hand off node structures without .blend files.  
- Archival: reconstruct exact node trees on any compatible Blender build.

The companion modules are:

| Module | Function |
|--------|----------|
| **export_geometry.py** | Exports Geometry Node trees to `.bndl` format. |
| **export_material.py** | Exports Shader/Material node trees to `.bndl` format. |
| **export_compositor.py** | Exports Compositor node trees to `.bndl` format. |
| **bndl2py_geometry.py** | Generates Python replay script from Geometry `.bndl` files. |
| **bndl2py_material.py** | Generates Python replay script from Material `.bndl` files. |
| **bndl2py_compositor.py** | Generates Python replay script from Compositor `.bndl` files. |

## 2. Core Principles
- **Readable**: explicit statements (`Create`, `Connect`, `Set`, `SetUser`, `Rename`, `Parent`).  
- **Idempotent**: replaying multiple times yields identical results.  
- **Complete**: includes all node types, connections, parameters, frames, and parenting.  
- **Scoped**: supports nested node groups and top-level modifiers.  
- **Multi-domain**: supports Geometry Nodes, Shader/Material Nodes, and Compositor Nodes.

## 3. File Layout
A BNDL file is divided into **sections**, each beginning with a `# ===` header.

```text
# BNDL v1.3
Tree_Type: GEOMETRY

# === GROUP DEFINITIONS ===
BEGIN GROUP NAMED GalaxySetup
    Create  [ Group Input #1 ] ; type=NodeGroupInput
    Set     [ Group Input #1 ]:
        § Galaxy Scale § to <4.5>
    Connect [ Group Input #1 ] ○ Geometry  to  [ Group Output #1 ] ⦿ Result
END GROUP NAMED GalaxySetup

# === TOP LEVEL ===
Create  [ Group Input #1 ] ; type=NodeGroupInput
Create  [ Frame #1 ] ; type=NodeFrame
Rename  [ Frame #1 ] to "Controls"
Set     [ Group Input #1 ]:
    § Instance Object § to ⊞GLX_Star⊞
    § Instance Scale Min § to <0.0>
    § Instance Scale Max § to <20.0>
Set     [ Frame #1 ]:
    § location § to <-100, 200>
Parent  [ Group Input #1 ]  to  [ Frame #1 ]

# === USER OVERRIDES ===
SetUser [ Group Input #1 ]:
    § Instance Scale Min § to <0.03>
    § Instance Scale Max § to <0.21>
    § Galaxy Scale § to <6.27>
```

## 4. Statement Types
| Statement | Purpose | Example |
|-----------|---------|---------|
| **Create** | Define a node and its type. | `Create [ Join Geometry #1 ] ; type=GeometryNodeJoinGeometry` |
| **Rename** | Set a node's label. | `Rename [ Frame #1 ] to "Controls"` |
| **Connect** | Create a link between node sockets. | `Connect [ NodeA #1 ] ○ Geometry to [ NodeB #2 ] ⦿ Mesh` |
| **Set** | Assign default parameter values (from original tree). | `Set [ Node #1 ]: § Scale § to <1.0>` |
| **SetUser** | Assign user-edited parameter values (from modifier UI). These override `Set` during replay. | `SetUser [ Group Input #1 ]: § Scale § to <2.0>` |
| **Parent** | Define frame parenting relationships. | `Parent [ Node #1 ] to [ Frame #2 ]` |
| **PairZone** | Link Simulation/Repeat zone input/output pairs. | `PairZone [ Simulation Input #1 ] <-> [ Simulation Output #2 ]` |

## 5. Node Identification
Each node appears as:
```
[ Node Name #Index ] ; type=NodeType
```
- `Node Name` – display name (e.g., "Transform Geometry", "Frame").  
- `#Index` – ordinal identifier (unique within scope).  
- `type=` – Blender node type ID (e.g., `GeometryNodeTransform`, `NodeFrame`).

## 6. Socket Markers
| Symbol | Meaning |
|:------:|:--------|
| `○` | Output socket |
| `⦿` | Input socket |
| `§ … §` | Socket or property name |
| `⊞Name⊞` | Object datablock reference |
| `❆Name❆` | Material datablock reference |
| `✸Name✸` | Collection datablock reference |
| `✷Name✷` | Image datablock reference |

## 7. Data Representation
| Data Kind | Example | Notes |
|-----------|---------|-------|
| Number | `<3.14>` | Float or int. |
| Boolean | `<True>` | Case-insensitive. |
| Enum | `©COMPONENTS©` | Enum identifier. |
| Vector / Color | `<1.0, 0.5, 0.0>` | Tuple syntax. |
| Datablock | `⊞MyObject⊞` | Recreates or proxies missing datablocks. |
| String | `~My String~` | Text values. |
| Units | `<90°>` | Converted to radians. |

## 8. Frame Support
**Frames are fully supported** as of v1.3:
- Frames are created like any other node: `Create [ Frame #1 ] ; type=NodeFrame`
- Frame labels are set via `Rename` statements
- Frame positions are set via `Set` statements with `location` property
- **Parenting** is handled via `Parent` statements:
  - Frame-to-frame parenting (nested frames)
  - Node-to-frame parenting (nodes inside frames)
- During replay:
  1. All nodes and frames are created
  2. Parenting relationships are applied
  3. Frame locations are set (only for root frames)
  4. Child frames and nodes position automatically relative to parents

## 9. Replay Lifecycle
1. **Export** – Tree-specific export module writes `Create`, `Rename`, `Connect`, `Set`, and `Parent` statements.  
2. **Generate Replay Script** – Tree-specific `bndl2py_*.py` module parses BNDL and generates Python replay script.  
3. **Execute Replay** – Running the script rebuilds nodes, applies parenting, sets properties, and mirrors Group Input defaults into the modifier UI.

## 10. Naming and Referencing Rules
- `Create` IDs (`#1`, `#2`, …) are local to their group.  
- Group names are unique.  
- Datablocks are linked or proxied as `bndlproxy_*` if missing.  
- **Reroutes are preserved** (collapsed during export, recreated during replay).
- **Frames are fully supported** with parenting and positioning.

## 11. Tree Type Detection
BNDL files include a `Tree_Type:` header to specify the node tree domain:
```
Tree_Type: GEOMETRY    # Geometry Nodes
Tree_Type: MATERIAL    # Shader/Material Nodes
Tree_Type: COMPOSITOR  # Compositor Nodes
```

The replay system automatically routes to the appropriate replay module based on this header.

## 12. Example Round Trip
| Step | Action | Result |
|------|--------|--------|
| ① | Build a node graph with frames. | Node tree with organized frames. |
| ② | Export via BNDLPro addon. | Creates `.bndl` file with all statements. |
| ③ | Replay via BNDLPro addon. | Recreates identical tree with frames, parenting, and values. |

## 13. Compatibility
- **Blender:** 4.0+ (`ng.interface` API).  
- **Domains:** Geometry Nodes, Shader/Material Nodes, Compositor Nodes.  
- **Frame Support:** Full (parenting, positioning, nesting).
- **Reroute Support:** Full (collapsed chains preserved).

## 14. Example Visual Outcome
```
Frame: "Controls" (TL)
  ├─ Frame: "Inputs" (C1)
  │   └─ Group Input
  └─ Frame: "Parameters" (C2)
      └─ Transform Geometry

Instance Object     → GLX_Star
Instance Material   → GLX_Emit
Galaxy Scale        → 6.270
```
✅ Replayed tree matches original exactly, including frame organization.

## 15. Version History
- **v1.0** - Initial Geometry Nodes support
- **v1.1** - Added Material/Shader Nodes support
- **v1.2** - Added Compositor Nodes support
- **v1.3** - **Full frame support** with `Parent` and `Rename` statements
