// 监测与预警跨患者 Mock 列表；患者360和工作台按 patient_id 读取同一患者状态。
export const mockCareAlerts = [
  { patientId: 'P001', type: '数据记录提醒', value: '2026-09-04', level: 'yellow', triggeredAt: '今天 09:15' },
  { patientId: 'P003', type: '体重趋势关注', value: '本周波动需复核', level: 'yellow', triggeredAt: '今天 09:15' },
  { patientId: 'P005', type: '肺康复不适', value: '训练时出现轻微气促', level: 'red', triggeredAt: '今天 08:40' },
  { patientId: 'P006', type: '评估资料缺失', value: 'Q14–Q45待补充', level: 'yellow', triggeredAt: '今天 09:15' },
]

const STORAGE_KEY = 'cm-care-alerts'
export function getCareAlerts() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    return Array.isArray(saved) ? saved : mockCareAlerts
  } catch { return mockCareAlerts }
}
export function markCareAlertHandled(patientId) {
  const next = getCareAlerts().map((item) => item.patientId === patientId ? { ...item, handled: true } : item)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}
