"""
BNDL Lite - Compositor Nodes Export (Disabled)

This is BNDL Lite (Materials Only).
Compositor Nodes export requires BNDL Pro.

Upgrade to unlock:
• Geometry Nodes export/replay
• Compositor Nodes export/replay
• Asset bundling
• Multi-project browser

Purchase at: https://kyoseigk.gumroad.com
Bulk licensing: contact@kyoseigk.com
"""

def export_compositor_to_bndl(compositor_tree):
    """Compositor export is not available in BNDL Lite."""
    raise NotImplementedError(
        "Compositor Nodes export requires BNDL Pro.\n\n"
        "Upgrade at: https://kyoseigk.gumroad.com\n"
        "Bulk licensing: contact@kyoseigk.com"
    )

# Stub class for compatibility
class _CompositorTreeExport:
    def __init__(self, nt):
        raise NotImplementedError(
            "Compositor Nodes export requires BNDL Pro.\n\n"
            "Upgrade at: https://kyoseigk.gumroad.com"
        )