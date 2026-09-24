// 兼容旧页面的导出入口；字段定义统一维护在 config/assessmentQuestions.js。
export { assessmentSections, assessmentQuestionCount, assessmentQuestionList, getSection } from '../config/assessmentQuestions'

export const mockAssessmentResults = {
  P001: { completion: 86, phenotype: 'B｜肥胖＋代谢异常', focus: ['规律三餐与蛋白质摄入', '循序渐进的肺预康复', '每周复测体重、体脂率和腰围'], safety: 'yellow' },
  P002: { completion: 100, phenotype: 'D｜营养风险', focus: ['保障能量和蛋白质摄入', '记录食欲与进食量'], safety: 'green' },
}

export const mockMedicalFiles = [
  { id: 'F001', patientId: 'P001', type: '胸部CT', date: '2026-08-25', name: '胸部CT报告-0825.pdf', status: '已保存', note: '待医护查看' },
  { id: 'F002', patientId: 'P001', type: '检验报告', date: '2026-08-28', name: '代谢检查记录.jpg', status: '已保存', note: '' },
]
