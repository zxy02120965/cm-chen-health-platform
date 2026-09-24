<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { assessmentSections } from '../../config/assessmentQuestions'
import { api } from '../../api/client'
import { assessmentData, assessmentResultData, consultationData, dailyRecordData, getPatientView, patientProfileData, planData, savePlanDraft, addPlanReview, setPlanStatus, publishPlan, refreshPatientFromApi, reviewAssessment } from '../../stores/patientStore'
import { labelFor, labelsFor } from '../../config/enumLabels'

const route = useRoute()
const patient = computed(() => getPatientView(route.params.id))
const tab = ref('overview')
const assessment = computed(() => assessmentData(route.params.id))
const assessmentResult = computed(() => { const value = assessmentResultData(route.params.id); return { ...value, safety: labelFor(value.safety, 'safety_level') } })
const records = computed(() => dailyRecordData(route.params.id))
const consultations = computed(() => consultationData(route.params.id))
const plan = ref(planData(route.params.id))
const editing = ref(false); const reviewOpen = ref(false); const reviewText = ref(''); const publishConfirm = ref(false); const draftJson = ref('')
const openDays = ref([1, 'exercise-1'])
const rawStructuredPlan = computed(() => plan.value?.draft || plan.value || {})
const hasValue = (value) => value !== null && value !== undefined && value !== '' && !(Array.isArray(value) && !value.length)
const nestedValue = (value) => {
  if (!hasValue(value)) return ''
  if (Array.isArray(value)) return value.map(nestedValue).filter(Boolean).join('、')
  if (typeof value === 'object') {
    const name = value.name || value.ingredient_name || value.ingredientName || value.dish_name || value.component_id
    const amount = value.amount ?? value.ingredient_amount ?? value.ingredientAmount
    const unit = value.unit || ''
    const basisValue = value.raw_or_cooked_basis || value.basis || ''
    const basis = ['生重', '熟重', '可食部'].find((item) => String(basisValue).includes(item)) || ''
    const method = value.cooking_method || value.method || ''
    const amountText = amount !== undefined && amount !== null ? `${formatNumber(amount)}${unit}` : ''
    if (name || amount !== undefined) return [name, amountText, basis, method].filter(Boolean).join(' ')
    return Object.entries(value).map(([key, item]) => `${key}：${nestedValue(item)}`).filter(Boolean).join('；')
  }
  return typeof value === 'number' ? formatNumber(value) : String(value)
}
const listValue = (value) => nestedValue(value)
function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  return Number(number.toFixed(digits)).toString()
}
const mealLabels = { breakfast: '早餐', lunch: '午餐', snack: '加餐', dinner: '晚餐' }
const mealLabel = (value) => mealLabels[value] || value || ''
const explicitBasis = (value) => ['生重', '熟重', '可食部'].find((item) => String(value || '').includes(item)) || ''
function ingredientRows(component) {
  const source = component?.ingredient_name || component?.ingredients || component?.ingredient_amount || component?.ingredient_amounts
  const flatten = (value) => Array.isArray(value) ? value.flatMap(flatten) : value ? [value] : []
  return flatten(source).map((item) => {
    if (!item || typeof item !== 'object') return { name: String(item), amount: '', basis: '', method: '' }
    return {
      name: item.ingredient_name || item.name || item.ingredientName || '',
      amount: item.amount ?? item.ingredient_amount ?? item.ingredientAmount,
      unit: item.unit || '',
      basis: explicitBasis(item.raw_or_cooked_basis || item.basis),
      method: item.cooking_method || item.method || '',
    }
  }).filter((item) => item.name || item.amount !== undefined)
}
const mealDistribution = (value) => {
  if (!value || typeof value !== 'object') return ''
  const labels = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }
  return Object.entries(value).map(([key, range]) => `${labels[key] || key} ${Array.isArray(range) ? `${formatNumber(range[0])}–${formatNumber(range[1])}%` : (typeof range === 'number' ? formatNumber(range) : range)}`).join(' · ')
}
const structuredPlan = computed(() => {
  const raw = rawStructuredPlan.value; const validation = raw.validation_result || {}; const content = validation.content_validation || validation.nutrition_plan_validation || '待校验'; const publish = validation.publish_validation || (raw.publication_blocked ? 'BLOCKED' : 'PASS')
  const diet = raw.diet_plan ? { ...raw.diet_plan, displayMealDistribution: mealDistribution(raw.diet_plan.meal_distribution) } : raw.diet_plan
  return { ...raw, diet_plan: diet, draft_source: labelFor(raw.draft_source || 'RULE_BASED_PENDING', 'draft_source'), goal_source: labelFor(raw.goal_source, 'goal_source'), safety_level: labelFor(raw.safety_level, 'safety_level'), validation_result: { ...validation, content_validation: content, publish_validation: publish } }
})
const candidateDraft = computed(() => rawStructuredPlan.value.candidate_draft === true || rawStructuredPlan.value.draft_source === 'CANDIDATE_MDT')
const weekDays = computed(() => (structuredPlan.value.weekly_schedule || []).map((day, index) => ({ ...day, day: day.day || index + 1 })))
const statusText = (value) => labelFor(value, 'plan_status')
const displayStatus = (value) => value === 'PUBLISHED' ? '已发布给患者' : statusText(value)
const shown = (value) => hasValue(value) ? (typeof value === 'object' ? nestedValue(value) : value) : ''
const macroLabel = (value) => { if (!hasValue(value)) return ''; if (value.min_pct != null && value.max_pct != null) return `${formatNumber(value.min_pct)}–${formatNumber(value.max_pct)}%能量`; return shown(value) }
const cleanDisplay = (value) => shown(value).replace(/[,，]?具体目标待医护确认/g, '').trim()
function toggleDay(day) { openDays.value = openDays.value.includes(day) ? openDays.value.filter((item) => item !== day) : [...openDays.value, day] }
function mealComponents(meal) { return meal?.components?.length ? meal.components : (meal ? [meal] : []) }
function dose(item) { return [item.duration != null ? `${formatNumber(item.duration)}分钟` : item.duration_range || item.duration_or_reps || item.dose_range || item.candidate_dose, item.repetitions != null ? `${formatNumber(item.repetitions)}次` : item.reps_range, item.sets != null ? `${formatNumber(item.sets)}组` : item.sets_range, item.intensity || item.intensity_range ? `强度：${item.intensity || item.intensity_range}` : ''].map((value) => String(value || '').replace(/（项目草案）|\(项目草案\)|（候选）|\(候选\)/g, '').trim()).filter(Boolean).filter((value, index, all) => all.indexOf(value) === index).join(' · ') }
const surgeryWindow = computed(() => assessment.value?.q6_surgeryWindow || plan.value?.surgery_window || plan.value?.management_period?.surgery_window || patient.value?.surgeryWindow || patient.value?.surgery_window || '未确定')
const safetySummary = computed(() => {
  const raw = rawStructuredPlan.value
  const level = raw.safety_level || 'green'
  const blocked = level === 'red' || raw.goal_conflict === true || raw.publication_blocked === true
  return {
    level: labelFor(level, 'safety_level'),
    trigger: raw.safety_rules?.triggered_items || raw.safety_rules?.triggered_rules || (blocked ? '存在当前方案阻断项' : '无'),
    nutrition: !blocked,
    enhanced: raw.enhanced_eligible === true && !blocked,
    aerobic: !blocked && weekDays.value.some((day) => (day.aerobic || []).length),
    resistance: !blocked && weekDays.value.some((day) => (day.resistance || []).length),
    progression: !blocked,
    pulmonary: !blocked && (raw.pulmonary_prehab_plan || []).length > 0,
    publish: plan.value?.status === 'PUBLISHED' || (raw.publish_eligible === true && !blocked),
    stop: raw.safety_rules?.stop_conditions || raw.stop_conditions || '',
    escalation: raw.safety_rules?.escalation || '出现暂停条件时停止相关任务并联系医护。',
  }
})
const dayExercises = (day, key) => Array.isArray(day?.[key]) ? day[key] : []
const energyTriplet = computed(() => [rawStructuredPlan.value.energy_calculation?.ree_value, rawStructuredPlan.value.energy_calculation?.pal, rawStructuredPlan.value.energy_calculation?.tee_base].filter(hasValue).map((value) => formatNumber(value)).join(' / '))
async function refresh() { await refreshPatientFromApi(route.params.id, true); plan.value = planData(route.params.id) }
onMounted(refresh); onActivated(refresh)
function displayAssessment(field) { const value = field.type === 'profile_ref' ? patientProfileData(route.params.id)[field.profileKey] : assessment.value[field.key]; if (field.type === 'q56_goal' && value && typeof value === 'object') return value.has_clinician_goal ? `首要目标：${labelFor(value.primary_goal, 'primary_goal')}；其他重点：${labelsFor(value.secondary_goals || [], 'secondary_goal') || '无'}` : '未设定医护目标，按A–F默认规则生成'; return Array.isArray(value) ? value.map((item) => labelFor(item, 'secondary_goal')).join('、') || '待填写' : hasValue(value) ? value : '待填写' }
const tabs = [['overview', '总览'], ['archive', '患者档案'], ['result', '评估结果'], ['plan', '方案管理'], ['monitor', '数据监测'], ['consult', '咨询记录'], ['history', '历史记录']]
function beginEdit() { draftJson.value = JSON.stringify(plan.value.draft || {}, null, 2); editing.value = true }
async function saveDraft() { try { plan.value = await savePlanDraft(route.params.id, JSON.parse(draftJson.value || '{}')); editing.value = false; await refresh() } catch { window.alert('方案保存失败，请检查内容格式') } }
async function saveReview() { if (!reviewText.value.trim()) return; try { await api.reviewPlan(route.params.id, 'start_review', 1, reviewText.value.trim()); plan.value = addPlanReview(route.params.id, { comment: reviewText.value.trim(), reviewer: '审核医护' }); reviewText.value = ''; reviewOpen.value = false; await refresh() } catch { window.alert('审核意见保存失败') } }
async function approveDraft() { try { plan.value = await setPlanStatus(route.params.id, 'APPROVED_PENDING_MDT_ACTIVATION'); await refresh() } catch (error) { window.alert(error?.response?.data?.detail || '审核未完成，请检查方案校验') } }
async function returnDraft() { try { plan.value = await setPlanStatus(route.params.id, 'RETURNED'); await refresh() } catch (error) { window.alert(error?.response?.data?.detail || '退回失败') } }
async function confirmPublish() { try { plan.value = await publishPlan(route.params.id); publishConfirm.value = false; await refresh() } catch (error) { window.alert(error?.response?.data?.detail || '当前方案仍不可发布') } }
async function completeAssessmentReview() { await reviewAssessment(route.params.id); await refresh() }
</script>

<template>
  <section class="care-page">
    <RouterLink to="/care/patients" class="care-back">← 返回患者列表</RouterLink>
    <section class="patient-summary-care"><div class="patient-avatar-care">{{ patient.name?.slice(0, 1) }}</div><div><h2>{{ patient.name }}</h2><p>{{ patient.id }} · {{ patient.sex }} · {{ patient.age }} · 距手术：{{ surgeryWindow }}</p></div><span class="care-status" :class="patient.safety">{{ patient.safety === 'red' ? '红色重点' : patient.safety === 'yellow' ? '黄色关注' : '绿色安全' }}</span></section>
    <div class="care-tabs detail-tabs"><button v-for="item in tabs" :key="item[0]" :class="{ active: tab === item[0] }" @click="tab = item[0]">{{ item[1] }}</button></div>

    <section v-if="tab === 'overview'" class="care-panel detail-panel"><h2>患者总览</h2><div class="care-detail-grid"><div><span>A-F基础表型</span><strong>{{ patient.phenotype }}</strong></div><div><span>疾病/代谢风险</span><strong>{{ patient.diseaseRisk }}</strong></div><div><span>安全等级</span><strong>{{ patient.safety }}</strong></div><div><span>当前方案</span><strong>{{ statusText(plan.status) }}</strong></div></div></section>
    <section v-else-if="tab === 'archive'" class="care-panel detail-panel"><h2>患者档案 · Q1–Q56 · V1.2</h2><div v-for="section in assessmentSections" :key="section.id" class="archive-care-section"><h3>{{ section.icon }} {{ section.title }}</h3><div v-for="field in section.fields" :key="field.key" class="care-question"><span>Q{{ field.questionId }} · {{ field.label }}</span><em>{{ displayAssessment(field) }}</em></div></div></section>
    <section v-else-if="tab === 'result'" class="care-panel detail-panel"><h2>评估结果</h2><div class="result-care-cards"><div><span>数据充分度</span><strong>{{ assessmentResult.completion > 60 ? '较充分' : '需补充' }}</strong></div><div><span>A-F基础表型</span><strong>{{ assessmentResult.phenotype }}</strong></div><div><span>安全等级</span><strong>{{ assessmentResult.safety }}</strong></div></div><p class="care-note">评估状态：{{ assessmentResult.status }}</p><button v-if="assessmentResult.status === 'SUBMITTED'" class="primary-care" @click="completeAssessmentReview">完成评估审核</button></section>

    <section v-else-if="tab === 'plan'" class="care-panel detail-panel plan-v21">
      <div class="care-panel-head"><div><p class="eyebrow">V2.1 第一周执行方案</p><h2>方案管理</h2><p class="care-note">{{ displayStatus(plan.status) }}<template v-if="plan.status !== 'PUBLISHED' && structuredPlan.draft_source"> · {{ structuredPlan.draft_source }}</template></p></div><span class="care-status" :class="plan.status === 'PUBLISHED' ? 'green' : 'yellow'">{{ displayStatus(plan.status) }}</span></div>
      <div v-if="candidateDraft && plan.status !== 'PUBLISHED'" class="governance-notice"><strong>系统候选方案｜仅供医护审核</strong><span>候选规则来源已保留审计信息，患者端仅显示正式发布版本。</span></div>

      <article class="plan-section"><h3>1. 当前管理周期与患者状态</h3><div class="plan-stat-grid"><div><span>管理阶段</span><strong>{{ shown(structuredPlan.management_period?.stage) }}</strong></div><div><span>距手术</span><strong>{{ surgeryWindow }}</strong></div><div><span>方案周期</span><strong>第1周</strong></div><div><span>当前状态</span><strong>{{ displayStatus(plan.status) }}</strong></div></div></article>
      <article class="plan-section"><h3>2. A-F表型与安全等级</h3><div class="plan-stat-grid"><div><span>主表型</span><strong>{{ shown(structuredPlan.phenotype || patient.phenotype) }}</strong></div><div><span>安全状态</span><strong>{{ shown(structuredPlan.safety_level) }}</strong></div><div><span>强化减脂资格</span><strong>{{ structuredPlan.enhanced_eligible ? '符合' : '不符合' }}</strong></div></div></article>
      <article class="plan-section"><h3>3. 本阶段管理目标</h3><p class="goal-highlight">{{ shown(structuredPlan.stage_goals?.overall_goal) }}</p><div class="plan-inline-values"><span v-if="hasValue(structuredPlan.stage_goals?.weight_goal)">体重目标：{{ structuredPlan.stage_goals.weight_goal }} kg</span><span v-if="hasValue(structuredPlan.stage_goals?.muscle_goal)">肌肉：{{ cleanDisplay(structuredPlan.stage_goals.muscle_goal) }}</span><span v-if="hasValue(structuredPlan.stage_goals?.surgery_preparation_goal)">术前准备：{{ structuredPlan.stage_goals.surgery_preparation_goal }}</span></div></article>
      <article class="plan-section"><h3>4. 能量与营养计算</h3><div class="plan-stat-grid"><div v-if="energyTriplet"><span>REE / PAL / TEE</span><strong>{{ energyTriplet }}</strong></div><div v-if="hasValue(structuredPlan.energy_calculation?.daily_energy_target_kcal)"><span>每日能量</span><strong>{{ formatNumber(structuredPlan.energy_calculation.daily_energy_target_kcal) }} kcal</strong></div><div v-if="hasValue(structuredPlan.diet_plan?.protein_target)"><span>蛋白质目标</span><strong>{{ formatNumber(structuredPlan.diet_plan.protein_target) }} g</strong></div><div v-if="hasValue(structuredPlan.diet_plan?.carbohydrate_target)"><span>碳水供能范围</span><strong>{{ macroLabel(structuredPlan.diet_plan.carbohydrate_target) }}</strong></div></div><p v-if="hasValue(structuredPlan.diet_plan?.displayMealDistribution)" class="plan-muted">餐次分配：{{ structuredPlan.diet_plan.displayMealDistribution }}</p></article>

      <article class="plan-section diet-section"><div class="section-heading-row"><h3>5. 第1周7天饮食方案</h3><small>默认仅展开第1天，点击日期查看其他天</small></div><div v-for="day in weekDays" :key="day.day" class="day-card"><button class="day-toggle" @click="toggleDay(day.day)"><span>第{{ day.day }}天</span><span>{{ openDays.includes(day.day) ? '收起' : '展开' }}⌄</span></button><div v-if="openDays.includes(day.day)" class="day-content"><div v-for="meal in (day.diet || [])" :key="`${day.day}-${meal.meal_type}-${meal.dish_name}`" class="meal-card"><div class="meal-title"><strong>{{ mealLabel(meal.meal_type) }}</strong><span>{{ meal.dish_name || meal.meal_name }}</span></div><div v-for="component in mealComponents(meal)" :key="`${component.knowledge_item_id}-${component.dish_name}`" class="ingredient-line"><span>{{ component.dish_name || component.meal_name }}</span><div class="ingredient-details"><small v-for="(ingredient, ingredientIndex) in ingredientRows(component)" :key="`${component.knowledge_item_id}-${ingredientIndex}`">{{ ingredient.name }}<template v-if="ingredient.amount !== undefined && ingredient.amount !== null"> {{ formatNumber(ingredient.amount) }}{{ ingredient.unit }}</template><template v-if="ingredient.basis">（{{ ingredient.basis }}）</template><template v-if="ingredient.method"> · {{ ingredient.method }}</template></small></div></div><p class="macro-line">{{ hasValue(meal.estimated_energy) ? `能量 ${formatNumber(meal.estimated_energy)} kcal` : '' }} {{ hasValue(meal.estimated_protein) ? `· 蛋白 ${formatNumber(meal.estimated_protein)}g` : '' }} {{ hasValue(meal.estimated_carbohydrate) ? `· 碳水 ${formatNumber(meal.estimated_carbohydrate)}g` : '' }} {{ hasValue(meal.estimated_fat) ? `· 脂肪 ${formatNumber(meal.estimated_fat)}g` : '' }}</p></div></div></div></article>

      <article class="plan-section"><h3>6. 本周运动处方</h3><div class="v3-weekly-cards"><article v-for="day in weekDays" :key="`exercise-day-${day.day}`" class="v3-day-card"><button class="day-toggle" @click="toggleDay(`exercise-${day.day}`)"><span>第{{ day.day }}天</span><span>{{ openDays.includes(`exercise-${day.day}`) ? '收起' : '展开' }}⌄</span></button><div v-if="openDays.includes(`exercise-${day.day}`)" class="v3-day-content"><template v-if="day.is_training"><section v-if="day.aerobic?.length" class="exercise-category"><h4>有氧</h4><div v-for="item in day.aerobic" :key="`aerobic-${day.day}-${item.exercise_id}`" class="prescription-card"><div><strong>{{ item.exercise_id }} · {{ item.name || item.exercise_name }}</strong><span v-if="dose(item)">{{ dose(item) }}</span></div><p v-if="hasValue(item.purpose)">目的：{{ item.purpose }}</p><p v-if="hasValue(item.steps)">步骤：{{ item.steps }}</p><small v-if="hasValue(item.frequency || item.frequency_range)">频率：{{ item.frequency || item.frequency_range }}</small><small v-if="hasValue(item.precautions)">注意：{{ item.precautions }}</small><small v-if="hasValue(item.stop_conditions)">停止：{{ item.stop_conditions }}</small><small v-if="hasValue(item.alternative_ids || item.alternatives)">替代：{{ listValue(item.alternative_ids || item.alternatives) }}</small></div></section><section v-if="day.resistance?.length" class="exercise-category"><h4>抗阻</h4><div v-for="item in day.resistance" :key="`resistance-${day.day}-${item.exercise_id}`" class="prescription-card"><div><strong>{{ item.exercise_id }} · {{ item.name || item.exercise_name }}</strong><span v-if="dose(item)">{{ dose(item) }}</span></div><p v-if="hasValue(item.purpose)">目的：{{ item.purpose }}</p><p v-if="hasValue(item.steps)">步骤：{{ item.steps }}</p><small v-if="hasValue(item.frequency || item.frequency_range)">频率：{{ item.frequency || item.frequency_range }}</small><small v-if="hasValue(item.precautions)">注意：{{ item.precautions }}</small><small v-if="hasValue(item.stop_conditions)">停止：{{ item.stop_conditions }}</small><small v-if="hasValue(item.alternative_ids || item.alternatives)">替代：{{ listValue(item.alternative_ids || item.alternatives) }}</small></div></section><section v-if="day.flexibility?.length" class="exercise-category"><h4>柔韧/功能</h4><div v-for="item in day.flexibility" :key="`flexibility-${day.day}-${item.exercise_id}`" class="prescription-card"><div><strong>{{ item.exercise_id }} · {{ item.name || item.exercise_name }}</strong><span v-if="dose(item)">{{ dose(item) }}</span></div><p v-if="hasValue(item.purpose)">目的：{{ item.purpose }}</p><p v-if="hasValue(item.steps)">步骤：{{ item.steps }}</p><small v-if="hasValue(item.precautions)">注意：{{ item.precautions }}</small></div></section><p v-if="!day.aerobic?.length && !day.resistance?.length && !day.flexibility?.length" class="plan-muted">恢复/日常活动</p></template><p v-else class="plan-muted">恢复/日常活动</p><p v-if="hasValue(day.stop_conditions)" class="day-stop">停止条件：{{ day.stop_conditions }}</p></div></article></div></article>
      <article class="plan-section"><h3>7. 本周肺预康复</h3><div v-for="item in structuredPlan.pulmonary_prehab_plan || []" :key="item.pulmonary_id || item.name" class="prescription-card"><div><strong>{{ item.pulmonary_id }} · {{ item.name || item.action_name }}</strong><span v-if="dose(item)">{{ dose(item) }}</span></div><p v-if="hasValue(item.purpose)">目的：{{ item.purpose }}</p><p v-if="hasValue(item.steps)">操作要点：{{ item.steps }}</p><small v-if="hasValue(item.frequency || item.frequency_range)">频率：{{ String(item.frequency || item.frequency_range).replace(/（项目草案）|\(项目草案\)/g, '') }}</small><small v-if="hasValue(item.stop_conditions)">停止条件：{{ item.stop_conditions }}</small></div></article>
      <article class="plan-section"><h3>8. 监测计划</h3><p>{{ listValue(structuredPlan.monitoring_plan?.items) }}</p><p v-if="hasValue(structuredPlan.monitoring_plan?.frequency)" class="plan-muted">频率：{{ structuredPlan.monitoring_plan.frequency }}</p></article>
      <article class="plan-section safety-section"><h3>9. 安全规则 / 暂停与升级条件</h3><div class="safety-summary-grid"><div><span>当前安全等级</span><strong>{{ safetySummary.level }}</strong></div><div><span>当前触发项</span><strong>{{ safetySummary.trigger }}</strong></div></div><div class="safety-permissions"><div><span>当前营养方案</span><b>{{ safetySummary.nutrition ? '允许' : '不允许' }}</b></div><div><span>强化减脂</span><b>{{ safetySummary.enhanced ? '允许' : '不允许' }}</b></div><div><span>有氧运动</span><b>{{ safetySummary.aerobic ? '允许' : '不允许' }}</b></div><div><span>抗阻训练</span><b>{{ safetySummary.resistance ? '允许' : '不允许' }}</b></div><div><span>运动进阶</span><b>{{ safetySummary.progression ? '允许' : '不允许' }}</b></div><div><span>肺预康复</span><b>{{ safetySummary.pulmonary ? '允许' : '不允许' }}</b></div><div><span>发布给患者</span><b>{{ safetySummary.publish ? '允许' : '不允许' }}</b></div></div><p v-if="hasValue(structuredPlan.safety_rules?.precautions)">注意事项：{{ structuredPlan.safety_rules.precautions }}</p><p v-if="hasValue(safetySummary.stop)">暂停条件：{{ safetySummary.stop }}</p><p v-if="hasValue(safetySummary.escalation)">升级处理：{{ safetySummary.escalation }}</p></article>
      <article v-if="(structuredPlan.missing_data || []).length" class="plan-section"><h3>10. 待补充资料</h3><p>{{ listValue(structuredPlan.missing_data) }}</p></article>
      <article class="plan-section"><h3>11. 周复评 / 下一周计划</h3><p v-if="hasValue(structuredPlan.weekly_review?.decision)">本周决策：{{ labelFor(structuredPlan.weekly_review.decision, 'weekly_decision') }}</p><p v-if="hasValue(structuredPlan.weekly_review?.reason)">{{ structuredPlan.weekly_review.reason }}</p><p v-if="hasValue(structuredPlan.next_week_adjustment?.status)">{{ structuredPlan.next_week_adjustment.status }}</p></article>
      <article class="plan-section"><h3>12. 医护审核意见与操作</h3><div v-if="reviewOpen" class="review-panel"><label>审核意见<textarea v-model="reviewText"></textarea></label><button class="primary-care" @click="saveReview">保存意见</button></div><div class="care-actions"><button @click="beginEdit">{{ plan.status === 'PUBLISHED' ? '编辑方案/生成新版本' : '编辑方案' }}</button><button @click="reviewOpen = true">添加审核意见</button><template v-if="plan.status !== 'PUBLISHED'"><button @click="returnDraft">退回修改</button><button class="primary-care" :disabled="!structuredPlan.review_eligible" @click="approveDraft">审核通过</button><button class="primary-care" :disabled="!structuredPlan.publish_eligible" @click="publishConfirm = true">发布给患者</button></template><button v-else class="published-action" disabled>已发布</button></div><div v-if="publishConfirm" class="confirm-panel"><strong>确认发布给患者？</strong><button class="primary-care" @click="confirmPublish">确认发布</button><button @click="publishConfirm = false">取消</button></div><div v-if="editing" class="plan-edit-panel"><label>高级编辑（结构化JSON）<textarea v-model="draftJson" rows="16"></textarea></label><div class="care-actions"><button class="primary-care" @click="saveDraft">保存新版本</button><button @click="editing = false">取消</button></div></div></article>
    </section>

    <section v-else-if="tab === 'monitor'" class="care-panel detail-panel"><h2>数据监测</h2><p>最近记录：{{ records.latestDate || '暂无' }}</p></section>
    <section v-else-if="tab === 'consult'" class="care-panel detail-panel"><h2>咨询记录</h2><div v-for="item in consultations" :key="item.id" class="care-task"><strong>{{ item.type }} · {{ item.status }}</strong><span>{{ item.summary }}</span></div></section>
    <section v-else class="care-panel detail-panel"><h2>重要历史记录</h2><p class="care-note">仅展示历史评估、方案版本和重要状态变更。</p></section>
  </section>
</template>
