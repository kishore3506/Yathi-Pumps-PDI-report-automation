const API_BASE = '/api';

export const api = {
  // Health
  checkHealth: async () => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Dashboard
  getDashboardStats: async () => {
    const res = await fetch(`${API_BASE}/dashboard/stats`);
    return res.json();
  },

  // Requirements & Extraction
  uploadRequirement: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/requirements/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  extractDetails: async (data) => {
    const formData = new FormData();
    if (data.requirement_id) formData.append('requirement_id', data.requirement_id);
    if (data.company_name) formData.append('company_name', data.company_name);
    if (data.product_type) formData.append('product_type', data.product_type);
    if (data.product_number) formData.append('product_number', data.product_number);
    if (data.lot_size) formData.append('lot_size', data.lot_size);
    if (data.customer_name) formData.append('customer_name', data.customer_name);
    if (data.customer_email) formData.append('customer_email', data.customer_email);

    const res = await fetch(`${API_BASE}/requirements/extract`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Extraction failed');
    }
    return res.json();
  },

  // Templates
  getTemplates: async () => {
    const res = await fetch(`${API_BASE}/templates`);
    return res.json();
  },

  uploadTemplate: async (formData) => {
    const res = await fetch(`${API_BASE}/templates/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Template upload failed');
    }
    return res.json();
  },

  matchTemplate: async (payload) => {
    const res = await fetch(`${API_BASE}/templates/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  getTemplateMappings: async (templateId) => {
    const res = await fetch(`${API_BASE}/templates/${templateId}/mappings`);
    return res.json();
  },

  // Reports
  generateReports: async (payload) => {
    const res = await fetch(`${API_BASE}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Report generation failed');
    }
    return res.json();
  },

  getJobs: async () => {
    const res = await fetch(`${API_BASE}/reports`);
    return res.json();
  },

  getJobDetails: async (jobId) => {
    const res = await fetch(`${API_BASE}/reports/jobs/${jobId}`);
    if (!res.ok) throw new Error('Job not found');
    return res.json();
  },

  getReport: async (reportId) => {
    const res = await fetch(`${API_BASE}/reports/${reportId}`);
    if (!res.ok) throw new Error('Report not found');
    return res.json();
  },

  updateReport: async (reportId, payload) => {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update report');
    }
    return res.json();
  },

  approveReport: async (reportId) => {
    const res = await fetch(`${API_BASE}/reports/${reportId}/approve`, {
      method: 'POST',
    });
    return res.json();
  },

  // Printing & Printers
  getPrinters: async () => {
    const res = await fetch(`${API_BASE}/reports/printers/list`);
    return res.json();
  },

  printJob: async (jobId, printerName = null) => {
    const res = await fetch(`${API_BASE}/reports/jobs/${jobId}/print`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, printer_name: printerName }),
    });
    return res.json();
  },

  // Email
  sendEmail: async (payload) => {
    const res = await fetch(`${API_BASE}/reports/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },

  // Download URLs
  getExcelDownloadUrl: (reportId) => `${API_BASE}/reports/${reportId}/download/excel`,
  getPdfDownloadUrl: (reportId) => `${API_BASE}/reports/${reportId}/download/pdf`,
  getZipDownloadUrl: (jobId) => `${API_BASE}/reports/jobs/${jobId}/download/zip`,
};
