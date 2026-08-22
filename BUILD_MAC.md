# macOS build guide

Use Python 3.11–3.13 on macOS. Builds must be produced on macOS because PyInstaller does not cross-compile application bundles.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[gui,build]'
python build_app.py
```

`build_macos.sh` performs the same pinned installation and build. Output is written under `dist/`; when `hdiutil` is present the wrapper also creates a DMG.

The standard desktop build handles still images only. PDF support is optional and uses PyMuPDF; confirm its AGPL-3.0/commercial licensing implications before packaging the `pdf` extra.

Before distribution:

1. Run the test suite from a development environment.
2. Smoke-test the `.app` on a clean supported Mac.
3. Confirm watermark, sRGB, metadata-removal, checksum and idempotent-rerun behaviour.
4. Sign with Developer ID, enable hardened runtime, and notarize/staple using the organisation's Apple credentials.

Keep signing credentials in Keychain or CI secrets. Never place them in this repository or a command file.
