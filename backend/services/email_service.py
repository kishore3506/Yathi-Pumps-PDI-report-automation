import os
import json
import base64
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db

logger = logging.getLogger(__name__)

DEFAULT_N8N_WEBHOOK = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/havells-pdi-email")

class EmailService:
    def __init__(self, webhook_url: str = DEFAULT_N8N_WEBHOOK):
        self.webhook_url = webhook_url

    def send_customer_email(
        self,
        job_id: int,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        report_ids: Optional[List[int]] = None,
        skip: bool = False
    ) -> Dict[str, Any]:
        """
        Triggers secured n8n webhook to deliver approved PDI reports to customer.
        Records job state and audit log in SQLite.
        """
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM report_jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        if not job:
            conn.close()
            raise ValueError(f"Job ID {job_id} not found")

        target_email = customer_email or job["customer_email"]
        target_name = customer_name or job["customer_name"] or "Valued Customer"
        now_str = datetime.now().isoformat()

        if skip:
            cursor.execute("""
                INSERT INTO email_jobs (job_id, customer_email, customer_name, webhook_url, status, response_data, sent_at)
                VALUES (?, ?, ?, ?, 'Skipped', 'Skipped by employee request', ?)
            """, (job_id, target_email or "N/A", target_name, self.webhook_url, now_str))

            cursor.execute("""
                UPDATE report_jobs
                SET status = CASE WHEN printed_reports > 0 THEN 'Completed' ELSE 'Awaiting Printing' END,
                    updated_at = ?
                WHERE id = ?
            """, (now_str, job_id))

            cursor.execute("""
                INSERT INTO audit_logs (job_id, action, performed_by, details_json, created_at)
                VALUES (?, 'SKIP_EMAIL', 'Employee', 'Email step explicitly skipped', ?)
            """, (job_id, now_str))

            conn.commit()
            conn.close()
            return {
                "success": True,
                "status": "Skipped",
                "message": "Email step skipped. Job status updated accordingly."
            }

        if not target_email:
            conn.close()
            return {
                "success": False,
                "status": "Failed",
                "message": "Customer email is required to send reports. Please enter a valid recipient email."
            }

        if report_ids:
            placeholders = ",".join(["?"] * len(report_ids))
            cursor.execute(f"SELECT * FROM generated_reports WHERE job_id = ? AND id IN ({placeholders})", [job_id] + report_ids)
        else:
            cursor.execute("SELECT * FROM generated_reports WHERE job_id = ?", (job_id,))
        
        reports = cursor.fetchall()
        attachments = []
        for rep in reports:
            file_to_send = rep["pdf_path"] if (rep["pdf_path"] and os.path.exists(rep["pdf_path"])) else rep["excel_path"]
            if os.path.exists(file_to_send):
                with open(file_to_send, "rb") as f:
                    b64_content = base64.b64encode(f.read()).decode("utf-8")
                attachments.append({
                    "filename": os.path.basename(file_to_send),
                    "file_type": "application/pdf" if file_to_send.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "content_base64": b64_content,
                    "report_code": rep["report_code"]
                })

        payload = {
            "job_id": job_id,
            "job_code": job["job_code"],
            "company_name": job["company_name"],
            "product_type": job["product_type"],
            "product_number": job["product_number"],
            "lot_size": job["lot_size"],
            "customer_name": target_name,
            "customer_email": target_email,
            "total_attachments": len(attachments),
            "attachments": attachments,
            "timestamp": now_str
        }

        email_status = "Failed"
        resp_data_str = ""
        success = False

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=20)
            resp_data_str = resp.text
            if resp.status_code in [200, 201, 202]:
                email_status = "Sent"
                success = True
            else:
                email_status = "Failed"
                resp_data_str = f"n8n returned status {resp.status_code}: {resp.text}"
        except Exception as e:
            logger.warning(f"Failed to connect to n8n webhook ({self.webhook_url}): {e}")
            email_status = "Failed"
            resp_data_str = f"Connection error: {str(e)}"

        cursor.execute("""
            INSERT INTO email_jobs (job_id, customer_email, customer_name, webhook_url, status, response_data, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_id, target_email, target_name, self.webhook_url, email_status, resp_data_str, now_str))

        if success:
            cursor.execute("UPDATE report_jobs SET emailed_reports = ?, status = 'Completed', updated_at = ? WHERE id = ?", (len(attachments), now_str, job_id))
            cursor.execute("UPDATE generated_reports SET status = 'Emailed', updated_at = ? WHERE job_id = ?", (now_str, job_id))

        cursor.execute("""
            INSERT INTO audit_logs (job_id, action, performed_by, details_json, created_at)
            VALUES (?, 'SEND_EMAIL_N8N', 'Employee', ?, ?)
        """, (job_id, json.dumps({"recipient": target_email, "status": email_status}), now_str))

        conn.commit()
        conn.close()

        return {
            "success": success,
            "status": email_status,
            "customer_email": target_email,
            "attachments_count": len(attachments),
            "response": resp_data_str,
            "webhook_url": self.webhook_url
        }
