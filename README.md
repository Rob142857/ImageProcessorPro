# ImageProcessorPro

ImageProcessorPro creates public web derivatives from high-resolution artwork scans. SharePoint remains the source of truth for originals; this repository performs deterministic local rendering and does not connect directly to Fedora or PostgreSQL.

## Production workflow

Use manifest mode for archive work:

```powershell
python cli.py --job-manifest job.json --config config/mjw-web-v2.yaml --output-dir derivatives
```

The approved `mjw-web-v2` profile creates a deterministic `${catalogId}_web.jpg` with:

- a 2400 px maximum edge, progressive JPEG encoding and a hard 2500 KB ceiling;
- physical EXIF orientation correction and sRGB output with an embedded ICC profile;
- public-safe metadata stripping, including GPS data;
- a restrained repeating MJW Estate watermark;
- atomic output writes, decode verification and SHA-256 fixity;
- a credential-free `*.jpg.json` sidecar containing stable SharePoint provenance, profile and watermark hashes, dimensions and input/output checksums.

The sidecar never records local absolute paths. A separately authenticated archive service should submit the derivative and sidecar to Fedora. Original scans remain read-only in SharePoint.

See [the production workflow](docs/PRODUCTION_WORKFLOW.md) for the contract and idempotency rules.

### Job manifest

```json
{
  "schemaVersion": "mjw.image-job.v1",
  "jobId": "job-2026-001",
  "catalogId": "MJW-P-2026-001",
  "inputPath": "C:/staging/scan-001.tif",
  "sourceSha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "sharePoint": {
    "siteId": "site-id",
    "driveId": "drive-id",
    "itemId": "item-id",
    "eTag": "etag-or-version-token",
    "version": "1.0",
    "originalFilename": "scan-001.tif",
    "relativePath": "Originals/scan-001.tif"
  },
  "rights": "Michael J Wright Estate - All Rights Reserved",
  "profileId": "mjw-web-v2",
  "profileVersion": "2.0.0"
}
```

Unknown fields, credential-like keys, `000` catalog sequences, PDFs and source checksum mismatches are rejected. Production output must be outside the staged originals directory. Credentials belong in the calling service's secret store, never in a job or derivative sidecar.

## Install and test

Python 3.11–3.13 is supported.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

For the core renderer only, use `python -m pip install .`. Add extras as needed:

```powershell
python -m pip install ".[gui]"
python -m pip install ".[pdf]"
python -m pip install ".[api]"
python -m pip install ".[azure]"
```

PDF support uses PyMuPDF, which is distributed under AGPL-3.0 or a commercial licence. Confirm the intended distribution model before packaging it. PDF processing is optional and disabled cleanly when the extra is absent.

## Interactive tools

The folder CLI and desktop GUI remain available for previews and legacy batches:

```powershell
python cli.py -i input
python gui_app.py
```

These interactive defaults are not the immutable archive profile. Production archive derivatives should always use manifest mode.

The `power_platform` HTTP API and `azure` helpers are compatibility prototypes, not the production ingest boundary. The API binds to localhost by default, requires `IMAGE_PROCESSOR_API_TOKEN` for every non-health route, caps request/decoded payload size and disables remote configuration changes unless explicitly enabled. Put it behind an authenticated gateway before any network exposure.

Azure Blob supports `DefaultAzureCredential` with `AZURE_STORAGE_ACCOUNT_URL`; a connection string remains compatibility-only. The legacy Computer Vision adapter is isolated in the `vision-legacy` extra because Azure Image Analysis is on a published retirement path.

## Build

Reproducible desktop builds use the pinned `build` extra:

```powershell
.venv\Scripts\python -m pip install ".[gui,build]"
.venv\Scripts\python build_app.py
```

Windows and macOS wrappers are provided in `build_windows.bat` and `build_macos.sh`.

## Key safeguards

- image source byte, decoded pixel and PDF page limits;
- no raw EXIF/GPS in public derivatives;
- bounded processing concurrency (maximum four workers);
- deterministic catalog-based production filenames and idempotency keys;
- collision-free archive jobs: one canonical catalog ID per manifest;
- atomic files and manifests, followed by reopen/decode and checksum verification;
- no Fedora, database, Cloudflare or SharePoint credentials in this application.
