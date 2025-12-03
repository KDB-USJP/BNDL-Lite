<img width="1008" height="506" alt="image" src="https://github.com/user-attachments/assets/8eb1ed0f-8213-4ba9-b8fb-02b8a16e6616" />

# BNDL-Lite
BNDL Lite is the Materials-tree only version of BNDL Pro. It can transform binary Blender Trees into editable, human-readable definitions and replay them against object with full fidelity.


BNDL Lite - Material Node Tree Exporter & Replayer
Version 1.4.0 | Download | 
Documentation
 | 
Upgrade to Pro

Export and replay Blender Material node trees as human-readable .bndl  text files. Perfect for version control, asset libraries, and team collaboration.

✨ What is BNDL Lite?
BNDL Lite lets you export Material node trees to 
.bndl text files and replay them to any object with one click. Think of it as "Save As" for your shader setups, but better:

📝 Human-readable format - Edit .bndl files in any text editor
🔄 Git-friendly - See exactly what changed between versions
📚 Centralized library - Browse materials across multiple projects
⚡ One-click replay - Apply materials instantly to selected objects

Free Forever
BNDL Lite is 100% free and includes everything you need to manage Material node trees. No trial period, no watermarks, no limitations on materials.

🎯 Key Features
Export Materials
One-click export from Shader Editor
Batch export all materials in your scene at once
Proxy mode for external textures (references by name)
Custom naming with prefix/suffix support
Replay Materials
Smart detection - Automatically identifies material trees
Apply to selection - Replay to all selected objects
Proxy handling - Creates placeholder textures for missing files
Create as New - Prevent name collisions with unique naming
Library Browser
Multi-project support - Organize materials by project folder
Live search - Filter materials by name
Favorites - Star your most-used materials
Recent files - Quick access to last 10 materials used

📦 Installation
Method 1: Download from Gumroad (Recommended)
Download BNDL_Lite_v1.4.0.zip from Gumroad
In Blender: Edit > Preferences > Add-ons > Install...
Select the downloaded ZIP file
Enable "BNDL Lite (Materials Only)"
Method 2: Manual Installation
Clone this repository or download as ZIP
Copy the BNDLPro folder to your Blender addons directory:
Windows: %APPDATA%\Blender Foundation\Blender\4.x\scripts\addons\
macOS: ~/Library/Application Support/Blender/4.x/scripts/addons/
Linux: ~/.config/blender/4.x/scripts/addons/
Restart Blender and enable the addon in Preferences
Requirements
Blender 4.0 or newer
No external dependencies required

🚀 Quick Start
1. Set Up Your Library
Open Edit > Preferences > Add-ons > BNDL Lite:

Click [+] to add a project directory
Name it (e.g., "My Materials")
Choose a folder to store 
.bndl
 files
Click outside to save
Tip: Add multiple projects to organize materials by client, show, or asset type.

2. Export Your First Material
Open Shader Editor with a material selected
Open N-Panel (N key) and find BNDL tab
Click Material button under "Export Node Trees"
Material saved as S-MaterialName.bndl in your project folder
3. Replay a Material
Select an object (or multiple objects)
In BNDL N-Panel, find your material in the library list
Click Apply to Selection
Material applied instantly!

📖 Documentation
Export Options
Single Material Export
Location: Shader Editor N-Panel > BNDL > Export Node Trees
Button: "Material"
Output: S-MaterialName.bndl in active project folder
Batch Material Export
Location: Same panel
Button: "Batch: Materials"
Output: Exports ALL materials in current .blend file
Naming: Uses material name + configured prefix/suffix
Export Settings (Preferences)
Name Prefix 1: [Project_]     # e.g., "Project_GoldMetal"
Name Prefix 2: [v1_]           # e.g., "v1_GoldMetal"  
Name Suffix 1: [_final]        # e.g., "GoldMetal_final"
Overall Notes: [For client X]  # Embedded in .bndl header

Replay Options
Apply to Selection
What it does: Replays material to all selected objects
Proxy behavior: Creates placeholder textures if images missing
Name handling: Reuses existing material if name matches

Create as New
What it does: Forces unique material name (e.g., GoldMetal.001)
Use case: Testing variations without overwriting original

Reuse Proxies
What it does: Reuses existing placeholder materials/textures
Use case: Consistent proxy naming across multiple replays

Library Browser
Project Filter
Dropdown: Top of library browser
Options: "All Projects" or individual project names
Effect: Shows only .bndl files from selected project
Search Field: Magnifying glass icon
Behavior: Filters by filename (case-insensitive)
Clear: Click [X] button Favorites
Star icon: Right side of each material
Effect: Moves material to top of list
Persistence: Saved in addon preferences
Recent Files
Automatic: Last 10 replayed materials
Location: Top of library list (if not filtered)
📄 .bndl File Format
BNDL files are human-readable text with a simple structure:

[HEADER]
bndl_version = 1.4
tree_type = ShaderNodeTree
tree_name = GoldMetal_PBR
export_date = 2025-01-15 14:30:00
notes = Metallic gold shader for hero prop
[NODES]
node_0|ShaderNodeBsdfPrincipled|Principled BSDF
  location|(-200.0, 300.0)
  inputs.Base Color|(0.8, 0.6, 0.2, 1.0)
  inputs.Metallic|1.0
  inputs.Roughness|0.15
node_1|ShaderNodeOutputMaterial|Material Output
  location|(100.0, 300.0)
[LINKS]
node_0.BSDF|node_1.Surface
Why This Format?
✅ Git-friendly - Meaningful diffs show exactly what changed
✅ Editable - Modify colors/values in any text editor
✅ Scriptable - Generate variations programmatically
✅ Portable - Works across Blender versions (within reason)

Editing .bndl Files
You can safely edit:

inputs.* values (colors, floats, vectors)
location coordinates
notes in header
Don't edit:
Node types (e.g., ShaderNodeBsdfPrincipled)
Link syntax (must match node IDs)
bndl_version or tree_type
🎓 Use Cases
Solo Artist: Material Library
my_materials/
  ├── metals/
  │   ├── S-Gold_PBR.bndl
  │   ├── S-Steel_Brushed.bndl
  │   └── S-Copper_Oxidized.bndl
  ├── fabrics/
  │   ├── S-Linen_Natural.bndl
  │   └── S-Velvet_Red.bndl
  └── organics/
      ├── S-Skin_Realistic.bndl
      └── S-Wood_Oak.bndl

Workflow:

Export materials as you create them
Organize into subfolders by category
Reuse across different .blend files
Version control with Git

Small Studio: Shared Library
studio_materials/  (shared network drive)
  ├── show_A/
  │   ├── S-Character_Skin.bndl
  │   └── S-Environment_Grass.bndl
  └── show_B/
      ├── S-Vehicle_Paint.bndl
      └── S-Building_Concrete.bndl

Workflow:
Each artist adds project folder pointing to shared drive
Export new materials to appropriate show folder
Other artists refresh library to see updates
Lead artist reviews .bndl files before approval
Freelancer: Client Projects
clients/
  ├── client_A/
  │   ├── S-Logo_Material.bndl
  │   └── S-Product_Metal.bndl
  └── client_B/
      ├── S-Brand_Color.bndl
      └── S-Packaging_Plastic.bndl

Workflow:
One project folder per client
Export materials with client prefix
Easy to find client-specific materials
Archive entire folder when project completes

🔄 Version Control Integration
Git Workflow
# Initialize repo
cd my_materials
git init
# Export material in Blender
# (creates S-GoldMetal.bndl)
# Commit
git add S-GoldMetal.bndl
git commit -m "Add gold metal shader"
# Modify material in Blender, re-export
git diff S-GoldMetal.bndl
Example diff:

[NODES]
node_0|ShaderNodeBsdfPrincipled|Principled BSDF
  location|(-200.0, 300.0)
- inputs.Roughness|0.15
+ inputs.Roughness|0.25
  inputs.Metallic|1.0
You can see exactly what changed! This is impossible with binary .blend files.

Team Collaboration
# Artist A exports new material
git push origin main
# Artist B pulls updates
git pull origin main
# Refresh library in Blender
# New material appears!

⚡ Tips & Tricks
Batch Operations
Export all materials: Use "Batch: Materials" to export entire scene
Apply to multiple objects: Select all objects, click "Apply to Selection"
Organize by prefix: Use "Name Prefix 1" for project codes (e.g., PROJ_)

Proxy Workflow
Missing textures? BNDL creates placeholder Image Texture nodes
Reuse proxies: Enable "Reuse proxies" to keep consistent naming
Replace later: Swap proxy textures with real files when available

Performance
Large libraries: Use project filter to show only relevant materials
Search: Type partial names to filter (e.g., "metal" finds all metal shaders)
Favorites: Star frequently-used materials for quick access

Naming Conventions
Descriptive names: S-Metal_Gold_Brushed.bndl > S-Material.001.bndl
Versioning: Use suffix for iterations (e.g., _v1, _v2, _final)
Categories: Prefix with category (e.g., Metal_, Fabric_, Organic_)

🆙 Upgrade to BNDL Pro
Love BNDL Lite? BNDL Pro adds support for Geometry Nodes and Compositor trees, plus advanced features:

Pro Features
Feature	Lite	Pro
Material export/replay	      ✅	    ✅
Multi-project browser         ✅     ✅
Favorites & recent files	    ✅   	✅
Geometry Nodes export/replay	❌	    ✅
Compositor export/replay	    ❌	    ✅
Asset bundling (.bndlpack)	  ❌	    ✅
Studio preferences system	    ❌	    ✅
Priority support	            ❌   	✅

Why Upgrade?
Geometry Nodes:
Export procedural modifiers as .bndl files
Share scatter systems, procedural modeling setups
Version control your Geo Nodes library

Compositor:
Export compositing node trees
Reuse color grading setups across projects
Build library of post-processing effects

Asset Bundling:
Export textures/images/object dependencies alongside .bndl files
No more broken texture paths
Portable material packages

Studio Preferences:
Centralized settings for entire team
User overrides for personal preferences
Consistent export naming across artists

Pricing
Single-Seat Pricing BNDL Pro: $29 (one-time purchase)
Upgrade from Lite: Seamless - just install Pro version instead

Get BNDL Pro →
🐛 Troubleshooting
"No .bndl files found"
Cause: No project directories configured
Fix: Define at least one project folder in Preferences > BNDL Lite

"Material not applying to object"
Cause: Object has no material slots
Fix: Add a material slot first, or BNDL will create one automatically

"Textures are missing/pink"
Cause: Image files not found at original path
Fix: Enable "Reuse proxies" or manually replace placeholder textures

"Export button grayed out"
Cause: No active material in Shader Editor
Fix: Select an object with a material, or create a new material

"Library list is empty after adding project"
Cause: No .bndl files in project folder yet
Fix: Export your first material, or add existing .bndl files to folder

"Addon won't enable"
Cause: Blender version too old
Fix: Upgrade to Blender 4.0 or newer

🤝 Contributing
BNDL Lite is free and open-source. Contributions welcome!

Reporting Bugs
Check existing issues
Create new issue with:
Blender version
Steps to reproduce
Expected vs actual behavior 
Include .bndl file if relevant

Feature Requests
Open an issue with [Feature Request] tag

Describe use case and benefit
Note: Geometry Nodes/Compositor features are Pro-only

Code Contributions
Fork the repository
Create feature branch (git checkout -b feature/amazing-feature)

Commit changes (git commit -m 'Add amazing feature')
Push to branch (git push origin feature/amazing-feature)
Open Pull Request

📜 License
BNDL Lite is free for personal and commercial use.

✅ Use in commercial projects
✅ Modify for personal use
✅ Share .bndl files freely
❌ Redistribute modified addon without permission
❌ Remove license/attribution

BNDL Pro is a commercial product with separate licensing.

🙏 Credits
Created by: Kyōsei Design Bureau
Support: 
gumroad_support@kyoseigk.com | Email
https://discord.gg/v4gJRBnwfy | Discord

Special Thanks
Blender Foundation for the amazing software
Community testers who provided feedback
All users who support BNDL development

📚 Additional Resources
Tutorials
Getting Started with BNDL Lite (5 min)
Building a Material Library (10 min)
Git + BNDL for Artists (15 min)

Community
BlenderArtists Thread
Reddit r/blender
Discord Server
Documentation
.bndl File Format Spec
API Documentation
Troubleshooting Guide

🎯 Roadmap
Planned for Lite
 Thumbnail previews in library browser
 Import/export library favorites
 Material tags/categories
 Improved search (fuzzy matching)
Pro-Only Features
 Geometry Nodes support
 Compositor support
 Asset bundling
 Database integration (v2.0)
 Cloud sync (v2.0)

Need Geometry Nodes? Upgrade to Pro →
