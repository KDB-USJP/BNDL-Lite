"""
Progress indicator utilities for BNDL addon.
Provides easy-to-use progress bars for long-running operations.
"""

import bpy  # type: ignore
from typing import Optional, Callable
from contextlib import contextmanager


class ProgressTracker:
    """
    Context manager for showing progress during long operations.
    
    Usage:
        with ProgressTracker("Exporting materials", total=10) as progress:
            for i in range(10):
                # Do work
                progress.update(i + 1, f"Processing material {i+1}/10")
    """
    
    def __init__(self, title: str = "Processing...", total: int = 100):
        """
        Initialize progress tracker.
        
        Args:
            title: Main progress message shown in status bar
            total: Total number of steps (for calculating percentage)
        """
        self.title = title
        self.total = max(1, total)  # Avoid division by zero
        self.current = 0
        self._wm = None
        self._is_active = False
    
    def __enter__(self):
        """Start progress tracking."""
        try:
            self._wm = bpy.context.window_manager
            if self._wm:
                self._wm.progress_begin(0, self.total)
                self._is_active = True
                print(f"[BNDL Progress] Started: {self.title}")
        except Exception as e:
            print(f"[BNDL Progress] Could not initialize: {e}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End progress tracking."""
        if self._is_active and self._wm:
            try:
                self._wm.progress_end()
                print(f"[BNDL Progress] Completed: {self.title}")
            except Exception as e:
                print(f"[BNDL Progress] Error ending progress: {e}")
            self._is_active = False
    
    def update(self, step: int, message: Optional[str] = None):
        """
        Update progress bar.
        
        Args:
            step: Current step number (0 to total)
            message: Optional status message to print to console
        """
        if not self._is_active or not self._wm:
            return
        
        self.current = min(step, self.total)
        
        try:
            self._wm.progress_update(self.current)
            
            # Calculate percentage for console output
            percentage = int((self.current / self.total) * 100)
            
            if message:
                print(f"[BNDL Progress] [{percentage}%] {message}")
            else:
                print(f"[BNDL Progress] [{percentage}%] {self.title}")
            
            # Force UI refresh to show progress
            for window in bpy.context.window_manager.windows:  # type: ignore
                for area in window.screen.areas:
                    area.tag_redraw()
                    
        except Exception as e:
            print(f"[BNDL Progress] Update error: {e}")
    
    def step(self, message: Optional[str] = None):
        """
        Increment progress by one step.
        
        Args:
            message: Optional status message
        """
        self.update(self.current + 1, message)
    
    def set_total(self, new_total: int):
        """
        Update the total number of steps (useful when total is unknown at start).
        
        Args:
            new_total: New total step count
        """
        self.total = max(1, new_total)


@contextmanager
def simple_progress(title: str):
    """
    Simplified progress context manager without step tracking.
    Just shows/hides a generic progress indicator.
    
    Usage:
        with simple_progress("Loading files..."):
            # Do work
            pass
    """
    wm = None
    try:
        wm = bpy.context.window_manager
        if wm:
            wm.progress_begin(0, 100)
            wm.progress_update(50)  # Show halfway
            print(f"[BNDL Progress] {title}")
        yield
    finally:
        if wm:
            try:
                wm.progress_end()
            except:
                pass


def modal_progress_wrapper(operator_execute: Callable, title: str = "Processing"):
    """
    Decorator for wrapping operator execute methods with progress tracking.
    
    Usage:
        @modal_progress_wrapper
        def execute(self, context):
            # Your code here
            return {'FINISHED'}
    """
    def wrapper(self, context):
        with simple_progress(title):
            return operator_execute(self, context)
    return wrapper


# Example operator showing progress tracking
class BNDL_OT_ProgressTest(bpy.types.Operator):
    """Test operator to demonstrate progress tracking"""
    bl_idname = "bndl.progress_test"
    bl_label = "Test Progress Tracking"
    bl_description = "Demonstrate progress indicators (for development)"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        import time
        
        # Example 1: Step-by-step progress
        with ProgressTracker("Testing progress indicators", total=10) as progress:
            for i in range(10):
                time.sleep(0.1)  # Simulate work
                progress.update(i + 1, f"Step {i+1} of 10")
        
        self.report({'INFO'}, "Progress test complete!")
        return {'FINISHED'}


def register():
    """Register progress utilities."""
    bpy.utils.register_class(BNDL_OT_ProgressTest)
    print("[BNDL Progress] Progress tracking system initialized")


def unregister():
    """Unregister progress utilities."""
    bpy.utils.unregister_class(BNDL_OT_ProgressTest)
