import { computed, reactive } from 'vue'
import { getMockPatient, mockPatients } from '../mock/patients'
import { assessmentQuestionCount, assessmentSections } from '../config/assessmentQuestions'
import { mockDailyRecords } from '../mock/dailyRecords'
import { mockConsultations } from '../mock/consultations'
import { getPublishedPlan } from '../mock/publishedPlans'
import { syncPlanTodo, syncAssessmentTodo } from '../mock/careTodos'
import { mockActivities } from '../mock/activities'
import { getCareAlerts } from '../mock/careAlerts'
import { api } from '../api/client'

const STORAGE_KEY = 'cm-chen-patient-v1'
function readSaved() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} } }
const saved = readSaved()
export const patientStore = reactive({ currentId: saved.currentId || 'P001', profileByPatient: saved.profileByPatient || {}, assessmentByPatient: saved.assessmentByPatient || {}, dailyRecords: saved.dailyRecords || {}, consultationsByPatient: saved.consultationsByPatient || {}, plansByPatient: saved.plansByPatient || {}, eventsByPatient: saved.eventsByPatient || {}, apiPatientsById: {}, apiProfilesByPatient: {}, apiAssessmentsByPatient: {}, apiResultsByPatient: {}, apiPlansByPatient: {}, apiPlanLoadedByPatient: {}, apiRecordsByPatient: {}, apiErrorsByPatient: {}, apiCarePatients: [], apiTodos: [], apiDashboard: null })

function ageText(birthDate) {
  if (!birthDate) return ''
  const birth = new Date(birthDate)
  if (Number.isNaN(birth.getTime())) return ''
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  if (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate())) age -= 1
  return `${age}岁`
}

function mergedPatient(id) {
  const mock = getMockPatient(id)
  const remote = patientStore.apiPatientsById[id]
  if (!remote) return mock
  const evaluation = remote.evaluation || {}
  return { ...mock, ...remote, id: remote.patient_id || remote.id || id, age: ageText(remote.birth_date) || mock.age,
    phenotype: evaluation.phenotype || (evaluation.phenotype_code ? `${evaluation.phenotype_code}` : mock.phenotype),
    diseaseRisk: evaluation.diseaseRisk || evaluation.disease_risk || mock.diseaseRisk,
    safety: evaluation.safety || mock.safety,
    execution: evaluation.execution || evaluation.execution_ability || mock.execution,
    profile: { ...(mock.profile || {}), ...(patientStore.apiProfilesByPatient[id] || {}) } }
}

export const currentPatient = computed(() => mergedPatient(patientStore.currentId))

export async function refreshPatientFromApi(id = patientStore.currentId, includeUnpublishedPlan = false) {
  try {
    const [patient, profile, assessment, result, records, measurements] = await Promise.all([api.getPatient(id), api.getProfile(id), api.getAssessment(id), api.getAssessmentResult(id).catch(() => null), api.listRecords(id).catch(() => []), api.listMeasurements(id).catch(() => [])])
    patientStore.apiPatientsById[id] = patient
    patientStore.apiProfilesByPatient[id] = { ...profile, birthDate: profile.birth_date || profile.birthDate, avatar: profile.avatar_url || profile.avatar }
    patientStore.apiAssessmentsByPatient[id] = assessment
    if (result) patientStore.apiResultsByPatient[id] = result
    patientStore.apiRecordsByPatient[id] = { records, measurements }
    try { patientStore.apiPlansByPatient[id] = await api.getPlan(id, includeUnpublishedPlan) } catch (error) { if (error?.status === 404) patientStore.apiPlansByPatient[id] = null; else throw error }
    patientStore.apiPlanLoadedByPatient[id] = true
    delete patientStore.apiErrorsByPatient[id]
    return { patient, profile, assessment, result, records, measurements, plan: patientStore.apiPlansByPatient[id] }
  } catch (error) {
    patientStore.apiErrorsByPatient[id] = error?.message || 'API暂不可用'
    return null
  }
}

export function getPatientView(id) { return mergedPatient(id) }

export async function refreshCarePatients() {
  try {
    const rows = await api.listPatients()
    const enriched = await Promise.all(rows.map(async (row) => {
      const id = row.patient_id || row.id
      const detail = await api.getPatient(id).catch(() => row)
      const assessment = await api.getAssessment(id).catch(() => null)
      const result = await api.getAssessmentResult(id).catch(() => null)
      const plan = await api.getPlan(id, true).catch(() => null)
      patientStore.apiPatientsById[id] = detail
      if (assessment) patientStore.apiAssessmentsByPatient[id] = assessment
      if (result) patientStore.apiResultsByPatient[id] = result
      patientStore.apiPlansByPatient[id] = plan
      patientStore.apiPlanLoadedByPatient[id] = true
      const evaluation = detail.evaluation || {}
      return { ...mergedPatient(id), ...detail, id, patient_id: id, phenotype: evaluation.phenotype || mergedPatient(id).phenotype, diseaseRisk: evaluation.diseaseRisk || mergedPatient(id).diseaseRisk, safety: evaluation.safety || mergedPatient(id).safety, execution: evaluation.execution || mergedPatient(id).execution, planStatus: plan?.status || mergedPatient(id).planStatus, assessmentStatus: assessment?.current?.status || mergedPatient(id).assessmentStatus, assessmentCompletion: assessmentProgress(id), weeklyProgress: mergedPatient(id).weeklyProgress }
    }))
    patientStore.apiCarePatients = enriched
    return enriched
  } catch (error) {
    patientStore.apiErrorsByPatient.__list = error?.message || 'API暂不可用'
    return mockPatients
  }
}

export async function refreshCareTodos(tab) {
  try { patientStore.apiTodos = await api.listTodos(tab); return patientStore.apiTodos } catch { return getCareTodos() }
}

export async function refreshDashboardSummary() {
  try { patientStore.apiDashboard = await api.dashboardSummary(); return patientStore.apiDashboard } catch { return null }
}
export function patientProfileData(id = patientStore.currentId) {
  const patient = mergedPatient(id)
  const fallback = { name: patient.name, sex: patient.sex, birthDate: '', phone: '', avatar: patient.name?.slice(0, 1) || '患' }
  const remote = patientStore.apiProfilesByPatient[id] || {}
  const overrides = Object.fromEntries(Object.entries({ ...remote, ...(patientStore.profileByPatient[id] || {}) }).filter(([, value]) => value !== '' && value !== null && value !== undefined))
  return { ...fallback, ...(patient.profile || {}), ...overrides }
}
export async function savePatientProfile(data, id = patientStore.currentId) {
  patientStore.profileByPatient[id] = { ...(patientStore.profileByPatient[id] || {}), ...data }
  persist()
  try {
    const remote = await api.updateProfile(id, { name: data.name, sex: data.sex, birth_date: data.birthDate, phone: data.phone, avatar_url: data.avatar })
    patientStore.apiProfilesByPatient[id] = { ...remote, birthDate: remote.birth_date || remote.birthDate, avatar: remote.avatar_url || remote.avatar }
    patientStore.apiPatientsById[id] = { ...(patientStore.apiPatientsById[id] || {}), ...remote }
    return remote
  } catch { return null }
}
export function assessmentData(id = patientStore.currentId) { return patientStore.apiAssessmentsByPatient[id]?.current?.answers || patientStore.assessmentByPatient[id] || {} }
export function dailyRecordData(id = patientStore.currentId) { return { ...(mockDailyRecords[id] || {}), ...(patientStore.dailyRecords[id] || {}) } }
export async function saveDailyRecord(type, data, id = patientStore.currentId) {
  const current = patientStore.dailyRecords[id] || {}
  const localEntry = { ...(current[type] || {}), ...data, pending_sync: type === 'body' ? false : true }
  patientStore.dailyRecords[id] = { ...current, latestDate: data.date || new Date().toISOString().slice(0, 10), [type]: localEntry }
  persist()
  if (type === 'body') return { ok: true, source: 'local-body-page' }
  const recordType = type === 'exercise' ? 'EXERCISE' : type === 'pulmonary' ? 'PULMONARY' : type === 'diet' ? 'DIET' : 'OTHER'
  const discomfort = data.discomfort === '无' ? 'NONE' : data.discomfort === '有' ? 'MILD' : data.discomfort || null
  try {
    const remote = await api.createRecord(id, { record_date: data.date || new Date().toISOString().slice(0, 10), record_type: recordType, actual_duration_min: Number(data.actualDuration || data.actualMinutes || 0) || null, actual_reps: Number(data.actualReps || data.actualTimes || 0) || null, actual_sets: Number(data.actualSets || 0) || null, intensity: data.intensity || null, discomfort, note: data.note || null, metadata_json: data })
    patientStore.dailyRecords[id][type] = { ...patientStore.dailyRecords[id][type], pending_sync: false, record_id: remote.record_id }
    persist()
    return { ok: true, source: 'api', remote }
  } catch (error) {
    patientStore.dailyRecords[id][type] = { ...patientStore.dailyRecords[id][type], pending_sync: true, sync_error: error?.message || 'API保存失败' }
    persist()
    return { ok: false, pending_sync: true, error: error?.message || 'API保存失败' }
  }
}
export function recordPatientEvent(id, text, type = 'info') {
  const event = { id: `EV-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, patientId: id, text, type, createdAt: new Date().toISOString(), time: '刚刚' }
  patientStore.eventsByPatient[id] = [event, ...(patientStore.eventsByPatient[id] || [])].slice(0, 30)
  persist()
  return event
}
export function patientEvents(id = patientStore.currentId) {
  const base = mockActivities.filter((item) => item.patientId === id).map((item) => ({ ...item, createdAt: item.createdAt || '2026-01-01T00:00:00.000Z' }))
  const alerts = getCareAlerts().filter((item) => item.patientId === id && !item.handled).map((item) => ({ id: `ALERT-${id}-${item.type}`, patientId: id, text: item.level === 'red' ? `出现红色重点：${item.type}` : `有一条黄色关注：${item.type}`, time: item.triggeredAt, createdAt: item.triggeredAt || '2026-01-01T00:00:00.000Z', type: 'monitoring' }))
  return [...base, ...(patientStore.eventsByPatient[id] || []), ...alerts].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)))
}
export function consultationData(id = patientStore.currentId) {
  const base = mockConsultations.filter((item) => item.patientId === id)
  const local = patientStore.consultationsByPatient[id] || []
  const merged = new Map(base.map((item) => [item.id, item]))
  local.forEach((item) => merged.set(item.id, item))
  return [...merged.values()].sort((a, b) => String(b.updatedAt || b.createdAt).localeCompare(String(a.updatedAt || a.createdAt)))
}
export function allConsultations() {
  return mockPatients.flatMap((patient) => consultationData(patient.id))
}
export function saveConsultation(data, id = patientStore.currentId) {
  const item = { id: `C${Date.now()}`, patientId: id, createdAt: new Date().toISOString().slice(0, 16).replace('T', ' '), type: data.type || '其他', summary: data.summary || '', status: '待回复', handling: '待处理', reply: '', repliedBy: '', updatedAt: new Date().toISOString().slice(0, 16).replace('T', ' ') }
  patientStore.consultationsByPatient[id] = [...(patientStore.consultationsByPatient[id] || []), item]
  persist()
  return item
}
export function updateConsultation(id, patch) {
  const source = mockConsultations.find((item) => item.id === id) || Object.values(patientStore.consultationsByPatient).flat().find((item) => item.id === id)
  if (!source) return
  const patientId = source.patientId
  patientStore.consultationsByPatient[patientId] = consultationData(patientId).map((item) => item.id === id ? { ...item, ...patch, updatedAt: new Date().toISOString().slice(0, 16).replace('T', ' ') } : item)
  persist()
}
export function sendConsultationReply(id, text, clinician = '审核医护') {
  const source = mockConsultations.find((item) => item.id === id) || Object.values(patientStore.consultationsByPatient).flat().find((item) => item.id === id)
  if (!source || !text?.trim()) return
  const current = consultationData(source.patientId).find((item) => item.id === id) || source
  const message = { from: 'clinician', text: text.trim(), at: new Date().toLocaleString('zh-CN', { hour12: false }) }
  updateConsultation(id, { status: '已回复', handling: '处理中', reply: text.trim(), repliedBy: clinician, messages: [...(current.messages || [{ from: 'patient', text: current.summary, at: current.createdAt }]), message] })
  recordPatientEvent(source.patientId, '您的咨询已回复', 'consultation')
}
export function planData(id = patientStore.currentId) {
  const patient = mergedPatient(id)
  const remote = patientStore.apiPlansByPatient[id]
  const apiLoaded = patientStore.apiPlanLoadedByPatient[id]
  const published = apiLoaded ? {} : getPublishedPlan(id)
  const base = { id: `PLAN-${id}`, patientId: id, status: apiLoaded ? (remote?.status || 'NONE') : patient.planStatus, ...published, draft: published, reviews: [] }
  const local = patientStore.plansByPatient[id] || {}
  // When an API response is loaded, it is authoritative.  Do not let an old
  // localStorage draft (for example version 5) overwrite the newest RDS
  // PUBLISHED content (for example version 9).
  const remoteDraft = remote?.draft || remote?.content || remote?.content_json || (remote?.contract_version ? remote : null)
  const draft = apiLoaded && remote ? { ...(remoteDraft || {}) } : { ...base.draft, ...(local.draft || {}) }
  const merged = apiLoaded && remote ? { ...base, ...remote } : { ...base, ...local }
  return { ...merged, patientId: id, draft, tasks: draft.tasks || (apiLoaded && remote ? [] : (local.tasks || base.tasks)) }
}
export async function savePlanDraft(id, draft) {
  const current = planData(id)
  patientStore.plansByPatient[id] = { ...current, draft: { ...current.draft, ...draft }, status: current.status === 'PUBLISHED' ? 'IN_REVIEW' : current.status }
  syncPlanTodo(id, patientStore.plansByPatient[id].status); persist(); recordPatientEvent(id, '本周计划内容已更新', 'plan')
  try {
    const remote = await api.savePlan(id, patientStore.plansByPatient[id].draft, patientStore.plansByPatient[id].status)
    patientStore.apiPlansByPatient[id] = remote
    return remote
  } catch { return planData(id) }
}
export function addPlanReview(id, review) {
  const current = planData(id)
  patientStore.plansByPatient[id] = { ...current, reviews: [...(current.reviews || []), { ...review, reviewer: review.reviewer || '审核医护', reviewedAt: review.reviewedAt || new Date().toLocaleString('zh-CN', { hour12: false }) }], status: current.status === 'PUBLISHED' ? 'IN_REVIEW' : current.status }
  persist(); return planData(id)
}
export async function setPlanStatus(id, status) {
  const current = planData(id)
  const previous = current
  patientStore.plansByPatient[id] = { ...current, status }
  syncPlanTodo(id, status); persist()
  if (['RETURNED', 'PAUSED', 'APPROVED_PENDING_PUBLISH', 'APPROVED_PENDING_MDT_ACTIVATION', 'READY_TO_PUBLISH'].includes(status)) recordPatientEvent(id, `方案状态已更新：${status === 'RETURNED' ? '已退回' : status === 'PAUSED' ? '已暂停' : status === 'APPROVED_PENDING_MDT_ACTIVATION' ? '医护审核已通过，待MDT激活' : '待发布'}`, 'plan')
  const action = { IN_REVIEW: 'start_review', APPROVED_PENDING_PUBLISH: 'approve', APPROVED_PENDING_MDT_ACTIVATION: 'approve', READY_TO_PUBLISH: 'approve', RETURNED: 'return', PAUSED: 'pause', PUBLISHED: 'publish' }[status]
  if (action) {
    try { patientStore.apiPlansByPatient[id] = await api.reviewPlan(id, action); return planData(id) } catch (error) {
      patientStore.plansByPatient[id] = previous; syncPlanTodo(id, previous.status); persist(); throw error
    }
  }
  return planData(id)
}
export async function publishPlan(id) {
  const current = planData(id)
  try {
    patientStore.apiPlansByPatient[id] = await api.reviewPlan(id, 'publish')
    const remote = patientStore.apiPlansByPatient[id]
    patientStore.plansByPatient[id] = { ...current, ...remote, status: remote?.status || 'PUBLISHED' }
    syncPlanTodo(id, patientStore.plansByPatient[id].status); persist(); recordPatientEvent(id, '您的专属方案已发布', 'plan')
    return planData(id)
  } catch (error) { throw error }
}
export async function saveAssessment(data, id = patientStore.currentId, status = 'DRAFT') {
  // Keep an explicit local sync marker while the real API is in flight.  A
  // pending cache entry must not create clinician todos or be presented as a
  // successfully submitted assessment.
  patientStore.assessmentByPatient[id] = { ...assessmentData(id), ...data, _status: status, _syncState: 'PENDING' }
  persist()
  try {
    const remote = await api.saveAssessment(id, data, status)
    patientStore.assessmentByPatient[id]._syncState = 'SYNCED'
    if (status === 'SUBMITTED') { syncAssessmentTodo(id, status); recordPatientEvent(id, '首次评估已提交，等待医护审核', 'assessment') }
    persist()
    patientStore.apiAssessmentsByPatient[id] = { patient_id: id, current: { status: remote.status, answers: remote.assessment }, history: patientStore.apiAssessmentsByPatient[id]?.history || [] }
    patientStore.apiPatientsById[id] = remote.patient || patientStore.apiPatientsById[id]
    // Final submission starts a new clinician-only draft from the freshly
    // persisted assessment.  The API creates an immutable plan version, so
    // an existing PUBLISHED version remains in history.
    if (status === 'SUBMITTED') {
      const draft = await api.createPlan(id)
      patientStore.apiPlansByPatient[id] = draft
    }
    return remote
  } catch (error) {
    // Never report a local-cache write as a successful business save.  The
    // caller can display the API error and offer retry; local state remains
    // available as an unsynced draft for recovery.
    patientStore.assessmentByPatient[id]._syncState = 'PENDING'
    persist()
    throw error
  }
}
export async function reviewAssessment(id = patientStore.currentId) {
  patientStore.assessmentByPatient[id] = { ...assessmentData(id), _status: 'REVIEWED' }
  syncAssessmentTodo(id, 'REVIEWED'); persist(); recordPatientEvent(id, '评估结果已更新', 'assessment')
  try {
    const remote = await api.reviewAssessment(id, 'approve')
    await refreshPatientFromApi(id)
    return remote
  } catch { return assessmentData(id) }
}
export function assessmentProgress(id = patientStore.currentId) {
  const data = assessmentData(id)
  // Completion is a shared business metric. Account identity refs (Q1-Q4)
  // are read-only profile data and optional/conditional questions do not
  // reduce the denominator. Explicit negative selections (for example “无”)
  // are valid answers and count as completed.
  const scorable = assessmentSections.flatMap((section) => section.fields).filter((field) => field.countsForProgress !== false && field.source !== 'patient_profile' && !field.optional && !field.optionalWhen)
  const answered = (value, field) => {
    if (field.type === 'repeaters') return Array.isArray(value) && value.length > 0
    if (field.type === 'composite' || field.type === 'labs' || field.type === 'liver_elasticity') {
      return !!value && typeof value === 'object' && Object.values(value).some((item) => answered(item, { type: Array.isArray(item) ? 'checkbox' : 'text' }))
    }
    if (Array.isArray(value)) return value.length > 0
    return value !== undefined && value !== null && String(value).trim() !== ''
  }
  const filled = scorable.filter((field) => {
    const value = field.source === 'patient_profile' ? patientProfileData(id)[field.profileKey] : data[field.key]
    return answered(value, field)
  }).length
  return scorable.length ? Math.min(100, Math.round((filled / scorable.length) * 100)) : 0
}
export function assessmentResultData(id = patientStore.currentId) {
  const patient = mergedPatient(id)
  const completion = assessmentProgress(id)
  const evaluation = patientStore.apiResultsByPatient[id] || patientStore.apiPatientsById[id]?.evaluation || {}
  const latestAnswers = patientStore.apiAssessmentsByPatient[id]?.current?.answers || assessmentData(id)
  const q56 = latestAnswers.q56_goal && typeof latestAnswers.q56_goal === 'object' ? latestAnswers.q56_goal : null
  const status = patientStore.apiAssessmentsByPatient[id]?.current?.status || assessmentData(id)._status || 'DRAFT'
  const focus = q56?.has_clinician_goal && q56.primary_goal === 'ENHANCED_FAT_LOSS'
    ? ['按医护指导评估强化减脂可行性', '优先保护肌肉和功能', '根据安全校验结果执行已发布方案']
    : evaluation.focus || ['规律三餐与蛋白质摄入', '循序渐进的肺预康复', '每周复测体重、体脂率和腰围']
  return { completion, status, phenotype: evaluation.phenotype || patient.phenotype, diseaseRisk: evaluation.diseaseRisk || patient.diseaseRisk, execution: evaluation.execution || patient.execution, safety: evaluation.safety || patient.safety, focus, q56Goal: q56, mdtConfirmation: evaluation.mdtConfirmation || 'PENDING' }
}
export function syncFromStorage() {
  const latest = readSaved()
  if (!latest || typeof latest !== 'object') return
  patientStore.currentId = latest.currentId || patientStore.currentId
  patientStore.profileByPatient = latest.profileByPatient || {}
  patientStore.assessmentByPatient = latest.assessmentByPatient || {}
  patientStore.dailyRecords = latest.dailyRecords || {}
  patientStore.consultationsByPatient = latest.consultationsByPatient || {}
  patientStore.plansByPatient = latest.plansByPatient || {}
  patientStore.eventsByPatient = latest.eventsByPatient || {}
}
export function persist() { localStorage.setItem(STORAGE_KEY, JSON.stringify({ currentId: patientStore.currentId, profileByPatient: patientStore.profileByPatient, assessmentByPatient: patientStore.assessmentByPatient, dailyRecords: patientStore.dailyRecords, consultationsByPatient: patientStore.consultationsByPatient, plansByPatient: patientStore.plansByPatient, eventsByPatient: patientStore.eventsByPatient })) }
if (typeof window !== 'undefined') window.addEventListener('storage', (event) => { if (event.key === STORAGE_KEY) syncFromStorage() })
