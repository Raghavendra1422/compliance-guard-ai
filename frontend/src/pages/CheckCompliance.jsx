import { useState } from 'react'
import { submitCheck, getCheck } from '../api'
import { useResult } from '../context/ResultContext'

// ── Helper: format number to Indian style ──────────────────────
const formatIndian = (num) => {
  if (!num && num !== 0) return ''
  const n = Number(num)
  if (isNaN(n)) return ''
  if (n >= 10000000) return `₹${(n/10000000).toFixed(2)} Cr`
  if (n >= 100000)   return `₹${(n/100000).toFixed(2)} L`
  if (n >= 1000)     return `₹${(n/1000).toFixed(1)} K`
  return `₹${n}`
}

// ── Smart Number Input ─────────────────────────────────────────
function SmartInput({ label, value, onChange, step = 1000, min = 0, prefix = '₹' }) {
  const [raw, setRaw] = useState('')
  const [focused, setFocused] = useState(false)

  const handleFocus = () => {
    setFocused(true)
    setRaw(value === 0 ? '' : String(value))
  }

  const handleBlur = () => {
    setFocused(false)
    const parsed = parseInt(raw.replace(/,/g, ''), 10)
    if (!isNaN(parsed) && parsed >= min) {
      onChange(parsed)
    } else {
      onChange(min)
    }
    setRaw('')
  }

  const handleChange = (e) => {
    // Allow only digits
    const val = e.target.value.replace(/[^0-9]/g, '')
    setRaw(val)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      onChange(Math.max(min, value + step))
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      onChange(Math.max(min, value - step))
    }
  }

  return (
    <div>
      <label className="text-slate-300 text-sm block mb-1">{label}</label>
      <div className="relative">
        <input
          type="text"
          inputMode="numeric"
          className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600 pr-20"
          value={focused ? raw : (value > 0 ? value.toLocaleString('en-IN') : '')}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={`e.g. ${(min || step * 10).toLocaleString('en-IN')}`}
        />
        {/* Up/Down buttons */}
        <div className="absolute right-0 top-0 h-full flex flex-col border-l border-slate-600">
          <button type="button"
            className="flex-1 px-3 text-slate-400 hover:text-white hover:bg-slate-600 rounded-tr-lg text-xs"
            onClick={() => onChange(value + step)}>▲</button>
          <button type="button"
            className="flex-1 px-3 text-slate-400 hover:text-white hover:bg-slate-600 rounded-br-lg text-xs border-t border-slate-600"
            onClick={() => onChange(Math.max(min, value - step))}>▼</button>
        </div>
      </div>
      {/* Indian format display */}
      {value > 0 && (
        <p className="text-blue-400 text-xs mt-1">
          {formatIndian(value)}
          {step >= 1000 && <span className="text-slate-500 ml-2">↑↓ steps of {formatIndian(step)}</span>}
        </p>
      )}
    </div>
  )
}

export default function CheckCompliance() {
  const { result: report, setResult: setReport } = useResult()
  const [form, setForm] = useState({
    applicant_name: '', applicant_city: 'Mumbai',
    applicant_income_monthly: 75000, cibil_score: 720,
    existing_loans: 0, loan_type: 'home_loan',
    loan_amount_inr: 4500000, property_value_inr: 5000000,
    interest_rate_percent: 8.5, tenure_years: 20,
    loan_purpose: 'purchase'
  })
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  const ltv = form.property_value_inr > 0
    ? ((form.loan_amount_inr / form.property_value_inr) * 100).toFixed(2)
    : 0

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    if (!form.applicant_name.trim()) return alert('Please enter applicant name')
    setLoading(true); setReport(null); setElapsed(0)
    try {
      const { data } = await submitCheck({ ...form, ltv_ratio: parseFloat(ltv) })
      const checkId = data.check_id
      const timer = setInterval(() => setElapsed(e => e + 3), 3000)
      const poll = setInterval(async () => {
        const res = await getCheck(checkId)
        if (res.data.status === 'completed') {
          clearInterval(poll); clearInterval(timer)
          setReport(res.data.report); setLoading(false)
        }
      }, 3000)
    } catch (e) {
      alert('Backend error — make sure FastAPI is running on port 8000')
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-1">Loan Compliance Check</h1>
      <p className="text-slate-400 mb-6">Submit a loan application for AI-powered RBI regulation check</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Applicant Details */}
        <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
          <h2 className="text-blue-400 font-semibold mb-4">👤 Applicant Details</h2>
          <div className="space-y-4">
            <div>
              <label className="text-slate-300 text-sm block mb-1">Applicant Name</label>
              <input className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600"
                value={form.applicant_name}
                onChange={e => {
                  const val = e.target.value.replace(/[^a-zA-Z\s]/g, '')
                  update('applicant_name', val)
                }}
                placeholder="Full name" />
            </div>

            <div>
              <label className="text-slate-300 text-sm block mb-1">City</label>
              <input className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600"
                value={form.applicant_city}
                onChange={e => {
                  const val = e.target.value.replace(/[^a-zA-Z\s]/g, '')
                  update('applicant_city', val)
                }}
                placeholder="City name" />
            </div>

            <SmartInput
              label="Monthly Income"
              value={form.applicant_income_monthly}
              onChange={v => update('applicant_income_monthly', v)}
              step={5000}
              min={5000}
            />

            <div>
              <label className="text-slate-300 text-sm block mb-1">
                CIBIL Score: <span className="text-blue-400 font-bold">{form.cibil_score}</span>
                <span className={`ml-2 text-xs ${form.cibil_score >= 750 ? 'text-green-400' : form.cibil_score >= 650 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {form.cibil_score >= 750 ? '● Excellent' : form.cibil_score >= 650 ? '● Good' : '● Poor'}
                </span>
              </label>
              <input type="range" min="300" max="900" step="10"
                className="w-full mt-1 accent-blue-500"
                value={form.cibil_score}
                onChange={e => update('cibil_score', +e.target.value)} />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>300 Poor</span><span>600 Fair</span><span>750 Good</span><span>900 Excellent</span>
              </div>
            </div>

            <div>
              <label className="text-slate-300 text-sm block mb-1">Existing Loans</label>
              <div className="flex items-center gap-3">
                <button onClick={() => update('existing_loans', Math.max(0, form.existing_loans - 1))}
                  className="w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-bold text-lg border border-slate-600">−</button>
                <span className="text-white font-bold text-xl w-8 text-center">{form.existing_loans}</span>
                <button onClick={() => update('existing_loans', form.existing_loans + 1)}
                  className="w-10 h-10 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-bold text-lg border border-slate-600">+</button>
              </div>
            </div>
          </div>
        </div>

        {/* Loan Details */}
        <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
          <h2 className="text-blue-400 font-semibold mb-4">🏦 Loan Details</h2>
          <div className="space-y-4">
            <div>
              <label className="text-slate-300 text-sm block mb-1">Loan Type</label>
              <select className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600"
                value={form.loan_type} onChange={e => update('loan_type', e.target.value)}>
                <option value="home_loan">🏠 Home Loan</option>
                <option value="msme_loan">🏭 MSME Loan</option>
                <option value="personal_loan">👤 Personal Loan</option>
                <option value="gold_loan">🥇 Gold Loan</option>
              </select>
            </div>

            <SmartInput
              label="Loan Amount"
              value={form.loan_amount_inr}
              onChange={v => update('loan_amount_inr', v)}
              step={50000}
              min={100000}
            />

            <SmartInput
              label="Property Value"
              value={form.property_value_inr}
              onChange={v => update('property_value_inr', v)}
              step={50000}
              min={100000}
            />

            <div>
              <label className="text-slate-300 text-sm block mb-1">
                Interest Rate: <span className="text-blue-400 font-bold">{form.interest_rate_percent}%</span>
              </label>
              <div className="flex items-center gap-2">
                <button onClick={() => update('interest_rate_percent', Math.max(1, +(form.interest_rate_percent - 0.25).toFixed(2)))}
                  className="w-9 h-9 bg-slate-700 hover:bg-slate-600 text-white rounded-lg border border-slate-600 font-bold">−</button>
                <input type="range" min="5" max="25" step="0.25"
                  className="flex-1 accent-blue-500"
                  value={form.interest_rate_percent}
                  onChange={e => update('interest_rate_percent', +e.target.value)} />
                <button onClick={() => update('interest_rate_percent', Math.min(25, +(form.interest_rate_percent + 0.25).toFixed(2)))}
                  className="w-9 h-9 bg-slate-700 hover:bg-slate-600 text-white rounded-lg border border-slate-600 font-bold">+</button>
              </div>
            </div>

            <div>
              <label className="text-slate-300 text-sm block mb-1">
                Tenure: <span className="text-blue-400 font-bold">{form.tenure_years} years</span>
              </label>
              <div className="flex items-center gap-2">
                <button onClick={() => update('tenure_years', Math.max(1, form.tenure_years - 1))}
                  className="w-9 h-9 bg-slate-700 hover:bg-slate-600 text-white rounded-lg border border-slate-600 font-bold">−</button>
                <input type="range" min="1" max="30"
                  className="flex-1 accent-blue-500"
                  value={form.tenure_years}
                  onChange={e => update('tenure_years', +e.target.value)} />
                <button onClick={() => update('tenure_years', Math.min(30, form.tenure_years + 1))}
                  className="w-9 h-9 bg-slate-700 hover:bg-slate-600 text-white rounded-lg border border-slate-600 font-bold">+</button>
              </div>
            </div>

            <div>
              <label className="text-slate-300 text-sm block mb-1">Loan Purpose</label>
              <select className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600"
                value={form.loan_purpose} onChange={e => update('loan_purpose', e.target.value)}>
                <option value="purchase">Purchase</option>
                <option value="construction">Construction</option>
                <option value="renovation">Renovation</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* LTV Badge */}
      <div className={`rounded-xl p-4 mb-6 text-center border ${ltv > 90 ? 'bg-red-900/30 border-red-600' : ltv > 80 ? 'bg-yellow-900/30 border-yellow-600' : 'bg-green-900/30 border-green-600'}`}>
        <span className="text-slate-300">Calculated LTV Ratio: </span>
        <span className={`text-2xl font-bold ${ltv > 90 ? 'text-red-400' : ltv > 80 ? 'text-yellow-400' : 'text-green-400'}`}>{ltv}%</span>
        <span className="text-slate-400 text-sm ml-2">(Loan ÷ Property Value × 100)</span>
        <div className="text-xs text-slate-500 mt-1">
          RBI Limit: ≤90% for loans up to ₹30L &nbsp;|&nbsp; ≤80% for ₹30L–₹75L &nbsp;|&nbsp; ≤75% above ₹75L
        </div>
      </div>

      {/* Submit Button */}
      <button onClick={handleSubmit} disabled={loading}
        className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-bold text-lg rounded-xl transition-all">
        {loading ? `⏳ AI Agent Analyzing RBI Regulations... (${elapsed}s)` : '🚀 Run Compliance Check'}
      </button>

      {/* Results */}
      {report && (
        <div className="mt-8 space-y-6">
          <div className={`rounded-xl p-6 text-center ${report.overall_compliant ? 'bg-green-900/50 border border-green-500' : 'bg-red-900/50 border border-red-500'}`}>
            <div className="text-4xl mb-2">{report.overall_compliant ? '✅' : '❌'}</div>
            <h2 className={`text-2xl font-bold ${report.overall_compliant ? 'text-green-400' : 'text-red-400'}`}>
              {report.overall_compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
            </h2>
            <p className="text-slate-300 mt-2">{report.recommendation}</p>
          </div>

          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'Risk Score', value: `${report.risk_score}/100`, color: report.risk_score > 50 ? 'text-red-400' : 'text-green-400' },
              { label: 'Total Checks', value: report.summary.total_checks, color: 'text-blue-400' },
              { label: 'Compliant', value: report.summary.compliant, color: 'text-green-400' },
              { label: 'Violations', value: report.summary.non_compliant, color: 'text-red-400' },
              { label: 'Confidence', value: `${Math.round(report.summary.average_confidence * 100)}%`, color: 'text-yellow-400' },
            ].map(m => (
              <div key={m.label} className="bg-slate-800 rounded-xl p-4 text-center border border-slate-700">
                <div className={`text-2xl font-bold ${m.color}`}>{m.value}</div>
                <div className="text-slate-400 text-xs mt-1">{m.label}</div>
              </div>
            ))}
          </div>

          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <p className="text-slate-300">💡 <span className="font-semibold">Recommendation:</span> {report.recommendation}</p>
          </div>

          {report.violations.length > 0 && (
            <div>
              <h3 className="text-red-400 font-bold text-lg mb-3">🚨 Violations Found</h3>
              <div className="space-y-4">
                {report.violations.map((v, i) => (
                  <div key={i} className="bg-red-950/40 border border-red-800 rounded-xl p-5">
                    <p className="text-red-300 font-semibold mb-3">❌ {v.question}</p>
                    {v.explanation.split('\n').map((line, j) => (
                      line.trim() && <p key={j} className={`text-sm mb-1 ${
                        line.startsWith('VERDICT') ? 'text-red-400 font-bold' :
                        line.startsWith('VIOLATED_RULE') ? 'text-yellow-400' :
                        line.startsWith('RECOMMENDATION') ? 'text-blue-300' : 'text-slate-300'
                      }`}>{line}</p>
                    ))}
                    {v.citations?.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-slate-400 text-xs font-semibold">📎 RBI SOURCES:</p>
                        {v.citations.map((c, k) => (
                          <div key={k} className="bg-blue-950/50 border-l-2 border-blue-500 rounded p-3 text-xs">
                            <span className="text-blue-400 font-bold">{c.circular_id}</span>
                            <span className="text-slate-400 ml-2">Relevance: {Math.round(c.relevance * 100)}%</span>
                            <p className="text-slate-300 mt-1 italic">"{c.excerpt.slice(0, 180)}..."</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="text-slate-300 font-bold text-lg mb-3">📝 All Checks</h3>
            <div className="space-y-2">
              {report.all_checks.map((c, i) => (
                <div key={i} className={`rounded-lg p-3 border text-sm flex justify-between items-center ${
                  c.verdict === 'COMPLIANT' ? 'bg-green-950/30 border-green-800' :
                  c.verdict === 'NON_COMPLIANT' ? 'bg-red-950/30 border-red-800' :
                  'bg-yellow-950/30 border-yellow-800'
                }`}>
                  <span className="text-slate-300">
                    {c.verdict === 'COMPLIANT' ? '✅' : c.verdict === 'NON_COMPLIANT' ? '❌' : '🔍'} {c.question}
                  </span>
                  <span className="text-slate-400 text-xs ml-4 shrink-0">{Math.round(c.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}