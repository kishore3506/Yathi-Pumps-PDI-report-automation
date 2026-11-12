import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "pdi_system.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. companies (Customers / OEM Brands)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT NOT NULL,
        is_supported INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. products
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        product_type TEXT NOT NULL,
        product_name TEXT NOT NULL,
        model_number TEXT,
        sku_number TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    """)
    
    # 3. pdi_templates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pdi_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        product_type TEXT NOT NULL,
        product_model TEXT,
        template_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        sheet_names TEXT NOT NULL,
        primary_sheet TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        registration_date TEXT NOT NULL,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    """)
    
    # 4. template_field_mappings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS template_field_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER NOT NULL,
        field_key TEXT NOT NULL,
        field_label TEXT NOT NULL,
        target_sheet TEXT NOT NULL,
        target_cell TEXT NOT NULL,
        is_header_field INTEGER DEFAULT 1,
        default_value TEXT,
        is_required INTEGER DEFAULT 0,
        validation_rule TEXT,
        FOREIGN KEY (template_id) REFERENCES pdi_templates(id) ON DELETE CASCADE
    );
    """)
    
    # 5. customers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    # 6. uploaded_requirements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploaded_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)
    
    # 7. extracted_product_details
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_product_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement_id INTEGER,
        company_name TEXT,
        product_type TEXT,
        product_number TEXT,
        lot_size INTEGER,
        customer_name TEXT,
        customer_email TEXT,
        supplier_name TEXT,
        supplier_location TEXT,
        po_number TEXT,
        po_total_qty INTEGER,
        raw_extracted_json TEXT,
        missing_fields TEXT,
        confirmed_by_user INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (requirement_id) REFERENCES uploaded_requirements(id) ON DELETE SET NULL
    );
    """)
    
    # 8. report_jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_code TEXT UNIQUE NOT NULL,
        requirement_id INTEGER,
        template_id INTEGER,
        company_name TEXT NOT NULL,
        product_type TEXT NOT NULL,
        product_number TEXT,
        lot_size INTEGER NOT NULL,
        customer_name TEXT,
        customer_email TEXT,
        status TEXT NOT NULL,
        total_reports INTEGER DEFAULT 0,
        approved_reports INTEGER DEFAULT 0,
        printed_reports INTEGER DEFAULT 0,
        emailed_reports INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (requirement_id) REFERENCES uploaded_requirements(id) ON DELETE SET NULL,
        FOREIGN KEY (template_id) REFERENCES pdi_templates(id) ON DELETE SET NULL
    );
    """)
    
    # 9. generated_reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        report_code TEXT NOT NULL,
        unit_index INTEGER NOT NULL,
        serial_number TEXT,
        excel_path TEXT NOT NULL,
        pdf_path TEXT,
        status TEXT NOT NULL,
        report_data_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES report_jobs(id) ON DELETE CASCADE
    );
    """)
    
    # 10. print_jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS print_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        report_id INTEGER,
        printer_name TEXT NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        printed_at TEXT NOT NULL,
        retries INTEGER DEFAULT 0,
        FOREIGN KEY (job_id) REFERENCES report_jobs(id) ON DELETE CASCADE,
        FOREIGN KEY (report_id) REFERENCES generated_reports(id) ON DELETE SET NULL
    );
    """)
    
    # 11. email_jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        customer_email TEXT NOT NULL,
        customer_name TEXT,
        webhook_url TEXT,
        status TEXT NOT NULL,
        response_data TEXT,
        sent_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES report_jobs(id) ON DELETE CASCADE
    );
    """)
    
    # 12. audit_logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        report_id INTEGER,
        action TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        details_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES report_jobs(id) ON DELETE SET NULL,
        FOREIGN KEY (report_id) REFERENCES generated_reports(id) ON DELETE SET NULL
    );
    """)

    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    backend_dir = os.path.dirname(__file__)
    templates_dir = os.path.join(backend_dir, "templates")

    # Supported OEM Customers for Yathi Pumps
    customers_data = [
        {"name": "Havells", "code": "HIL", "file": "Havells_Surface_Pump_PDI.xlsx"},
        {"name": "Crompton", "code": "CGCEL", "file": "Crompton_Surface_Pump_PDI.xlsx"},
        {"name": "KBS", "code": "KBS", "file": "KBS_Surface_Pump_PDI.xlsx"},
        {"name": "KOEL", "code": "KOEL", "file": "KOEL_Surface_Pump_PDI.xlsx"},
    ]

    for c in customers_data:
        cursor.execute("SELECT id FROM companies WHERE name = ?", (c["name"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO companies (name, code, is_supported, created_at) VALUES (?, ?, 1, ?)", (c["name"], c["code"], now))
            company_id = cursor.lastrowid
        else:
            company_id = row["id"]

        # Check template
        cursor.execute("SELECT id FROM pdi_templates WHERE company_id = ? AND product_type = 'Surface Pump'", (company_id,))
        t_row = cursor.fetchone()
        tpl_path = os.path.join(templates_dir, c["file"])

        # Rebase template records bundled with a project copy. Existing local
        # databases may contain absolute paths from the machine that created it.
        if t_row and os.path.exists(tpl_path):
            cursor.execute("UPDATE pdi_templates SET file_path = ? WHERE id = ?", (tpl_path, t_row["id"]))

        if not t_row and os.path.exists(tpl_path):
            sheet_names = ["Surface Pump", "Sampling Std", "Annexure-1", "Annexure-2", "Annexure-3", "Sheet1", "Sheet2"]
            cursor.execute("""
                INSERT INTO pdi_templates (
                    company_id, product_type, product_model, template_name,
                    file_path, sheet_names, primary_sheet, is_active, registration_date
                ) VALUES (?, 'Surface Pump', 'MMB/CMB/SW/PB', ?, ?, ?, 'Surface Pump', 1, ?)
            """, (company_id, c["file"], tpl_path, json.dumps(sheet_names), now))
            template_id = cursor.lastrowid

            mappings = [
                ("supplier_name", "Supplier Code / Name", "Surface Pump", "C3", 1, "Yathi Pumps Pvt. Ltd.", 0, ""),
                ("supplier_location", "Supplier Location", "Surface Pump", "F3", 1, "Coimbatore, Tamil Nadu", 0, ""),
                ("sku_no", "SKU No.", "Surface Pump", "C4", 1, "", 1, ""),
                ("model_name", "Model Name", "Surface Pump", "D4", 1, "", 1, "prefix:Model Name : "),
                ("po_number", "PO Number", "Surface Pump", "C5", 1, "", 0, ""),
                ("lot_qty", "Lot Qty", "Surface Pump", "D5", 1, "", 1, "prefix:Lot Qty : "),
                ("po_total_qty", "PO Total QTY", "Surface Pump", "C6", 1, "", 0, ""),
                ("inspected_by", "Inspected by", "Surface Pump", "D6", 1, "Yathi QA Inspector", 0, "prefix:Inspected by : "),
                ("reject_reason", "Reject reason", "Surface Pump", "F6", 1, "", 0, ""),
                ("total_dispatched_qty", "Total Dispatched Qty", "Surface Pump", "C7", 1, "", 0, ""),
                ("approved_by", "Approved by", "Surface Pump", "D7", 1, "Quality Head", 0, "prefix:Approved by : "),
                ("residual_qty", "Residual Qty", "Surface Pump", "C8", 1, "", 0, ""),
                ("inspection_date", "Inspection Date", "Surface Pump", "H2", 1, "", 0, "prefix:Inspection Date : \n"),
                ("lot_dispatch_date", "Lot Dispatch Date", "Surface Pump", "J2", 1, "", 0, "prefix:Lot Dispatch Date : "),
                ("final_judgment", "Final Judgment (OK/Reject)", "Surface Pump", "E5", 1, "OK", 1, "highlight_or_tick")
            ]
            for m in mappings:
                cursor.execute("""
                    INSERT INTO template_field_mappings (
                        template_id, field_key, field_label, target_sheet,
                        target_cell, is_header_field, default_value, is_required, validation_rule
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (template_id, m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7]))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully for Yathi Pumps PDI Automation.")
