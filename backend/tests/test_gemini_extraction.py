import json
import unittest
from unittest.mock import patch

from services.gemini_service import GeminiService


class FakeResponse:
    status_code = 200
    ok = True

    def __init__(self, result):
        self.result = result

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(self.result)}]}}]}


class GeminiExtractionTests(unittest.TestCase):
    @patch("services.gemini_service.requests.post")
    def test_sends_image_to_gemini_and_validates_lot_size(self, post):
        post.return_value = FakeResponse({
            "lot_size": 1201,
            "product_number": "HV-101",
            "missing_fields": [],
            "field_confidence": {"lot_size": "high", "product_number": "low"},
            "uncertain_fields": [],
        })

        result = GeminiService(api_key="test-key", model="gemini-test").extract_document_info(
            image_base64_list=["encoded-image"]
        )

        request = post.call_args.kwargs
        self.assertEqual(request["headers"]["x-goog-api-key"], "test-key")
        self.assertIn("gemini-test:generateContent", post.call_args.args[0])
        self.assertEqual(request["json"]["contents"][0]["parts"][1]["inlineData"]["data"], "encoded-image")
        self.assertEqual(request["json"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(result["lot_size"], 1201)
        self.assertIsNone(result["product_number"])
        self.assertIn("product_number", result["missing_fields"])
        self.assertIn("product_number", result["uncertain_fields"])

    @patch("services.gemini_service.requests.post")
    def test_populates_confidence_when_gemini_omits_it(self, post):
        post.return_value = FakeResponse({
            "company_name": "Havells",
            "product_type": "Surface Pump",
            "model_name": "SP-220",
            "product_number": "HV-SP-220",
            "po_number": "PO-731",
            "lot_size": 101,
            "missing_fields": [],
        })

        result = GeminiService(api_key="test-key").extract_document_info(image_base64_list=["encoded-image"])

        self.assertEqual(result["field_confidence"]["model_name"], "medium")
        self.assertEqual(result["field_confidence"]["po_number"], "medium")
        self.assertEqual(result["field_confidence"]["lot_size"], "medium")

    def test_returns_clear_message_when_api_key_is_missing(self):
        result = GeminiService(api_key="").extract_document_info(image_base64_list=["encoded-image"])

        self.assertIn("GEMINI_API_KEY", result["error"])


if __name__ == "__main__":
    unittest.main()
