const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  let payload = null
  try { payload = await response.json() } catch { /* empty response */ }
  if (!response.ok) {
    const detail = payload?.detail
    const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `API ${response.status}`
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return payload
}

export const api = {
  health: () => request('/health'),
  listPatients: () => request('/patients'),
  getPatient: (id) => request(`/patients/${encodeURIComponent(id)}`),
  getProfile: (id) => request(`/patients/${encodeURIComponent(id)}/profile`),
  updateProfile: (id, data) => request(`/patients/${encodeURIComponent(id)}/profile`, { method: 'PUT', body: JSON.stringify(data) }),
  getAssessment: (id) => request(`/patients/${encodeURIComponent(id)}/assessment`),
  getAssessmentResult: (id) => request(`/patients/${encodeURIComponent(id)}/assessment/result`),
  saveAssessment: (id, answers, status = 'SUBMITTED') => request(`/patients/${encodeURIComponent(id)}/assessment`, { method: 'PUT', body: JSON.stringify({ answers, status }) }),
  reviewAssessment: (id, action = 'approve', reviewerId = 1, note = '', q56Goal = undefined) => request(`/patients/${encodeURIComponent(id)}/assessment/review`, { method: 'POST', body: JSON.stringify({ action, reviewer_id: reviewerId, note, ...(q56Goal === undefined ? {} : { q56_goal: q56Goal }) }) }),
  getPlan: (id, includeUnpublished = false) => request(`/patients/${encodeURIComponent(id)}/plan${includeUnpublished ? '?include_unpublished=true' : ''}`),
  createPlan: (id) => request(`/patients/${encodeURIComponent(id)}/plans/draft`, { method: 'POST' }),
  savePlan: (id, draft, status) => request(`/patients/${encodeURIComponent(id)}/plan`, { method: 'PUT', body: JSON.stringify({ draft, status }) }),
  reviewPlan: (id, action, reviewerId = 1, note = '') => request(`/patients/${encodeURIComponent(id)}/plans/review`, { method: 'POST', body: JSON.stringify({ action, reviewer_id: reviewerId, note }) }),
  listPlanTasks: (id) => request(`/patients/${encodeURIComponent(id)}/plan/tasks`),
  listTodos: (tab) => request(`/todos${tab ? `?tab=${encodeURIComponent(tab)}` : ''}`),
  dashboardSummary: () => request('/dashboard/summary'),
  weeklyReview: (id) => request(`/patients/${encodeURIComponent(id)}/weekly-review`),
  listRecords: (id, type) => request(`/patients/${encodeURIComponent(id)}/records${type ? `?record_type=${encodeURIComponent(type)}` : ''}`),
  createRecord: (id, data) => request(`/patients/${encodeURIComponent(id)}/records`, { method: 'POST', body: JSON.stringify(data) }),
  listMeasurements: (id) => request(`/patients/${encodeURIComponent(id)}/measurements`),
  createMeasurement: (id, data) => request(`/patients/${encodeURIComponent(id)}/measurements`, { method: 'POST', body: JSON.stringify(data) }),
}

export { API_BASE }
