"""Strict, credential-free contract for one MJW web-derivative job."""

from __future__ import annotations

import json
import hashlib
import hmac
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "mjw.image-job.v1"
CATALOG_ID_RE = re.compile(r"^MJW-(P|D|S|PH|PM|NB)-(\d{4})-(\d{3})$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
FORBIDDEN_KEY_RE = re.compile(r"(?:password|secret|token|credential|authorization|api[_-]?key|connection[_-]?string)", re.I)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRODUCTION_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class ManifestValidationError(ValueError):
    """Raised when a job manifest is not safe or complete enough to process."""


def _require_string(value: Any, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ManifestValidationError(f"{field} must be a non-empty string no longer than {maximum} characters")
    return value.strip()


def _strict_object(value: Any, field: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{field} must be an object")
    unknown = set(value) - keys
    if unknown:
        raise ManifestValidationError(f"{field} contains unsupported field(s): {', '.join(sorted(unknown))}")
    missing = keys - set(value)
    if missing:
        raise ManifestValidationError(f"{field} is missing required field(s): {', '.join(sorted(missing))}")
    return value


def _reject_credentials(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if FORBIDDEN_KEY_RE.search(str(key)):
                raise ManifestValidationError(f"{path}.{key} is not allowed: credentials belong in the runtime secret store")
            _reject_credentials(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credentials(child, f"{path}[{index}]")


@dataclass(frozen=True)
class SharePointSource:
    site_id: str
    drive_id: str
    item_id: str
    etag: str
    version: str
    original_filename: str
    relative_path: str

    def as_dict(self) -> dict[str, str]:
        return {
            "siteId": self.site_id,
            "driveId": self.drive_id,
            "itemId": self.item_id,
            "eTag": self.etag,
            "version": self.version,
            "originalFilename": self.original_filename,
            "relativePath": self.relative_path,
        }


@dataclass(frozen=True)
class JobManifest:
    schema_version: str
    job_id: str
    catalog_id: str
    input_path: Path
    source_sha256: str
    source: SharePointSource
    rights: str
    profile_id: str
    profile_version: str

    @property
    def output_filename(self) -> str:
        return f"{self.catalog_id}_web.jpg"

    @property
    def idempotency_key(self) -> str:
        material = {
            "catalogId": self.catalog_id,
            "sourceSha256": self.source_sha256,
            "sharePoint": self.source.as_dict(),
            "rights": self.rights,
            "profileId": self.profile_id,
            "profileVersion": self.profile_version,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return f"sha256:{digest}"

    def provenance(self) -> dict[str, Any]:
        """Only stable, non-secret fields intended for derivative sidecars/Fedora metadata."""
        return {
            "schemaVersion": self.schema_version,
            "jobId": self.job_id,
            "catalogId": self.catalog_id,
            "sourceSha256": self.source_sha256,
            "sharePoint": self.source.as_dict(),
            "rights": self.rights,
            "profileId": self.profile_id,
            "profileVersion": self.profile_version,
            "idempotencyKey": self.idempotency_key,
        }


def load_job_manifest(path: str | Path) -> JobManifest:
    """Load and strictly validate a single JSON job manifest without credentials."""
    manifest_path = Path(path)
    try:
        if manifest_path.stat().st_size > 64 * 1024:
            raise ManifestValidationError("Manifest exceeds the 64 KiB contract limit")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"Manifest not found: {manifest_path}") from exc
    except OSError as exc:
        raise ManifestValidationError(f"Manifest could not be read: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Manifest must be valid JSON: {exc.msg}") from exc

    _reject_credentials(data)
    root = _strict_object(data, "manifest", {
        "schemaVersion", "jobId", "catalogId", "inputPath", "sourceSha256", "sharePoint", "rights", "profileId", "profileVersion",
    })
    if root["schemaVersion"] != SCHEMA_VERSION:
        raise ManifestValidationError(f"schemaVersion must be {SCHEMA_VERSION}")

    job_id = _require_string(root["jobId"], "jobId", maximum=256)
    catalog_id = _require_string(root["catalogId"], "catalogId", maximum=32).upper()
    if not ID_RE.fullmatch(job_id):
        raise ManifestValidationError("jobId must contain only letters, numbers, '.', '_', ':' or '-'")
    catalog_match = CATALOG_ID_RE.fullmatch(catalog_id)
    if not catalog_match or catalog_match.group(3) == "000":
        raise ManifestValidationError("catalogId must use MJW-{TYPE}-{YEAR}-{001..999}")

    input_path = Path(_require_string(root["inputPath"], "inputPath")).expanduser()
    if not input_path.is_absolute() or not input_path.is_file():
        raise ManifestValidationError("inputPath must be an existing absolute local file path")
    if input_path.suffix.lower() not in PRODUCTION_IMAGE_EXTENSIONS:
        raise ManifestValidationError("inputPath must be a supported still image; PDF jobs require a separate multi-page contract")

    source_sha256 = _require_string(root["sourceSha256"], "sourceSha256", maximum=64).lower()
    if not SHA256_RE.fullmatch(source_sha256):
        raise ManifestValidationError("sourceSha256 must be a 64-character SHA-256 hex digest")
    digest = hashlib.sha256()
    with input_path.open("rb") as source_stream:
        for block in iter(lambda: source_stream.read(1024 * 1024), b""):
            digest.update(block)
    if not hmac.compare_digest(source_sha256, digest.hexdigest()):
        raise ManifestValidationError("sourceSha256 does not match the staged input file")

    source_data = _strict_object(root["sharePoint"], "sharePoint", {
        "siteId", "driveId", "itemId", "eTag", "version", "originalFilename", "relativePath",
    })
    source = SharePointSource(
        site_id=_require_string(source_data["siteId"], "sharePoint.siteId", maximum=256),
        drive_id=_require_string(source_data["driveId"], "sharePoint.driveId", maximum=256),
        item_id=_require_string(source_data["itemId"], "sharePoint.itemId", maximum=256),
        etag=_require_string(source_data["eTag"], "sharePoint.eTag", maximum=512),
        version=_require_string(source_data["version"], "sharePoint.version", maximum=256),
        original_filename=_require_string(source_data["originalFilename"], "sharePoint.originalFilename", maximum=512),
        relative_path=_require_string(source_data["relativePath"], "sharePoint.relativePath", maximum=2048).replace("\\", "/"),
    )
    relative_parts = PurePosixPath(source.relative_path).parts
    if not relative_parts or ".." in relative_parts or source.relative_path.startswith("/") or ":" in relative_parts[0]:
        raise ManifestValidationError("sharePoint.relativePath must be a relative path without '..'")
    if Path(source.original_filename).name != source.original_filename:
        raise ManifestValidationError("sharePoint.originalFilename must not contain a path")
    if PurePosixPath(source.relative_path).name != source.original_filename:
        raise ManifestValidationError("sharePoint.relativePath must end with originalFilename")
    if input_path.name != source.original_filename:
        raise ManifestValidationError("inputPath filename must match sharePoint.originalFilename")

    return JobManifest(
        schema_version=SCHEMA_VERSION,
        job_id=job_id,
        catalog_id=catalog_id,
        input_path=input_path,
        source_sha256=source_sha256,
        source=source,
        rights=_require_string(root["rights"], "rights", maximum=2000),
        profile_id=_require_string(root["profileId"], "profileId", maximum=128),
        profile_version=_require_string(root["profileVersion"], "profileVersion", maximum=128),
    )
