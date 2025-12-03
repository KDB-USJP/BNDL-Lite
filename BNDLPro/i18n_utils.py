"""
i18n utilities for BNDL addon
Provides translation functions that automatically detect Blender's language setting.
"""

import bpy
import json
import os
from typing import Dict, Optional

# Cache for loaded translations
_translations: Optional[Dict] = None
_current_locale: Optional[str] = None

# Supported locales (must match keys in bndl_i18n.json)
SUPPORTED_LOCALES = {
    'en_US', 'ja_JP', 'de_DE', 'es', 'fr_FR', 
    'it_IT', 'ko_KR', 'pt_BR', 'ru_RU', 'zh_CN'
}

# Locale mapping for Blender's locale codes
LOCALE_MAPPING = {
    'en_US': 'en_US',
    'ja_JP': 'ja_JP',
    'de_DE': 'de_DE',
    'es': 'es',
    'es_ES': 'es',
    'fr_FR': 'fr_FR',
    'it_IT': 'it_IT',
    'ko_KR': 'ko_KR',
    'pt_BR': 'pt_BR',
    'pt_PT': 'pt_BR',  # Use Brazilian Portuguese for Portugal
    'ru_RU': 'ru_RU',
    'zh_CN': 'zh_CN',
    'zh_HANS': 'zh_CN',  # Simplified Chinese
    'zh_TW': 'zh_CN',  # Use Simplified for Traditional (can be expanded later)
}


def load_translations() -> Dict:
    """Load translation data from JSON file."""
    global _translations
    
    if _translations is not None:
        return _translations
    
    # Get path to i18n JSON file
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    i18n_path = os.path.join(addon_dir, "i18n", "bndl_i18n.json")
    
    try:
        with open(i18n_path, 'r', encoding='utf-8') as f:
            _translations = json.load(f)
        print(f"[BNDL i18n] Loaded translations from {i18n_path}")
    except Exception as e:
        print(f"[BNDL i18n] Failed to load translations: {e}")
        # Return minimal English fallback
        _translations = {
            'en_US': {
                'UI': {},
                'Operator': {},
                'Tooltip': {},
                'Property': {},
                'PropertyEnum': {},
                'PropertyEnumDesc': {},
                'Message': {},
                'Error': {}
            }
        }
    
    return _translations


def get_current_locale() -> str:
    """Get the current locale from Blender's preferences."""
    global _current_locale
    
    try:
        # Get Blender's current locale
        blender_locale = bpy.app.translations.locale
        
        # Map to our supported locale
        locale = LOCALE_MAPPING.get(blender_locale, 'en_US')
        
        # Fallback if not in our translations
        translations = load_translations()
        if locale not in translations:
            locale = 'en_US'
        
        _current_locale = locale
        return locale
        
    except Exception as e:
        print(f"[BNDL i18n] Error detecting locale: {e}")
        return 'en_US'


def get_text(category: str, key: str, **kwargs) -> str:
    """
    Get translated text for a given category and key.
    
    Args:
        category: Category name ('UI', 'Operator', 'Tooltip', 'Property', etc.)
        key: Translation key
        **kwargs: Optional format arguments for string interpolation
    
    Returns:
        Translated string with optional formatting applied
    
    Example:
        get_text('Message', 'Export success', filename='test.bndl')
        get_text('UI', 'BNDL Tools')
    """
    translations = load_translations()
    locale = get_current_locale()
    
    try:
        # Try to get translation for current locale
        text = translations[locale][category].get(key)
        
        # Fallback to English if not found
        if text is None and locale != 'en_US':
            text = translations['en_US'][category].get(key)
        
        # Ultimate fallback to key itself
        if text is None:
            text = key
        
        # Apply formatting if kwargs provided
        if kwargs:
            text = text.format(**kwargs)
        
        return text
        
    except Exception as e:
        print(f"[BNDL i18n] Translation error for {category}.{key}: {e}")
        return key


def reload_translations():
    """Force reload of translations (useful for testing/development)."""
    global _translations, _current_locale
    _translations = None
    _current_locale = None
    load_translations()
    get_current_locale()
    print(f"[BNDL i18n] Reloaded translations for locale: {_current_locale}")


# Convenience functions for common categories
def ui(key: str) -> str:
    """Get UI text translation."""
    return get_text('UI', key)


def op(key: str) -> str:
    """Get Operator text translation."""
    return get_text('Operator', key)


def tip(key: str) -> str:
    """Get Tooltip text translation."""
    return get_text('Tooltip', key)


def prop(key: str) -> str:
    """Get Property text translation."""
    return get_text('Property', key)


def enum(key: str) -> str:
    """Get PropertyEnum text translation."""
    return get_text('PropertyEnum', key)


def enum_desc(key: str) -> str:
    """Get PropertyEnumDesc text translation."""
    return get_text('PropertyEnumDesc', key)


def msg(key: str, **kwargs) -> str:
    """Get Message text translation with optional formatting."""
    return get_text('Message', key, **kwargs)


def err(key: str, **kwargs) -> str:
    """Get Error text translation with optional formatting."""
    return get_text('Error', key, **kwargs)


# Operator for reloading translations (useful for development)
class BNDL_OT_ReloadTranslations(bpy.types.Operator):
    """Reload i18n translations from disk"""
    bl_idname = "bndl.reload_translations"
    bl_label = "Reload Translations"
    bl_description = "Reload translation files (for development/testing)"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        reload_translations()
        self.report({'INFO'}, f"Translations reloaded for locale: {_current_locale}")
        
        # Force UI refresh
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        
        return {'FINISHED'}


def _build_blender_translation_dict():
    """Build a dictionary compatible with Blender's translation system."""
    translations_dict = {}
    
    data = load_translations()
    if not data:
        return translations_dict
    
    # For each supported locale
    for locale_code in SUPPORTED_LOCALES:
        if locale_code == 'en_US' or locale_code not in data:
            continue  # Skip English (default) and missing locales
            
        locale_data = data[locale_code]
        
        # Convert to Blender's expected format: {locale: {("*", "Original Text"): "Translated Text"}}
        translations_dict[locale_code] = {}
        
        # Process all categories
        for category, translations in locale_data.items():
            for key, value in translations.items():
                if value and value != key:  # Only add actual translations
                    # Blender expects ("*", "English text") as the key
                    # We use our keys as the English text
                    translations_dict[locale_code][("*", key)] = value
    
    return translations_dict


def register_blender_translations():
    """Register translations with Blender's built-in translation system."""
    try:
        trans_dict = _build_blender_translation_dict()
        if trans_dict:
            bpy.app.translations.register(__package__, trans_dict)
            print(f"[BNDL i18n] Registered {len(trans_dict)} locale translations with Blender")
    except Exception as e:
        print(f"[BNDL i18n] Warning: Could not register Blender translations: {e}")


def unregister_blender_translations():
    """Unregister translations from Blender's translation system."""
    try:
        bpy.app.translations.unregister(__package__)
        print("[BNDL i18n] Unregistered Blender translations")
    except Exception as e:
        print(f"[BNDL i18n] Warning: Could not unregister Blender translations: {e}")


def register():
    """Register i18n utilities."""
    bpy.utils.register_class(BNDL_OT_ReloadTranslations)
    
    # Load translations on startup
    load_translations()
    get_current_locale()
    print(f"[BNDL i18n] Initialized with locale: {_current_locale}")
    
    # Register with Blender's translation system for automatic property tooltips
    register_blender_translations()


def unregister():
    """Unregister i18n utilities."""
    unregister_blender_translations()
    bpy.utils.unregister_class(BNDL_OT_ReloadTranslations)
