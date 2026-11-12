import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { 
  UploadCloud, 
  FileCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Sparkles, 
  Layers, 
  Cpu, 
  Loader2, 
  ArrowRight,
  Info,
  Building2
} from 'lucide-react';

const SUPPORTED_CUSTOMERS = [
  { id: 'Havells', name: 'Havells', code: 'HIL', color: 'border-red-500 bg-red-50 text-red-700', activeBg: 'bg-red-600 text-white' },
  { id: 'Crompton', name: 'Crompton', code: 'CGCEL', color: 'border-blue-500 bg-blue-50 text-blue-700', activeBg: 'bg-blue-600 text-white' },
  { id: 'KBS', name: 'KBS', code: 'KBS', color: 'border-emerald-500 bg-emerald-50 text-emerald-700', activeBg: 'bg-emerald-600 text-white' },
  { id: 'KOEL', name: 'KOEL', code: 'KOEL', color: 'border-amber-500 bg-amber-50 text-amber-700', activeBg: 'bg-amber-600 text-white' }
];

export default function NewInspectionPage({ setActiveTab, setSelectedJobId }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractionFailed, setExtractionFailed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Start blank: all order data must come from the uploaded requirement or explicit review.
  const [formData, setFormData] = useState({
    requirement_id: null,
    company_name: '',
    product_type: '',
    product_number: '',
    model_name: '',
    lot_size: '',
    customer_name: '',
    customer_email: '',
    supplier_name: '',
    supplier_location: '',
    po_number: '',
    po_total_qty: '',
    inspection_date: '',
    lot_dispatch_date: '',
  });

  const [missingFields, setMissingFields] = useState([]);
  const [uncertainFields, setUncertainFields] = useState([]);
  const reportCount = useMemo(() => {
    const qty = Number(formData.lot_size);
    if (!Number.isInteger(qty) || qty < 1) return 0;
    if (qty <= 100) return 1;
    if (qty <= 1200) return 2;
    if (qty <= 2500) return 3;
    if (qty <= 4000) return 4;
    return 5;
  }, [formData.lot_size]);
  const [templateMatch, setTemplateMatch] = useState({
    matched: false,
    template_id: null,
    template_name: '',
    company_supported: false,
    message: 'Upload a document or select a customer to match its PDI template'
  });

  // Check template match on mount or customer change
  const triggerMatch = async (customerName, productType = formData.product_type) => {
    if (!customerName) {
      setTemplateMatch({ matched: false, template_id: null, template_name: '', company_supported: false, message: 'Upload a document or select a customer to match its PDI template' });
      return;
    }
    try {
      const matchRes = await api.matchTemplate({
        company_name: customerName,
        product_type: productType,
        product_model: formData.model_name
      });
      setTemplateMatch(matchRes);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    triggerMatch(formData.company_name);
  }, [formData.company_name]);

  // Handle customer pill selection
  const handleSelectCustomer = (customer) => {
    setFormData(prev => ({
      ...prev,
      company_name: customer,
      customer_name: customer
    }));
    triggerMatch(customer);
  };

  const extractUploadedRequirement = async (requirementId) => {
    setExtracting(true);
    const extRes = await api.extractDetails({ requirement_id: requirementId });
    if (extRes.error) throw new Error(extRes.error);

    const extractedValues = {
      ...formData,
      requirement_id: requirementId,
      company_name: extRes.company_name ?? extRes.customer_name ?? '',
      product_type: extRes.product_type ?? '',
      product_number: extRes.product_number ?? '',
      model_name: extRes.model_name ?? '',
      lot_size: extRes.lot_size ?? '',
      customer_name: extRes.customer_name ?? extRes.company_name ?? '',
      customer_email: extRes.customer_email ?? '',
      supplier_name: extRes.supplier_name ?? '',
      supplier_location: extRes.supplier_location ?? '',
      po_number: extRes.po_number ?? '',
      po_total_qty: extRes.po_total_qty ?? '',
      inspection_date: '',
      lot_dispatch_date: '',
    };
    setFormData(extractedValues);

    const requiredImageFields = ['company_name', 'product_type', 'product_number', 'model_name', 'lot_size', 'po_number'];
    setMissingFields((extRes.missing_fields || []).filter(field => requiredImageFields.includes(field)));
    const uncertain = new Set((extRes.uncertain_fields || []).filter(field => requiredImageFields.includes(field)));
    Object.entries(extRes.field_confidence || {}).forEach(([field, level]) => {
      if (requiredImageFields.includes(field) && String(level).toLowerCase() === 'low') uncertain.add(field);
    });
    setUncertainFields([...uncertain]);

    const matchRes = extractedValues.company_name && extractedValues.product_type
      ? await api.matchTemplate({
          company_name: extractedValues.company_name,
          product_type: extractedValues.product_type,
          product_model: extractedValues.model_name
        })
      : null;
    setTemplateMatch(matchRes || {
      matched: false, template_id: null, template_name: '', company_supported: false,
      message: 'Could not match an OEM template from the extracted customer and product.'
    });
    setExtractionFailed(false);
  };

  const handleRetryExtraction = async () => {
    if (!formData.requirement_id) return;
    setErrorMsg('');
    setExtractionFailed(false);
    try {
      await extractUploadedRequirement(formData.requirement_id);
    } catch (err) {
      setErrorMsg(err.message);
      setExtractionFailed(true);
    } finally {
      setExtracting(false);
    }
  };

  // Handle requirement file upload
  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setFile(selectedFile);
    setErrorMsg('');
    setExtractionFailed(false);
    setMissingFields([]);
    setUncertainFields([]);
    setFormData(prev => ({ ...prev, requirement_id: null, company_name: '', product_type: '', product_number: '', model_name: '', lot_size: '', customer_name: '', customer_email: '', supplier_name: '', supplier_location: '', po_number: '', po_total_qty: '' }));
    setTemplateMatch({ matched: false, template_id: null, template_name: '', company_supported: false, message: 'Reading the uploaded requirement…' });

    let uploadedRequirementId = null;
    try {
      setUploading(true);
      const upRes = await api.uploadRequirement(selectedFile);
      uploadedRequirementId = upRes.requirement_id;
      setFormData(prev => ({ ...prev, requirement_id: upRes.requirement_id }));
      setUploading(false);
      await extractUploadedRequirement(upRes.requirement_id);
    } catch (err) {
      setErrorMsg(err.message);
      setExtractionFailed(!!uploadedRequirementId);
    } finally {
      setUploading(false);
      setExtracting(false);
      setGenerating(false);
    }
  };

  const generateJob = async (values, match) => {
    const res = await api.generateReports({
      requirement_id: values.requirement_id,
      template_id: match.template_id,
      company_name: values.company_name,
      product_type: values.product_type,
      product_number: values.product_number,
      model_name: values.model_name,
      lot_size: parseInt(values.lot_size),
      customer_name: values.customer_name,
      customer_email: values.customer_email,
      supplier_name: values.supplier_name,
      supplier_location: values.supplier_location,
      po_number: values.po_number,
      po_total_qty: values.po_total_qty ? parseInt(values.po_total_qty) : null,
      inspection_date: values.inspection_date || null,
      lot_dispatch_date: values.lot_dispatch_date || null,
    });
    setSelectedJobId(res.job_id);
    setActiveTab('job-review');
    return res;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !formData.requirement_id) {
      setErrorMsg('Upload the purchase order or requirement image first. Reports are generated from the uploaded document.');
      return;
    }
    const missingRequired = ['company_name', 'product_type', 'product_number', 'model_name', 'lot_size', 'po_number']
      .filter(field => String(formData[field] ?? '').trim() === '');
    if (missingRequired.length) {
      setErrorMsg(`Fill or correct the required details before generating: ${missingRequired.join(', ')}.`);
      return;
    }
    if (!templateMatch.matched || !templateMatch.template_id) {
      setErrorMsg(`Cannot generate reports: A valid registered PDI template must be matched for customer '${formData.company_name}'.`);
      return;
    }
    if (!Number.isInteger(Number(formData.lot_size)) || Number(formData.lot_size) <= 0) {
      setErrorMsg('Lot size must be at least 1.');
      return;
    }

    try {
      setGenerating(true);
      setErrorMsg('');
      await generateJob(formData, templateMatch);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Initiate Pre-Dispatch Inspection (PDI)</h1>
        <p className="text-sm text-gray-500 mt-1">
          <b>Upload-first workflow:</b> Upload the purchase order or requirement image. Google Gemini reads the customer, product, model, SKU, PO number, and lot size, then fills the editable report fields. Review them and choose Generate.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 border-l-4 border-red-600 rounded-r-lg flex items-start space-x-3 text-red-800 text-sm">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Notice:</div>
            <div>{errorMsg}</div>
          </div>
        </div>
      )}

      {/* Prominent Customer OEM Selection Card */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Building2 className="w-4 h-4 text-blue-700" />
              <span>Choose OEM Customer *</span>
            </label>
            <p className="text-xs text-gray-500 mt-0.5">Select which customer's official PDI report format and structure to generate</p>
          </div>
          <span className="text-xs font-bold text-blue-800 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
            Selected: {formData.company_name || 'Not selected'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          {SUPPORTED_CUSTOMERS.map((cust) => {
            const isSelected = formData.company_name.toLowerCase() === cust.id.toLowerCase();
            return (
              <button
                key={cust.id}
                type="button"
                onClick={() => handleSelectCustomer(cust.id)}
                className={`p-3.5 rounded-xl border-2 text-center transition flex flex-col items-center justify-center space-y-1 ${
                  isSelected
                    ? `${cust.activeBg} shadow-md border-transparent ring-2 ring-blue-500`
                    : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100 hover:border-gray-300'
                }`}
              >
                <span className="font-extrabold text-base tracking-tight">{cust.name}</span>
                <span className={`text-[11px] font-semibold uppercase ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
                  {cust.code} Format
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid: Upload Box + Template Match */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Upload Box (Col 1-2) */}
        <div className="md:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-gray-800 flex items-center space-x-2">
            <UploadCloud className="w-5 h-5 text-blue-700" />
              <span>Upload Requirement Document (Required)</span>
          </h2>

          <div className="border-2 border-dashed border-gray-300 hover:border-blue-400 rounded-xl p-6 text-center transition cursor-pointer bg-gray-50/50">
            <input
              type="file"
              id="file-upload"
              accept=".jpg,.jpeg,.png,.pdf,.xlsx,.xls"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-upload" className="cursor-pointer block space-y-2">
              <div className="w-12 h-12 mx-auto rounded-full bg-blue-50 text-blue-700 flex items-center justify-center">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="text-sm font-semibold text-gray-700">
                {file ? file.name : "Choose a purchase order or requirement image/PDF"}
              </div>
              <p className="text-xs text-gray-400">
                Required. Gemini analyzes JPG/PNG images and reads text from PDF/XLSX. Extracted values populate the report below.
              </p>
            </label>
          </div>

          {(uploading || extracting) && (
            <div className="flex items-center space-x-3 text-sm text-gray-600 bg-blue-50/60 p-3 rounded-lg border border-blue-100">
              <Loader2 className="w-5 h-5 text-blue-700 animate-spin" />
              <span>
                {uploading ? "Uploading document to host..." : "Gemini is reading the document..."}
              </span>
            </div>
          )}

          {uncertainFields.length > 0 && (
            <div className="text-xs text-amber-800 bg-amber-50 p-3 rounded-lg border border-amber-200">
              Verify these difficult-to-read fields: {uncertainFields.join(', ')}. Unreadable values were left blank.
            </div>
          )}
          {file && !uploading && !extracting && !extractionFailed && (
            <div className="flex items-center space-x-2 text-xs font-semibold text-green-700 bg-green-50 p-2.5 rounded-lg border border-green-200">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Document loaded: {file.name}. Review extracted values below.</span>
            </div>
          )}
          {extractionFailed && formData.requirement_id && !uploading && !extracting && (
            <button type="button" onClick={handleRetryExtraction} className="px-4 py-2 text-sm font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100">
              Retry image extraction
            </button>
          )}
        </div>

        {/* Template Match Card (Col 3) */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-800 flex items-center space-x-2">
              <Layers className="w-5 h-5 text-blue-700" />
              <span>Active Template</span>
            </h2>
            <p className="text-xs text-gray-500 mt-1">Pre-registered customer PDI workbook</p>

            <div className="mt-4 p-4 rounded-lg border bg-gray-50 space-y-2">
              <div className="text-xs font-medium text-gray-500">Customer OEM</div>
              <div className="font-bold text-sm text-gray-900 flex items-center justify-between">
                <span>{formData.company_name}</span>
                <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded font-semibold">Active</span>
              </div>

              <div className="text-xs font-medium text-gray-500 pt-2 border-t">Report Template</div>
              <div className="font-semibold text-sm text-gray-900 truncate" title={templateMatch.template_name}>
                {templateMatch.template_name || 'Matching...'}
              </div>

              <div className="text-xs text-gray-500 italic">
                {templateMatch.message}
              </div>
            </div>
          </div>

          <div className="text-xs text-gray-500 bg-gray-50 p-2.5 rounded border flex items-start space-x-1.5">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-blue-600" />
            <span>Preserves all 56 inspection criteria, formulas, tolerances, and multi-sample observation cells.</span>
          </div>
        </div>

      </div>

      {/* Confirmation & Editing Form */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-6">
        <div className="border-b pb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">AI-extracted order details</h2>
            <p className="text-xs text-gray-500">These values are read from your uploaded requirement. Review or edit them, then choose Generate to create editable reports from the Havells template.</p>
          </div>
          {missingFields.length > 0 && (
            <span className="text-xs bg-amber-100 text-amber-800 font-medium px-2.5 py-1 rounded-full border border-amber-200">
              {missingFields.length} field(s) require review
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
          
          {/* Customer OEM Selection Dropdown */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Customer OEM *
            </label>
            <select
              value={formData.company_name}
              onChange={(e) => handleSelectCustomer(e.target.value)}
              className="w-full px-3 py-2 text-sm font-bold text-gray-900 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
            >
              <option value="">Select from image or choose customer</option>
              <option value="Havells">Havells (HIL)</option>
              <option value="Crompton">Crompton (CGCEL)</option>
              <option value="KBS">KBS Pumps</option>
              <option value="KOEL">KOEL (Kirloskar Oil Engines)</option>
            </select>
          </div>

          {/* Product Type */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Product Type *
            </label>
            <input
              type="text"
              required
              value={formData.product_type}
              onChange={(e) => setFormData({ ...formData, product_type: e.target.value })}
              placeholder="e.g. Surface Pump"
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Model Name */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Model Name *
            </label>
            <input
              type="text"
              required
              value={formData.model_name}
              onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
              placeholder="Enter or review the value read from the image"
              className="w-full px-3 py-2 text-sm font-semibold border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* SKU No */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              SKU No. *
            </label>
            <input
              type="text"
              required
              value={formData.product_number}
              onChange={(e) => setFormData({ ...formData, product_number: e.target.value })}
              placeholder="Enter or review the value read from the image"
              className="w-full px-3 py-2 text-sm font-mono font-semibold border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* PO Number */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              PO Number *
            </label>
            <input
              type="text"
              required
              value={formData.po_number}
              onChange={(e) => setFormData({ ...formData, po_number: e.target.value })}
              placeholder="Enter or review the value read from the image"
              className="w-full px-3 py-2 text-sm font-semibold border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Lot Size / Qty */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Lot Size / Qty * (Calculates report count)
            </label>
            <input
              type="number"
              min="1"
              max="1000000"
              required
              value={formData.lot_size}
              onChange={(e) => setFormData({ ...formData, lot_size: e.target.value })}
              className="w-full px-3 py-2 text-sm font-black text-blue-700 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <p className="text-[11px] text-gray-500 mt-1">{reportCount ? `${reportCount} editable report${reportCount === 1 ? '' : 's'}; quantities are split as evenly as possible.` : 'Enter a valid lot size to calculate the report count.'}</p>
          </div>

          {/* PO Total Qty */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              PO Total Qty
            </label>
            <input
              type="number"
              value={formData.po_total_qty}
              onChange={(e) => setFormData({ ...formData, po_total_qty: e.target.value })}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Supplier Name (Defaults to Yathi Pumps) */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Manufacturer / Supplier Name
            </label>
            <input
              type="text"
              value={formData.supplier_name}
              onChange={(e) => setFormData({ ...formData, supplier_name: e.target.value })}
              placeholder="Yathi Pumps Pvt. Ltd."
              className="w-full px-3 py-2 text-sm font-semibold border rounded-lg bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Supplier Location */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Supplier Location
            </label>
            <input
              type="text"
              value={formData.supplier_location}
              onChange={(e) => setFormData({ ...formData, supplier_location: e.target.value })}
              placeholder="Coimbatore, Tamil Nadu"
              className="w-full px-3 py-2 text-sm border rounded-lg bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Inspection Date */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Inspection Date
            </label>
            <input
              type="date"
              value={formData.inspection_date}
              onChange={(e) => setFormData({ ...formData, inspection_date: e.target.value })}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Customer Dispatch Date */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Lot Dispatch Date
            </label>
            <input
              type="date"
              value={formData.lot_dispatch_date}
              onChange={(e) => setFormData({ ...formData, lot_dispatch_date: e.target.value })}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Customer Email for n8n */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
              Customer QA Contact Email
            </label>
            <input
              type="email"
              value={formData.customer_email}
              onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

        </div>

        {/* Action Button */}
        <div className="pt-4 border-t flex justify-end">
          <button
            type="submit"
              disabled={generating || !templateMatch.matched || !file || !formData.requirement_id}
            className={`flex items-center space-x-2 font-bold px-7 py-3 rounded-lg shadow-lg transition ${
              generating || !templateMatch.matched || !file || !formData.requirement_id
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-700 hover:bg-blue-800 text-white'
            }`}
          >
            {generating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Generating {reportCount} PDI Reports for {formData.company_name}...</span>
              </>
            ) : (
              <>
                <span>Generate {reportCount} Reports ({formData.company_name} Format)</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>

      </form>

    </div>
  );
}
