// 每日打卡 Mock。方案页只读取这些记录展示任务状态，不额外创建“任务完成”字段。
export const mockDailyRecords = {
  P001: {
    latestDate: '2026-09-04',
    diet: { status: 'completed', label: '三餐已记录', detail: '早餐、午餐、晚餐均已完成文字记录' },
    exercise: { status: 'completed', label: '今日已完成', detail: '步行训练 25 分钟', items: [{ type: '步行训练', duration: 25, reps: '', sets: '', intensity: '轻度' }] },
    pulmonary: { status: 'pending', label: '待记录', detail: '完成缩唇呼吸训练后上传记录', items: [{ name: '缩唇呼吸', planned: 3, completed: 0 }] },
  },
  P004: {
    latestDate: '2026-09-04',
    diet: { status: 'completed', label: '三餐已记录', detail: '按方案完成记录' },
    exercise: { status: 'completed', label: '今日已完成', detail: '步行训练 20 分钟', items: [{ type: '步行训练', duration: 20, reps: '', sets: '', intensity: '轻度' }] },
    pulmonary: { status: 'completed', label: '今日已完成', detail: '呼吸训练 10 分钟', items: [{ name: '缩唇呼吸', planned: 3, completed: 3 }] },
  },
}

// 已发布方案任务 Mock：患者端只读取 plan 字段，不能修改；actual 字段由患者每日提交。
// 未来接入真实业务时对应 PublishedPlan → DailyTask → PatientRecord。
export const mockPublishedPlanTasks = {
  default: {
    exercise: [
      { type: '步行训练', duration: 30, reps: '', sets: 1 },
      { type: '肩关节活动', duration: 10, reps: 10, sets: 2 },
      { type: '拉伸训练', duration: 10, reps: 8, sets: 2 },
      { type: '肌力训练', duration: 15, reps: 12, sets: 2 },
      { type: '燃脂操', duration: 20, reps: '', sets: 1 },
      { type: '其他', duration: 10, reps: '', sets: 1 },
    ],
    pulmonary: [
      { name: '缩唇呼吸', times: 3, duration: 5, sets: 1 },
      { name: '腹式呼吸', times: 3, duration: 5, sets: 1 },
      { name: '呼吸操', times: 2, duration: 10, sets: 1 },
      { name: '步行配合呼吸', times: 1, duration: 15, sets: 1 },
      { name: '其他', times: '', duration: '', sets: '' },
    ],
  },
  P001: {
    exercise: [
      { type: '步行训练', duration: 30, reps: '', sets: 1 },
      { type: '肩关节活动', duration: 10, reps: 10, sets: 2 },
      { type: '拉伸训练', duration: 10, reps: 8, sets: 2 },
    ],
    pulmonary: [
      { name: '缩唇呼吸', times: 3, duration: 5, sets: 1 },
      { name: '腹式呼吸', times: 3, duration: 5, sets: 1 },
    ],
  },
}
