// 患者端和医护端共用同一份咨询 Mock；双方通过 patientId 关联同一业务对象。
export const mockConsultations = [
  { id: 'C001', patientId: 'P001', createdAt: '2026-09-04 09:10', type: '方案问题', summary: '本周运动是否需要调整？', status: '待回复', handling: '待处理', reply: '', repliedBy: '', messages: [{ from: 'patient', text: '本周运动是否需要调整？', at: '2026-09-04 09:10' }], updatedAt: '2026-09-04 09:10' },
  { id: 'C002', patientId: 'P003', createdAt: '2026-09-03 16:20', type: '指标变化', summary: '体重记录后有些波动，需要关注吗？', status: '已回复', handling: '处理中', reply: '请继续按计划记录，复评时一起查看趋势。', repliedBy: '审核医护', messages: [{ from: 'patient', text: '体重记录后有些波动，需要关注吗？', at: '2026-09-03 16:20' }, { from: 'clinician', text: '请继续按计划记录，复评时一起查看趋势。', at: '2026-09-03 17:05' }], updatedAt: '2026-09-03 17:05' },
  { id: 'C003', patientId: 'P005', createdAt: '2026-09-02 11:40', type: '肺预康复', summary: '训练时出现轻微气促。', status: '待回复', handling: '待处理', reply: '', repliedBy: '', messages: [{ from: 'patient', text: '训练时出现轻微气促。', at: '2026-09-02 11:40' }], updatedAt: '2026-09-02 11:40' },
  { id: 'C004', patientId: 'P004', createdAt: '2026-09-01 14:30', type: '饮食', summary: '想确认蛋白质摄入记录方式。', status: '已完成', handling: '已完成', reply: '可以按家庭估算方式记录。', repliedBy: '审核医护', messages: [{ from: 'patient', text: '想确认蛋白质摄入记录方式。', at: '2026-09-01 14:30' }, { from: 'clinician', text: '可以按家庭估算方式记录。', at: '2026-09-01 15:00' }], updatedAt: '2026-09-01 15:00' },
]
