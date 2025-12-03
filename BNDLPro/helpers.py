import bpy, os, sys, importlib

def reveal_in_explorer(path: str):
    if not path:
        return
    try:
        path = os.path.normpath(path)
        plat = sys.platform.lower()
        if plat.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif plat == "darwin":
            import subprocess; subprocess.Popen(["open", path])
        else:
            import subprocess; subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print("[BNDL] reveal failed:", e)

def ensure_text_block(name: str):
    txt = bpy.data.texts.get(name)
    if txt is None:
        txt = bpy.data.texts.new(name)
    return txt

def import_vendor(modname: str):
    """Import bndl_addon.vendor.<modname>, return module or None."""
    try:
        full = f"{__package__}.vendor.{modname}"
        mod = importlib.import_module(full)
        return mod
    except Exception as e:
        print(f"[BNDL] vendor module not found: {modname} ({e})")
        return None
