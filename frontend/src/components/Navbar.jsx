import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { 
  FileSpreadsheet, 
  PlusCircle, 
  Layers, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle,
  LayoutDashboard,
  Gauge
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'offline' }));
  }, []);

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          
          {/* Brand Logo & Title */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-10 h-10 rounded-lg bg-blue-700 flex items-center justify-center text-white font-black text-xl shadow-md tracking-wider">
              Y
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-gray-900 text-lg tracking-tight">YATHI PUMPS</span>
                <span className="text-xs bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded">PDI AUTOMATION</span>
              </div>
              <p className="text-xs text-gray-500">OEM Clients: Havells • Crompton • KBS • KOEL</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex space-x-1 sm:space-x-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('new-inspection')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'new-inspection'
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Inspection</span>
            </button>

            <button
              onClick={() => setActiveTab('templates')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'templates'
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Client Templates</span>
            </button>
          </nav>

          {/* Gemini API Status Pill */}
          <div className="hidden md:flex items-center space-x-2 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-full text-xs">
            <Cpu className="w-3.5 h-3.5 text-gray-500" />
            <span className="text-gray-600 font-medium">Gemini AI:</span>
            {health?.gemini?.status === 'connected' ? (
              <span className="inline-flex items-center text-green-700 font-semibold">
                <span className="w-2 h-2 rounded-full bg-green-500 mr-1.5 animate-pulse"></span>
                {health.gemini.active_model}
              </span>
            ) : (
              <span className="inline-flex items-center text-amber-600 font-medium">
                <span className="w-2 h-2 rounded-full bg-amber-400 mr-1.5"></span>
                {health?.gemini?.status === 'not_configured' ? 'API key needed' : 'Unavailable'}
              </span>
            )}
          </div>

        </div>
      </div>
    </header>
  );
}
