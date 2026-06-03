import { useEffect, useState } from 'react'
import { getDocs, ingestDoc, searchDocs, checkDocExists, deleteDoc } from '../api'

export default function Documents() {
  const [docs, setDocs]           = useState([])
  const [showAll, setShowAll]     = useState(false)
  const [query, setQuery]         = useState('')
  const [results, setResults]     = useState([])
  const [file, setFile]           = useState(null)
  const [circId, setCircId]       = useState('')
  const [category, setCategory]   = useState('home_loan')
  const [uploading, setUploading] = useState(false)
  const [message, setMessage]     = useState('')
  const [msgType, setMsgType]     = useState('success')
  const [searching, setSearching] = useState(false)
  const [existing, setExisting]   = useState(null)

  useEffect(() => { fetchDocs() }, [])

  const fetchDocs = () => {
    getDocs().then(r => setDocs(r.data.documents)).catch(() => {})
  }

  const visibleDocs = showAll ? docs : docs.slice(0, 5)

  const handleCircIdChange = async (e) => {
    const val = e.target.value.toUpperCase().replace(/[^A-Z0-9\-]/g, '')
    setCircId(val)
    if (val.length > 5) {
      try {
        const res = await checkDocExists(val)
        setExisting(res.data)
      } catch { setExisting(null) }
    } else {
      setExisting(null)
    }
  }

  const handleIngest = async () => {
    if (!file)        return showMsg('Please select a PDF file', 'error')
    if (!circId.trim()) return showMsg('Please enter a Circular ID', 'error')

    setUploading(true)
    setMessage('')
    const form = new FormData()
    form.append('file', file)
    form.append('circular_id', circId.trim())
    form.append('category', category)
    form.append('replace', 'true')

    try {
      const r = await ingestDoc(form)
      const action = r.data.action === 'replaced'
        ? `♻️ Replaced old version — ${r.data.replaced_chunks} old chunks removed, ${r.data.total_chunks} new chunks added`
        : `✅ Ingested ${r.data.total_chunks} chunks successfully`
      showMsg(action, 'success')
      setFile(null)
      setCircId('')
      setCategory('home_loan')
      setExisting(null)
      document.getElementById('fileInput').value = ''
      fetchDocs()
    } catch {
      showMsg('❌ Ingestion failed. Make sure file is a valid PDF.', 'error')
    }
    setUploading(false)
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    setResults([])
    try {
      const r = await searchDocs(query)
      setResults(r.data.results)
    } catch { showMsg('Search failed', 'error') }
    setSearching(false)
  }

  const showMsg = (msg, type) => {
    setMessage(msg)
    setMsgType(type)
    setTimeout(() => setMessage(''), 5000)
  }

  const categoryLabel = {
    home_loan:     '🏠 Home Loan',
    msme_loan:     '🏭 MSME Loan',
    personal_loan: '👤 Personal Loan',
    kyc:           '🪪 KYC',
    general:       '📄 General',
  }

  const categoryColor = {
    home_loan:     'bg-blue-900/50 text-blue-300 border-blue-700',
    msme_loan:     'bg-purple-900/50 text-purple-300 border-purple-700',
    personal_loan: 'bg-orange-900/50 text-orange-300 border-orange-700',
    kyc:           'bg-green-900/50 text-green-300 border-green-700',
    general:       'bg-slate-700/50 text-slate-300 border-slate-600',
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">📁 RBI Document Management</h1>
        <p className="text-slate-400 text-sm mt-1">
          Manage the knowledge base that powers compliance checks
        </p>
      </div>

      {/* ── Knowledge Base ───────────────────────────────────── */}
      <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-blue-400 font-semibold">
            Knowledge Base
            <span className="ml-2 bg-blue-900/50 text-blue-300 text-xs px-2 py-0.5 rounded-full border border-blue-700">
              {docs.length} documents
            </span>
          </h2>
          {docs.length > 0 && (
            <span className="text-slate-400 text-xs">Latest first</span>
          )}
        </div>

        {docs.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <div className="text-4xl mb-2">📭</div>
            <p>No documents ingested yet.</p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {visibleDocs.map((d, i) => (
                <div key={i}
                  className="flex items-center justify-between bg-slate-700/50 hover:bg-slate-700 rounded-lg px-4 py-3 transition-all border border-slate-600">
                  <div className="flex items-center gap-3">
                    <div className="text-lg">📄</div>
                    <div>
                      <p className="text-white font-mono text-sm font-semibold">
                        {d.circular_id}
                      </p>
                      <p className="text-slate-500 text-xs mt-0.5">
                        {d.source_file}
                        {d.version && d.version !== 'unknown' && (
                          <span className="ml-2 text-slate-600">v{d.version}</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full border ${categoryColor[d.category] || categoryColor.general}`}>
                    {categoryLabel[d.category] || d.category}
                  </span>
                </div>
              ))}
            </div>

            {docs.length > 5 && (
              <button
                onClick={() => setShowAll(s => !s)}
                className="w-full mt-3 py-2 text-sm text-blue-400 hover:text-blue-300 hover:bg-slate-700 rounded-lg border border-slate-600 transition-all">
                {showAll ? '▲ Show Less' : `▼ View ${docs.length - 5} More Documents`}
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Upload New PDF ───────────────────────────────────── */}
      <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
        <h2 className="text-blue-400 font-semibold mb-4">📤 Upload New RBI Circular</h2>

        <div className="space-y-4">

          {/* File picker */}
          <div
            className="border-2 border-dashed border-slate-600 rounded-xl p-6 text-center cursor-pointer hover:border-blue-500 transition-all"
            onClick={() => document.getElementById('fileInput').click()}>
            <input id="fileInput" type="file" accept=".pdf"
              className="hidden"
              onChange={e => setFile(e.target.files[0])} />
            {file ? (
              <div>
                <div className="text-3xl mb-1">📄</div>
                <p className="text-green-400 font-semibold text-sm">{file.name}</p>
                <p className="text-slate-400 text-xs mt-1">
                  {(file.size / 1024).toFixed(1)} KB — Click to change
                </p>
              </div>
            ) : (
              <div>
                <div className="text-3xl mb-1">☁️</div>
                <p className="text-slate-300 text-sm">Click to select PDF</p>
                <p className="text-slate-500 text-xs mt-1">Only .pdf files accepted</p>
              </div>
            )}
          </div>

          {/* Circular ID */}
          <div>
            <label className="text-slate-300 text-sm block mb-1">Circular ID</label>
            <input
              value={circId}
              onChange={handleCircIdChange}
              placeholder="e.g. RBI-MSME-2024"
              className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600 font-mono" />
            <p className="text-slate-500 text-xs mt-1">Format: RBI-CATEGORY-YEAR</p>

            {/* Duplicate warning */}
            {existing?.exists && (
              <div className="mt-2 bg-yellow-900/40 border border-yellow-700 rounded-lg px-4 py-3">
                <p className="text-yellow-400 text-sm font-semibold">
                  ⚠️ This Circular ID already exists in knowledge base
                </p>
                <p className="text-yellow-300 text-xs mt-1">
                  Current: <span className="font-mono">{existing.source_file}</span> — {existing.chunk_count} chunks
                </p>
                <p className="text-green-400 text-xs mt-2 font-semibold">
                  ✅ Old version will be automatically replaced with your new PDF
                </p>
              </div>
            )}

            {existing !== null && !existing?.exists && circId.length > 5 && (
              <p className="text-green-400 text-xs mt-1">
                ✅ New circular ID — will be added fresh
              </p>
            )}
          </div>

          {/* Category */}
          <div>
            <label className="text-slate-300 text-sm block mb-1">Category</label>
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="w-full bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600">
              <option value="home_loan">🏠 Home Loan</option>
              <option value="msme_loan">🏭 MSME Loan</option>
              <option value="personal_loan">👤 Personal Loan</option>
              <option value="kyc">🪪 KYC</option>
              <option value="general">📄 General</option>
            </select>
          </div>

          {/* Ingest Button */}
          <button onClick={handleIngest} disabled={uploading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
            {uploading
              ? <><span className="animate-spin">⏳</span> Ingesting into Knowledge Base...</>
              : <>📥 Ingest Document</>}
          </button>

          {/* Message */}
          {message && (
            <div className={`rounded-lg px-4 py-3 text-sm font-medium ${
              msgType === 'success'
                ? 'bg-green-900/50 text-green-400 border border-green-700'
                : 'bg-red-900/50 text-red-400 border border-red-700'
            }`}>
              {message}
            </div>
          )}
        </div>
      </div>

      {/* ── Search ──────────────────────────────────────────── */}
      <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
        <h2 className="text-blue-400 font-semibold mb-4">🔍 Search Knowledge Base</h2>

        <div className="flex gap-3 mb-4">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. What is the maximum LTV ratio for home loans?"
            className="flex-1 bg-slate-700 text-white rounded-lg px-3 py-2 border border-slate-600" />
          <button onClick={handleSearch} disabled={searching}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold rounded-xl transition-all">
            {searching ? '...' : 'Search'}
          </button>
        </div>

        {results.length > 0 && (
          <div className="space-y-3">
            <p className="text-slate-400 text-xs">{results.length} results found</p>
            {results.map((r, i) => (
              <div key={i} className="bg-slate-700 rounded-lg p-4 border-l-4 border-blue-500">
                <div className="flex justify-between mb-2">
                  <span className="text-blue-400 font-semibold text-sm">
                    {r.metadata.circular_id}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    r.relevance_score > 0.3
                      ? 'bg-green-900/50 text-green-400 border-green-700'
                      : 'bg-slate-600 text-slate-400 border-slate-500'
                  }`}>
                    Relevance: {(r.relevance_score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{r.content}</p>
              </div>
            ))}
          </div>
        )}

        {results.length === 0 && query && !searching && (
          <p className="text-slate-500 text-sm text-center py-4">
            No results found. Try a different query.
          </p>
        )}
      </div>
    </div>
  )
}