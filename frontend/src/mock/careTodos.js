// 医护待办跨患者 Mock 列表；工作台与待办页共用，统计不再单独写死。
export const mockCareTodos = [
  { key: 'a1', tab: 'pending-assessment', patient: '王女士', id: 'P003', type: '首次评估', summary: '还有身体测量与关键化验待补充', updated: '今天 09:20', status: '待完成' },
  { key: 'a2', tab: 'assessment-review', patient: '李先生', id: 'P002', type: '首次评估', summary: 'Q1–Q55 已提交，等待审核', updated: '今天 08:50', status: '待审核' },
  { key: 'a3', tab: 'plan-review', patient: '张女士', id: 'P001', type: 'AI方案草稿', summary: '术前营养与功能准备方案待审核', updated: '昨天 16:40', status: '待审核' },
  { key: 'a4', tab: 'publish', patient: '赵女士', id: 'P004', type: '已审核方案', summary: '审核通过，等待正式发布', updated: '昨天 15:10', status: '待发布' },
  { key: 'a5', tab: 'returned', patient: '陈先生', id: 'P006', type: '方案草稿', summary: '需要补充手术时间窗口后重新生成', updated: '9月2日', status: '已退回' },
]

const STORAGE_KEY = 'cm-care-todos'
export function getCareTodos() {
  try { const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); return Array.isArray(saved) ? saved : mockCareTodos } catch { return mockCareTodos }
}
export function syncPlanTodo(patientId, status) {
  const current = getCareTodos()
  let next = current
  if (status === 'PUBLISHED') next = current.filter((item) => !(item.id === patientId && ['plan-review', 'publish'].includes(item.tab)))
  else if (status === 'APPROVED_PENDING_PUBLISH') next = current.map((item) => item.id === patientId && item.tab === 'plan-review' ? { ...item, tab: 'publish', status: '待发布' } : item)
  else if (status === 'RETURNED') next = current.map((item) => item.id === patientId && ['plan-review', 'publish'].includes(item.tab) ? { ...item, tab: 'returned', status: '已退回' } : item)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); return next
}
export function syncAssessmentTodo(patientId, status) {
  const current = getCareTodos()
  const exists = current.some((item) => item.id === patientId && ['pending-assessment', 'assessment-review'].includes(item.tab))
  let next = current
  if (status === 'SUBMITTED' && !exists) next = [...current, { key: `assessment-${patientId}`, tab: 'assessment-review', patient: patientId, id: patientId, type: '首次评估', summary: 'Q1–Q55 已提交，等待审核', updated: '刚刚', status: '待审核' }]
  if (status === 'REVIEWED') next = current.filter((item) => !(item.id === patientId && item.tab === 'assessment-review'))
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); return next
}
