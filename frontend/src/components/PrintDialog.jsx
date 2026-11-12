import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Printer, CheckCircle, AlertTriangle, Loader2, X } from 'lucide-react';

export default function PrintDialog({ isOpen, onClose, jobId, reportId, onPrintSuccess }) {
  const [printers, setPrinters] = useState([]);
  const [selectedPrinter, setSelectedPrinter] = useState('');
  const [loading, setLoading] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      setError('');
      setResult(null);
      api.getPrinters()
        .then((list) => {
          setPrinters(list);
          const def = list.find(p => p.is_default) || list[0];
          if (def) setSelectedPrinter(def.name);
        })
        .catch((err) => setError('Failed to detect Windows printers: ' + err.message))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handlePrint = async () => {
    setPrinting(true);
    setError('');
    try {
      const res = await api.printJob(jobId, selectedPrinter);
      setResult(res);
      if (onPrintSuccess) onPrintSuccess(res);
    } catch (err) {
      setError(err.message || 'Printing failed');
    } finally {
      setPrinting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl relative border">
        
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 text-gray-900 border-b pb-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-red-100 text-red-700 flex items-center justify-center">
            <Printer className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Windows Host Print Service</h3>
            <p className="text-xs text-gray-500">Send inspection reports directly to connected printer</p>
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
            <div className="p-4 bg-green-50 text-green-800 rounded-lg border border-green-200 text-sm space-y-1">
              <div className="flex items-center space-x-2 font-bold">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span>Reports printed successfully!</span>
              </div>
              <p className="text-xs text-green-700">
                Printed {result.success_count} report(s) on printer: <b>{selectedPrinter}</b>
              </p>
            </div>

            <div className="flex justify-end space-x-2">
              <button
                onClick={onClose}
                className="bg-gray-900 hover:bg-black text-white px-4 py-2 text-sm font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Select Connected Printer
              </label>
              {loading ? (
                <div className="text-xs text-gray-500 flex items-center space-x-2 p-2 border rounded">
                  <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                  <span>Scanning local Windows printer ports...</span>
                </div>
              ) : (
                <select
                  value={selectedPrinter}
                  onChange={(e) => setSelectedPrinter(e.target.value)}
                  className="w-full border rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-red-500 focus:outline-none"
                >
                  {printers.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name} {p.is_default ? '(Default)' : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg border">
              Reports will be queued in the Windows print spooler and dispatched to the hardware printer.
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePrint}
                disabled={printing || loading || !selectedPrinter}
                className="bg-red-600 hover:bg-red-700 text-white font-bold px-5 py-2 text-sm rounded-lg flex items-center space-x-2 shadow"
              >
                {printing && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{printing ? 'Sending to Printer...' : 'Confirm & Print'}</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
