import os
import io
import base64
import logging
from typing import Dict, Any, Optional, List
import openpyxl
from pypdf import PdfReader
from PIL import Image, ImageOps

try:
    from .gemini_service import GeminiService
    from .template_matcher import SUPPORTED_CUSTOMERS
except (ImportError, ValueError):
    from services.gemini_service import GeminiService
    from services.template_matcher import SUPPORTED_CUSTOMERS

logger = logging.getLogger(__name__)

class DocumentExtractor:
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.ai = gemini_service or GeminiService()

    @staticmethod
    def _encode_vision_image(image_bytes: bytes) -> str:
        """Normalize uploads to a legible, bounded-size JPEG for faster local inference."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=92, optimize=True)
                image_bytes = output.getvalue()
        except Exception:
            # Preserve an original image format if it cannot be decoded here.
            pass
        return base64.b64encode(image_bytes).decode("utf-8")

    def process_file(self, file_path: str, extra_hints: Optional[str] = None) -> Dict[str, Any]:
        """Process an uploaded requirement document (image, PDF, Excel) and extract fields via Gemini."""
        ext = os.path.splitext(file_path)[1].lower()
        extracted_text = ""
        base64_images: List[str] = []

        if ext in [".jpg", ".jpeg", ".png"]:
            with open(file_path, "rb") as img_file:
                base64_images.append(self._encode_vision_image(img_file.read()))
            extracted_text = f"[Image Document: {os.path.basename(file_path)}]"

        elif ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                pdf_texts = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        pdf_texts.append(f"--- Page {idx+1} ---\n{t}")
                extracted_text = "\n".join(pdf_texts)
                if not extracted_text.strip():
                    for idx, page in enumerate(reader.pages[:3]):
                        for img in page.images:
                            b64_str = self._encode_vision_image(img.data)
                            base64_images.append(b64_str)
                            break
            except Exception as e:
                logger.error(f"Error reading PDF: {e}")
                extracted_text = f"[Error reading PDF text: {e}]"

        elif ext in [".xlsx", ".xls"]:
            try:
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheet_summaries = []
                for sname in wb.sheetnames:
                    ws = wb[sname]
                    rows_text = []
                    for r in range(1, min(ws.max_row + 1, 60)):
                        vals = [str(ws.cell(r, c).value).strip() for c in range(1, min(ws.max_column + 1, 15)) if ws.cell(r, c).value is not None]
                        if vals:
                            rows_text.append(" | ".join(vals))
                    if rows_text:
                        sheet_summaries.append(f"=== Sheet: {sname} ===\n" + "\n".join(rows_text))
                extracted_text = "\n\n".join(sheet_summaries)
            except Exception as e:
                logger.error(f"Error reading Excel requirement: {e}")
                extracted_text = f"[Error reading Excel text: {e}]"
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Send to Gemini API
        ai_result = self.ai.extract_document_info(
            text_content=extracted_text,
            image_base64_list=base64_images if base64_images else None,
            extra_hints=extra_hints
        )

        # Validate customer OEM support for Yathi Pumps
        # Gemini may identify the buyer as customer_name while leaving the
        # duplicate company_name field empty. Normalize either label to the OEM.
        raw_company = ai_result.get("company_name") or ai_result.get("customer_name") or ""
        normalized_customer = None
        raw_lower = raw_company.lower()

        for key, canonical in SUPPORTED_CUSTOMERS.items():
            if key in raw_lower:
                normalized_customer = canonical
                break

        if normalized_customer:
            ai_result["company_name"] = normalized_customer
            ai_result["is_company_supported"] = True
            if "company_name" in (ai_result.get("missing_fields") or []):
                ai_result["missing_fields"].remove("company_name")
            confidence = ai_result.setdefault("field_confidence", {})
            if not confidence.get("company_name") or confidence.get("company_name") == "low":
                confidence["company_name"] = confidence.get("customer_name", "medium")
            ai_result["uncertain_fields"] = [
                field for field in ai_result.get("uncertain_fields", []) if field != "company_name"
            ]
        else:
            ai_result["company_name"] = raw_company or None
            ai_result["is_company_supported"] = False

        return ai_result
