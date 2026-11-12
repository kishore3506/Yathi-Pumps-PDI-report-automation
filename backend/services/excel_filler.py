import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from typing import Dict, Any, List, Optional
import os
import shutil
import logging

try:
    from ..database import get_db
except (ImportError, ValueError):
    from database import get_db

logger = logging.getLogger(__name__)

class ExcelFiller:
    def __init__(self):
        pass

    def get_mappings_for_template(self, template_id: int) -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT field_key, field_label, target_sheet, target_cell,
                   is_header_field, default_value, is_required, validation_rule
            FROM template_field_mappings
            WHERE template_id = ?
        """, (template_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def populate_template(
        self,
        template_file_path: str,
        output_file_path: str,
        template_id: int,
        data: Dict[str, Any],
        observation_overrides: Optional[Dict[str, Any]] = None,
        unit_index: int = 1,
        serial_number: Optional[str] = None
    ) -> str:
        """
        Populate an Excel report template using field mappings while strictly preserving:
        - Original styles, borders, colors, and layout
        - Fixed inspection criteria and standards
        - Company branding and images
        - Formulas
        """
        if not os.path.exists(template_file_path):
            raise FileNotFoundError(f"Template not found: {template_file_path}")

        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        if os.path.abspath(template_file_path) != os.path.abspath(output_file_path):
            shutil.copyfile(template_file_path, output_file_path)

        wb = openpyxl.load_workbook(output_file_path, data_only=False)
        mappings = self.get_mappings_for_template(template_id)
        mapping_dict = {m["field_key"]: m for m in mappings}

        primary_sheet = "Surface Pump"
        ws = wb[primary_sheet] if primary_sheet in wb.sheetnames else wb.active

        def set_mapped_cell(key: str, raw_value: Any):
            mapping = mapping_dict.get(key)
            if not mapping or raw_value is None or str(raw_value).strip() == "":
                return

            sheet_name = mapping["target_sheet"]
            target_ws = wb[sheet_name] if sheet_name in wb.sheetnames else ws
            cell_coord = mapping["target_cell"]
            rule = mapping.get("validation_rule") or ""

            val_str = str(raw_value).strip()
            if rule.startswith("prefix:"):
                prefix = rule[len("prefix:"):]
                final_val = f"{prefix}{val_str}"
            else:
                final_val = val_str

            target_ws[cell_coord].value = final_val

        # Populate standard header fields
        set_mapped_cell("supplier_name", data.get("supplier_name"))
        set_mapped_cell("supplier_location", data.get("supplier_location"))
        set_mapped_cell("sku_no", data.get("product_number"))
        set_mapped_cell("model_name", data.get("model_name"))
        set_mapped_cell("po_number", data.get("po_number"))
        set_mapped_cell("lot_qty", data.get("lot_size"))
        set_mapped_cell("po_total_qty", data.get("po_total_qty"))
        set_mapped_cell("inspected_by", data.get("inspected_by"))
        set_mapped_cell("approved_by", data.get("approved_by"))
        set_mapped_cell("total_dispatched_qty", data.get("total_dispatched_qty"))
        set_mapped_cell("residual_qty", data.get("residual_qty"))

        if data.get("inspection_date"):
            set_mapped_cell("inspection_date", data.get("inspection_date"))
        if data.get("lot_dispatch_date"):
            set_mapped_cell("lot_dispatch_date", data.get("lot_dispatch_date"))

        final_judgment = (data.get("final_judgment") or "").upper()
        ok_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        reject_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

        if "REJECT" in final_judgment:
            ws["E5"].value = None
            ws["F5"].value = "Reject [✔]"
            ws["F5"].fill = reject_fill
            if data.get("reject_reason"):
                ws["F6"].value = data.get("reject_reason")
        elif final_judgment in {"OK", "PASS", "ACCEPT"}:
            ws["E5"].value = "OK [✔]"
            ws["E5"].fill = ok_fill
            ws["F5"].value = "Reject"

        if serial_number:
            ws["C4"].value = f"{data.get('product_number', '')} / S/N: {serial_number}"

        if observation_overrides:
            for row_key, obs_val in observation_overrides.items():
                try:
                    r_idx = int(row_key)
                    if isinstance(obs_val, dict):
                        for col_letter, c_val in obs_val.items():
                            if c_val is not None:
                                ws[f"{col_letter}{r_idx}"].value = str(c_val)
                    else:
                        ws[f"G{r_idx}"].value = str(obs_val)
                except Exception as e:
                    logger.warning(f"Failed to apply override at row {row_key}: {e}")

        wb.save(output_file_path)
        wb.close()
        return output_file_path
