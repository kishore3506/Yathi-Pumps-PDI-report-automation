import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { 
  FileSpreadsheet, 
  CheckCircle, 
  Clock, 
  Printer, 
  Mail, 
  ArrowRight, 
  Plus, 
  Download, 
  RefreshCw,
  Search,
  AlertCircle,
  Building2
} from 'lucide-react';

export default function DashboardPage({ setActiveTab, setSelectedJobId, setSelectedReportId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCustomerFilter, setSelectedCustomerFilter] = useState('ALL');

  const loadStats = () => {
    setLoading(true);
    api.getDashboardStats()
      .then(setStats)
      .catch((err) => console.error('Error fetching dashboard stats:', err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStats();
  }, []);

  const getStatusBadge = (status) => {
    const map = {
      'Completed': 'bg-green-100 text-green-800 border-green-200',
      'Approved': 'bg-blue-100 text-blue-800 border-blue-200',
      'Printed': 'bg-indigo-100 text-indigo-800 border-indigo-200',
      'Emailed': 'bg-purple-100 text-purple-800 border-purple-200',
      'Awaiting Review': 'bg-amber-100 text-amber-800 border-amber-200',
      'Awaiting Printing': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'Generating': 'bg-sky-100 text-sky-800 border-sky-200',
      'Failed': 'bg-red-100 text-red-800 border-red-200'
    };
    const cls = map[status] || 'bg-gray-100 text-gray-800 border-gray-200';
    return (
      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${cls}`}>
        {status}
      </span>
    );
  };

  const getCustomerBadge = (companyName) => {
    const map = {
      'Havells': 'bg-red-50 text-red-700 border-red-200',
      'Crompton': 'bg-blue-50 text-blue-700 border-blue-200',
      'KBS': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'KOEL': 'bg-amber-50 text-amber-700 border-amber-200',
    };
    const cls = map[companyName] || 'bg-gray-50 text-gray-700 border-gray-200';
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-bold border ${cls}`}>
        {companyName}
      </span>
    );
  };

  const filteredJobs = stats?.recent_jobs?.filter(j => {
    const matchesSearch = 
      j.job_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.product_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.product_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.customer_name?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCustomer = 
      selectedCustomerFilter === 'ALL' || 
      j.company_name?.toLowerCase() === selectedCustomerFilter.toLowerCase();

    return matchesSearch && matchesCustomer;
  }) || [];

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-blue-800 to-indigo-900 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-extrabold bg-blue-500/40 text-blue-100 px-2.5 py-0.5 rounded uppercase tracking-wider">
              Yathi Pumps Manufacturing QA
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight mt-1">Yathi Pumps PDI Operations Dashboard</h1>
          <p className="text-blue-100 text-sm mt-1">
            Automated Pre-Dispatch Inspection report generation & verification for OEM Customers: <b>Havells</b>, <b>Crompton</b>, <b>KBS</b>, and <b>KOEL</b>.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={loadStats}
            className="p-2.5 bg-blue-800/80 hover:bg-blue-700 rounded-lg text-white border border-blue-500/40 transition"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setActiveTab('new-inspection')}
            className="flex items-center space-x-2 bg-white text-blue-900 font-bold px-4 py-2.5 rounded-lg shadow hover:bg-blue-50 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Generate PDI Reports</span>
          </button>
        </div>
      </div>

      {/* 5 Top Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Reports Generated</span>
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats?.total_reports_generated ?? 0}</div>
          <p className="text-xs text-gray-400 mt-1">Editable Excel copies</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Completed Jobs</span>
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats?.completed_jobs ?? 0}</div>
          <p className="text-xs text-gray-400 mt-1">Inspected, printed & sent</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Review</span>
            <Clock className="w-5 h-5 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats?.awaiting_review ?? 0}</div>
          <p className="text-xs text-gray-400 mt-1">Pending QA sign-off</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Printing</span>
            <Printer className="w-5 h-5 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats?.awaiting_printing ?? 0}</div>
          <p className="text-xs text-gray-400 mt-1">Windows printer spool</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Email</span>
            <Mail className="w-5 h-5 text-purple-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{stats?.awaiting_email ?? 0}</div>
          <p className="text-xs text-gray-400 mt-1">n8n customer delivery</p>
        </div>

      </div>

      {/* Customer OEM Filter Buttons */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1">
        <span className="text-xs font-bold text-gray-500 uppercase mr-2 flex items-center space-x-1">
          <Building2 className="w-3.5 h-3.5" />
          <span>Filter Customer:</span>
        </span>
        {['ALL', 'Havells', 'Crompton', 'KBS', 'KOEL'].map((cust) => (
          <button
            key={cust}
            onClick={() => setSelectedCustomerFilter(cust)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              selectedCustomerFilter === cust
                ? 'bg-blue-700 text-white shadow'
                : 'bg-white border text-gray-600 hover:bg-gray-100'
            }`}
          >
            {cust === 'ALL' ? 'All Customers' : cust}
          </button>
        ))}
      </div>

      {/* Recent Activity Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Recent Inspection Jobs</h2>
            <p className="text-xs text-gray-500">Track and review batch reports generated across OEM customer templates</p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search job, SKU, PO..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-3 px-4">Job Code</th>
                <th className="py-3 px-4">Customer OEM</th>
                <th className="py-3 px-4">Model & SKU</th>
                <th className="py-3 px-4 text-center">Lot Size</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-center">Progress</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-gray-400">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    No inspection jobs found. Click "Generate PDI Reports" to start!
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50 transition">
                    <td className="py-3.5 px-4 font-mono font-medium text-gray-800">
                      {job.job_code}
                    </td>
                    <td className="py-3.5 px-4">
                      {getCustomerBadge(job.company_name)}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-gray-900">{job.product_type}</div>
                      <div className="text-xs text-gray-500">
                        SKU: <span className="font-mono text-gray-700 font-medium">{job.product_number}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-center font-bold text-gray-800">
                      {job.lot_size} Units
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {getStatusBadge(job.status)}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <div className="flex items-center justify-center space-x-2 text-xs text-gray-500">
                        <span title="Approved" className="text-green-700 font-semibold">{job.approved_reports}/{job.total_reports} App</span>
                        <span>•</span>
                        <span title="Printed" className="text-indigo-700 font-semibold">{job.printed_reports} Prn</span>
                        <span>•</span>
                        <span title="Emailed" className="text-purple-700 font-semibold">{job.emailed_reports} Eml</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <a
                          href={api.getZipDownloadUrl(job.id)}
                          download
                          className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded"
                          title="Download All Reports (ZIP)"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          onClick={() => {
                            setSelectedJobId(job.id);
                            setActiveTab('job-review');
                          }}
                          className="flex items-center space-x-1 text-xs font-semibold bg-blue-700 hover:bg-blue-800 text-white px-3 py-1.5 rounded transition shadow-sm"
                        >
                          <span>Review</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
