import os
import json
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List, Dict, Any
import openpyxl

try:
    from ..database import get_db
    from ..services.template_matcher import TemplateMatcher
except (ImportError, ValueError):
    from database import get_db
    from services.template_matcher import TemplateMatcher

router = APIRouter(prefix="/api/templates", tags=["Templates"])
matcher = TemplateMatcher()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

@router.get("")
async def list_templates():
    """List all registered PDI Excel templates."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, c.name as company_name, c.code as company_code
        FROM pdi_templates t
        JOIN companies c ON t.company_id = c.id
        ORDER BY t.id DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for r in rows:
        try:
            r["sheet_names"] = json.loads(r["sheet_names"])
        except Exception:
            r["sheet_names"] = [r["primary_sheet"]]
        r["is_active"] = bool(r["is_active"])

    return rows

@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    product_type: str = Form(...),
    product_model: Optional[str] = Form(None),
    primary_sheet: Optional[str] = Form(None)
):
    """Uploads and registers an existing PDI Excel report template."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".xlsx", ".xlsm"]:
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xlsm) are supported as PDI templates.")

    target_path = os.path.join(TEMPLATES_DIR, file.filename)
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        wb = openpyxl.load_workbook(target_path, data_only=False)
        sheet_names = wb.sheetnames
        selected_primary = primary_sheet if (primary_sheet and primary_sheet in sheet_names) else sheet_names[0]
        wb.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to inspect uploaded Excel template: {e}")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE LOWER(name) = LOWER(?)", (company_name.strip(),))
    comp = cursor.fetchone()
    now_str = datetime.now().isoformat()
    if not comp:
        is_havells = "havells" in company_name.lower()
        cursor.execute("INSERT INTO companies (name, code, is_supported, created_at) VALUES (?, ?, ?, ?)",
                       (company_name.strip(), company_name.strip()[:4].upper(), 1 if is_havells else 0, now_str))
        company_id = cursor.lastrowid
    else:
        company_id = comp["id"]

    cursor.execute("""
        INSERT INTO pdi_templates (
            company_id, product_type, product_model, template_name,
            file_path, sheet_names, primary_sheet, is_active, registration_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        company_id,
        product_type.strip(),
        product_model.strip() if product_model else None,
        file.filename,
        target_path,
        json.dumps(sheet_names),
        selected_primary,
        now_str
    ))
    template_id = cursor.lastrowid

    default_mappings = [
        ("supplier_name", "Supplier Code / Name", selected_primary, "C3", 1, "", 0, ""),
        ("supplier_location", "Supplier Location", selected_primary, "F3", 1, "", 0, ""),
        ("sku_no", "SKU No.", selected_primary, "C4", 1, "", 1, ""),
        ("model_name", "Model Name", selected_primary, "D4", 1, "", 1, "prefix:Model Name : "),
        ("po_number", "PO Number", selected_primary, "C5", 1, "", 0, ""),
        ("lot_qty", "Lot Qty", selected_primary, "D5", 1, "", 1, "prefix:Lot Qty : "),
        ("inspected_by", "Inspected by", selected_primary, "D6", 1, "Havells QA", 0, "prefix:Inspected by : "),
        ("approved_by", "Approved by", selected_primary, "D7", 1, "Quality Head", 0, "prefix:Approved by : "),
        ("inspection_date", "Inspection Date", selected_primary, "H2", 1, "", 0, "prefix:Inspection Date : \n"),
        ("lot_dispatch_date", "Lot Dispatch Date", selected_primary, "J2", 1, "", 0, "prefix:Lot Dispatch Date : "),
        ("final_judgment", "Final Judgment", selected_primary, "E5", 1, "OK", 1, "highlight_or_tick")
    ]
    for m in default_mappings:
        cursor.execute("""
            INSERT INTO template_field_mappings (
                template_id, field_key, field_label, target_sheet,
                target_cell, is_header_field, default_value, is_required, validation_rule
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (template_id, m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7]))

    conn.commit()
    conn.close()

    return {
        "template_id": template_id,
        "template_name": file.filename,
        "product_type": product_type,
        "sheet_names": sheet_names,
        "primary_sheet": selected_primary,
        "message": "Template uploaded and registered successfully."
    }

@router.post("/match")
async def match_template_endpoint(data: Dict[str, Any]):
    """Match company and product type to registered templates."""
    company_name = data.get("company_name", "")
    product_type = data.get("product_type", "")
    product_model = data.get("product_model")

    result = matcher.match_template(
        company_name=company_name,
        product_type=product_type,
        product_model=product_model
    )
    return result

@router.get("/{template_id}/mappings")
async def get_template_mappings(template_id: int):
    """Get field mappings for a template."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM template_field_mappings WHERE template_id = ?", (template_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
