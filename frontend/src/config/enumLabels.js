// UI-only labels. API/RDS continue to use stable English codes.
export const enumLabels = {
  primary_goal: {
    STANDARD_FAT_LOSS: '标准减脂', ENHANCED_FAT_LOSS: '强化减脂',
    WEIGHT_MAINTENANCE_MUSCLE_PRESERVATION: '体重维持/保肌',
    NUTRITION_RECOVERY_WEIGHT_GAIN: '营养恢复/增重', STOP_WEIGHT_LOSS: '停止继续下降',
    MUSCLE_GAIN: '增肌', METABOLIC_CONTROL: '代谢控制', FUNCTION_IMPROVEMENT: '提高运动能力',
    PULMONARY_IMPROVEMENT: '改善肺功能', COMPREHENSIVE_PREOP: '术前综合准备',
  },
  secondary_goal: {
    MUSCLE_PRESERVATION: '保肌', BODY_FAT_REDUCTION: '降低体脂', WAIST_REDUCTION: '缩小腰围',
    GLUCOSE_CONTROL: '控糖', LIPID_CONTROL: '降脂', URIC_ACID_CONTROL: '降尿酸',
    FUNCTION_IMPROVEMENT: '提高运动能力', PULMONARY_IMPROVEMENT: '改善肺功能',
  },
  goal_source: { Q56_CLINICIAN: '医护指导目标', SYSTEM_DEFAULT_AF: 'A-F系统默认目标' },
  energy_mode: {
    STANDARD_FAT_LOSS: '标准减脂', ENHANCED_FAT_LOSS: '强化减脂',
    MUSCLE_PRESERVATION: '保肌模式', NUTRITION_RECOVERY: '营养恢复',
    STOP_WEIGHT_LOSS: '停止继续下降', SAFE_EXECUTABLE: '安全可执行模式',
  },
  safety_level: { green: '绿色/安全', yellow: '黄色/重点关注', red: '红色/重点处理' },
  plan_status: {
    AI_GENERATED_PENDING_REVIEW: '规则生成待审核', RULE_GENERATED_PENDING_REVIEW: '规则生成待审核',
    AI_ASSISTED_PENDING_REVIEW: 'AI辅助生成待审核', PENDING_REVIEW: '待审核', IN_REVIEW: '审核中',
    APPROVED_PENDING_PUBLISH: '审核通过', APPROVED_PENDING_MDT_ACTIVATION: '医护审核通过', READY_TO_PUBLISH: '待发布', PUBLISHED: '已发布', RETURNED: '已退回', PAUSED: '已暂停',
  },
  draft_source: { ACTIVE_MDT: '正式MDT参数', CANDIDATE_MDT: '系统生成候选方案', RULE_BASED_PENDING: '规则生成待审核' },
  weekly_decision: {
    MAINTAIN: '维持当前方案', BARRIER_FIRST: '先处理执行障碍', DATA_INSUFFICIENT: '数据不足',
    PRESERVE_MUSCLE: '优先保护肌肉', NUTRITION_RECOVERY: '营养恢复', INTENSIFY_CANDIDATE: '可评估强化',
    DEINTENSIFY: '降低方案强度', SAFETY_REVIEW: '安全复核',
  },
}

export function labelFor(value, domain) {
  if (value === null || value === undefined || value === '') return '待医护确认'
  const map = enumLabels[domain] || {}
  return map[value] || value
}

export function labelsFor(values, domain) {
  if (!Array.isArray(values)) return labelFor(values, domain)
  return values.map((value) => labelFor(value, domain)).join('、')
}
