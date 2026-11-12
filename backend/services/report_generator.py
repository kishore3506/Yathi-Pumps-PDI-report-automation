import os
import re
import json
import zipfile
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

try:
    from ..database import get_db
    from .excel_filler import ExcelFiller
    from .excel_reader import ExcelReader
except (ImportError, ValueError):
    from database import get_db
    from services.excel_filler import ExcelFiller
    from services.excel_reader import ExcelReader

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)


def report_count_for_lot(lot_size: int) -> int:
    """Return the inspection report count required for a lot size."""
    lot_size = int(lot_size)
    if lot_size < 1:
        raise ValueError("Lot size must be at least 1")
    if lot_size <= 100:
        return 1
    if lot_size <= 1200:
        return 2
    if lot_size <= 2500:
        return 3
    if lot_size <= 4000:
        return 4
    return 5


def allocate_lot_quantity(lot_size: int, report_count: int) -> List[int]:
    """Split a lot evenly; earlier reports receive any remainder units."""
    base, remainder = divmod(int(lot_size), int(report_count))
    return [base + (1 if i < remainder else 0) for i in range(report_count)]

class ReportGenerator:
    def __init__(self):
        self.filler = ExcelFiller()
        self.reader = ExcelReader()

    def generate_batch_reports(
        self,
        job_data: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Generates the rule-based number of editable Excel reports. Each report
        records its allocated quantity, with allocations summing to the lot.
        """
        conn = get_db()
        cursor = conn.cursor()

        company_name = job_data.get("company_name")
        if not company_name:
            raise ValueError("Customer must be read from the input or selected by the user")
        clean_company = re.sub(r'[^a-zA-Z0-9]', '', company_name)
        product_type = job_data.get("product_type")
        product_number = job_data.get("product_number")
        if not product_type or not product_number or not job_data.get("model_name") or not job_data.get("po_number"):
            raise ValueError("Product type, model name, SKU, and PO number are required")
        lot_size = int(job_data["lot_size"])
        report_count = report_count_for_lot(lot_size)
        allocations = allocate_lot_quantity(lot_size, report_count)
        template_id = int(job_data.get("template_id"))

        # Fetch template record
        cursor.execute("SELECT * FROM pdi_templates WHERE id = ?", (template_id,))
        template_row = cursor.fetchone()
        if not template_row:
            conn.close()
            raise ValueError(f"Template ID {template_id} not found")

        template_file_path = template_row["file_path"]
        primary_sheet = template_row["primary_sheet"]

        # Generate unique Job Code for Yathi Pumps
        cust_prefix = clean_company[:3].upper() if clean_company else "OEM"
        job_code = f"JOB-YATHI-{cust_prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().isoformat()

        # Insert report_job
        cursor.execute("""
            INSERT INTO report_jobs (
                job_code, requirement_id, template_id, company_name, product_type,
                product_number, lot_size, customer_name, customer_email,
                status, total_reports, approved_reports, printed_reports, emailed_reports,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Generating', ?, 0, 0, 0, ?, ?)
        """, (
            job_code,
            job_data.get("requirement_id"),
            template_id,
            company_name,
            product_type,
            product_number,
            lot_size,
            job_data.get("customer_name"),
            job_data.get("customer_email"),
            report_count,
            now_str,
            now_str
        ))
        job_id = cursor.lastrowid

        clean_prod_num = product_number.replace(" ", "-").replace("/", "-")
        job_folder = os.path.join(output_dir, job_code)
        os.makedirs(job_folder, exist_ok=True)

        generated_reports_list = []
        serial_numbers = job_data.get("serial_numbers") or []

        for idx in range(1, report_count + 1):
            report_code = f"{clean_company}_PDI_{clean_prod_num}_{idx:03d}"
            filename = f"{report_code}.xlsx"
            file_path = os.path.join(job_folder, filename)

            unit_serial = serial_numbers[idx - 1] if idx - 1 < len(serial_numbers) else None

            report_job_data = dict(job_data)
            report_job_data["lot_size"] = allocations[idx - 1]
            self.filler.populate_template(
                template_file_path=template_file_path,
                output_file_path=file_path,
                template_id=template_id,
                data=report_job_data,
                observation_overrides=job_data.get("observation_overrides"),
                unit_index=idx,
                serial_number=unit_serial
            )

            report_data = self.reader.read_report(file_path, primary_sheet)
            report_data_json = json.dumps(report_data)

            cursor.execute("""
                INSERT INTO generated_reports (
                    job_id, report_code, unit_index, serial_number,
                    excel_path, pdf_path, status, report_data_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, NULL, 'Awaiting Review', ?, ?, ?)
            """, (
                job_id,
                report_code,
                idx,
                unit_serial,
                file_path,
                report_data_json,
                now_str,
                now_str
            ))
            rep_id = cursor.lastrowid
            generated_reports_list.append({
                "id": rep_id,
                "job_id": job_id,
                "report_code": report_code,
                "unit_index": idx,
                "allocated_quantity": allocations[idx - 1],
                "serial_number": unit_serial,
                "excel_path": file_path,
                "pdf_path": None,
                "status": "Awaiting Review",
                "report_data": report_data,
                "created_at": now_str
            })

        cursor.execute("UPDATE report_jobs SET status = 'Awaiting Review' WHERE id = ?", (job_id,))
        
        cursor.execute("""
            INSERT INTO audit_logs (job_id, action, performed_by, details_json, created_at)
            VALUES (?, 'GENERATE_BATCH', 'System', ?, ?)
        """, (job_id, json.dumps({"lot_size": lot_size, "job_code": job_code}), now_str))

        conn.commit()
        conn.close()

        return {
            "job_id": job_id,
            "job_code": job_code,
            "company_name": company_name,
            "product_type": product_type,
            "product_number": product_number,
            "lot_size": lot_size,
            "report_count": report_count,
            "quantity_allocations": allocations,
            "customer_name": job_data.get("customer_name"),
            "customer_email": job_data.get("customer_email"),
            "status": "Awaiting Review",
            "total_reports": report_count,
            "approved_reports": 0,
            "printed_reports": 0,
            "emailed_reports": 0,
            "template_name": template_row["template_name"],
            "created_at": now_str,
            "updated_at": now_str,
            "reports": generated_reports_list
        }

    def create_zip_archive(self, job_id: int) -> str:
        """Create a ZIP file containing all generated reports for a job."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT job_code FROM report_jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        if not job:
            conn.close()
            raise ValueError(f"Job ID {job_id} not found")

        job_code = job["job_code"]
        cursor.execute("SELECT excel_path, pdf_path FROM generated_reports WHERE job_id = ?", (job_id,))
        reports = cursor.fetchall()
        conn.close()

        zip_dir = os.path.dirname(reports[0]["excel_path"]) if reports else "."
        zip_path = os.path.join(zip_dir, f"{job_code}_all_reports.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for rep in reports:
                if rep["excel_path"] and os.path.exists(rep["excel_path"]):
                    zipf.write(rep["excel_path"], os.path.basename(rep["excel_path"]))
                if rep["pdf_path"] and os.path.exists(rep["pdf_path"]):
                    zipf.write(rep["pdf_path"], os.path.basename(rep["pdf_path"]))

        return zip_path

    def convert_to_pdf(self, report_id: int) -> str:
        """
        Converts a report to PDF. Tries LibreOffice headless first;
        if not present, generates a clean PDF using ReportLab.
        """
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM generated_reports WHERE id = ?", (report_id,))
        rep = cursor.fetchone()
        if not rep:
            conn.close()
            raise ValueError(f"Report ID {report_id} not found")

        excel_path = rep["excel_path"]
        pdf_path = os.path.splitext(excel_path)[0] + ".pdf"

        if os.path.exists(pdf_path):
            cursor.execute("UPDATE generated_reports SET pdf_path = ? WHERE id = ?", (pdf_path, report_id))
            conn.commit()
            conn.close()
            return pdf_path

        report_data = json.loads(rep["report_data_json"])
        self._generate_pdf_reportlab(report_data, pdf_path, rep["report_code"])

        cursor.execute("UPDATE generated_reports SET pdf_path = ? WHERE id = ?", (pdf_path, report_id))
        conn.commit()
        conn.close()
        return pdf_path

    def _generate_pdf_reportlab(self, data: Dict[str, Any], output_pdf: str, report_code: str):
        """Generates a high-quality PDF replica of the Havells PDI report."""
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=1,
            textColor=colors.HexColor('#9C0006'),
            spaceAfter=4
        )
        normal_style = ParagraphStyle('NormalSmall', fontName='Helvetica', fontSize=7, leading=8)
        header_lbl = ParagraphStyle('HeaderLbl', fontName='Helvetica-Bold', fontSize=7, leading=8)

        hdr = data.get("header_data", {})

        header_matrix = [
            [
                Paragraph("<b>HAVELLS INDIA LTD</b><br/><font size=6>Pre-dispatch Inspection</font>", header_lbl),
                Paragraph(f"<b>{hdr.get('title', 'Pump - Pre-dispatch Inspection Report')}</b>", title_style),
                Paragraph(f"<b>{hdr.get('doc_no', 'Doc No: HIL/PDI/01')}</b><br/>{hdr.get('inspection_date', '')}", normal_style)
            ],
            [
                Paragraph(f"<b>Supplier:</b> {hdr.get('supplier_name', '')}", normal_style),
                Paragraph(f"<b>Model:</b> {hdr.get('model_name', '')} | <b>SKU:</b> {hdr.get('sku_no', '')}", normal_style),
                Paragraph(f"<b>Lot Qty:</b> {hdr.get('lot_qty', '')} | <b>PO:</b> {hdr.get('po_number', '')}", normal_style)
            ],
            [
                Paragraph(f"<b>Inspected by:</b> {hdr.get('inspected_by', '')}", normal_style),
                Paragraph(f"<b>Approved by:</b> {hdr.get('approved_by', '')}", normal_style),
                Paragraph(f"<b>Judgment:</b> {'PASS / OK' if hdr.get('judgment_ok') else 'REJECT'}", header_lbl)
            ]
        ]
        t_header = Table(header_matrix, colWidths=[180, 420, 200])
        t_header.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2F2F2')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 6))

        table_data = [
            ["S.N.", "Inspection Type", "Parameter", "Specification", "Method", "Frequency", "Observations"]
        ]
        
        checkpoints = data.get("checkpoints", [])
        for cp in checkpoints:
            obs = cp.get("observations", {})
            obs_str = obs.get("G", "")
            if obs.get("H"):
                obs_str += f" | {obs.get('H')}"
            if obs.get("K") and obs.get("K") != obs.get("G"):
                obs_str += f" .. {obs.get('K')}"

            table_data.append([
                Paragraph(str(cp.get("item_sn", "")), normal_style),
                Paragraph(str(cp.get("inspection_type", "")), normal_style),
                Paragraph(str(cp.get("parameter", "")), normal_style),
                Paragraph(str(cp.get("specification", "")), normal_style),
                Paragraph(str(cp.get("method", "")), normal_style),
                Paragraph(str(cp.get("frequency", "")), normal_style),
                Paragraph(obs_str, normal_style)
            ])

        t_body = Table(table_data, colWidths=[25, 110, 155, 230, 90, 90, 100], repeatRows=1)
        t_body.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(t_body)

        doc.build(elements)
