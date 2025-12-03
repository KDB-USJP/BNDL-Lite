# Studio License Setup Guide

## Overview
BNDL-Pro supports **bulk licensing** for studios with multiple workstations. This guide explains how to configure automatic license activation across all machines using centralized preferences.

---

## What is Studio Licensing?

Studio licensing allows you to:
- **Pre-configure license keys** in a central location
- **Automatic activation** on all workstations
- **No manual entry** required by artists
- **Single source of truth** for studio preferences

Perfect for:
- Animation studios
- VFX facilities
- Architectural firms
- Educational institutions
- Any organization with 3+ Blender seats

---

## Setup Steps

### 1. Obtain a Bulk License

Contact support or purchase a bulk license key from:
- Gumroad product page
- Direct email: support@bndl.tools

You'll receive:
- A license key (e.g., `STUDIO-ABC123-XYZ789`)
- Email address for registration
- Number of allowed activations

---

### 2. Create Studio Preferences File

Create a `studio_prefs.json` file with your license information:

```json
{
  "bndl_directories": [
    {
      "name": "Studio Node Library",
      "directory": "//server/share/bndl_library"
    }
  ],
  "name_prefix_1": "STUDIO",
  "overall_notes": "Contact: techsupport@studio.com",
  "keep_replay_text": false,
  "round_float_precision": true,
  "reuse_proxies": true,
  "asset_dependency_mode": "APPEND_ASSETS",
  "studio_license_email": "studio@yourcompany.com",
  "studio_license_key": "YOUR-BULK-LICENSE-KEY-HERE"
}
```

**Important Fields:**
- `studio_license_email`: Email registered with your bulk license
- `studio_license_key`: Your bulk license key (replace placeholder)

---

### 3. Deploy Studio Preferences

Place `studio_prefs.json` in a shared network location:

```
\\server\share\config\studio_prefs.json    (Windows)
//server/share/config/studio_prefs.json    (macOS/Linux)
```

---

### 4. Configure Location Pointer

In each BNDL-Pro addon installation, create `studio_prefs_location.json`:

```json
{
  "studio_prefs_path": "//server/share/config/studio_prefs.json"
}
```

Place this file in the addon root directory (same folder as `__init__.py`).

**Path Formats Supported:**
- UNC paths: `\\server\share\config\studio_prefs.json` (Windows)
- Forward slashes: `//server/share/config/studio_prefs.json` (cross-platform)
- Local paths: `/opt/studio/config/studio_prefs.json`
- Blender relative: `//config/studio_prefs.json` (relative to .blend file)

---

## How Auto-Activation Works

1. **Addon loads** → Reads `studio_prefs_location.json`
2. **Finds studio prefs** → Reads `studio_prefs.json` from network location
3. **Checks for license fields** → If `studio_license_email` and `studio_license_key` exist...
4. **Auto-activates** → Validates license and enables Pro features
5. **Silent operation** → Artists see Pre-activated addon (no manual activation needed)

---

## Monitoring Activations

Your studio license includes activation tracking:
- Each workstation = 1 activation
- Tracked by machine hardware ID
- Discord/Slack alerts when thresholds reached
- View activation counts in admin dashboard

**Alert Thresholds:**
- Alert sent on **every new activation**
- Monitor for unauthorized usage
- Track which machines are activated

---

## Troubleshooting

### License Not Auto-Activating

**Check console output** (Window → Toggle System Console):
```
[BNDL] Loaded studio preferences from: \\server\share\config\studio_prefs.json
[BNDL] Studio license auto-activated successfully for studio@yourcompany.com
```

**Common Issues:**

1. **"Cannot resolve '//' path - no .blend file open"**
   - Use absolute paths instead of `//` relative paths
   - OR: Open any .blend file before addon loads

2. **"Studio prefs not found at: ..."**
   - Check network path is correct
   - Ensure file exists and is readable
   - Test path in File Browser

3. **"Studio license validation failed"**
   - Verify license key is correct (no extra spaces)
   - Check email matches registered email
   - Ensure internet connection for first validation
   - After validation, works offline for 30 days

4. **Placeholder Key Not Replaced**
   - Replace `YOUR-BULK-LICENSE-KEY-HERE` with actual key
   - Check for typos in JSON syntax

---

## Security Best Practices

### Protect Your License Key

- **Network location**: Use read-only permissions for artists
- **File permissions**: Only admins should edit studio_prefs.json
- **Don't share publicly**: License keys are tied to your studio
- **Monitor activations**: Watch for unexpected activation alerts

### Recommended File Permissions

```
studio_prefs.json:
  - Admins: Read/Write
  - Artists: Read-only

studio_prefs_location.json:
  - Everyone: Read-only (packaged with addon)
```

---

## User Overrides

Even with studio licensing, individual artists can:
- Save personal user preferences
- Toggle "Prefer User Prefs" in addon preferences
- Override studio defaults (directories, naming, etc.)
- Cannot override license (studio license always applies)

---

## Example Deployment Script

PowerShell script to deploy addon with studio prefs:

```powershell
# Deploy BNDL-Pro to all workstations
$addonZip = "\\server\software\BNDL_Pro_v1.0.zip"
$configJson = @"
{
  "studio_prefs_path": "//server/share/config/studio_prefs.json"
}
"@

# Extract addon to Blender scripts folder
$blenderScripts = "$env:APPDATA\Blender Foundation\Blender\4.0\scripts\addons"
Expand-Archive -Path $addonZip -DestinationPath $blenderScripts -Force

# Create studio prefs location pointer
$addonRoot = "$blenderScripts\BNDL_pro_2"
$configJson | Out-File -FilePath "$addonRoot\studio_prefs_location.json" -Encoding utf8

Write-Host "BNDL-Pro deployed with studio licensing"
```

---

## Contact & Support

For bulk license inquiries:
- Email: licensing@bndl.tools
- Discord: [Your Discord invite]
- Documentation: https://docs.bndl.tools

---

## See Also

- [PREFERENCES.md](PREFERENCES.md) - General preference system
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Getting started guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Feature overview
