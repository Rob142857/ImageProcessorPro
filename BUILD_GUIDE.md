# Desktop build guide

ImageProcessorPro 2.0 uses the maintained `build_app.py` entrypoint. No `.spec` file is required.

## Windows

Use Python 3.11–3.13 from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install ".[gui,build]"
.venv\Scripts\python build_app.py
```

Or run `build_windows.bat`. The portable application and ZIP are written under `dist/`.

The standard desktop build handles still images only. PDF support is a separately licensed optional extra; review the PyMuPDF licence before adding `pdf` to the install and packaging configuration.

Before distribution:

1. Run `.venv\Scripts\python -m pytest` in an environment installed with the `dev` extra.
2. Launch `dist\ImageProcessorPro\ImageProcessorPro.exe` on a clean Windows machine.
3. Process one portrait-orientation JPEG and one high-resolution TIFF.
4. Confirm the derivative is progressive sRGB, watermarked, metadata-stripped and accompanied by a valid checksum sidecar.
5. Code-sign the executable using the organisation's normal signing process.

Do not package `.env`, source scans, derivative output, logs or cloud credentials.
