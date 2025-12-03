# BNDL Vendor Modules
#
# This directory contains core export/replay functionality for the BNDL system.
#
# Active Modules (v1.3):
#  - bndl_common.py         - Shared utilities (TreeType enum, file prefixes, etc.)
#  - bndl_round.py          - Float precision rounder for .bndl output
#  - export_geometry.py     - Geometry Nodes exporter (v1.3 format)
#  - export_material.py     - Material/Shader nodes exporter (v1.3 format)
#  - export_compositor.py   - Compositor nodes exporter (v1.3 format)
#  - replay_direct.py       - Direct replay for materials & compositor (bypasses bndl2py)
#  - replay_multitree.py    - Multi-tree replay orchestrator
#  - bndl2py.py             - Parser & codegen for Geometry Nodes (legacy compatibility)
#
# Legacy/Optional:
#  - exportbndl.py          - (Deprecated) Old single-tree exporter, superseded by export_*.py
#  - replayer_pro.py        - (Optional) Commercial replayer stub for pro version detection
#
# Architecture Notes:
#  - Geometry Nodes: Still uses bndl2py.py for replay (generates Python scripts)
#  - Materials & Compositor: Use replay_direct.py for immediate node tree construction
#  - All three use their respective export_*.py modules for .bndl generation

