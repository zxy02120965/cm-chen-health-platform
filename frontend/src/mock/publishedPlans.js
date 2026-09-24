// 患者端与医护端共用的已发布方案 Mock。方案状态仍由患者基础资料中的 planStatus 决定。
const defaultTasks = {
  diet: { title: '饮食任务', icon: '餐', detail: '规律三餐，按医护审核的份量完成记录。' },
  exercise: { title: '运动任务', icon: '动', detail: '完成低冲击步行或居家活动，按当天状态调整。', plannedDuration: '20分钟' },
  pulmonary: { title: '肺康复任务', icon: '肺', detail: '完成缩唇呼吸训练，并记录训练感受。', plannedCount: '2组' },
}
export const mockPublishedPlans = {
  default: { version: 'V1', publishedAt: '2026-09-03', stage: '术前营养与功能准备', cycle: '第1周', goal: '营养充分、保护肌肉，稳步完成术前功能准备', goalNote: '下一周结合体重、体脂率和腰围复评。', monitoring: '按医护要求记录体重、体脂率和腰围；每周复评一次。', caution: '出现明显不适时先停止并联系医护。', tasks: defaultTasks },
  P001: { version: 'V1', publishedAt: '2026-09-03', stage: '术前营养与功能准备', cycle: '第1周', goal: '营养充分、保护肌肉，稳步完成术前功能准备', goalNote: '下一周结合体重、体脂率和腰围复评。', monitoring: '按医护要求记录体重、体脂率和腰围；每周复评一次。', caution: '出现明显不适时先停止并联系医护。', tasks: defaultTasks },
  P004: { version: 'V2', publishedAt: '2026-09-02', stage: '术前功能维持', cycle: '第2周', goal: '维持营养摄入，逐步提高日常活动耐力', goalNote: '按本周记录结果进入下一次复评。', monitoring: '每日记录运动和肺预康复，按周记录身体数据。', caution: '训练中出现明显不适时停止并联系医护。', tasks: { ...defaultTasks, exercise: { ...defaultTasks.exercise, detail: '步行训练与肩关节活动交替完成。', plannedDuration: '25分钟' } } },
}
export function getPublishedPlan(id) { return mockPublishedPlans[id] || mockPublishedPlans.default }
