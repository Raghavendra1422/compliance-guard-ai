import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import CheckCompliance from './pages/CheckCompliance'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import { ResultProvider } from './context/ResultContext'

export default function App() {
  return (
    <ResultProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-900 flex">

          {/* Sidebar */}
          <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
            <div className="p-5 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-xl">🏦</div>
                <div>
                  <div className="text-white font-bold text-sm">Compliance-Guard AI</div>
                  <div className="text-slate-400 text-xs">RBI Intelligence Platform</div>
                </div>
              </div>
            </div>

            <nav className="flex-1 p-4 space-y-2">
              {[
                { to: '/',          label: '🔍 Check Compliance' },
                { to: '/dashboard', label: '📊 Dashboard' },
                { to: '/documents', label: '📁 Documents' },
              ].map(link => (
                <NavLink key={link.to} to={link.to} end={link.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:bg-slate-700 hover:text-white'
                    }`
                  }>
                  {link.label}
                </NavLink>
              ))}
            </nav>

            <div className="p-4 border-t border-slate-700">
              <div className="text-xs text-slate-500 text-center">
                Powered by Deep RAG + Groq AI
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/"          element={<CheckCompliance />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/documents" element={<Documents />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </ResultProvider>
  )
}