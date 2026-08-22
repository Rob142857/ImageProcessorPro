import base64
import json
from io import BytesIO

from PIL import Image

from image_processor import ProcessingConfig
from power_platform import power_platform_integration as module


def image_bytes():
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, "JPEG")
    return buffer.getvalue()


def app(monkeypatch, token="test-token", allow_config=False):
    monkeypatch.setenv("IMAGE_PROCESSOR_API_TOKEN", token)
    monkeypatch.setenv("IMAGE_PROCESSOR_ALLOW_CONFIG_MUTATION", str(allow_config).lower())
    config = ProcessingConfig(use_text_watermark=False, use_tiled_watermark=False)
    return module.PowerPlatformAPI(config).app.test_client()


def test_health_is_public_but_processing_requires_bearer_token(monkeypatch):
    client = app(monkeypatch)
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/process-base64", json={"image": "x"}).status_code == 401


def test_base64_validation_and_processing(monkeypatch):
    client = app(monkeypatch)
    headers = {"Authorization": "Bearer test-token"}
    invalid = client.post("/api/process-base64", json={"image": "not-base64"}, headers=headers)
    assert invalid.status_code == 400
    encoded = base64.b64encode(image_bytes()).decode()
    valid = client.post("/api/process-base64", json={"image": encoded}, headers=headers)
    assert valid.status_code == 200
    assert valid.get_json()["success"] is True

    bad_options = client.post(
        "/api/process-base64",
        json={"image": encoded, "options": {"quality": 1000}},
        headers=headers,
    )
    assert bad_options.status_code == 400
    assert bad_options.get_json()["error"]["code"] == "invalid_options"


def test_config_mutation_is_disabled_by_default(monkeypatch):
    client = app(monkeypatch)
    response = client.post(
        "/api/config",
        json={"jpeg_quality": 1},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "config_mutation_disabled"


def test_generated_http_actions_reference_secure_bearer_parameter(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    module.create_power_automate_templates()

    def http_actions(value):
        if isinstance(value, dict):
            if value.get("type") == "HTTP":
                yield value
            for child in value.values():
                yield from http_actions(child)
        elif isinstance(value, list):
            for child in value:
                yield from http_actions(child)

    templates = list((tmp_path / "power_platform" / "templates").glob("*_flow.json"))
    assert len(templates) == 3
    for path in templates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["secureParameters"]["ImageProcessorApiToken"]["type"] == "SecureString"
        actions = list(http_actions(payload))
        assert actions
        assert all(
            "ImageProcessorApiToken" in action["headers"]["Authorization"]
            for action in actions
        )
