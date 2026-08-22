"""Safe, repeatable web-derivative generation for archive images."""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import yaml
from loguru import logger
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

try:
    import fitz
except ImportError:  # PDF support is an explicit, separately licensed extra.
    fitz = None


Path("logs").mkdir(exist_ok=True)
logger.add("logs/image_processor_{time}.log", rotation="1 day", retention="30 days")
_SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
_RENDERER_VERSION = "2.0.0"


@dataclass
class ProcessingConfig:
    input_folder: str = ""
    output_folder: str = ""
    watermark_path: str = ""
    jpeg_quality: int = 82
    png_compression: int = 6
    webp_quality: int = 82
    target_max_size_kb: int = 1200
    preserve_metadata: bool = False
    metadata_policy: str = "public"  # public, safe, preserve
    watermark_opacity: float = 0.30
    watermark_position: str = "bottom-right"
    watermark_scale: float = 0.20
    use_tiled_watermark: bool = True
    tile_size_ratio: float = 0.20
    tile_spacing_ratio: float = 1.50
    tile_opacity_reduction: float = 0.70
    use_text_watermark: bool = True
    watermark_text: str = "Michael J Wright Estate | All Rights Reserved"
    text_font_size_ratio: float = 0.015
    text_watermark_opacity: int = 63
    text_watermark_color: Tuple[int, int, int] = (128, 128, 128)
    text_rotation_angle: int = -30
    text_spacing_ratio: float = 0.20
    use_text_outline: bool = False
    text_outline_width: int = 0
    text_outline_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    long_edge_pixels: int = 1200
    output_dpi: int = 72
    convert_to_srgb: bool = True
    web_output_suffix: str = "_web"
    create_subfolder: bool = True
    subfolder_name: str = "web_optimized"
    max_width: int = 1920  # retained for backwards compatibility; long_edge_pixels is authoritative
    max_height: int = 1080
    output_format: str = "JPEG"
    preserve_aspect_ratio: bool = True
    use_multiprocessing: bool = False
    max_workers: Optional[int] = None
    pdf_dpi: int = 150
    max_pixels: int = 80_000_000
    max_pdf_pages: int = 100
    max_source_bytes: int = 2 * 1024 * 1024 * 1024

    def validate(self) -> None:
        boolean_fields = (
            "preserve_metadata", "convert_to_srgb", "use_tiled_watermark",
            "use_text_watermark", "use_text_outline", "create_subfolder",
            "preserve_aspect_ratio", "use_multiprocessing",
        )
        if any(type(getattr(self, name)) is not bool for name in boolean_fields):
            raise ValueError("boolean configuration fields must use true or false")
        integer_fields = (
            "jpeg_quality", "png_compression", "webp_quality", "target_max_size_kb",
            "text_watermark_opacity", "text_rotation_angle", "text_outline_width",
            "long_edge_pixels", "output_dpi", "max_width", "max_height", "pdf_dpi",
            "max_pixels", "max_pdf_pages", "max_source_bytes",
        )
        if any(type(getattr(self, name)) is not int for name in integer_fields):
            raise ValueError("integer configuration fields must contain whole numbers")
        numeric_fields = (
            "watermark_opacity", "watermark_scale", "tile_size_ratio",
            "tile_spacing_ratio", "tile_opacity_reduction", "text_font_size_ratio",
            "text_spacing_ratio",
        )
        if any(
            isinstance(getattr(self, name), bool)
            or not isinstance(getattr(self, name), (int, float))
            for name in numeric_fields
        ):
            raise ValueError("ratio and opacity fields must contain numbers")
        if any(
            not isinstance(value, str)
            for value in (
                self.output_format, self.metadata_policy, self.watermark_text,
                self.subfolder_name, self.web_output_suffix, self.watermark_position,
                self.input_folder, self.output_folder, self.watermark_path,
            )
        ):
            raise ValueError("path, format, policy and text configuration must use strings")
        if self.output_format.upper() not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("output_format must be JPEG, PNG, or WEBP")
        if not 1 <= self.jpeg_quality <= 100 or not 1 <= self.webp_quality <= 100:
            raise ValueError("JPEG and WebP quality must be 1..100")
        if not 0 <= self.png_compression <= 9 or self.target_max_size_kb < 1:
            raise ValueError("invalid compression or target size")
        if self.metadata_policy not in {"public", "safe", "preserve"}:
            raise ValueError("metadata_policy must be public, safe, or preserve")
        # Preserve the old boolean configuration without allowing it to disagree
        # with the explicit v2 policy.
        if self.preserve_metadata:
            self.metadata_policy = "preserve"
        elif self.metadata_policy == "preserve":
            self.preserve_metadata = True
        if self.long_edge_pixels < 64 or self.max_pixels < 1 or self.max_pdf_pages < 1:
            raise ValueError("invalid image resource limit")
        if self.max_source_bytes < 1 or not 0 <= self.watermark_opacity <= 1:
            raise ValueError("invalid source size or watermark opacity")
        if not 0.01 <= self.watermark_scale <= 1:
            raise ValueError("watermark_scale must be between 0.01 and 1")
        if not 0.01 <= self.tile_size_ratio <= 1 or not 0.25 <= self.tile_spacing_ratio <= 10:
            raise ValueError("tile size/spacing is outside the safe range")
        if not 0 <= self.tile_opacity_reduction <= 1:
            raise ValueError("tile_opacity_reduction must be between 0 and 1")
        if not 0.005 <= self.text_font_size_ratio <= 0.2:
            raise ValueError("watermark scales and spacing must be positive")
        if not 0 <= self.text_spacing_ratio <= 10:
            raise ValueError("text_spacing_ratio must keep tile steps positive")
        if not 0 <= self.text_watermark_opacity <= 255:
            raise ValueError("text watermark opacity must be 0..255")
        if not isinstance(self.text_watermark_color, (tuple, list)) or len(self.text_watermark_color) != 3 or any(not 0 <= int(v) <= 255 for v in self.text_watermark_color):
            raise ValueError("text watermark color must contain RGB bytes")
        if not isinstance(self.text_outline_color, (tuple, list)) or len(self.text_outline_color) != 4 or any(not 0 <= int(v) <= 255 for v in self.text_outline_color):
            raise ValueError("text outline color must contain RGBA bytes")
        if not 0 <= self.text_outline_width <= 20 or not -360 <= self.text_rotation_angle <= 360:
            raise ValueError("invalid text outline width or rotation")
        if self.use_text_watermark and not self.watermark_text.strip():
            raise ValueError("watermark_text is required when text watermarking is enabled")
        if not 1 <= self.output_dpi <= 1200 or not 36 <= self.pdf_dpi <= 600:
            raise ValueError("invalid output or PDF DPI")
        if self.max_workers is not None and type(self.max_workers) is not int:
            raise ValueError("max_workers must be a whole number or null")
        if self.max_workers is not None and not 1 <= self.max_workers <= 64:
            raise ValueError("max_workers must be 1..64 or null")
        if self.watermark_position not in {"center", "top-left", "top-right", "bottom-left", "bottom-right"}:
            raise ValueError("invalid watermark_position")
        if not self.preserve_aspect_ratio:
            raise ValueError("non-proportional resizing is not supported for artwork derivatives")
        if (
            not self.subfolder_name
            or Path(self.subfolder_name).name != self.subfolder_name
            or self.subfolder_name in {".", ".."}
        ):
            raise ValueError("subfolder_name must be one safe folder name")
        if any(separator in self.web_output_suffix for separator in ("/", "\\")):
            raise ValueError("web_output_suffix cannot contain path separators")

    def save_to_file(self, filepath: str) -> None:
        self.validate()
        data = asdict(self)
        for key in ("text_watermark_color", "text_outline_color"):
            data[key] = list(data[key])
        with open(filepath, "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=True)

    @classmethod
    def load_from_file(cls, filepath: str) -> "ProcessingConfig":
        with open(filepath, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("configuration must be a YAML mapping")
        for key in ("text_watermark_color", "text_outline_color"):
            if key in data:
                data[key] = tuple(data[key])
        config = cls(**data)
        config.validate()
        return config


class ImageProcessor:
    supported_formats = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".pdf", ".webp"}

    def __init__(self, config: ProcessingConfig, provenance: Optional[Dict[str, Any]] = None):
        config.validate()
        self.config = config
        self.provenance = provenance or {}
        self.watermark_image: Optional[Image.Image] = None
        if config.watermark_path:
            self.load_watermark(config.watermark_path)
        if config.output_folder:
            Path(config.output_folder).mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(exist_ok=True)

    def load_watermark(self, watermark_path: str) -> None:
        try:
            with Image.open(watermark_path) as source:
                self.watermark_image = source.convert("RGBA")
        except Exception as error:
            logger.warning("Watermark disabled; could not read {}: {}", watermark_path, error)
            self.watermark_image = None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _profile_hash(self) -> str:
        data = asdict(self.config)
        data.pop("input_folder", None)
        data.pop("output_folder", None)
        watermark_path = Path(self.config.watermark_path) if self.config.watermark_path else None
        profile = {
            "config": data,
            "watermark_asset_sha256": (
                self._sha256(watermark_path) if watermark_path and watermark_path.is_file() else None
            ),
        }
        return hashlib.sha256(json.dumps(profile, sort_keys=True, default=list).encode()).hexdigest()

    def _source_ok(self, path: Path) -> None:
        if path.stat().st_size > self.config.max_source_bytes:
            raise ValueError(f"source exceeds configured size limit: {path.name}")

    def _open_oriented_srgb(self, path: Path) -> Tuple[Image.Image, Optional[bytes], Optional[bytes]]:
        self._source_ok(path)
        with Image.open(path) as opened:
            if opened.width * opened.height > self.config.max_pixels:
                raise ValueError(f"source exceeds {self.config.max_pixels:,} pixel limit")
            opened.load()
            source_exif = opened.getexif()
            icc = opened.info.get("icc_profile")
            image = ImageOps.exif_transpose(opened)
            # Pixels are physically transposed above, so retaining Orientation would
            # make metadata-aware clients rotate the derivative a second time.
            if 274 in source_exif:
                del source_exif[274]
            if self.config.metadata_policy == "preserve":
                exif = source_exif.tobytes()
            elif self.config.metadata_policy == "safe":
                safe_exif = Image.Exif()
                for tag in (315, 33432):  # Artist, Copyright
                    if tag in source_exif:
                        safe_exif[tag] = source_exif[tag]
                exif = safe_exif.tobytes() if len(safe_exif) else None
            else:
                exif = None
            if self.config.convert_to_srgb and icc:
                try:
                    source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    if image.mode == "RGBA":
                        alpha = image.getchannel("A")
                        rgb = ImageCms.profileToProfile(image.convert("RGB"), source_profile, ImageCms.createProfile("sRGB"), outputMode="RGB")
                        image = Image.merge("RGBA", (*rgb.split(), alpha))
                    else:
                        # Keep CMYK/LAB pixels in their source mode until ImageCms has
                        # interpreted them through the embedded source profile.
                        image = ImageCms.profileToProfile(
                            image, source_profile, ImageCms.createProfile("sRGB"), outputMode="RGB"
                        )
                except Exception as error:
                    logger.warning("ICC conversion failed for {}: {}", path.name, error)
                    image = image.convert("RGBA" if image.mode == "RGBA" else "RGB")
            elif image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            return image.copy(), exif, _SRGB_PROFILE

    def resize_for_web(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        scale = min(1.0, self.config.long_edge_pixels / max(width, height))
        if scale == 1:
            return image
        return image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.LANCZOS)

    def _font(self, size: int) -> ImageFont.ImageFont:
        for path in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"):
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def apply_text_watermark(self, image: Image.Image) -> Image.Image:
        canvas = image.convert("RGBA")
        size = max(12, round(canvas.width * self.config.text_font_size_ratio))
        font = self._font(size)
        text = self.config.watermark_text.strip()
        if not text.startswith("©"):
            text = "© " + text
        sample = Image.new("RGBA", (1, 1))
        box = ImageDraw.Draw(sample).textbbox((0, 0), text, font=font)
        pad = max(12, size // 2)
        stamp = Image.new("RGBA", (box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2))
        draw = ImageDraw.Draw(stamp)
        color = tuple(self.config.text_watermark_color) + (self.config.text_watermark_opacity,)
        draw.text((pad, pad), text, font=font, fill=color, stroke_width=self.config.text_outline_width if self.config.use_text_outline else 0, stroke_fill=tuple(self.config.text_outline_color))
        stamp = stamp.rotate(self.config.text_rotation_angle, expand=True, resample=Image.Resampling.BICUBIC)
        step_x = max(1, round(stamp.width * (1 + self.config.text_spacing_ratio)))
        step_y = max(1, round(stamp.height * (1 + self.config.text_spacing_ratio)))
        overlay = Image.new("RGBA", canvas.size)
        for row, y in enumerate(range(-stamp.height, canvas.height + stamp.height, step_y)):
            offset = step_x // 2 if row % 2 else 0
            for x in range(-stamp.width + offset, canvas.width + stamp.width, step_x):
                overlay.alpha_composite(stamp, (x, y))
        return Image.alpha_composite(canvas, overlay)

    def apply_tiled_watermark(self, image: Image.Image) -> Image.Image:
        if not self.watermark_image:
            return image
        canvas = image.convert("RGBA")
        width = max(1, round(canvas.width * self.config.tile_size_ratio))
        height = max(1, round(width * self.watermark_image.height / self.watermark_image.width))
        tile = self.watermark_image.resize((width, height), Image.Resampling.LANCZOS).copy()
        alpha = tile.getchannel("A").point(lambda value: round(value * self.config.watermark_opacity * self.config.tile_opacity_reduction))
        tile.putalpha(alpha)
        step_x = max(1, round(width * self.config.tile_spacing_ratio))
        step_y = max(1, round(height * self.config.tile_spacing_ratio))
        overlay = Image.new("RGBA", canvas.size)
        for row, y in enumerate(range(0, canvas.height, step_y)):
            for x in range((step_x // 2 if row % 2 else 0), canvas.width, step_x):
                overlay.alpha_composite(tile, (x, y))
        return Image.alpha_composite(canvas, overlay)

    def calculate_watermark_position(self, img_width: int, img_height: int, watermark_width: int, watermark_height: int) -> Tuple[int, int]:
        margin = min(20, max(0, min(img_width, img_height) // 20))
        positions = {"center": ((img_width-watermark_width)//2, (img_height-watermark_height)//2), "top-left": (margin, margin), "top-right": (img_width-watermark_width-margin, margin), "bottom-left": (margin, img_height-watermark_height-margin), "bottom-right": (img_width-watermark_width-margin, img_height-watermark_height-margin)}
        return positions.get(self.config.watermark_position, positions["bottom-right"])

    def apply_single_watermark(self, image: Image.Image) -> Image.Image:
        if not self.watermark_image:
            return image
        canvas = image.convert("RGBA")
        width = max(1, round(canvas.width * self.config.watermark_scale))
        height = max(1, round(width * self.watermark_image.height / self.watermark_image.width))
        stamp = self.watermark_image.resize((width, height), Image.Resampling.LANCZOS).copy()
        stamp.putalpha(stamp.getchannel("A").point(lambda value: round(value * self.config.watermark_opacity)))
        overlay = Image.new("RGBA", canvas.size)
        overlay.alpha_composite(stamp, self.calculate_watermark_position(*canvas.size, width, height))
        return Image.alpha_composite(canvas, overlay)

    def apply_watermark(self, image: Image.Image) -> Image.Image:
        if self.config.use_text_watermark:
            return self.apply_text_watermark(image)
        return self.apply_tiled_watermark(image) if self.config.use_tiled_watermark else self.apply_single_watermark(image)

    def _encoded_output(self, image: Image.Image, exif: Optional[bytes], icc: bytes) -> bytes:
        """Encode once in memory so the final file can be replaced atomically."""
        fmt = self.config.output_format.upper()
        if fmt == "JPEG" and image.mode != "RGB":
            backdrop = Image.new("RGB", image.size, "white")
            backdrop.paste(image, mask=image.getchannel("A") if image.mode == "RGBA" else None)
            image = backdrop

        def encode(quality: Optional[int] = None) -> bytes:
            if fmt == "JPEG":
                kwargs: Dict[str, Any] = {
                    "quality": quality if quality is not None else self.config.jpeg_quality,
                    "subsampling": 0,
                    "optimize": True,
                    "progressive": True,
                    "dpi": (self.config.output_dpi, self.config.output_dpi),
                    "icc_profile": icc,
                }
                if exif and self.config.metadata_policy in {"safe", "preserve"}:
                    kwargs["exif"] = exif
            elif fmt == "PNG":
                kwargs = {
                    "compress_level": self.config.png_compression,
                    "optimize": True,
                    "dpi": (self.config.output_dpi, self.config.output_dpi),
                    "icc_profile": icc,
                }
            else:
                kwargs = {
                    "quality": quality if quality is not None else self.config.webp_quality,
                    "method": 6,
                    "icc_profile": icc,
                }
            buffer = io.BytesIO()
            image.save(buffer, fmt, **kwargs)
            return buffer.getvalue()

        initial_quality = self.config.jpeg_quality if fmt == "JPEG" else self.config.webp_quality
        payload = encode(initial_quality if fmt in {"JPEG", "WEBP"} else None)
        limit = self.config.target_max_size_kb * 1024
        if fmt not in {"JPEG", "WEBP"} or len(payload) <= limit:
            return payload

        # Select the highest usable quality. A hard failure is safer than claiming
        # a derivative meets the production profile when it does not.
        # Search the complete valid quality range.  A hard size ceiling is a
        # real contract, and some photographic sources only meet a small
        # ceiling below quality 40; starting at 40 incorrectly reported those
        # derivatives as impossible.
        low, high = 1, max(1, initial_quality - 1)
        best: Optional[bytes] = None
        while low <= high:
            quality = (low + high) // 2
            candidate = encode(quality)
            if len(candidate) <= limit:
                best = candidate
                low = quality + 1
            else:
                high = quality - 1
        if best is None:
            raise ValueError(
                f"output cannot meet configured {self.config.target_max_size_kb} KB limit at minimum quality"
            )
        return best

    def _save_atomic(self, image: Image.Image, output: Path, exif: Optional[bytes], icc: bytes) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = self._encoded_output(image, exif, icc)
        fd, temporary = tempfile.mkstemp(prefix=output.stem + ".", suffix=".tmp", dir=output.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush(); os.fsync(handle.fileno())
            with Image.open(temporary) as check:
                check.load()
                if check.size != image.size:
                    raise RuntimeError("output verification dimensions mismatch")
            os.replace(temporary, output)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def _manifest_path(self, output: Path) -> Path:
        return output.with_suffix(output.suffix + ".json")

    def _is_current(self, source: Path, output: Path, provenance: Dict[str, Any]) -> bool:
        manifest = self._manifest_path(output)
        if not output.exists() or not manifest.exists(): return False
        try:
            record = json.loads(manifest.read_text(encoding="utf-8"))
            recorded_provenance = record.get("provenance", {})
            if provenance.get("idempotencyKey"):
                provenance_matches = (
                    recorded_provenance.get("idempotencyKey") == provenance["idempotencyKey"]
                )
            else:
                provenance_matches = recorded_provenance == provenance
            return (
                record.get("rendererVersion") == _RENDERER_VERSION
                and record["input"]["sha256"] == self._sha256(source)
                and record["profile"]["sha256"] == self._profile_hash()
                and record["output"]["sha256"] == self._sha256(output)
                and provenance_matches
            )
        except Exception:
            return False

    def _write_manifest(
        self,
        source: Path,
        output: Path,
        image: Image.Image,
        provenance: Dict[str, Any],
    ) -> None:
        watermark_asset = Path(self.config.watermark_path) if self.config.watermark_path else None
        record = {
            "schemaVersion": "mjw.image-derivative.v1",
            "rendererVersion": _RENDERER_VERSION,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "input": {
                "filename": source.name,
                "sha256": self._sha256(source),
                "bytes": source.stat().st_size,
            },
            "output": {
                "filename": output.name,
                "sha256": self._sha256(output),
                "bytes": output.stat().st_size,
                "width": image.width,
                "height": image.height,
                "mimeType": {"JPEG":"image/jpeg", "PNG":"image/png", "WEBP":"image/webp"}[self.config.output_format.upper()],
                "colorProfile": "sRGB" if self.config.convert_to_srgb else "source-or-unspecified",
            },
            "profile": {
                "id": provenance.get("profileId"),
                "version": provenance.get("profileVersion"),
                "sha256": self._profile_hash(),
            },
            "watermark": {
                "enabled": bool(self.config.use_text_watermark or self.watermark_image),
                "textSha256": (
                    hashlib.sha256(self.config.watermark_text.encode("utf-8")).hexdigest()
                    if self.config.use_text_watermark else None
                ),
                "assetSha256": (
                    self._sha256(watermark_asset)
                    if watermark_asset and watermark_asset.is_file() else None
                ),
            },
            "metadataPolicy": self.config.metadata_policy,
            "provenance": provenance,
        }
        target = self._manifest_path(output)
        fd, temporary = tempfile.mkstemp(prefix=target.stem + ".", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, sort_keys=True); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def _iter_pdf_pages(self, pdf_path: str) -> Iterator[Tuple[int, Image.Image]]:
        if fitz is None:
            raise RuntimeError("PDF support is not installed; install ImageProcessorPro with the 'pdf' extra")
        path = Path(pdf_path)
        self._source_ok(path)
        document = fitz.open(path)
        try:
            if document.page_count > self.config.max_pdf_pages: raise ValueError("PDF page count exceeds configured limit")
            matrix = fitz.Matrix(self.config.pdf_dpi / 72, self.config.pdf_dpi / 72)
            for number, page in enumerate(document, 1):
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                if pixmap.width * pixmap.height > self.config.max_pixels: raise ValueError("PDF page exceeds pixel limit")
                yield number, Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        finally:
            document.close()

    def process_pdf(self, pdf_path: str) -> List[Image.Image]:
        """Legacy convenience API; production processing streams pages instead."""
        return [image for _, image in self._iter_pdf_pages(pdf_path)]

    def process_single_image(
        self,
        input_path: str,
        output_path: str,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> bool:
        source, output = Path(input_path), Path(output_path)
        effective_provenance = dict(self.provenance if provenance is None else provenance)
        try:
            if source.suffix.lower() != ".pdf" and self._is_current(source, output, effective_provenance):
                logger.info("Skipping current derivative {}", output.name); return True
            if source.suffix.lower() == ".pdf":
                processed = 0
                for number, page in self._iter_pdf_pages(str(source)):
                    page_output = output.with_name(f"{output.stem}_page_{number:03d}{output.suffix}")
                    page_provenance = {**effective_provenance, "pdfPage": number}
                    if self._is_current(source, page_output, page_provenance):
                        processed += 1
                        page.close()
                        continue
                    try:
                        rendered = self.apply_watermark(self.resize_for_web(page))
                        self._save_atomic(rendered, page_output, None, _SRGB_PROFILE)
                        self._write_manifest(source, page_output, rendered, page_provenance)
                        processed += 1
                    finally:
                        page.close()
                return processed > 0
            image, exif, icc = self._open_oriented_srgb(source)
            rendered = self.apply_watermark(self.resize_for_web(image))
            self._save_atomic(rendered, output, exif, icc or _SRGB_PROFILE)
            self._write_manifest(source, output, rendered, effective_provenance)
            return True
        except Exception as error:
            logger.error("Failed to process {}: {}", input_path, error); return False

    def save_optimized_image(self, image: Image.Image, output_path: str) -> None:
        self._save_atomic(image, Path(output_path), None, _SRGB_PROFILE)

    def get_image_files(self, folder_path: str) -> List[str]:
        root_path = Path(folder_path); files: List[str] = []
        supported = self.supported_formats if fitz is not None else self.supported_formats - {".pdf"}
        for root, dirs, names in os.walk(root_path):
            dirs[:] = [name for name in dirs if name.lower() != self.config.subfolder_name.lower()]
            for name in names:
                path = Path(root) / name
                if path.suffix.lower() in supported and not path.stem.lower().endswith(self.config.web_output_suffix.lower()): files.append(str(path))
        return sorted(files)

    def _get_output_path(self, input_path: str) -> str:
        source = Path(input_path)
        directory = source.parent / self.config.subfolder_name if self.config.create_subfolder else Path(self.config.output_folder) / source.relative_to(self.config.input_folder).parent
        return str(directory / f"{source.stem}{self.config.web_output_suffix}.{self.config.output_format.lower()}")

    def process_folder(self, progress_callback: Optional[Callable[[int, int], Any]] = None) -> Dict[str, Any]:
        sources = self.get_image_files(self.config.input_folder)
        results = {"processed": 0, "failed": 0, "total": len(sources)}
        if not sources: return results
        requested_workers = self.config.max_workers or (os.cpu_count() or 1)
        workers = min(4, requested_workers, len(sources)) if self.config.use_multiprocessing else 1

        output_groups: Dict[str, List[str]] = {}
        for source in sources:
            output_path = self._get_output_path(source)
            output_groups.setdefault(os.path.normcase(os.path.abspath(output_path)), []).append(source)
        tasks: List[Tuple[str, str]] = []
        for grouped_sources in output_groups.values():
            if len(grouped_sources) > 1:
                results["failed"] += len(grouped_sources)
                logger.error(
                    "Output-name collision; refusing to overwrite: {}",
                    ", ".join(Path(source).name for source in grouped_sources),
                )
            else:
                source = grouped_sources[0]
                tasks.append((source, self._get_output_path(source)))
        if not tasks:
            return results
        if workers == 1:
            for index, task in enumerate(tasks, 1):
                results["processed" if self.process_single_image(*task) else "failed"] += 1
                if progress_callback and progress_callback(index, len(tasks)) is False: results["stopped"] = True; break
            return results
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(self.process_single_image, *task): task for task in tasks}
            for index, future in enumerate(as_completed(future_map), 1):
                results["processed" if future.result() else "failed"] += 1
                if progress_callback and progress_callback(index, len(tasks)) is False:
                    results["stopped"] = True
                    for pending in future_map:
                        pending.cancel()
                    break
        return results
