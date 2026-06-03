import { useEffect, useState } from 'react'
import { getStats, getHistory } from '../api'

export default function Dashboard() {
  const [stats, setStats]     = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    getStats().then(r => setStats(r.data)).catch(() => {})
    getHistory().then(r => setHistory(r.data.checks)).catch(() => {})
  }, [])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">📊 Dashboard</h1>

      {stats ? (
        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { label: 'Total Checks', value: stats.total_checks, color: 'text-blue-400' },
            { label: 'Completed', value: stats.completed, color: 'text-green-400' },
            { label: 'Compliant', value: stats.compliant, color: 'text-green-400' },
            { label: 'Non-Compliant', value: stats.non_compliant, color: 'text-red-400' },
            { label: 'Compliance Rate', value: stats.compliance_rate, color: 'text-yellow-400' },
          ].map(m => (
            <div key={m.label} className="bg-slate-800 rounded-xl p-5 text-center border border-slate-700">
              <div className={`text-3xl font-bold ${m.color}`}>{m.value}</div>
              <div className="text-slate-400 text-sm mt-1">{m.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-slate-400 mb-8">Loading stats...</p>
      )}

      <h2 className="text-lg font-semibold text-slate-300 mb-4">Recent Checks</h2>
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-slate-300">Check ID</th>
              <th className="text-left px-4 py-3 text-slate-300">Status</th>
              <th className="text-left px-4 py-3 text-slate-300">Created</th>
              <th className="text-left px-4 py-3 text-slate-300">Completed</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h, i) => (
              <tr key={i} className="border-t border-slate-700 hover:bg-slate-750">
                <td className="px-4 py-3 text-blue-400 font-mono">{h.check_id}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    h.status === 'completed' ? 'bg-green-900 text-green-400' : 'bg-yellow-900 text-yellow-400'
                  }`}>{h.status}</span>
                </td>
                <td className="px-4 py-3 text-slate-400">{h.created_at?.slice(0, 19)}</td>
                <td className="px-4 py-3 text-slate-400">{h.completed_at?.slice(0, 19) || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}