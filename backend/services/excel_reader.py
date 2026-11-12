import openpyxl
from typing import Dict, Any, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

class ExcelReader:
    def __init__(self):
        pass

    def read_report(self, file_path: str, primary_sheet: str = "Surface Pump") -> Dict[str, Any]:
        """Reads an existing template or generated report into a structured JSON representation."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Report file not found: {file_path}")

        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet_names = wb.sheetnames
        ws = wb[primary_sheet] if primary_sheet in sheet_names else wb.active

        # Extract Header fields
        header_data = {
            "title": str(ws.cell(1, 3).value or "").strip(),
            "doc_no": str(ws.cell(1, 8).value or "").strip(),
            "inspection_date": str(ws.cell(2, 8).value or "").replace("Inspection Date :", "").strip(),
            "lot_dispatch_date": str(ws.cell(2, 10).value or "").replace("Lot Dispatch Date :", "").strip(),
            "supplier_name": str(ws.cell(3, 3).value or "").strip(),
            "supplier_location": str(ws.cell(3, 6).value or "").strip(),
            "special_remarks": str(ws.cell(3, 7).value or "").strip(),
            "sku_no": str(ws.cell(4, 3).value or "").strip(),
            "model_name": str(ws.cell(4, 4).value or "").replace("Model Name :", "").strip(),
            "po_number": str(ws.cell(5, 3).value or "").strip(),
            "lot_qty": str(ws.cell(5, 4).value or "").replace("Lot Qty :", "").strip(),
            "judgment_ok": ws.cell(5, 5).value,
            "judgment_reject": ws.cell(5, 6).value,
            "po_total_qty": str(ws.cell(6, 3).value or "").strip(),
            "inspected_by": str(ws.cell(6, 4).value or "").replace("Inspected by :", "").strip(),
            "reject_reason": str(ws.cell(6, 5).value or "").strip(),
            "total_dispatched_qty": str(ws.cell(7, 3).value or "").strip(),
            "approved_by": str(ws.cell(7, 4).value or "").replace("Approved by :", "").strip(),
            "standards_ref": str(ws.cell(7, 5).value or "").strip(),
            "residual_qty": str(ws.cell(8, 3).value or "").strip(),
        }

        # Extract Inspection Observations (Rows 10 to 80)
        checkpoints: List[Dict[str, Any]] = []
        current_type = ""
        for r in range(10, 81):
            sn = ws.cell(row=r, column=1).value
            itype = ws.cell(row=r, column=2).value
            param = ws.cell(row=r, column=3).value
            spec = ws.cell(row=r, column=4).value
            method = ws.cell(row=r, column=5).value
            freq = ws.cell(row=r, column=6).value
            
            if itype:
                current_type = str(itype).replace("\n", " ").strip()

            # Columns G to K (7 to 11)
            obs_g = ws.cell(row=r, column=7).value
            obs_h = ws.cell(row=r, column=8).value
            obs_i = ws.cell(row=r, column=9).value
            obs_j = ws.cell(row=r, column=10).value
            obs_k = ws.cell(row=r, column=11).value

            # Skip rows that are empty or notes
            if sn is None and param is None and spec is None:
                continue

            checkpoints.append({
                "row_index": r,
                "item_sn": str(sn or "").strip(),
                "inspection_type": current_type,
                "parameter": str(param or "").strip(),
                "specification": str(spec or "").strip(),
                "method": str(method or "").strip(),
                "frequency": str(freq or "").strip(),
                "observations": {
                    "G": str(obs_g) if obs_g is not None else "",
                    "H": str(obs_h) if obs_h is not None else "",
                    "I": str(obs_i) if obs_i is not None else "",
                    "J": str(obs_j) if obs_j is not None else "",
                    "K": str(obs_k) if obs_k is not None else "",
                },
                "is_multi_sample": (obs_h is not None or obs_k is not None) and (str(obs_h) != "")
            })

        # Footer notes
        footer_note = str(ws.cell(81, 2).value or "").strip()

        return {
            "sheet_names": sheet_names,
            "primary_sheet": primary_sheet,
            "header_data": header_data,
            "checkpoints": checkpoints,
            "footer_note": footer_note
        }
