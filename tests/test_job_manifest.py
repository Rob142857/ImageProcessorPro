import json
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from job_manifest import ManifestValidationError, load_job_manifest


class JobManifestTests(unittest.TestCase):
    def payload(self, image):
        return {
            'schemaVersion': 'mjw.image-job.v1', 'jobId': 'job-2026-001', 'catalogId': 'MJW-P-2026-001',
            'inputPath': str(image), 'sourceSha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'rights': 'Michael J Wright Estate - All Rights Reserved',
            'profileId': 'mjw-web-v2', 'profileVersion': '2.0.0',
            'sharePoint': {'siteId': 'site', 'driveId': 'drive', 'itemId': 'item', 'eTag': 'etag', 'version': '1.0',
                           'originalFilename': image.name, 'relativePath': 'Originals/' + image.name},
        }

    def test_loads_canonical_credential_free_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'original.jpg'; image.write_bytes(b'image')
            manifest = Path(directory) / 'job.json'; manifest.write_text(json.dumps(self.payload(image)))
            job = load_job_manifest(manifest)
            self.assertEqual(job.output_filename, 'MJW-P-2026-001_web.jpg')
            self.assertRegex(job.idempotency_key, r'^sha256:[0-9a-f]{64}$')

    def test_rejects_credentials_and_noncanonical_catalog_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'original.jpg'; image.write_bytes(b'image')
            payload = self.payload(image); payload['apiToken'] = 'never-here'
            manifest = Path(directory) / 'job.json'; manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)
            payload = self.payload(image); payload['catalogId'] = 'MJW-PTG-2026-001'
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)

    def test_rejects_source_mismatch_zero_id_pdf_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'original.jpg'; image.write_bytes(b'image')
            manifest = Path(directory) / 'job.json'

            payload = self.payload(image); payload['sourceSha256'] = '0' * 64
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)

            payload = self.payload(image); payload['catalogId'] = 'MJW-P-2026-000'
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)

            payload = self.payload(image); payload['sharePoint']['relativePath'] = '../original.jpg'
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)

            pdf = Path(directory) / 'original.pdf'; pdf.write_bytes(b'%PDF-1.7')
            payload = self.payload(pdf)
            manifest.write_text(json.dumps(payload))
            with self.assertRaises(ManifestValidationError): load_job_manifest(manifest)
