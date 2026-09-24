export const knowledgeItems = [
  { id: 'breathing', title: '术前呼吸训练方法', category: '肺预康复', type: '视频', duration: '6分钟', intro: '跟随医院宣教内容，学习术前可练习的缩唇呼吸和腹式呼吸。', status: 'PUBLISHED' },
  { id: 'safe-activity', title: '术前安全活动指导', category: '运动康复', type: '视频', duration: '5分钟', intro: '了解术前活动的强度选择、热身方式和需要停止的情况。', status: 'PUBLISHED' },
  { id: 'diet', title: '肺结节患者饮食注意事项', category: '营养管理', type: '视频', duration: '7分钟', intro: '从规律进食、蛋白质摄入和饮食记录三个方面做好营养准备。', status: 'PUBLISHED' },
  { id: 'preop', title: '手术前准备事项', category: '术前准备', type: '视频', duration: '4分钟', intro: '整理手术前的生活安排、资料准备和与医护沟通要点。', status: 'PUBLISHED' },
  { id: 'recovery', title: '术后恢复中的常见问题', category: '术后恢复', type: '图文', duration: '3分钟', intro: '用简短图文了解术后恢复阶段的基本注意事项。', status: 'DRAFT' },
  { id: 'faq', title: '肺结节健康管理常见问题', category: '常见问题', type: '图文', duration: '4分钟', intro: '集中回答健康管理过程中的常见疑问。', status: 'DRAFT' },
]
const STORAGE_KEY = 'cm-education-content'
export function getKnowledgeItems() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (!Array.isArray(saved)) return knowledgeItems
    const overrides = new Map(saved.map((item) => [item.id, item]))
    return knowledgeItems.map((item) => ({ ...item, ...(overrides.get(item.id) || {}) }))
  } catch { return knowledgeItems }
}
export function publishKnowledgeItem(id) {
  const next = getKnowledgeItems().map((item) => item.id === id ? { ...item, status: 'PUBLISHED', publishedAt: new Date().toISOString() } : item)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}
export function getKnowledgeItem(id) { const items = getKnowledgeItems(); return items.find((item) => item.id === id && item.status === 'PUBLISHED') || items.find((item) => item.status === 'PUBLISHED') }
