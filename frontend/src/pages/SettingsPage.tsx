import { Settings as SettingsIcon, Save, HardDrive } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="p-6 h-full flex flex-col animate-in max-w-4xl mx-auto w-full">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">System Settings</h1>
          <p className="text-sm text-slate-500 mt-0.5">Configure scoring engine and storage preferences</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Save className="w-4 h-4" /> Save Changes
        </button>
      </div>

      <div className="space-y-6">
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-gold-400" /> AI Scoring Engine
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Confidence Threshold</label>
              <input type="range" min="0" max="100" defaultValue="60" className="w-full accent-gold-500" />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>0%</span>
                <span>Current: 60%</span>
                <span>100%</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Target Face Type</label>
              <select className="input-dark w-full">
                <option>WA 10-Ring (Default)</option>
                <option>WA 6-Ring</option>
                <option>Custom Indoor</option>
              </select>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-blue-400" /> Storage Management
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-navy-800/50 border border-navy-700 rounded-lg">
              <div>
                <p className="font-medium text-slate-200">Raw Images Retention</p>
                <p className="text-xs text-slate-500">Days to keep unannotated images</p>
              </div>
              <input type="number" defaultValue="90" className="input-dark w-24 text-right" />
            </div>
            <div className="flex items-center justify-between p-4 bg-navy-800/50 border border-navy-700 rounded-lg">
              <div>
                <p className="font-medium text-slate-200">Auto-delete old sessions</p>
                <p className="text-xs text-slate-500">Permanently remove sessions older than 1 year</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" />
                <div className="w-11 h-6 bg-navy-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gold-500"></div>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
