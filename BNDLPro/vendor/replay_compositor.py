"""
BNDL Lite - Compositor Replay Wrapper (Disabled)

This is BNDL Lite (Materials Only).
Compositor replay requires BNDL Pro.
"""

def replay_compositor(bndl_text):
    """Compositor replay is not available in BNDL Lite."""
    try:
        import bpy  # type: ignore
        
        def draw_upgrade_popup(self, context):
            layout = self.layout
            layout.label(text="Geometry and Compositor BNDLs are in the Pro version only", icon='ERROR')
            layout.separator()
            layout.label(text="Upgrade to replay all tree types")
            layout.separator()
            op = layout.operator("wm.url_open", text="Upgrade to Pro", icon='URL')
            op.url = "https://kyoseigk.gumroad.com"
        
        bpy.context.window_manager.popup_menu(draw_upgrade_popup, title="BNDL Pro Required", icon='INFO')  # type: ignore
        return {'CANCELLED'}
    except:
        raise NotImplementedError(
            "Compositor replay requires BNDL Pro.\\n\\n"
            "Upgrade at: https://kyoseigk.gumroad.com"
        )
