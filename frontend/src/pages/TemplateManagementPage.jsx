import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  Layers, 
  Upload, 
  FileSpreadsheet, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Settings, 
  Calendar,
  FileCheck
} from 'lucide-react';

export default function TemplateManagementPage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Upload modal form fields
  const [companyName, setCompanyName] = useState('Havells');
  const [productType, setProductType] = useState('');
  const [productModel, setProductModel] = useState('');
  const [templateFile, setTemplateFile] = useState(null);

  const loadTemplates = () => {
    setLoading(true);
    api.getTemplates()
      .then(setTemplates)
      .catch((err) => setErrorMsg('Failed to load templates: ' + err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!templateFile) {
      setErrorMsg('Please select an Excel (.xlsx) template file.');
      return;
    }

    setUploading(true);
    setErrorMsg('');
    setStatusMsg('');

    try {
      const formData = new FormData();
      formData.append('file', templateFile);
      formData.append('company_name', companyName);
      formData.append('product_type', productType);
      if (productModel) formData.append('product_model', productModel);

      await api.uploadTemplate(formData);
      setStatusMsg(`Template '${templateFile.name}' registered successfully!`);
      setShowUploadModal(false);
      setTemplateFile(null);
      setProductType('');
      setProductModel('');
      loadTemplates();
    } catch (err) {
      setErrorMsg(err.message || 'Template upload failed');
    } finally {
      setUploading(false);
    }
  };

  const viewMappings = async (template) => {
    setSelectedTemplate(template);
    try {
      const maps = await api.getTemplateMappings(template.id);
      setMappings(maps);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">PDI Template Management</h1>
          <p className="text-sm text-gray-500 mt-1">
            Register and manage company-specific PDI Excel templates with deterministic field mapping rules.
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white font-bold px-4 py-2.5 rounded-lg shadow transition text-sm"
        >
          <Upload className="w-4 h-4" />
          <span>Register New Template</span>
        </button>
      </div>

      {statusMsg && (
        <div className="p-4 bg-green-50 text-green-800 text-sm rounded-lg border border-green-200 flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 shrink-0 text-green-600" />
          <span>{statusMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-red-50 text-red-800 text-sm rounded-lg border border-red-200 flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Templates Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-gray-200">
          <h2 className="text-base font-bold text-gray-800">Registered Inspection Templates</h2>
          <p className="text-xs text-gray-500">Only verified Havells template files are used for automated population.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Product Type</th>
                <th className="py-3 px-4">Model / Category</th>
                <th className="py-3 px-4">Template File</th>
                <th className="py-3 px-4">Sheets</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Field Mappings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-gray-400">
                    <Loader2 className="w-6 h-6 mx-auto animate-spin mb-2 text-red-600" />
                    Loading registered templates...
                  </td>
                </tr>
              ) : templates.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-gray-400">
                    No templates registered. Click "Register New Template" to upload one.
                  </td>
                </tr>
              ) : (
                templates.map((tpl) => (
                  <tr key={tpl.id} className="hover:bg-gray-50 transition">
                    <td className="py-3.5 px-4 font-bold text-red-700">
                      {tpl.company_name}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-gray-900">
                      {tpl.product_type}
                    </td>
                    <td className="py-3.5 px-4 text-gray-600 text-xs">
                      {tpl.product_model || 'Standard'}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-1.5 text-xs text-gray-700 font-mono">
                        <FileSpreadsheet className="w-4 h-4 text-green-600 shrink-0" />
                        <span className="truncate max-w-[200px]" title={tpl.template_name}>
                          {tpl.template_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-gray-500">
                      <span className="bg-gray-100 px-2 py-0.5 rounded font-mono">
                        {Array.isArray(tpl.sheet_names) ? tpl.sheet_names.length : 1} sheets
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                        Active
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => viewMappings(tpl)}
                        className="text-xs font-semibold text-gray-700 hover:text-red-600 hover:bg-gray-100 px-3 py-1.5 rounded border transition"
                      >
                        Inspect Mappings
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Field Mappings Viewer Modal / Drawer */}
      {selectedTemplate && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <div>
              <h3 className="text-base font-bold text-gray-900 flex items-center space-x-2">
                <Settings className="w-4 h-4 text-red-600" />
                <span>Field Mappings: {selectedTemplate.template_name} ({selectedTemplate.product_type})</span>
              </h3>
              <p className="text-xs text-gray-500">Deterministic coordinate cells mapped for automated Excel population</p>
            </div>
            <button
              onClick={() => setSelectedTemplate(null)}
              className="text-xs font-semibold text-gray-500 hover:text-gray-800"
            >
              Close Viewer
            </button>
          </div>

          <div className="overflow-x-auto max-h-[350px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-gray-100 text-gray-600">
                <tr>
                  <th className="py-2 px-3 border">Field Key</th>
                  <th className="py-2 px-3 border">Report Label</th>
                  <th className="py-2 px-3 border">Target Sheet</th>
                  <th className="py-2 px-3 border">Target Cell</th>
                  <th className="py-2 px-3 border">Transformation / Prefix Rule</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="py-2 px-3 font-mono font-bold text-gray-800">{m.field_key}</td>
                    <td className="py-2 px-3 text-gray-700">{m.field_label}</td>
                    <td className="py-2 px-3 text-gray-500">{m.target_sheet}</td>
                    <td className="py-2 px-3 font-mono font-bold text-red-700 bg-red-50/40 text-center">{m.target_cell}</td>
                    <td className="py-2 px-3 font-mono text-gray-500">{m.validation_rule || 'Direct Value'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Template Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-2xl relative border">
            <h3 className="font-bold text-lg text-gray-900 mb-1">Register New PDI Excel Template</h3>
            <p className="text-xs text-gray-500 mb-4">
              Upload an existing Havells template file. The system will inspect sheets and generate mappings.
            </p>

            <form onSubmit={handleUploadSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-gray-700 mb-1">Company Name *</label>
                <input
                  type="text"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full border rounded p-2 text-sm focus:ring-1 focus:ring-red-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Product Type *</label>
                <input
                  type="text"
                  required
                  value={productType}
                  onChange={(e) => setProductType(e.target.value)}
                  placeholder="e.g. Industrial Fan, Water Heater, Switchgear"
                  className="w-full border rounded p-2 text-sm focus:ring-1 focus:ring-red-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Model / Category (Optional)</label>
                <input
                  type="text"
                  value={productModel}
                  onChange={(e) => setProductModel(e.target.value)}
                  placeholder="e.g. HV-FAN-101 Series"
                  className="w-full border rounded p-2 text-sm focus:ring-1 focus:ring-red-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Excel Template File (.xlsx) *</label>
                <input
                  type="file"
                  required
                  accept=".xlsx,.xlsm"
                  onChange={(e) => setTemplateFile(e.target.files[0])}
                  className="w-full border rounded p-2 text-xs"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50 text-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="bg-red-600 hover:bg-red-700 text-white font-bold px-5 py-2 rounded-lg flex items-center space-x-1"
                >
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  <span>{uploading ? 'Registering...' : 'Register Template'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
