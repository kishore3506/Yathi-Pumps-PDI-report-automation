import React, { useState } from 'react';
import { api } from '../services/api';
import { Mail, CheckCircle2, AlertTriangle, Loader2, X, Paperclip, Send } from 'lucide-react';

export default function EmailDialog({ isOpen, onClose, job, onEmailSuccess }) {
  const [customerEmail, setCustomerEmail] = useState(job?.customer_email || '');
  const [customerName, setCustomerName] = useState(job?.customer_name || '');
  const [sending, setSending] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  if (!isOpen || !job) return null;

  const handleSendEmail = async () => {
    if (!customerEmail) {
      setError('Please provide a valid recipient email address.');
      return;
    }
    setSending(true);
    setError('');
    try {
      const res = await api.sendEmail({
        job_id: job.id,
        customer_email: customerEmail,
        customer_name: customerName,
        skip: false
      });
      setResult(res);
      if (onEmailSuccess) onEmailSuccess(res);
    } catch (err) {
      setError(err.message || 'Email delivery failed');
    } finally {
      setSending(false);
    }
  };

  const handleSkip = async () => {
    setSkipping(true);
    setError('');
    try {
      const res = await api.sendEmail({
        job_id: job.id,
        skip: true
      });
      setResult(res);
      if (onEmailSuccess) onEmailSuccess(res);
    } catch (err) {
      setError(err.message || 'Failed to update job status');
    } finally {
      setSkipping(false);
    }
  };

  const reportCount = job.reports?.length || job.total_reports || 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-2xl relative border">
        
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 text-gray-900 border-b pb-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-red-100 text-red-700 flex items-center justify-center">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Send PDI Reports to Customer</h3>
            <p className="text-xs text-gray-500">Automated dispatch via secured n8n workflow</p>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg mb-4 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-lg border text-sm space-y-1 ${
              result.status === 'Sent' 
                ? 'bg-green-50 text-green-800 border-green-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}>
              <div className="flex items-center space-x-2 font-bold">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <span>{result.status === 'Sent' ? 'Reports sent successfully to customer!' : 'Email step skipped.'}</span>
              </div>
              <p className="text-xs">
                {result.status === 'Sent'
                  ? `Delivered to ${result.customer_email}. Job status has been marked as Completed.`
                  : 'Job state updated. You can dispatch later from the dashboard.'}
              </p>
            </div>

            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="bg-gray-900 hover:bg-black text-white px-5 py-2 text-sm font-semibold rounded-lg"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-700 font-medium">
              Would you like to send the official approved PDI reports to the customer now?
            </p>

            <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
                  Customer / Recipient Name
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Customer Contact / Company"
                  className="w-full border rounded-lg p-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
                  Customer Email *
                </label>
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  placeholder="customer@domain.com"
                  className="w-full border rounded-lg p-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>

              <div className="pt-2 border-t flex items-center justify-between text-xs text-gray-600">
                <span className="flex items-center space-x-1">
                  <Paperclip className="w-4 h-4 text-gray-400" />
                  <span>Attachments: <b>{reportCount} PDI Report(s)</b> (Excel & PDF copies)</span>
                </span>
                <span className="font-mono text-gray-500">{job.job_code}</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={handleSkip}
                disabled={sending || skipping}
                className="text-gray-500 hover:text-gray-700 text-sm font-semibold px-4 py-2 hover:bg-gray-100 rounded-lg"
              >
                {skipping ? 'Skipping...' : 'Skip for Now'}
              </button>

              <button
                type="button"
                onClick={handleSendEmail}
                disabled={sending || skipping}
                className="bg-red-600 hover:bg-red-700 text-white font-bold px-6 py-2.5 text-sm rounded-lg flex items-center space-x-2 shadow"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>{sending ? 'Triggering n8n Workflow...' : 'Send Email'}</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
