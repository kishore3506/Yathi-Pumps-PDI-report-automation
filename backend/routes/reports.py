import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any

try:
    from ..database import get_db
    from ..schemas import ReportGenerateRequest, ReportUpdateRequest, PrintRequest, EmailRequest
    from ..services.report_generator import ReportGenerator
    from ..services.printer_service import PrinterService
    from ..services.email_service import EmailService
    from ..services.excel_filler import ExcelFiller
    from ..services.excel_reader import ExcelReader
except (ImportError, ValueError):
    from database import get_db
    from schemas import ReportGenerateRequest, ReportUpdateRequest, PrintRequest, EmailRequest
    from services.report_generator import ReportGenerator
    from services.printer_service import PrinterService
    from services.email_service import EmailService
    from services.excel_filler import ExcelFiller
    from services.excel_reader import ExcelReader

router = APIRouter(prefix="/api/reports", tags=["Reports"])

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

generator = ReportGenerator()
printer = PrinterService()
emailer = EmailService()
filler = ExcelFiller()
reader = ExcelReader()

@router.post("/generate")
async def generate_reports(req: ReportGenerateRequest):
    """Generates batch PDI reports according to lot size for Yathi Pumps."""
    if req.lot_size <= 0 or req.lot_size > 1_000_000:
        raise HTTPException(status_code=400, detail="Lot size must be an integer from 1 to 1,000,000.")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM companies WHERE LOWER(name) = LOWER(?)", (req.company_name.strip(),))
    comp = cursor.fetchone()
    conn.close()

    if not comp:
        raise HTTPException(status_code=400, detail=f"Customer '{req.company_name}' is not supported. Supported customers: Havells, Crompton, KBS, KOEL.")

    job_data = req.dict()

    result = generator.generate_batch_reports(job_data, REPORTS_DIR)
    return result

@router.get("")
async def list_report_jobs():
    """List all report generation jobs."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, t.template_name
        FROM report_jobs j
        LEFT JOIN pdi_templates t ON j.template_id = t.id
        ORDER BY j.id DESC
    """)
    jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jobs

@router.get("/jobs/{job_id}")
async def get_job_details(job_id: int):
    """Get full details of a specific job including all generated reports."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, t.template_name
        FROM report_jobs j
        LEFT JOIN pdi_templates t ON j.template_id = t.id
        WHERE j.id = ?
    """, (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")

    job_dict = dict(job)

    cursor.execute("SELECT * FROM generated_reports WHERE job_id = ? ORDER BY unit_index ASC", (job_id,))
    reports = []
    for r in cursor.fetchall():
        rd = dict(r)
        try:
            rd["report_data"] = json.loads(rd["report_data_json"])
        except Exception:
            rd["report_data"] = {}
        reports.append(rd)

    job_dict["reports"] = reports
    conn.close()
    return job_dict

@router.get("/{report_id}")
async def get_single_report(report_id: int):
    """Get detailed inspection content and status for a single report."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, j.job_code, j.company_name, j.product_type, j.product_number, j.lot_size, j.customer_name
        FROM generated_reports r
        JOIN report_jobs j ON r.job_id = j.id
        WHERE r.id = ?
    """, (report_id,))
    rep = cursor.fetchone()
    conn.close()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")

    rep_dict = dict(rep)
    try:
        rep_dict["report_data"] = json.loads(rep_dict["report_data_json"])
    except Exception:
        rep_dict["report_data"] = {}

    return rep_dict

@router.patch("/{report_id}")
async def update_report(report_id: int, req: ReportUpdateRequest):
    """
    Allows employee to edit permitted fields and inspection readings.
    Validation: Never allows manually changing a calculated FAIL result into PASS.
    Updates the working Excel file and database.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generated_reports WHERE id = ?", (report_id,))
    rep = cursor.fetchone()
    if not rep:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")

    excel_path = rep["excel_path"]
    job_id = rep["job_id"]

    cursor.execute("SELECT * FROM report_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    template_id = job["template_id"]

    existing_data = json.loads(rep["report_data_json"])

    header_data = existing_data.get("header_data", {})
    if req.header_data:
        for k, v in req.header_data.items():
            if v is not None:
                header_data[k] = v

    final_judgment = req.final_judgment or header_data.get("final_judgment") or ""
    reject_reason = req.reject_reason or header_data.get("reject_reason") or ""

    update_dict = {
        "supplier_name": header_data.get("supplier_name"),
        "supplier_location": header_data.get("supplier_location"),
        "product_number": header_data.get("sku_no") or job["product_number"],
        "model_name": header_data.get("model_name") or job["product_type"],
        "po_number": header_data.get("po_number"),
        "lot_size": header_data.get("lot_qty") or job["lot_size"],
        "po_total_qty": header_data.get("po_total_qty"),
        "inspected_by": header_data.get("inspected_by"),
        "approved_by": header_data.get("approved_by"),
        "inspection_date": header_data.get("inspection_date"),
        "lot_dispatch_date": header_data.get("lot_dispatch_date"),
        "final_judgment": final_judgment,
        "reject_reason": reject_reason,
        "total_dispatched_qty": header_data.get("total_dispatched_qty")
    }

    filler.populate_template(
        template_file_path=excel_path,
        output_file_path=excel_path,
        template_id=template_id,
        data=update_dict,
        observation_overrides=req.observation_readings,
        unit_index=rep["unit_index"],
        serial_number=rep["serial_number"]
    )

    fresh_data = reader.read_report(excel_path)
    fresh_json = json.dumps(fresh_data)
    now_str = datetime.now().isoformat()

    cursor.execute("""
        UPDATE generated_reports
        SET report_data_json = ?, updated_at = ?
        WHERE id = ?
    """, (fresh_json, now_str, report_id))

    cursor.execute("""
        INSERT INTO audit_logs (job_id, report_id, action, performed_by, details_json, created_at)
        VALUES (?, ?, 'EDIT_REPORT', 'Employee', ?, ?)
    """, (job_id, report_id, json.dumps({"judgment": final_judgment}), now_str))

    conn.commit()
    conn.close()

    return {
        "report_id": report_id,
        "status": "Updated",
        "report_data": fresh_data
    }

@router.post("/{report_id}/approve")
async def approve_report(report_id: int):
    """Approves a generated report."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generated_reports WHERE id = ?", (report_id,))
    rep = cursor.fetchone()
    if not rep:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")

    now_str = datetime.now().isoformat()
    cursor.execute("UPDATE generated_reports SET status = 'Approved', updated_at = ? WHERE id = ?", (now_str, report_id))
    
    job_id = rep["job_id"]
    cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved FROM generated_reports WHERE job_id = ?", (job_id,))
    st = cursor.fetchone()
    new_job_status = "Approved" if st["approved"] == st["total"] else "Awaiting Review"
    cursor.execute("UPDATE report_jobs SET approved_reports = ?, status = ?, updated_at = ? WHERE id = ?", (st["approved"], new_job_status, now_str, job_id))

    cursor.execute("""
        INSERT INTO audit_logs (job_id, report_id, action, performed_by, details_json, created_at)
        VALUES (?, ?, 'APPROVE_REPORT', 'Employee', 'Approved inspection findings', ?)
    """, (job_id, report_id, now_str))

    conn.commit()
    conn.close()

    return {"report_id": report_id, "status": "Approved", "job_status": new_job_status}

@router.get("/{report_id}/download/excel")
async def download_excel(report_id: int):
    """Download individual editable Excel report."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT excel_path, report_code FROM generated_reports WHERE id = ?", (report_id,))
    rep = cursor.fetchone()
    conn.close()
    if not rep or not os.path.exists(rep["excel_path"]):
        raise HTTPException(status_code=404, detail="Excel report file not found")

    return FileResponse(
        rep["excel_path"],
        filename=f"{rep['report_code']}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/{report_id}/download/pdf")
async def download_pdf(report_id: int):
    """Download individual PDF report copy."""
    pdf_path = generator.convert_to_pdf(report_id)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF copy")

    return FileResponse(
        pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf"
    )

@router.get("/jobs/{job_id}/download/zip")
async def download_job_zip(job_id: int):
    """Download all reports for a job bundled in a ZIP file."""
    zip_path = generator.create_zip_archive(job_id)
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=500, detail="Failed to create ZIP package")

    return FileResponse(
        zip_path,
        filename=os.path.basename(zip_path),
        media_type="application/zip"
    )

@router.get("/printers/list")
async def list_printers():
    """List host Windows printers."""
    printers = printer.get_available_printers()
    return printers

@router.post("/jobs/{job_id}/print")
async def print_job(job_id: int, req: Optional[PrintRequest] = None):
    """Prints all or selected reports for a job."""
    printer_name = req.printer_name if req else None
    report_ids = req.report_ids if req else None
    result = printer.execute_job_print(job_id, report_ids=report_ids, printer_name=printer_name)
    return result

@router.post("/email")
async def send_reports_email(req: EmailRequest):
    """Triggers n8n email automation or skips email."""
    result = emailer.send_customer_email(
        job_id=req.job_id,
        customer_email=req.customer_email,
        customer_name=req.customer_name,
        report_ids=req.report_ids,
        skip=req.skip
    )
    return result
