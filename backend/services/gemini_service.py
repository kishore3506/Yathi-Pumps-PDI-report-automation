import json
import logging
import os
import re
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
def _configured_setting(name: str, default: str) -> str:
    value = os.getenv(name)
    if value:
        return value.strip()
    service_dir = os.path.dirname(__file__)
    for env_path in (
        os.path.abspath(os.path.join(service_dir, "..", ".env")),
        os.path.abspath(os.path.join(service_dir, "..", "..", ".env")),
    ):
        try:
            with open(env_path, encoding="utf-8") as env_file:
                for line in env_file:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:].strip()
                    key, separator, configured_value = line.partition("=")
                    if separator and key.strip() == name:
                        return configured_value.strip().strip('"').strip("'") or default
        except OSError:
            continue
    return default


GEMINI_MODEL = _configured_setting("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TIMEOUT_SECONDS = int(_configured_setting("GEMINI_TIMEOUT_SECONDS", "60"))


def _configured_api_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    key = key.strip() if key else _configured_setting("GEMINI_API_KEY", "") or _configured_setting("GOOGLE_API_KEY", "")
    return key if key and not key.lower().startswith("your_") else None

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": ["string", "null"]},
        "product_type": {"type": ["string", "null"]},
        "product_number": {"type": ["string", "null"]},
        "model_name": {"type": ["string", "null"]},
        "lot_size": {"type": ["integer", "null"]},
        "customer_name": {"type": ["string", "null"]},
        "customer_email": {"type": ["string", "null"]},
        "supplier_name": {"type": ["string", "null"]},
        "supplier_location": {"type": ["string", "null"]},
        "po_number": {"type": ["string", "null"]},
        "po_total_qty": {"type": ["integer", "null"]},
        "serial_numbers": {"type": ["array", "null"], "items": {"type": "string"}},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "uncertain_fields": {"type": "array", "items": {"type": "string"}},
        "field_confidence": {
            "type": "object",
            "properties": {
                field: {"type": "string", "enum": ["high", "medium", "low"]}
                for field in (
                    "company_name", "product_type", "product_number", "model_name", "lot_size",
                    "customer_name", "customer_email", "supplier_name", "supplier_location",
                    "po_number", "po_total_qty",
                )
            },
            "required": [
                "company_name", "product_type", "product_number", "model_name", "lot_size",
                "customer_name", "customer_email", "supplier_name", "supplier_location",
                "po_number", "po_total_qty",
            ],
        },
    },
    "required": [
        "company_name", "product_type", "product_number", "model_name", "lot_size", "customer_name",
        "customer_email", "supplier_name", "supplier_location", "po_number", "po_total_qty",
        "serial_numbers", "missing_fields", "uncertain_fields", "field_confidence",
    ],
}

SYSTEM_PROMPT = """You are a strict visual and document data extraction system for industrial PDI reports.
Extract values only when they are explicitly visible in the provided image or document text. Never guess, invent, or use template/example values.
Read the whole image, including order headers and tables. Preserve exact identifiers, punctuation, and leading zeros.
Use company_name for the recognized OEM (Havells, Crompton, KBS, or KOEL). Extract model_name, product_number (SKU), po_number, and lot_size from their corresponding labeled fields.
lot_size must come from the order's lot/order quantity field, never from a sampling plan, PO total, or serial-number count.
For each field, return high confidence only when clearly legible, medium when readable with some ambiguity, and low when unreadable or absent. For low-confidence or absent fields return null and list them in missing_fields and uncertain_fields. Return only the requested JSON object."""


def _empty_result(error: str) -> Dict[str, Any]:
    return {
        "company_name": None,
        "product_type": None,
        "product_number": None,
        "model_name": None,
        "lot_size": None,
        "customer_name": None,
        "customer_email": None,
        "supplier_name": None,
        "supplier_location": None,
        "po_number": None,
        "po_total_qty": None,
        "serial_numbers": None,
        "missing_fields": [
            "company_name", "product_type", "product_number", "model_name", "lot_size", "po_number",
        ],
        "field_confidence": {},
        "uncertain_fields": [],
        "error": error,
    }


class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL):
        self.api_key = api_key if api_key is not None else _configured_api_key()
        self.model = model
        self.timeout = GEMINI_TIMEOUT_SECONDS

    def check_health(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "status": "not_configured",
                "provider": "Google Gemini API",
                "active_model": self.model,
                "api_key_configured": False,
            }
        try:
            response = requests.get(
                f"{GEMINI_API_BASE}/{self.model}",
                headers={"x-goog-api-key": self.api_key},
                timeout=8,
            )
            if response.ok:
                return {
                    "status": "connected",
                    "provider": "Google Gemini API",
                    "active_model": self.model,
                    "api_key_configured": True,
                }
            detail = "Model access check failed"
            try:
                detail = response.json().get("error", {}).get("message", detail)
            except (ValueError, AttributeError):
                pass
            return {
                "status": "error",
                "provider": "Google Gemini API",
                "active_model": self.model,
                "api_key_configured": True,
                "message": f"Gemini API returned HTTP {response.status_code}: {detail[:240]}",
            }
        except requests.RequestException as exc:
            return {
                "status": "unreachable",
                "provider": "Google Gemini API",
                "active_model": self.model,
                "api_key_configured": True,
                "message": str(exc),
            }

    def extract_document_info(
        self,
        text_content: Optional[str] = None,
        image_base64_list: Optional[List[str]] = None,
        extra_hints: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return _empty_result("Gemini API key is not configured. Set GEMINI_API_KEY and restart the app.")

        user_prompt = (
            f"{SYSTEM_PROMPT}\n\nDocument text:\n{text_content or 'No text layer; inspect the attached image.'}\n\n"
            f"Additional context (not evidence; never use it to fill absent values): {extra_hints or 'None'}"
        )
        parts: List[Dict[str, Any]] = [{"text": user_prompt}]
        for image_b64 in image_base64_list or []:
            parts.append({"inlineData": {"mimeType": "image/jpeg", "data": image_b64}})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 512,
                "thinkingConfig": {"thinkingLevel": "low"},
                "responseMimeType": "application/json",
                "responseJsonSchema": EXTRACTION_SCHEMA,
            },
        }

        try:
            # Prefer the newest fast multimodal model, but move to supported
            # Flash versions if Google reports temporary capacity/rate limits.
            model_candidates = list(dict.fromkeys([self.model, "gemini-3.8-flash", "gemini-3.7-flash"]))
            response = None
            last_error = None
            for candidate in model_candidates:
                current_payload = dict(payload)
                current_payload["generationConfig"] = dict(payload["generationConfig"])
                try:
                    response = requests.post(
                        f"{GEMINI_API_BASE}/{candidate}:generateContent",
                        headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                        json=current_payload,
                        timeout=self.timeout,
                    )
                except requests.Timeout as exc:
                    last_error = f"Gemini model {candidate} timed out after {self.timeout} seconds"
                    if candidate != model_candidates[-1]:
                        logger.warning("Gemini model %s timed out; trying fallback", candidate)
                        continue
                    raise RuntimeError(last_error) from exc
                if response.ok:
                    self.last_model = candidate
                    break
                try:
                    detail = response.json().get("error", {}).get("message", response.text)
                except (ValueError, AttributeError):
                    detail = response.text
                last_error = f"Gemini API returned HTTP {response.status_code}: {str(detail)[:500]}"
                if response.status_code not in (429, 500, 502, 503, 504):
                    raise RuntimeError(last_error)
                logger.warning("Gemini model %s temporarily unavailable (HTTP %s); trying fallback", candidate, response.status_code)
            if response is None or not response.ok:
                raise RuntimeError(last_error or "Gemini extraction failed for all supported Flash models")

            body = response.json()
            candidates = body.get("candidates") or []
            content = candidates[0].get("content", {}) if candidates else {}
            raw_text = "".join(part.get("text", "") for part in content.get("parts", []))
            if not raw_text:
                raise RuntimeError("Gemini returned no text for the extraction result")
            extracted = json.loads(raw_text)

            required_keys = [
                "company_name", "product_type", "product_number", "model_name", "lot_size",
                "customer_name", "customer_email", "supplier_name", "supplier_location",
                "po_number", "po_total_qty",
            ]
            missing = extracted.get("missing_fields", [])
            if not isinstance(missing, list):
                missing = []
            for field in required_keys:
                value = extracted.get(field)
                if value is None or value == "" or value == "null":
                    extracted[field] = None
                    if field not in missing:
                        missing.append(field)

            if not isinstance(extracted.get("field_confidence"), dict):
                extracted["field_confidence"] = {}
            if not isinstance(extracted.get("uncertain_fields"), list):
                extracted["uncertain_fields"] = []
            for field in required_keys:
                extracted["field_confidence"].setdefault(field, "low" if extracted.get(field) is None else "medium")
            for field, confidence in extracted["field_confidence"].items():
                if str(confidence).lower() == "low":
                    extracted[field] = None
                    if field not in missing:
                        missing.append(field)
                    if field not in extracted["uncertain_fields"]:
                        extracted["uncertain_fields"].append(field)

            lot_size = extracted.get("lot_size")
            if isinstance(lot_size, str) and re.fullmatch(r"\d[\d,]*", lot_size.strip()):
                lot_size = int(lot_size.replace(",", ""))
                extracted["lot_size"] = lot_size
            if isinstance(lot_size, bool) or (lot_size is not None and (not isinstance(lot_size, int) or lot_size < 1)):
                extracted["lot_size"] = None
                if "lot_size" not in missing:
                    missing.append("lot_size")
                if "lot_size" not in extracted["uncertain_fields"]:
                    extracted["uncertain_fields"].append("lot_size")
            extracted["missing_fields"] = missing
            extracted["model_used"] = getattr(self, "last_model", self.model)
            return extracted
        except Exception as exc:
            logger.exception("Gemini extraction failed")
            return _empty_result(str(exc))
