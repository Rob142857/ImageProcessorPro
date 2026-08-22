import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from image_processor import ImageProcessor, ProcessingConfig


def config(tmp_path, **changes):
    values = dict(input_folder=str(tmp_path), output_folder=str(tmp_path), create_subfolder=False, use_text_watermark=False, output_format="JPEG")
    values.update(changes)
    return ProcessingConfig(**values)


def test_public_derivative_orients_strips_exif_and_writes_fixity(tmp_path):
    source = tmp_path / "source.jpg"; output = tmp_path / "out.jpg"
    image = Image.new("RGB", (20, 40), "red")
    exif = Image.Exif(); exif[274] = 6; exif[315] = "Private curator metadata"
    image.save(source, exif=exif)
    assert ImageProcessor(config(tmp_path)).process_single_image(str(source), str(output))
    with Image.open(output) as result:
        assert result.size == (40, 20)
        assert not result.getexif()
        assert result.info.get("icc_profile")
    manifest = json.loads((tmp_path / "out.jpg.json").read_text())
    assert manifest["input"]["sha256"] and manifest["output"]["sha256"]
    assert manifest["metadataPolicy"] == "public"
    assert str(tmp_path) not in json.dumps(manifest)


def test_atomic_manifest_makes_identical_rerun_idempotent(tmp_path):
    source = tmp_path / "a.png"; output = tmp_path / "a_web.jpg"; Image.new("RGB", (32, 32), "blue").save(source)
    processor = ImageProcessor(config(tmp_path))
    assert processor.process_single_image(str(source), str(output))
    first = output.stat().st_mtime_ns
    assert processor.process_single_image(str(source), str(output))
    assert output.stat().st_mtime_ns == first


def test_config_validation_yaml_and_watermark_guards(tmp_path):
    with pytest.raises(ValueError): ProcessingConfig(text_spacing_ratio=-1).validate()
    with pytest.raises(ValueError): ProcessingConfig(max_pixels=0).validate()
    path = tmp_path / "settings.yaml"; ProcessingConfig().save_to_file(path)
    assert "python/tuple" not in path.read_text()
    assert ProcessingConfig.load_from_file(path).text_watermark_color == (128, 128, 128)

    config_dir = Path(__file__).parents[1] / "config"
    for preset in config_dir.glob("*.yaml"):
        ProcessingConfig.load_from_file(str(preset))


def test_watermark_does_not_double_copyright(tmp_path):
    processor = ImageProcessor(config(tmp_path, use_text_watermark=True, watermark_text="© Estate", text_spacing_ratio=0.1))
    result = processor.apply_text_watermark(Image.new("RGB", (100, 100), "white"))
    assert result.mode == "RGBA" and result.size == (100, 100)
    assert result.convert("RGB").tobytes() != Image.new("RGB", (100, 100), "white").tobytes()


def test_impossible_size_target_fails_without_partial_output(tmp_path):
    source = tmp_path / "noise.png"; output = tmp_path / "noise.jpg"
    Image.effect_noise((512, 512), 100).convert("RGB").save(source)
    processor = ImageProcessor(config(tmp_path, target_max_size_kb=1))
    assert not processor.process_single_image(str(source), str(output))
    assert not output.exists()


def test_batch_refuses_same_stem_output_collision(tmp_path):
    Image.new("RGB", (20, 20), "red").save(tmp_path / "same.jpg")
    Image.new("RGB", (20, 20), "blue").save(tmp_path / "same.png")
    processor = ImageProcessor(config(tmp_path, input_folder=str(tmp_path)))
    result = processor.process_folder()
    assert result == {"processed": 0, "failed": 2, "total": 2}
