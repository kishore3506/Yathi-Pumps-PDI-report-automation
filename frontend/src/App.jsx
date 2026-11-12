import React, { useState } from 'react';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import NewInspectionPage from './pages/NewInspectionPage';
import ReportEditorPage from './pages/ReportEditorPage';
import TemplateManagementPage from './pages/TemplateManagementPage';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState(null);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <DashboardPage
            setActiveTab={setActiveTab}
            setSelectedJobId={setSelectedJobId}
            setSelectedReportId={setSelectedReportId}
          />
        )}

        {activeTab === 'new-inspection' && (
          <NewInspectionPage
            setActiveTab={setActiveTab}
            setSelectedJobId={setSelectedJobId}
          />
        )}

        {activeTab === 'job-review' && (
          <ReportEditorPage
            jobId={selectedJobId}
            setActiveTab={setActiveTab}
            setSelectedJobId={setSelectedJobId}
          />
        )}

        {activeTab === 'report-editor' && (
          <ReportEditorPage
            reportId={selectedReportId}
            setActiveTab={setActiveTab}
            setSelectedJobId={setSelectedJobId}
          />
        )}

        {activeTab === 'templates' && (
          <TemplateManagementPage />
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 py-4 mt-auto text-xs text-gray-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-gray-800">Yathi Pumps Pvt. Ltd.</span>
            <span>•</span>
            <span>PDI Automation System (Supported Clients: Havells, Crompton, KBS, KOEL)</span>
          </div>
          <div>
            Google Gemini API • openpyxl Engine • Host Windows Printer Service • n8n Webhook
          </div>
        </div>
      </footer>
    </div>
  );
}
