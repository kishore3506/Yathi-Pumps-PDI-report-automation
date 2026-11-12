import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import PrintDialog from '../components/PrintDialog';
import EmailDialog from '../components/EmailDialog';
import { 
  FileSpreadsheet, 
  Download, 
  Printer, 
  Mail, 
  CheckCircle, 
  Save, 
  ArrowLeft, 
  FileText, 
  ShieldCheck, 
  AlertCircle,
  ExternalLink,
  Loader2,
  RefreshCw
} from 'lucide-react';

export default function ReportEditorPage({ jobId, reportId, setActiveTab, setSelectedJobId }) {
  const [job, setJob] = useState(null);
  const [currentReport, setCurrentReport] = useState(null);
  const [activeUnitIndex, setActiveUnitIndex] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Dialog states
  const [isPrintOpen, setIsPrintOpen] = useState(false);
  const [isEmailOpen, setIsEmailOpen] = useState(false);

  // Editable fields in current report
  const [editHeader, setEditHeader] = useState({});
  const [editObservations, setEditObservations] = useState({});
  const [finalJudgment, setFinalJudgment] = useState('OK');
  const [rejectReason, setRejectReason] = useState('');

  // Load job and report details
  const loadJobData = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      if (jobId) {
        const j = await api.getJobDetails(jobId);
        setJob(j);
        if (j.reports && j.reports.length > 0) {
          const rep = j.reports.find(r => r.unit_index === activeUnitIndex) || j.reports[0];
          initReportForm(rep);
        }
      } else if (reportId) {
        const rep = await api.getReport(reportId);
        initReportForm(rep);
        if (rep.job_id) {
          const j = await api.getJobDetails(rep.job_id);
          setJob(j);
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load report details');
    } finally {
      setLoading(false);
    }
  };

  const initReportForm = (rep) => {
    setCurrentReport(rep);
    setActiveUnitIndex(rep.unit_index || 1);
    const rData = rep.report_data || {};
    const hdr = rData.header_data || {};
    setEditHeader({
      supplier_name: hdr.supplier_name || '',
      supplier_location: hdr.supplier_location || '',
      sku_no: hdr.sku_no || '',
      model_name: hdr.model_name || '',
      po_number: hdr.po_number || '',
      lot_qty: hdr.lot_qty || '',
      po_total_qty: hdr.po_total_qty || '',
      inspected_by: hdr.inspected_by || 'Yathi QA Inspector',
      approved_by: hdr.approved_by || 'Quality Head',
      inspection_date: hdr.inspection_date || '',
      lot_dispatch_date: hdr.lot_dispatch_date || '',
    });
    setFinalJudgment(hdr.judgment_reject ? 'Reject' : 'OK');
    setRejectReason(hdr.reject_reason || '');

    // Initialize observations
    const obsMap = {};
    (rData.checkpoints || []).forEach(cp => {
      obsMap[cp.row_index] = { ...cp.observations };
    });
    setEditObservations(obsMap);
  };

  useEffect(() => {
    loadJobData();
  }, [jobId, reportId, activeUnitIndex]);

  // Handle single observation change
  const handleObservationChange = (rowIndex, col, value) => {
    setEditObservations(prev => ({
      ...prev,
      [rowIndex]: {
        ...(prev[rowIndex] || {}),
        [col]: value
      }
    }));
  };

  // Save changes
  const handleSaveChanges = async () => {
    if (!currentReport) return;
    setSaving(true);
    setErrorMsg('');
    setSaveSuccess(false);

    try {
      const payload = {
        header_data: editHeader,
        observation_readings: editObservations,
        final_judgment: finalJudgment,
        reject_reason: rejectReason
      };

      const res = await api.updateReport(currentReport.id, payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      
      // Update local state with fresh report data
      setCurrentReport(prev => ({ ...prev, report_data: res.report_data }));
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  // Approve report
  const handleApprove = async () => {
    if (!currentReport) return;
    try {
      await api.approveReport(currentReport.id);
      loadJobData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to approve report');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin" />
        <span className="text-sm text-gray-500 font-medium">Loading inspection report workbook...</span>
      </div>
    );
  }

  const reportsList = job?.reports || (currentReport ? [currentReport] : []);
  const checkpoints = currentReport?.report_data?.checkpoints || [];

  return (
    <div className="space-y-6">
      
      {/* Top Breadcrumb & Job Header */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setActiveTab('dashboard')}
              className="p-2 border rounded-lg hover:bg-gray-100 text-gray-600 transition"
              title="Back to Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs bg-gray-100 text-gray-700 font-bold px-2 py-0.5 rounded">
                  {job?.job_code || currentReport?.report_code}
                </span>
                <span className="text-xs bg-blue-100 text-blue-800 font-extrabold px-2 py-0.5 rounded">
                  {job?.company_name ? `${job.company_name.toUpperCase()} OEM FORMAT` : 'CUSTOMER OEM FORMAT'}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  {job?.status || currentReport?.status}
                </span>
              </div>
              <h1 className="text-xl font-bold text-gray-900 mt-1">
                {job?.product_type || 'Surface Pump'} — {reportsList.length} Individual Report(s)
              </h1>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            {job && (
              <a
                href={api.getZipDownloadUrl(job.id)}
                download
                className="flex items-center space-x-1.5 text-xs font-semibold bg-gray-100 text-gray-700 hover:bg-gray-200 px-3 py-2 rounded-lg border transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download All (ZIP)</span>
              </a>
            )}

            {currentReport && (
              <>
                <a
                  href={api.getExcelDownloadUrl(currentReport.id)}
                  download
                  className="flex items-center space-x-1.5 text-xs font-semibold bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 px-3 py-2 rounded-lg transition"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Excel</span>
                </a>

                <a
                  href={api.getPdfDownloadUrl(currentReport.id)}
                  download
                  className="flex items-center space-x-1.5 text-xs font-semibold bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 px-3 py-2 rounded-lg transition"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>PDF</span>
                </a>
              </>
            )}

            <button
              onClick={() => setIsPrintOpen(true)}
              className="flex items-center space-x-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded-lg shadow transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Reports</span>
            </button>

            <button
              onClick={() => setIsEmailOpen(true)}
              className="flex items-center space-x-1.5 text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded-lg shadow transition"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>Send Email</span>
            </button>
          </div>
        </div>

        {/* Individual Lot Unit Tabs */}
        {reportsList.length > 1 && (
          <div className="pt-3 border-t flex items-center space-x-2 overflow-x-auto pb-1">
            <span className="text-xs font-bold text-gray-500 uppercase mr-1">Lot Units:</span>
            {reportsList.map((r) => (
              <button
                key={r.id}
                onClick={() => {
                  setActiveUnitIndex(r.unit_index);
                  initReportForm(r);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition shrink-0 ${
                  r.unit_index === activeUnitIndex
                    ? 'bg-red-600 text-white shadow'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Unit #{r.unit_index} ({r.report_code})
              </button>
            ))}
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 text-red-800 text-sm rounded-xl border border-red-200 flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {saveSuccess && (
        <div className="p-4 bg-green-50 text-green-800 text-sm rounded-xl border border-green-200 flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 shrink-0 text-green-600" />
          <span>Report modifications saved directly into the editable Excel workbook!</span>
        </div>
      )}

      {/* Excel Sheet Simulator & Editor */}
      <div className="bg-white rounded-xl border border-gray-300 shadow-sm overflow-hidden">
        
        {/* Sheet Top Banner mimicking official Havells sheet header */}
        <div className="bg-gray-100 p-4 border-b border-gray-300 flex flex-col md:flex-row md:items-center justify-between text-xs gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-red-600 text-white font-bold flex items-center justify-center text-sm shadow">
              H
            </div>
            <div>
              <div className="font-extrabold text-gray-900 text-sm">Pump - Pre-dispatch Inspection Report (MMB,CMB,SW,PB)</div>
              <div className="text-gray-500">Doc. No. : HIL/PDI/Surface Pump /01, Date : 01-06-2023 | Sheet: Surface Pump</div>
            </div>
          </div>
          <div className="flex items-center space-x-3 font-semibold text-gray-700">
            <span>Status: <b>{currentReport?.status}</b></span>
            <span>•</span>
            <span>Unit: <b>#{currentReport?.unit_index} of {reportsList.length}</b></span>
          </div>
        </div>

        {/* Permitted Header Fields Grid */}
        <div className="p-5 border-b border-gray-200 bg-gray-50/50">
          <div className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
            Inspection Metadata & Header Parameters
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-xs">
            
            <div>
              <label className="text-gray-500 font-medium">Supplier Code / Name (C3)</label>
              <input
                type="text"
                value={editHeader.supplier_name}
                onChange={(e) => setEditHeader({ ...editHeader, supplier_name: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">Supplier Location (F3)</label>
              <input
                type="text"
                value={editHeader.supplier_location}
                onChange={(e) => setEditHeader({ ...editHeader, supplier_location: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">SKU No. (C4)</label>
              <input
                type="text"
                value={editHeader.sku_no}
                onChange={(e) => setEditHeader({ ...editHeader, sku_no: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">Model Name (D4)</label>
              <input
                type="text"
                value={editHeader.model_name}
                onChange={(e) => setEditHeader({ ...editHeader, model_name: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">PO Number (C5)</label>
              <input
                type="text"
                value={editHeader.po_number}
                onChange={(e) => setEditHeader({ ...editHeader, po_number: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">Lot Qty (D5)</label>
              <input
                type="number"
                value={editHeader.lot_qty}
                onChange={(e) => setEditHeader({ ...editHeader, lot_qty: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs font-bold text-red-700 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">Inspected By (D6)</label>
              <input
                type="text"
                value={editHeader.inspected_by}
                onChange={(e) => setEditHeader({ ...editHeader, inspected_by: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            <div>
              <label className="text-gray-500 font-medium">Approved By (D7)</label>
              <input
                type="text"
                value={editHeader.approved_by}
                onChange={(e) => setEditHeader({ ...editHeader, approved_by: e.target.value })}
                className="mt-1 w-full border rounded p-1.5 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>

            {/* Final Judgment Radios */}
            <div className="col-span-2 flex items-center space-x-6 p-2 rounded border bg-white">
              <span className="font-bold text-gray-700">Final Judgment (E5/F5):</span>
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="judgment"
                  value="OK"
                  checked={finalJudgment === 'OK'}
                  onChange={() => setFinalJudgment('OK')}
                  className="text-green-600 focus:ring-green-500"
                />
                <span className="font-bold text-green-700">PASS / OK [✔]</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="judgment"
                  value="Reject"
                  checked={finalJudgment === 'Reject'}
                  onChange={() => setFinalJudgment('Reject')}
                  className="text-red-600 focus:ring-red-500"
                />
                <span className="font-bold text-red-700">REJECT [✔]</span>
              </label>
            </div>

            {finalJudgment === 'Reject' && (
              <div className="col-span-2">
                <label className="text-red-600 font-bold">Reject Reason (E6/F6)</label>
                <input
                  type="text"
                  required
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Specify root cause / defect..."
                  className="mt-1 w-full border border-red-300 rounded p-1.5 bg-red-50/50 text-xs text-red-900"
                />
              </div>
            )}

          </div>
        </div>

        {/* Observation Table mimicking Excel grid */}
        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="sticky top-0 bg-gray-800 text-white z-10">
              <tr>
                <th className="py-2.5 px-3 border border-gray-700 text-center w-12">S.N.</th>
                <th className="py-2.5 px-3 border border-gray-700 w-36">Inspection Type</th>
                <th className="py-2.5 px-3 border border-gray-700 w-48">Parameter</th>
                <th className="py-2.5 px-3 border border-gray-700 w-64">Specification</th>
                <th className="py-2.5 px-3 border border-gray-700 w-28">Method</th>
                <th className="py-2.5 px-3 border border-gray-700 w-28">Frequency</th>
                <th className="py-2.5 px-3 border border-gray-700 bg-red-950/70 text-center">
                  Observation / Readings (Col G .. K)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {checkpoints.map((cp) => {
                const obs = editObservations[cp.row_index] || cp.observations || {};
                const isMulti = cp.is_multi_sample;

                return (
                  <tr key={cp.row_index} className="hover:bg-amber-50/30 transition">
                    <td className="py-2 px-3 border border-gray-200 text-center font-bold text-gray-600 bg-gray-50/50">
                      {cp.item_sn}
                    </td>
                    <td className="py-2 px-3 border border-gray-200 font-semibold text-gray-700 bg-gray-50/30">
                      {cp.inspection_type}
                    </td>
                    <td className="py-2 px-3 border border-gray-200 font-medium text-gray-900">
                      {cp.parameter}
                    </td>
                    <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">
                      {cp.specification}
                    </td>
                    <td className="py-2 px-3 border border-gray-200 text-gray-500 text-[11px]">
                      {cp.method}
                    </td>
                    <td className="py-2 px-3 border border-gray-200 text-gray-500 text-[11px]">
                      {cp.frequency}
                    </td>
                    
                    {/* Observation input(s) */}
                    <td className="py-1 px-2 border border-gray-200 bg-white">
                      {isMulti ? (
                        <div className="grid grid-cols-5 gap-1">
                          {['G', 'H', 'I', 'J', 'K'].map((colKey, sIdx) => (
                            <input
                              key={colKey}
                              type="text"
                              value={obs[colKey] || ''}
                              onChange={(e) => handleObservationChange(cp.row_index, colKey, e.target.value)}
                              title={`Sample #${sIdx + 1} (Col ${colKey})`}
                              placeholder={`S${sIdx + 1}`}
                              className="w-full text-[11px] p-1 border rounded bg-gray-50/50 text-center focus:bg-white focus:outline-none focus:ring-1 focus:ring-red-500 font-mono"
                            />
                          ))}
                        </div>
                      ) : (
                        <input
                          type="text"
                          value={obs['G'] || ''}
                          onChange={(e) => handleObservationChange(cp.row_index, 'G', e.target.value)}
                          className="w-full text-xs p-1.5 border rounded bg-gray-50/40 focus:bg-white focus:outline-none focus:ring-1 focus:ring-red-500 font-medium"
                        />
                      )}
                    </td>

                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Bottom Save & Approve Bar */}
        <div className="p-4 bg-gray-50 border-t border-gray-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="text-xs text-gray-500">
            Note: Fixed inspection criteria and company-defined standards cannot be modified. All edits are validated against IS tolerances.
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleSaveChanges}
              disabled={saving}
              className="flex items-center space-x-1.5 bg-gray-900 hover:bg-black text-white px-5 py-2 rounded-lg text-xs font-bold transition shadow"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>{saving ? 'Updating Excel...' : 'Save Changes'}</span>
            </button>

            <button
              onClick={handleApprove}
              className="flex items-center space-x-1.5 bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg text-xs font-bold transition shadow"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Approve Report</span>
            </button>
          </div>
        </div>

      </div>

      {/* Host Print Dialog */}
      <PrintDialog
        isOpen={isPrintOpen}
        onClose={() => setIsPrintOpen(false)}
        jobId={job?.id}
        reportId={currentReport?.id}
        onPrintSuccess={() => {
          setIsPrintOpen(false);
          setIsEmailOpen(true); // Requirement 10: After successful printing, prompt email dialog!
          loadJobData();
        }}
      />

      {/* Customer Email Dialog */}
      <EmailDialog
        isOpen={isEmailOpen}
        onClose={() => setIsEmailOpen(false)}
        job={job}
        onEmailSuccess={() => {
          setIsEmailOpen(false);
          loadJobData();
        }}
      />

    </div>
  );
}
