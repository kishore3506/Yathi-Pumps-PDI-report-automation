# Yathi Pumps PDI Automation System

A production-grade, local Pre-Delivery Inspection (PDI) report automation platform specifically built for **Yathi Pumps Pvt. Ltd.** to generate, verify, and deliver official PDI Excel reports for major OEM customers:
- **Havells** (HIL)
- **Crompton** (CGCEL)
- **KBS** (KBS Pumps / KBL)
- **KOEL** (Kirloskar Oil Engines Limited)

---

## 1. System Overview

- **Template Preservation:** Generated workbooks start from the registered OEM template. Its layout, predefined inspection criteria, existing values, formulas, and styles are preserved; only supplied/extracted order details are written into their mapped cells.
- **Customer OEM Selection:** Choose between **Havells**, **Crompton**, **KBS**, and **KOEL**. The engine selects the corresponding customer PDI template preserving the exact structure, formatting, formulas, Indian Standards (`IS 9079/8472/...`), sampling plan (`IS 2500 / S2`), and 56 inspection criteria.
- **Havells Surface Pump Reference:** The included Havells Surface Pump workbook is the editable report template corresponding to the supplied filled PDI PDF.
- **Required Image-Based Extraction:** Upload a purchase order/requirement before generating. Google Gemini reads the customer, product, model, SKU, PO number, and lot size, then fills the editable fields. Review and correct the extracted values, then click **Generate**. The app never creates a job automatically during extraction. Unreadable required values stay blank and are flagged for review.
  - **Model Name** (Cell `D4` with prefix `Model Name : `)
  - **SKU No.** (Cell `C4`)
  - **PO Number** (Cell `C5`)
  - **Lot Size / Qty** (Cell `D5` with prefix `Lot Qty : `)
  - **PO Total Qty** (Cell `C6`)
  - **Inspection Date** & **Dispatch Date** (Cells `H2`, `J2`) only when supplied or readable
  - Existing inspection checklist, observation values, and judgment in the selected template are retained
- **Lot Size-Based Report Generation:** Generates the requested 1–5 editable workbooks and splits the lot quantity evenly across them. The original Excel templates and their formatting are preserved.
- **Interactive In-Browser Editor:** Excel-like grid preview and live editor for header metadata and all 56 checkpoint observation readings (including multi-sample columns G to K for electrical/hydraulic performance tests).
- **Export, Print & Email:**
  - Download individual `.xlsx` reports, bundled `.zip` archives, and ReportLab landscape A4 `.pdf` copies.
  - Native Windows Host Printing with spooler status tracking.
  - Secured n8n webhook email dispatch to customer QA departments.

---

## 2. Customer Templates & Coordinates

| Field Key | Report Cell | Format / Prefix Rule |
| :--- | :---: | :--- |
| `supplier_name` | **`C3`** (merged `C3:D3`) | `Yathi Pumps Pvt. Ltd.` |
| `supplier_location`| **`F3`** | `Coimbatore, Tamil Nadu` |
| `sku_no` | **`C4`** | Input SKU No. (or `SKU / S/N: ...`) |
| `model_name` | **`D4`** | `prefix:Model Name : ` + Input Model |
| `po_number` | **`C5`** | Input PO Number |
| `lot_qty` | **`D5`** | `prefix:Lot Qty : ` + Input Lot Size |
| `final_judgment` | **`E5` / `F5`** | Preserves the registered template's value unless explicitly changed |
| `po_total_qty` | **`C6`** | Input PO Total Qty |
| `inspected_by` | **`D6`** | Inspector label; name only when supplied |
| `reject_reason` | **`F6`** | Recorded if judgment is Reject |
| `total_dispatched_qty`| **`C7`** | Residual and dispatch quantities |
| `approved_by` | **`D7`** | Approver label; name only when supplied |
| `residual_qty` | **`C8`** | Numeric residual |
| `inspection_date`| **`H2`** | `prefix:Inspection Date : \n` + Date |
| `lot_dispatch_date`| **`J2`** | `prefix:Lot Dispatch Date : ` + Date |

---

## 3. Running the Application on Windows

### Gemini API

Create an API key in [Google AI Studio](https://aistudio.google.com/app/apikey), then put it in `backend/.env` or set it in the process environment. Do not commit or share the key. Example `backend/.env`:

```text
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=45
```

Restart the backend after setting the key. Upload a JPG/PNG image, searchable PDF, or XLSX requirement. The backend sends the image/text to Gemini's multimodal API for extraction. Review/edit the extracted fields and click **Generate**. The report count comes from the extracted lot size. The template's predefined inspection criteria and values remain intact. The app never infers lot size from PO total quantity. Text-based PDFs are read from their text layer; scanned PDFs rely on embedded page images. Gemini returns schema-constrained JSON, and images are orientation-corrected and resized to a maximum 1280 px before sending.

### Report counts and quantity allocation

| Uploaded lot size | Workbooks | Quantity recorded in each workbook |
| --- | ---: | --- |
| 1–10 | 1 | Entire lot |
| 11–100 | 1 | Entire lot |
| 101–1,200 | 2 | Even split |
| 1,201–2,500 | 3 | Even split |
| 2,501–4,000 | 4 | Even split |
| Greater than 4,000 | 5 | Even split |

When a split has a remainder, the first reports receive one extra unit each (for example, lot 101 becomes 51 and 50). The quantities recorded across all workbooks sum to the original lot size.

### Start FastAPI Backend
```powershell
cd C:\path\to\compliance-pdi
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
cd .\backend
python main.py
```
*Backend runs on `http://127.0.0.1:8000` and automatically serves the pre-compiled frontend.*

### Access the Web Application
Open your browser at:
**`http://127.0.0.1:8000`**

*(For hot-reloading dev mode: `cd ..\frontend; npm install; npm run dev` at `http://localhost:5173`)*

---

## 4. Run the workflow checks

From the project folder, run the lot-size, extraction-validation, and workbook-generation checks:
```powershell
cd .\backend
python -m unittest discover -s tests -v
```
