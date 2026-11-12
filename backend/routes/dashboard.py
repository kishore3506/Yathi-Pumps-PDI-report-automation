from fastapi import APIRouter
from typing import Dict, Any, List

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def get_dashboard_stats():
    """Retrieve top-level statistics and recent jobs for the dashboard."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM generated_reports")
    total_reports = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM report_jobs WHERE status = 'Completed'")
    completed_jobs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM report_jobs WHERE status = 'Awaiting Review'")
    awaiting_review = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM report_jobs WHERE status IN ('Approved', 'Awaiting Printing') AND printed_reports < total_reports")
    awaiting_printing = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM report_jobs WHERE printed_reports > 0 AND emailed_reports = 0 AND status != 'Completed'")
    awaiting_email = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT j.*, t.template_name
        FROM report_jobs j
        LEFT JOIN pdi_templates t ON j.template_id = t.id
        ORDER BY j.id DESC
        LIMIT 10
    """)
    recent_jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "total_reports_generated": total_reports,
        "completed_jobs": completed_jobs,
        "awaiting_review": awaiting_review,
        "awaiting_printing": awaiting_printing,
        "awaiting_email": awaiting_email,
        "recent_jobs": recent_jobs
    }
