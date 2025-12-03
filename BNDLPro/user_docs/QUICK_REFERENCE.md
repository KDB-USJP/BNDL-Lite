# BNDL-Pro Quick Reference Card

## Common Operations

### Export
1. Select object with Geometry Nodes modifier
2. N-Panel → BNDL → Export .bndl
3. Choose save location

### Replay
1. Select target object(s)
2. N-Panel → BNDL → Choose .bndl...
3. Select .bndl file

### Library Browser
1. N-Panel → BNDL → Library section
2. Select project from dropdown
3. Click .bndl in list
4. Click "Apply to Selection"

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open N-Panel | `N` |
| Toggle System Console | `Window Menu → Toggle System Console` |
| Refresh Preferences | Click button in Addon Preferences |

---

## Preference Modes

### PROXIES Mode
- Fast replay
- Creates placeholder objects
- Use when: Assets already exist in scene

### APPEND_ASSETS Mode  
- Full asset import
- Requires matching .blend file
- Use when: Sharing trees with assets

---

## Asset Bundling Workflow

```
1. Create node tree → 2. Export .bndl → 3. .blend auto-created
                                                 ↓
6. Tree applied     ← 5. Assets imported  ← 4. Replay .bndl
```

---

## Console Messages

| Message | Meaning |
|---------|---------|
| `[BNDL] Found X asset reference(s)` | X assets will be imported |
| `[BNDL] Appended Y asset(s)` | Y datablocks imported from .blend |
| `[BNDL] Stage 4 Complete` | Replay finished successfully |
| `[BNDL] Objects already linked` | Assets pre-organized (normal) |

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Missing assets | Enable APPEND_ASSETS mode |
| Tree doesn't work | Check console for errors |
| Can't find .bndl | Check project path in preferences |
| Objects not visible | Check BNDL_Assets collection visibility |

---

## File Locations

### Studio Preferences
```
//network/share/bndl/studio_prefs.json
```

### User Preferences  
```
Blender Preferences → Add-ons → BNDL Tools
```

### Library Structure
```
project_name/
  ├─ BNDL-name-HASH.bndl
  └─ BNDL-name-HASH.blend
```

---

## JSON Studio Prefs Template

```json
{
  "asset_dependency_mode": "APPEND_ASSETS",
  "keep_replay_text": false,
  "projects": [
    {
      "name": "Project Name",
      "path": "//path/to/library"
    }
  ]
}
```

---

*Quick reference for BNDL-Pro v2.0*
