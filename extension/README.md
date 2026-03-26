# BlackboardSync Browser Extension (MVP)

This extension is an initial browser-based downloader for Blackboard pages,
inspired by projects like Canvas course downloaders.

## Scope (MVP)

- Detect downloadable links from the current Blackboard page.
- Download all detected links to a folder named after the current course.
- Keep the desktop app as the primary full-sync option.

## Build/Package

No build step is required for the MVP.

To load locally in Chrome/Edge:

1. Open `chrome://extensions` or `edge://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `extension/` folder

## Release

Use a tag with prefix `ext-v` (example: `ext-v0.1.0`).
The GitHub workflow `.github/workflows/release-extension.yml` will:

- package the `extension/` folder as a `.zip`
- create a GitHub Release with that asset
