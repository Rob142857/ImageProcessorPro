import json
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli


class CliManifestTests(unittest.TestCase):
    def test_parser_exposes_manifest_mode(self):
        args = cli.create_parser().parse_args(
            ["--job-manifest", "job.json", "--output-dir", "derivatives"]
        )
        self.assertEqual(args.job_manifest, "job.json")
        self.assertEqual(args.output_dir, "derivatives")

    def test_manifest_run_creates_verified_derivative_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source_dir = base / "staged-originals"
            source_dir.mkdir()
            image = source_dir / "original.jpg"
            Image.new("RGB", (320, 200), "navy").save(image)
            payload = {
                "schemaVersion": "mjw.image-job.v1",
                "jobId": "job-2026-001",
                "catalogId": "MJW-P-2026-001",
                "inputPath": str(image),
                "sourceSha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "rights": "Michael J Wright Estate - All Rights Reserved",
                "profileId": "mjw-web-v2",
                "profileVersion": "2.0.0",
                "sharePoint": {
                    "siteId": "site",
                    "driveId": "drive",
                    "itemId": "item",
                    "eTag": "etag",
                    "version": "1",
                    "originalFilename": "original.jpg",
                    "relativePath": "Originals/original.jpg",
                },
            }
            manifest = base / "job.json"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            output_dir = base / "out"

            self.assertEqual(cli.run_job_manifest(str(manifest), None, str(output_dir)), 0)
            output = output_dir / "MJW-P-2026-001_web.jpg"
            sidecar = json.loads(
                output.with_suffix(".jpg.json").read_text(encoding="utf-8")
            )
            self.assertTrue(output.is_file())
            self.assertLessEqual(output.stat().st_size, 2500 * 1024)
            with Image.open(output) as derivative:
                self.assertLessEqual(max(derivative.size), 2400)
                self.assertTrue(derivative.info.get("progressive") or derivative.info.get("progression"))
                self.assertTrue(derivative.info.get("icc_profile"))
            self.assertEqual(sidecar["schemaVersion"], "mjw.image-derivative.v1")
            self.assertEqual(sidecar["provenance"]["catalogId"], "MJW-P-2026-001")
            self.assertEqual(sidecar["profile"]["id"], "mjw-web-v2")
            self.assertRegex(sidecar["watermark"]["textSha256"], r"^[0-9a-f]{64}$")
            self.assertNotIn(str(base), json.dumps(sidecar))

            first_mtime = output.stat().st_mtime_ns
            payload["jobId"] = "job-2026-retry-002"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(cli.run_job_manifest(str(manifest), None, str(output_dir)), 0)
            self.assertEqual(output.stat().st_mtime_ns, first_mtime)

    def test_manifest_mode_rejects_output_inside_source_and_unpaired_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); staged = base / "staged"; staged.mkdir()
            image = staged / "original.jpg"; Image.new("RGB", (20, 20)).save(image)
            payload = {
                "schemaVersion": "mjw.image-job.v1", "jobId": "job-1",
                "catalogId": "MJW-P-2026-001", "inputPath": str(image),
                "sourceSha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "rights": "Estate rights", "profileId": "mjw-web-v2", "profileVersion": "2.0.0",
                "sharePoint": {"siteId": "site", "driveId": "drive", "itemId": "item", "eTag": "etag",
                               "version": "1", "originalFilename": image.name, "relativePath": "Originals/original.jpg"},
            }
            manifest = base / "job.json"; manifest.write_text(json.dumps(payload))
            self.assertEqual(cli.run_job_manifest(str(manifest), None, str(staged / "derivatives")), 2)

            output_dir = base / "derivatives"; output_dir.mkdir()
            (output_dir / "MJW-P-2026-001_web.jpg").write_bytes(b"untracked collision")
            self.assertEqual(cli.run_job_manifest(str(manifest), None, str(output_dir)), 2)


if __name__ == "__main__":
    unittest.main()


class CliFolderWithProfileTests(unittest.TestCase):
    def test_command_line_folders_override_profile_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source_dir = base / "batch"
            out_dir = base / "web"
            source_dir.mkdir()
            Image.new("RGB", (640, 400), "teal").save(source_dir / "art-one.jpg")
            profile = Path(__file__).resolve().parents[1] / "config" / "mjw-web-v2.yaml"
            argv = ["cli.py", "-i", str(source_dir), "-o", str(out_dir), "--config", str(profile), "--quiet"]
            old_argv = sys.argv
            sys.argv = argv
            try:
                self.assertEqual(cli.main(), 0)
            finally:
                sys.argv = old_argv
            self.assertTrue((out_dir / "art-one_web.jpeg").exists())
