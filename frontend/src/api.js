import axios from 'axios'

const API = axios.create({
  baseURL: window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000/api/v1'
    : '/api/v1'
})

export const submitCheck   = (data)     => API.post('/compliance/check', data)
export const getCheck      = (id)       => API.get(`/compliance/check/${id}`)
export const getStats      = ()         => API.get('/compliance/stats')
export const getHistory    = (limit=10) => API.get(`/compliance/history?limit=${limit}`)
export const getDocs       = ()         => API.get('/documents/list')
export const ingestDoc     = (form)     => API.post('/documents/ingest', form)
export const searchDocs    = (query)    => API.post(`/documents/search?query=${encodeURIComponent(query)}`)
export const checkDocExists = (id)      => API.get(`/documents/check/${id}`)
export const deleteDoc      = (id)      => API.delete(`/documents/delete/${id}`)