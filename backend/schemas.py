from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CompanyModel(BaseModel):
    id: Optional[int] = None
    name: str
    code: str
    is_supported: bool = False
    created_at: Optional[str] = None

class TemplateFieldMapping(BaseModel):
    id: Optional[int] = None
    field_key: str
    field_label: str
    target_sheet: str
    target_cell: str
    is_header_field: bool = True
    default_value: Optional[str] = ""
    is_required: bool = False
    validation_rule: Optional[str] = ""

class TemplateModel(BaseModel):
    id: Optional[int] = None
    company_id: int
    company_name: Optional[str] = None
    product_type: str
    product_model: Optional[str] = None
    template_name: str
    file_path: str
    sheet_names: List[str] = []
    primary_sheet: str = "Surface Pump"
    is_active: bool = True
    registration_date: Optional[str] = None
    field_mappings: Optional[List[TemplateFieldMapping]] = None

class RequirementUploadResponse(BaseModel):
    requirement_id: int
    filename: str
    original_name: str
    file_type: str
    file_path: str
    uploaded_at: str
    status: str

class ExtractedDetails(BaseModel):
    requirement_id: Optional[int] = None
    company_name: Optional[str] = None
    product_type: Optional[str] = None
    product_number: Optional[str] = None
    model_name: Optional[str] = None
    lot_size: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_location: Optional[str] = None
    po_number: Optional[str] = None
    po_total_qty: Optional[int] = None
    missing_fields: List[str] = []
    is_company_supported: bool = True
    suggested_template_id: Optional[int] = None
    confidence_notes: Optional[str] = None

class TemplateMatchRequest(BaseModel):
    company_name: str
    product_type: str
    product_model: Optional[str] = None

class TemplateMatchResponse(BaseModel):
    matched: bool
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    company_supported: bool = True
    message: str
    available_templates: Optional[List[Dict[str, Any]]] = None

class ReportGenerateRequest(BaseModel):
    requirement_id: Optional[int] = None
    template_id: int
    company_name: str
    product_type: str
    product_number: str
    model_name: str
    lot_size: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_location: Optional[str] = None
    po_number: str
    po_total_qty: Optional[int] = None
    inspection_date: Optional[str] = None
    lot_dispatch_date: Optional[str] = None
    inspected_by: Optional[str] = None
    approved_by: Optional[str] = None
    serial_numbers: Optional[List[str]] = None # Optional list of serial numbers if given per unit
    header_overrides: Optional[Dict[str, Any]] = None
    observation_overrides: Optional[Dict[str, Any]] = None # custom readings

class GeneratedReportItem(BaseModel):
    id: int
    job_id: int
    report_code: str
    unit_index: int
    serial_number: Optional[str] = None
    excel_path: str
    pdf_path: Optional[str] = None
    status: str
    report_data: Dict[str, Any]
    created_at: str

class ReportJobResponse(BaseModel):
    job_id: int
    job_code: str
    company_name: str
    product_type: str
    product_number: Optional[str] = None
    lot_size: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: str
    total_reports: int
    approved_reports: int
    printed_reports: int
    emailed_reports: int
    template_name: Optional[str] = None
    created_at: str
    updated_at: str
    reports: Optional[List[GeneratedReportItem]] = None

class ReportUpdateRequest(BaseModel):
    header_data: Optional[Dict[str, Any]] = None
    observation_readings: Optional[Dict[str, Any]] = None # e.g. {"1": "Visual Ok...", "29": {"G": "2.14", "K": "2.13"}}
    final_judgment: Optional[str] = None # "OK" or "Reject"
    reject_reason: Optional[str] = None

class PrintRequest(BaseModel):
    job_id: int
    report_ids: Optional[List[int]] = None # None means all in job
    printer_name: Optional[str] = None

class EmailRequest(BaseModel):
    job_id: int
    report_ids: Optional[List[int]] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    skip: bool = False

class DashboardStats(BaseModel):
    total_reports_generated: int
    completed_jobs: int
    awaiting_review: int
    awaiting_printing: int
    awaiting_email: int
    recent_jobs: List[Dict[str, Any]]
