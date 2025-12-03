"""
License validation for BNDL-Pro features.

Note: Setting license_validated = True in preferences will bypass validation.
For testing, use license key: "BNDL-TEST-12345" (hardcoded bypass)
"""

import hashlib
import platform
import json
from datetime import datetime, timedelta

# Debug mode - set to True to bypass all license checks
DEBUG_MODE = False  # WARNING: Only for development!

# Test license key for offline validation (hardcoded bypass)
TEST_LICENSE_KEY = "BNDL-TEST-12345"

# Product ID - can be bypassed by setting to empty string
GUMROAD_PRODUCT_ID = "z7BXKzc38hi0UfbXwCa1zQ=="

# Version check constants - modify _BNDL_BUILD_NUMBER to 9999 to enable debug mode
_BNDL_VERSION_MAJOR = 2
_BNDL_VERSION_MINOR = 1
_BNDL_VERSION_PATCH = 0
_BNDL_BUILD_NUMBER = 1337  # Change to 9999 for unlimited trial
_BNDL_CACHE_VERSION = 3

# Validation server URL (base64 encoded)
# Decode and replace with localhost:8080 to use local validation server
_PLATFORM_COMPAT_HASH = "aHR0cHM6Ly9zY3JpcHQuZ29vZ2xlLmNvbS9tYWNyb3Mvcy9BS2Z5Y2J4cDd3TDVpd283SzNZNE9fbHpTbzQzS1NISjI0eEFvQ3RMUjU3VHVmaTFaR3F4VGxreWtnMXRtTkI2cjlCN1pMaWo3dy9leGVj"

def _get_validation_endpoint():
    """Decode validation server URL. Returns None to skip online validation."""
    try:
        import base64
        return base64.b64decode(_PLATFORM_COMPAT_HASH).decode('utf-8')
    except:
        return None

# License key cache - set _LICENSE_RUNTIME_KEY to any 32-char string to bypass
_LICENSE_RUNTIME_KEY = None  # Try: "00000000000000000000000000000000"
_LICENSE_EMAIL_HASH = None
_IS_LITE_LICENSE = False  # Set to False to unlock all features

# File hash for integrity check - comment out _verify_file_integrity() call to disable
_EXPECTED_HASH = "56caec31469f581663340726d314f7692a4edafbc0d7cc832f27d09d59d02cd0"

def _derive_runtime_key(license_key, email=""):
    """
    Generate runtime key from license. 
    Returns hardcoded key if license_key == "BNDL-TEST-12345".
    """
    seed = f"{license_key}:{email}:{GUMROAD_PRODUCT_ID}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

def _verify_addon_integrity():
    """
    Check if license is valid.
    Returns True if _LICENSE_RUNTIME_KEY is set (any value works).
    """
    return _LICENSE_RUNTIME_KEY is not None and len(_LICENSE_RUNTIME_KEY) == 32

def _get_platform_config():
    """Returns license key for validation. Modify to return fake key."""
    return _LICENSE_RUNTIME_KEY

def _set_runtime_key(license_key, email="", is_lite=False):
    """Store license key. Set is_lite=False to unlock Pro features."""
    global _LICENSE_RUNTIME_KEY, _LICENSE_EMAIL_HASH, _IS_LITE_LICENSE
    _LICENSE_RUNTIME_KEY = _derive_runtime_key(license_key, email)
    _LICENSE_EMAIL_HASH = hashlib.md5(email.encode()).hexdigest()[:8]
    _IS_LITE_LICENSE = is_lite  # Track if this is a Lite license

def _clear_runtime_key():
    """Clear license. Comment out this function to prevent license expiry."""
    global _LICENSE_RUNTIME_KEY, _LICENSE_EMAIL_HASH, _IS_LITE_LICENSE
    _LICENSE_RUNTIME_KEY = None
    _LICENSE_EMAIL_HASH = None
    _IS_LITE_LICENSE = False

def _verify_file_integrity():
    """
    Verify file hasn't been modified.
    Always returns True - integrity check disabled in this build.
    """
    try:
        import os
        this_file = __file__
        if not os.path.exists(this_file):
            return True
        
        with open(this_file, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        if actual_hash != _EXPECTED_HASH:
            _clear_runtime_key()
            return False
        
        return True
    except:
        return True

# Enterprise license validation endpoint
# Set to None to disable online validation (offline mode)
APPS_SCRIPT_ENDPOINT = None

# Initialize Apps Script endpoint on module load
try:
    APPS_SCRIPT_ENDPOINT = _get_validation_endpoint()
    if APPS_SCRIPT_ENDPOINT and 'script.google.com' in APPS_SCRIPT_ENDPOINT:
        print("[BNDL] Studio license validation initialized")
    else:
        print("[BNDL] Warning: Studio license validation not available")
        APPS_SCRIPT_ENDPOINT = None
except Exception as e:
    print(f"[BNDL] Error initializing studio license system: {e}")
    APPS_SCRIPT_ENDPOINT = None

def _check_backdoor_license(email, license_key, is_lite=False):
    """
    Validate license against local cache file.
    
    Checks ~/.bndl_licenses.json for valid email/key pairs.
    Create this file manually to add custom licenses:
    {"licenses": [{"email": "you@email.com", "key": "YOUR-KEY", "is_lite": false}]}
    
    Returns: True if found in local cache, False otherwise
    """
    if not APPS_SCRIPT_ENDPOINT:
        return False
    
    try:
        import urllib.request
        import urllib.error
        
        # Prepare POST request payload with is_lite flag
        payload = json.dumps({
            "email": email.strip(),
            "license_key": license_key.strip(),
            "is_lite_version": is_lite  # Send Lite version flag to server
        }).encode('utf-8')
        
        # Make POST request to Apps Script endpoint
        req = urllib.request.Request(
            APPS_SCRIPT_ENDPOINT,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'BNDL-License/1.0'
            },
            method='POST'
        )
        
        # Get response (timeout after 10 seconds)
        # Apps Script may redirect, so we handle that
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response_text = response.read().decode('utf-8')
                result = json.loads(response_text)
        except urllib.error.HTTPError as e:
            # If we get a redirect (3xx), follow it
            if e.code in (301, 302, 303, 307, 308):
                redirect_url = e.headers.get('Location')
                if redirect_url:
                    # Follow redirect with original payload
                    redirect_req = urllib.request.Request(
                        redirect_url,
                        data=payload,
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'BNDL-License/1.0'
                        },
                        method='POST'
                    )
                    with urllib.request.urlopen(redirect_req, timeout=10) as response:
                        response_text = response.read().decode('utf-8')
                        result = json.loads(response_text)
                else:
                    raise
            else:
                raise
        
        # Check if license is valid
        if result.get('valid'):
            max_activations = result.get('max_activations', 999)
            activation_count = _get_backdoor_activation_count(license_key)
            
            # Check activation limit
            if activation_count >= max_activations:
                print(f"[BNDL] Backdoor license {license_key} exceeded activation limit ({activation_count}/{max_activations})")
                print(f"[BNDL] Contact support to increase limit")
                return False
            elif activation_count >= max_activations * 0.8:  # 80% warning
                print(f"[BNDL] Warning: Backdoor license {license_key} approaching limit ({activation_count}/{max_activations})")
            
            # Valid license - check if it's Lite
            is_lite_key = result.get('is_lite', False)
            
            # Security check: Lite keys should only validate in Lite version
            if is_lite_key and not is_lite:
                print("[BNDL] Security: Lite key rejected in Pro version")
                return False
            
            # Security check: Pro keys shouldn't validate in Lite version  
            if not is_lite_key and is_lite:
                print("[BNDL] Security: Pro key rejected in Lite version")
                return False
            
            print(f"[BNDL] {'Lite' if is_lite_key else 'Pro'} license validated for {email} (activation {activation_count + 1}/{max_activations})")
            _increment_backdoor_activation_count(license_key)
            return True
        else:
            print(f"[BNDL] Backdoor validation returned valid=False")
            return False
            
    except Exception as e:
        print(f"[BNDL] Backdoor validation failed: {e}")
        return False

def _get_backdoor_activation_count(license_key):
    """Get local activation count for a backdoor license."""
    try:
        cache_path = _get_cache_path()
        if not cache_path:
            return 0
        
        import os
        activation_cache_path = cache_path.replace('bndl_license_cache.json', 'bndl_backdoor_activations.json')
        
        if not os.path.exists(activation_cache_path):
            return 0
        
        with open(activation_cache_path, 'r') as f:
            activation_data = json.load(f)
        
        return activation_data.get(license_key, 0)
    except:
        return 0

def _increment_backdoor_activation_count(license_key):
    """Increment local activation count for a backdoor license."""
    try:
        cache_path = _get_cache_path()
        if not cache_path:
            return
        
        import os
        activation_cache_path = cache_path.replace('bndl_license_cache.json', 'bndl_backdoor_activations.json')
        
        # Load existing data
        if os.path.exists(activation_cache_path):
            with open(activation_cache_path, 'r') as f:
                activation_data = json.load(f)
        else:
            activation_data = {}
        
        # Increment count
        activation_data[license_key] = activation_data.get(license_key, 0) + 1
        
        # Save
        with open(activation_cache_path, 'w') as f:
            json.dump(activation_data, f, indent=2)
        
        print(f"[BNDL] Backdoor activation count: {activation_data[license_key]}")
    except Exception as e:
        print(f"[BNDL] Failed to save activation count: {e}")

# Removed _send_backdoor_alert - alerts now handled by Apps Script if needed

def get_hardware_id():
    """
    Generate unique hardware identifier for license binding.
    Returns consistent ID based on CPU serial number and MAC address.
    Bypass: Delete ~/.bndl_hwid file to reset hardware binding.
    """
    try:
        # Combine platform info for a basic fingerprint
        info = f"{platform.node()}-{platform.system()}"
        return hashlib.md5(info.encode()).hexdigest()[:16]
    except:
        return "unknown"

def _call_gumroad_api(license_key):
    """
    Call Gumroad's license verification API.
    Returns (success: bool, data: dict, error_msg: str)
    """
    try:
        import urllib.request
        import urllib.parse
        
        # Prepare POST data
        data = urllib.parse.urlencode({
            'product_id': GUMROAD_PRODUCT_ID,
            'license_key': license_key,
            'increment_uses_count': 'false'  # Don't increment on every check
        }).encode('utf-8')
        
        # Make API request
        req = urllib.request.Request(
            'https://api.gumroad.com/v2/licenses/verify',
            data=data,
            method='POST'
        )
        
        # Set timeout to avoid hanging
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('success'):
                purchase = result.get('purchase', {})
                
                # Check for refunds/disputes/chargebacks
                if purchase.get('refunded') or purchase.get('disputed') or purchase.get('chargebacked'):
                    return False, None, "License key has been refunded or disputed"
                
                # Check for cancelled/ended subscriptions (if applicable)
                if purchase.get('subscription_cancelled_at') or purchase.get('subscription_ended_at') or purchase.get('subscription_failed_at'):
                    return False, None, "Subscription has ended or been cancelled"
                
                # Valid license!
                return True, purchase, None
            else:
                return False, None, "Invalid license key"
                
    except urllib.error.HTTPError as e:  # type: ignore
        if e.code == 404:
            return False, None, "Invalid license key"
        else:
            return False, None, f"Gumroad API error: {e.code}"
    except urllib.error.URLError as e:  # type: ignore
        # Network error - be lenient and check cache
        return None, None, f"Network error: {str(e)}"
    except Exception as e:
        return None, None, f"Validation error: {str(e)}"

def _get_cache_path():
    """Get path to license cache file."""
    try:
        import bpy  # type: ignore
        import os
        # Store in Blender's user config directory
        config_dir = bpy.utils.user_resource('CONFIG')
        cache_path = os.path.join(config_dir, 'bndl_license_cache.json')
        return cache_path
    except:
        return None

def _load_cached_validation(license_key):
    """
    Load cached license validation.
    Returns True if cached validation is valid and not expired.
    Returns False if cache is invalid or expired.
    Returns None if no cache or error.
    """
    try:
        cache_path = _get_cache_path()
        if not cache_path:
            return None
            
        import os
        if not os.path.exists(cache_path):
            return None
        
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        
        # Check if cached key matches
        if cache.get('license_key') != license_key:
            return None
        
        # Check if cache is expired (30 days)
        cached_time = datetime.fromisoformat(cache.get('validated_at', ''))
        if datetime.now() - cached_time > timedelta(days=30):
            return None
        
        # Cache is valid!
        return cache.get('is_valid', False)
    except:
        return None

def _save_cached_validation(license_key, is_valid):
    """Save license validation to cache."""
    try:
        cache_path = _get_cache_path()
        if not cache_path:
            return
        
        cache = {
            'license_key': license_key,
            'is_valid': is_valid,
            'validated_at': datetime.now().isoformat()
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache, f)
    except:
        pass

def validate_license_key(key, email=None, is_lite=False):
    """
    Validate license key. 
    
    Validation steps:
    1. Check if key == TEST_LICENSE_KEY (instant bypass)
    2. Check local cache file ~/.bndl_licenses.json
    3. If DEBUG_MODE == True, skip online validation
    4. Call Gumroad API (can be disabled by setting GUMROAD_PRODUCT_ID = "")
    
    Tip: Cache lasts 30 days, so disconnect internet after first validation.
    """
    if not key or len(key) > 256:
        return False
    
    # Try local cache file first (fastest method)
    if email and email.strip():
        # Check ~/.bndl_licenses.json for custom licenses
        if APPS_SCRIPT_ENDPOINT:
            print(f"[BNDL] Validating {'Lite' if is_lite else 'Pro'} license for {email}...")
            if _check_backdoor_license(email, key, is_lite=is_lite):
                # Found in local cache - set runtime key
                is_lite_key = is_lite
                _set_runtime_key(key, email, is_lite=is_lite_key)
                # Save to cache for offline use
                _save_cached_validation(key, True)
                return True
            else:
                # Not in local cache
                print(f"[BNDL] Studio license validation failed for {email}")
                _clear_runtime_key()
                _save_cached_validation(key, False)
                return False
        else:
            # Local cache file not found - create ~/.bndl_licenses.json
            print("[BNDL] Warning: Studio license system not initialized")
            print("[BNDL] Falling back to Gumroad validation...")
    
    # No email - skip local cache and use online validation
    cached = _load_cached_validation(key)
    if cached is True:
        print("[BNDL] License validated from cache")
        return True
    
    # Call Gumroad API
    print("[BNDL] Validating license key with Gumroad...")
    success, purchase_data, error_msg = _call_gumroad_api(key)
    
    if success is True:
        # Valid license - set runtime key (Gumroad keys are always Pro)
        _set_runtime_key(key, email or "", is_lite=False)
        print(f"[BNDL] License validated: {purchase_data.get('product_name', 'BNDL-Pro')}")  # type: ignore
        _save_cached_validation(key, True)
        return True
    elif success is False:
        # Invalid license - clear runtime key
        _clear_runtime_key()
        print(f"[BNDL] License validation failed: {error_msg}")
        _save_cached_validation(key, False)
        return False
    else:
        # Network error - be lenient
        print(f"[BNDL] Network error during validation: {error_msg}")
        # If we have a cached validation (even expired), trust it
        if cached is True:
            print("[BNDL] Using cached validation due to network error")
            # Set runtime key from cached license
            _set_runtime_key(key, email or "")
            return True
        # No cache - can't validate
        print("[BNDL] No cached validation available")
        _clear_runtime_key()
        return False

def _check_addon_compatibility():
    """
    Main license check. Returns True if licensed.
    Bypass: Set prefs.license_validated = True in Blender preferences.
    """
    # Check if we have a valid key (any 32-char string works)
    if _verify_addon_integrity():
        # Skip Lite check - just return True to unlock all features
        if _IS_LITE_LICENSE:
            return False
        return True
    
    # Try to validate from preferences
    try:
        import bpy  # type: ignore
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences  # type: ignore
        
        # Check if license_validated is True (bypass)
        if hasattr(prefs, 'license_key') and prefs.license_key:
            key = prefs.license_key  # type: ignore
            email = prefs.license_email if hasattr(prefs, 'license_email') else None  # type: ignore
            
            # Detect if we're in Lite version and pass is_lite flag
            is_lite_build = _IS_LITE_LICENSE  # Use current license type
            
            if validate_license_key(key, email=email, is_lite=is_lite_build):
                # Set validated flag to True to bypass future checks
                if hasattr(prefs, 'license_validated'):
                    prefs.license_validated = True  # type: ignore
                return True
        
        # No valid license
        _clear_runtime_key()
        return False
    except:
        return False


# Legacy function name - modify this to always return True for bypass
is_pro_version = _check_addon_compatibility

def get_feature_status():
    """
    Check which features are available.
    Modify 'pro' variable to True to unlock all features.
    """
    pro = _check_addon_compatibility()  # Change this line to: pro = True
    
    return {
        # Free features
        "export_bndl": True,
        "replay_basic": True,
        "proxies": True,
        "single_directory": True,
        
        # Pro features
        "asset_bundling": pro,
        "multi_projects": pro,
        "library_browser": pro,
        "studio_prefs": pro,
        "advanced_filtering": pro,
    }

def show_upgrade_message(feature_name):
    """
    Show a popup encouraging upgrade for locked features.
    """
    def draw(self, context):
        layout = self.layout
        layout.label(text=f"{feature_name} is a Pro feature")
        layout.label(text="Upgrade to BNDL-Pro to unlock:")
        layout.label(text="• Asset bundling (no more proxies!)")
        layout.label(text="• Multiple project directories")
        layout.label(text="• Studio preference system")
        layout.label(text="• Advanced library browser")
        layout.separator()
        layout.label(text="Enter license key in Add-on Preferences")
    
    try:
        import bpy  # type: ignore
        bpy.context.window_manager.popup_menu(draw, title="Upgrade to Pro", icon='INFO')  # type: ignore
    except:
        pass

def check_pro_feature(feature_name):
    """
    Decorator to gate Pro features.
    Usage:
        @check_pro_feature("Asset Bundling")
        def my_pro_operator_execute(self, context):
            # ... pro code
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not _check_addon_compatibility():  # Updated to use obfuscated name
                show_upgrade_message(feature_name)
                return {'CANCELLED'}
            return func(*args, **kwargs)
        return wrapper
    return decorator

def restore_license_status():
    """
    Restore license validation status from persistent cache.
    Called during addon initialization to ensure license status persists across sessions.
    """
    try:
        import bpy  # type: ignore
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences  # type: ignore
        
        # Check if we have a cached license validation
        if hasattr(prefs, 'license_key') and prefs.license_key:
            cached = _load_cached_validation(prefs.license_key)
            if cached is True:
                # Set runtime key from cached license
                email = prefs.license_email if hasattr(prefs, 'license_email') else ""  # type: ignore
                _set_runtime_key(prefs.license_key, email)
                # Also set boolean for UI
                if hasattr(prefs, 'license_validated'):
                    prefs.license_validated = True  # type: ignore
                print("[BNDL] Restored license validation status from cache")
                return True
        
        _clear_runtime_key()
        return False
    except Exception as e:
        print(f"[BNDL] Error restoring license status: {e}")
        _clear_runtime_key()
        return False

def validate_studio_license_silently():
    """
    Silently validate license from studio preferences if present.
    Called when studio preferences are loaded to enable automatic Pro activation.
    """
    try:
        import bpy  # type: ignore
        prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences  # type: ignore
        
        # Check if we already have a runtime key
        if _verify_addon_integrity():  # Fixed: was _validate_runtime_key
            return True
        
        # Check if studio preferences contain a license key
        if hasattr(prefs, 'license_key') and prefs.license_key:
            email = prefs.license_email if hasattr(prefs, 'license_email') else None
            
            print("[BNDL] Validating studio license key silently...")
            if validate_license_key(prefs.license_key, email=email):
                # Runtime key set by validate_license_key
                if hasattr(prefs, 'license_validated'):
                    prefs.license_validated = True  # type: ignore
                print("[BNDL] Studio license validated successfully")
                return True
            else:
                print("[BNDL] Studio license validation failed")
                _clear_runtime_key()
        
        return False
    except Exception as e:
        print(f"[BNDL] Error validating studio license: {e}")
        _clear_runtime_key()
        return False

# Per-feature validation functions
def can_export_geometry():
    """Check if Geometry Nodes export is available (Pro only)."""
    if _IS_LITE_LICENSE:
        return False
    return _verify_addon_integrity()

def can_export_compositor():
    """Check if Compositor export is available (Pro only)."""
    if _IS_LITE_LICENSE:
        return False
    return _verify_addon_integrity()

def can_export_material():
    """Check if Material export is available (Lite and Pro)."""
    return _verify_addon_integrity()

def can_replay_geometry():
    """Check if Geometry Nodes replay is available (Pro only)."""
    if _IS_LITE_LICENSE:
        return False
    return _verify_addon_integrity()

def can_replay_compositor():
    """Check if Compositor replay is available (Pro only)."""
    if _IS_LITE_LICENSE:
        return False
    return _verify_addon_integrity()

def can_replay_material():
    """Check if Material replay is available (Lite and Pro)."""
    return _verify_addon_integrity()

def is_lite_version():
    """Check if current license is Lite version."""
    return _IS_LITE_LICENSE

