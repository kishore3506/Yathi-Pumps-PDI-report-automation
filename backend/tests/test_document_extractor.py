import unittest
import os
import tempfile
import io
import base64

from PIL import Image

from services.document_extractor import DocumentExtractor


class FakeGemini:
    def extract_document_info(self, **kwargs):
        return {
            "company_name": None,
            "customer_name": "Havells",
            "missing_fields": ["company_name"],
            "field_confidence": {"customer_name": "high", "company_name": "low"},
            "uncertain_fields": ["company_name"],
        }


class DocumentExtractorTests(unittest.TestCase):
    def test_prepares_large_images_at_a_bounded_resolution(self):
        source = Image.new("RGB", (2000, 1000), "white")
        raw = io.BytesIO()
        source.save(raw, format="PNG")

        encoded = DocumentExtractor._encode_vision_image(raw.getvalue())
        prepared = Image.open(io.BytesIO(base64.b64decode(encoded)))

        self.assertEqual(prepared.format, "JPEG")
        self.assertEqual(prepared.size, (1280, 640))

    def test_normalizes_detected_customer_as_oem_when_company_field_is_blank(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image:
            image.write(b"image-bytes")
            image_path = image.name
        try:
            result = DocumentExtractor(FakeGemini()).process_file(image_path)
        finally:
            os.unlink(image_path)

        self.assertEqual(result["company_name"], "Havells")
        self.assertTrue(result["is_company_supported"])
        self.assertNotIn("company_name", result["missing_fields"])
        self.assertNotIn("company_name", result["uncertain_fields"])
        self.assertEqual(result["field_confidence"]["company_name"], "high")


if __name__ == "__main__":
    unittest.main()
