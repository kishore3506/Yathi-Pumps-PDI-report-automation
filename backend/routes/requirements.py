import os
import shutil
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

try:
    from ..database import get_db
    from ..services.document_extractor import DocumentExtractor
except (ImportError, ValueError):
    from database import get_db
    from services.document_extractor import DocumentExtractor

router = APIRouter(prefix="/api/requirements", tags=["Requirements"])
extractor = DocumentExtractor()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_requirement(
    file: UploadFile = File(...)
):
    """Uploads a requirement document (JPG, PNG, PDF, XLSX)."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}. Permitted: JPG, PNG, PDF, XLSX.")

    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    now_str = datetime.now().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO uploaded_requirements (filename, original_name, file_type, file_path, uploaded_at, status)
        VALUES (?, ?, ?, ?, ?, 'Uploaded')
    """, (unique_filename, file.filename, ext, saved_path, now_str))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "requirement_id": req_id,
        "filename": unique_filename,
        "original_name": file.filename,
        "file_type": ext,
        "file_path": saved_path,
        "uploaded_at": now_str,
        "status": "Uploaded"
    }

@router.post("/extract")
async def extract_requirement_details(
    requirement_id: int = Form(...),
    company_name: Optional[str] = Form(None),
    product_type: Optional[str] = Form(None),
    product_number: Optional[str] = Form(None),
    lot_size: Optional[int] = Form(None),
    customer_name: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None)
):
    """
    Extracts details from uploaded requirement document via Gemini API.
    Combines with user input hints and strictly reports missing fields.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM uploaded_requirements WHERE id = ?", (requirement_id,))
    req = cursor.fetchone()
    conn.close()
    if not req or not os.path.exists(req["file_path"]):
        raise HTTPException(status_code=404, detail="Uploaded requirement was not found on the server")
    file_path = req["file_path"]

    hints_list = []
    if company_name: hints_list.append(f"Company: {company_name}")
    if product_type: hints_list.append(f"Product Type: {product_type}")
    if product_number: hints_list.append(f"Product Number: {product_number}")
    if lot_size: hints_list.append(f"Lot Size: {lot_size}")
    if customer_name: hints_list.append(f"Customer Name: {customer_name}")
    if customer_email: hints_list.append(f"Customer Email: {customer_email}")
    extra_hints = "; ".join(hints_list)

    extracted = extractor.process_file(file_path, extra_hints=extra_hints)
    if extracted.get("error"):
        raise HTTPException(status_code=502, detail=f"Gemini could not analyze this document: {extracted['error']}")

    if company_name: extracted["company_name"] = company_name
    if product_type: extracted["product_type"] = product_type
    if product_number: extracted["product_number"] = product_number
    if lot_size: extracted["lot_size"] = int(lot_size)
    if customer_name: extracted["customer_name"] = customer_name
    if customer_email: extracted["customer_email"] = customer_email

    extracted["is_company_supported"] = bool(extracted.get("company_name"))

    now_str = datetime.now().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO extracted_product_details (
            requirement_id, company_name, product_type, product_number,
            lot_size, customer_name, customer_email, supplier_name, supplier_location,
            po_number, po_total_qty, raw_extracted_json, missing_fields, confirmed_by_user, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        requirement_id,
        extracted.get("company_name"),
        extracted.get("product_type"),
        extracted.get("product_number"),
        extracted.get("lot_size"),
        extracted.get("customer_name"),
        extracted.get("customer_email"),
        extracted.get("supplier_name"),
        extracted.get("supplier_location"),
        extracted.get("po_number"),
        extracted.get("po_total_qty"),
        str(extracted),
        str(extracted.get("missing_fields", [])),
        now_str
    ))
    conn.commit()
    conn.close()

    return extracted
