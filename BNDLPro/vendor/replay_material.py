# replay_material.py — Material-specific replay logic
# SELF-CONTAINED: Uses bndl2py_material which has ALL Material replay code embedded

from __future__ import annotations
from typing import Optional

class MaterialReplay:
    """Handles replay logic for Material (Shader) Node trees.
    
    This is a lightweight wrapper around bndl2py_material, which contains
    the complete, self-contained Material script generator (3500+ lines).
    """

    @staticmethod
    def generate_script(bndl_text: str) -> str:
        """Generate a self-contained replay script for material nodes.
        
        Args:
            bndl_text: BNDL format material tree text
            
        Returns:
            Complete Python script that can run standalone in Blender
        """
        # Import the self-contained material script generator
        from . import bndl2py_material
        
        # Generate script using the complete, self-contained generator
        return bndl2py_material.generate_script(bndl_text)