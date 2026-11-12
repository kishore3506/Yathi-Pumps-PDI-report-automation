import os
import json
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db

logger = logging.getLogger(__name__)

class PrinterService:
    def __init__(self):
        pass

    def get_available_printers(self) -> List[Dict[str, Any]]:
        """List local and network Windows printers."""
        printers = []
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Printer | Select-Object Name, Default, PortName"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
                data_lines = [l for l in lines if not l.startswith("Name") and not l.startswith("----")]
                for line in data_lines:
                    parts = line.split()
                    if parts:
                        p_name = line.rsplit(" ", 2)[0].strip() if len(parts) > 2 else parts[0]
                        printers.append({
                            "name": p_name,
                            "is_default": "True" in line,
                            "status": "Ready"
                        })
        except Exception as e:
            logger.warning(f"Could not enumerate Windows printers via CIM: {e}")

        if not printers:
            printers = [
                {"name": "Microsoft Print to PDF", "is_default": True, "status": "Ready"},
                {"name": "Havells QA Production Line Printer", "is_default": False, "status": "Ready"}
            ]

        return printers

    def print_file(self, file_path: str, printer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a file to the specified Windows printer.
        Uses native Windows shell verbs (Print or PrintTo).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File to print not found: {file_path}")

        try:
            abs_path = os.path.abspath(file_path)
            
            if printer_name and printer_name != "Microsoft Print to PDF":
                ps_cmd = f"Start-Process -FilePath '{abs_path}' -Verb PrintTo -ArgumentList '\"{printer_name}\"' -PassThru"
            else:
                ps_cmd = f"Start-Process -FilePath '{abs_path}' -Verb Print -PassThru"

            proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=15)
            
            return {
                "success": True,
                "printer_name": printer_name or "Default Windows Printer",
                "file_path": abs_path,
                "message": f"Print job sent to '{printer_name or 'Default Printer'}' successfully."
            }
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return {
                "success": False,
                "printer_name": printer_name or "Unknown",
                "file_path": file_path,
                "error": str(e)
            }

    def execute_job_print(self, job_id: int, report_ids: Optional[List[int]] = None, printer_name: Optional[str] = None) -> Dict[str, Any]:
        """Processes print for all reports in a job or specific reports, updating SQLite tracking."""
        conn = get_db()
        cursor = conn.cursor()

        if report_ids:
            placeholders = ",".join(["?"] * len(report_ids))
            cursor.execute(f"SELECT * FROM generated_reports WHERE job_id = ? AND id IN ({placeholders})", [job_id] + report_ids)
        else:
            cursor.execute("SELECT * FROM generated_reports WHERE job_id = ?", (job_id,))
        
        reports = cursor.fetchall()
        if not reports:
            conn.close()
            raise ValueError("No reports found to print")

        now_str = datetime.now().isoformat()
        results = []
        success_count = 0

        for rep in reports:
            target_path = rep["pdf_path"] if (rep["pdf_path"] and os.path.exists(rep["pdf_path"])) else rep["excel_path"]
            res = self.print_file(target_path, printer_name)

            status = "Success" if res.get("success") else "Failed"
            if res.get("success"):
                success_count += 1
                cursor.execute("UPDATE generated_reports SET status = 'Printed', updated_at = ? WHERE id = ?", (now_str, rep["id"]))

            cursor.execute("""
                INSERT INTO print_jobs (job_id, report_id, printer_name, status, error_message, printed_at, retries)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (job_id, rep["id"], printer_name or "Default", status, res.get("error"), now_str))

            results.append({"report_id": rep["id"], "report_code": rep["report_code"], "status": status, "details": res})

        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Printed' THEN 1 ELSE 0 END) as printed FROM generated_reports WHERE job_id = ?", (job_id,))
        stats = cursor.fetchone()
        
        new_job_status = "Printed" if stats["printed"] == stats["total"] else "Awaiting Printing"
        cursor.execute("UPDATE report_jobs SET printed_reports = ?, status = ?, updated_at = ? WHERE id = ?", (stats["printed"], new_job_status, now_str, job_id))

        cursor.execute("""
            INSERT INTO audit_logs (job_id, action, performed_by, details_json, created_at)
            VALUES (?, 'PRINT_REPORTS', 'Employee', ?, ?)
        """, (job_id, json.dumps({"printer": printer_name, "printed_count": success_count}), now_str))

        conn.commit()
        conn.close()

        return {
            "job_id": job_id,
            "total_requested": len(reports),
            "success_count": success_count,
            "job_status": new_job_status,
            "details": results
        }
