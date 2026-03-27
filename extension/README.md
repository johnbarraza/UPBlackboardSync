# BlackboardSync Browser Extension

A browser-based course archiver for Blackboard, inspired by Canvas-style download workflows.

## Features (Current)

- Select one or multiple courses discovered from your Blackboard dashboard/page.
- Active/past filtering with search in the course selector.
- Export presets:
  - Full Archive
  - Files Only
  - Text Content Only
  - Linked Files Only
  - Custom
- Settings page with:
  - Content type toggles
  - Conflict handling
  - Delay/throttling
  - Folder prefix
  - ZIP bundling (one ZIP per course)
  - Incremental mode
  - File filters (exclude video, max file size)
- Keyboard shortcut:
  - Windows/Linux: `Ctrl+Shift+D`
  - macOS: `Cmd+Shift+D`
- Works with Blackboard sessions already logged in on the browser.

## Notes

- The extension crawls course pages reachable from the selected course URL and attempts to extract linked/downloadable resources.
- ZIP bundling uses local browser-side ZIP generation (no server upload).
- All settings and incremental history are stored locally via `chrome.storage.local`.

## Install (Chrome / Edge)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select the `extension/` folder.

## Release

Desktop tag (`0.x.y`) can attach extension assets through:
- `.github/workflows/release-extension-assets.yml`

Extension-only tag (`ext-vx.y.z`) uses:
- `.github/workflows/release-extension.yml`
