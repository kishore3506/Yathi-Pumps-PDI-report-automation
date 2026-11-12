import os
import shutil
import tempfile
import unittest

import openpyxl

import database
from services.report_generator import ReportGenerator


class ReportGenerationTests(unittest.TestCase):
    def test_two_reports_split_101_units_and_preserve_template(self):
        original_db_path = database.DB_PATH
        template = os.path.join(os.path.dirname(__file__), "..", "templates", "Havells_Surface_Pump_PDI.xlsx")
        template = os.path.abspath(template)
        with tempfile.TemporaryDirectory() as temp_dir:
            database.DB_PATH = os.path.join(temp_dir, "test.db")
            with open(template, "rb") as template_file:
                template_before = template_file.read()
            template_wb = openpyxl.load_workbook(template, data_only=True)
            template_ws = template_wb["Surface Pump"]
            preserved_cells = {cell: template_ws[cell].value for cell in ("E5", "F5", "C7", "C6", "G10", "G44", "K44")}
            template_wb.close()
            try:
                database.init_db()
                conn = database.get_db()
                template_id = conn.execute(
                    "SELECT id FROM pdi_templates WHERE template_name = ?",
                    ("Havells_Surface_Pump_PDI.xlsx",),
                ).fetchone()["id"]
                conn.close()

                result = ReportGenerator().generate_batch_reports({
                    "template_id": template_id,
                    "company_name": "Havells",
                    "product_type": "Surface Pump",
                    "product_number": "HV-101",
                    "model_name": "Test Model",
                    "lot_size": 101,
                    "po_number": "PO-101",
                    "supplier_name": "Yathi Pumps Pvt. Ltd.",
                    "supplier_location": "Coimbatore, Tamil Nadu",
                }, os.path.join(temp_dir, "reports"))

                self.assertEqual(result["total_reports"], 2)
                self.assertEqual(result["quantity_allocations"], [51, 50])
                self.assertEqual(len(result["reports"]), 2)
                quantities = []
                for report in result["reports"]:
                    workbook = openpyxl.load_workbook(report["excel_path"], data_only=True)
                    sheet = workbook["Surface Pump"]
                    quantities.append(sheet["D5"].value)
                    for cell, expected_value in preserved_cells.items():
                        self.assertEqual(sheet[cell].value, expected_value, f"Template value changed at {cell}")
                    self.assertEqual(sheet["D4"].value, "Model Name : Test Model")
                    self.assertEqual(sheet["C4"].value, "HV-101")
                    self.assertEqual(sheet["C5"].value, "PO-101")
                    workbook.close()
                self.assertEqual(quantities, ["Lot Qty : 51", "Lot Qty : 50"])
                with open(template, "rb") as template_file:
                    self.assertEqual(template_file.read(), template_before)
            finally:
                database.DB_PATH = original_db_path


if __name__ == "__main__":
    unittest.main()
