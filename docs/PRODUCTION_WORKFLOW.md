# Production derivative workflow

ImageProcessorPro is a derivative renderer, not an archive, upload service or source of truth.

1. SharePoint retains the original file. The renderer receives a locally staged, read-only copy and a JSON job manifest containing its expected SHA-256 plus stable SharePoint site, drive, item, eTag and version identifiers.
2. Run one manifest with `python cli.py --job-manifest job.json --config config/mjw-web-v2.yaml --output-dir derivatives`.
3. The renderer creates only `${catalogId}_web.jpg` and a JSON sidecar in the output directory. The sidecar records source and derivative SHA-256 values, the profile, watermark/provenance fields and idempotency key.
4. A separately authenticated MJW submission service validates the manifest/catalog reservation and submits the derivative plus sidecar to Fedora. This tool never receives Fedora, database, SharePoint or Cloudflare credentials.

## Current integration boundary

Step 4 is deliberately not implemented in this repository. The current MJW lodgement Worker accepts artwork metadata and binaries, but does not yet expose a derivative-sidecar endpoint. Do not discard the sidecar or claim an end-to-end ingest until that bridge exists.

The bridge must map and test at least: `catalogId` to Fedora identifier/container; rights; stable SharePoint site/drive/item/eTag/version and source checksum; derivative checksum, dimensions, MIME and sRGB profile; rendering profile/watermark hashes; and the idempotency key. A replay with the same key must return the existing Fedora derivative, while changed source/profile semantics must create an explicitly versioned replacement. Curatorial title/date/type/collection metadata remains owned by the lodgement record and must be joined by catalog ID rather than invented by this renderer.

The idempotency key is a SHA-256 over the canonical catalog ID, expected source checksum, complete SharePoint identity/version, rights and approved profile. A new operational `jobId` does not force a rerender; changed source, rights or profile semantics do.

The manifest is strict JSON, uses schema version `mjw.image-job.v1`, and must contain `jobId`, canonical `catalogId`, absolute `inputPath`, expected `sourceSha256`, SharePoint `siteId`, `driveId`, `itemId`, `eTag`, `version`, `originalFilename`, `relativePath`, rights, `profileId`, and `profileVersion`. It rejects credentials, unknown fields, source checksum mismatches and catalog sequence `000`. Manifest mode accepts still images only; PDF needs a distinct multi-page output contract.

Write derivatives to a separate workspace, never into the staged originals tree. An existing derivative without its matching sidecar (or vice versa) is treated as an operator-visible collision instead of being overwritten.

`mjw-web-v2` is the approved 2400px progressive sRGB JPEG profile (quality up to 88, hard 2500 KB target, metadata stripped, restrained text watermark, no more than four workers). The renderer lowers encoding quality only when necessary to meet the size ceiling and fails closed if it cannot.

Run the complete checks with `python -m pytest`.
