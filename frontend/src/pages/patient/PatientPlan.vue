<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import StatePanel from '../../components/common/StatePanel.vue'
import { assessmentData, currentPatient, dailyRecordData, planData, refreshPatientFromApi } from '../../stores/patientStore'

const patient = currentPatient
const assessment = computed(() => assessmentData(patient.value.id))
const plan = computed(() => planData(patient.value.id))
const isPublished = computed(() => plan.value.status === 'PUBLISHED')
const records = computed(() => dailyRecordData())
const structured = computed(() => (isPublished.value ? (plan.value.draft || plan.value) : {}))
const weekDays = computed(() => (structured.value.weekly_schedule || []).map((day, index) => ({ ...day, day: day.day || index + 1 })))
const todayDay = 1
const today = computed(() => weekDays.value.find((day) => day.day === todayDay) || weekDays.value[0] || null)
const showFullWeek = ref(false)
const openFullDays = ref([todayDay])
const mealLabels = { breakfast: '早餐', lunch: '午餐', snack: '加餐', dinner: '晚餐' }
const hasValue = (value) => value !== null && value !== undefined && value !== '' && !(Array.isArray(value) && !value.length)
function formatNumber(value, digits = 1) { if (!hasValue(value)) return ''; const number = Number(value); return Number.isFinite(number) ? Number(number.toFixed(digits)).toString() : String(value) }
function cleanText(value) { return String(value || '').replace(/（项目草案）|\(项目草案\)|（候选）|\(候选\)|原文口径|按组件原文重量口径|需MDT统一|MDT确认|MDT/g, '').replace(/同[A-Z]\d+/g, '按同类安全提示').trim() }
function flatten(value) { return Array.isArray(value) ? value.flatMap(flatten) : hasValue(value) ? [value] : [] }
function ingredientRows(component) {
  const source = component?.ingredient_name || component?.ingredients || component?.ingredient_amount || component?.ingredient_amounts
  return flatten(source).map((item) => {
    if (!item || typeof item !== 'object') return { name: String(item), amount: '', unit: '', basis: '', method: '' }
    const basisRaw = item.raw_or_cooked_basis || item.basis || ''
    return { name: item.ingredient_name || item.name || item.ingredientName || '', amount: item.amount ?? item.ingredient_amount ?? item.ingredientAmount, unit: item.unit || '', basis: ['生重', '熟重', '可食部'].find((basis) => String(basisRaw).includes(basis)) || '', method: cleanText(item.cooking_method || item.method || '') }
  }).filter((item) => item.name || item.amount !== undefined)
}
function mealComponents(meal) { return meal?.components?.length ? meal.components : (meal ? [meal] : []) }
function mealTitle(meal) { return meal?.dish_name || meal?.meal_name || '' }
function shown(value, fallback = '') {
  if (!hasValue(value)) return fallback
  if (Array.isArray(value)) return value.map((item) => shown(item, '')).filter(Boolean).join('、') || fallback
  if (typeof value === 'object') {
    return Object.values(value).map((item) => shown(item, '')).filter(Boolean).join('、') || fallback
  }
  return cleanText(typeof value === 'number' ? formatNumber(value) : value)
}
function dose(item) {
  const parts = []
  if (hasValue(item.duration)) parts.push(formatNumber(item.duration) + '分钟')
  else if (hasValue(item.duration_range)) parts.push(cleanText(item.duration_range))
  else if (hasValue(item.duration_or_reps)) parts.push(cleanText(item.duration_or_reps))
  else if (hasValue(item.dose_range)) parts.push(cleanText(item.dose_range))
  if (hasValue(item.repetitions)) parts.push(formatNumber(item.repetitions) + '次')
  else if (hasValue(item.reps_range)) parts.push(cleanText(item.reps_range))
  if (hasValue(item.sets)) parts.push(formatNumber(item.sets) + '组')
  else if (hasValue(item.sets_range)) parts.push(cleanText(item.sets_range))
  if (hasValue(item.intensity || item.intensity_range)) parts.push('强度：' + cleanText(item.intensity || item.intensity_range))
  return [...new Set(parts.filter(Boolean))].join(' · ')
}
const tasks = computed(() => {
  const configured = plan.value.draft?.tasks || plan.value.tasks || {}
  return ['diet', 'exercise', 'pulmonary'].map((key) => {
    const fallback = { diet: { title: '饮食任务', icon: '餐', detail: '按医护审核的方案完成饮食记录。' }, exercise: { title: '运动任务', icon: '动', detail: '按医护审核的方案完成运动记录。' }, pulmonary: { title: '肺康复任务', icon: '肺', detail: '按医护审核的方案完成肺康复记录。' } }[key]
    const record = records.value[key] || {}
    return { key, ...fallback, ...(configured[key] || {}), status: record.status || 'pending', label: record.label || '待记录' }
  })
})
function statusText(status) { return status === 'completed' ? '已完成' : status === 'attention' ? '需关注' : '待记录' }
const surgeryWindow = computed(() => assessment.value?.q6_surgeryWindow || structured.value.surgery_window || structured.value.management_period?.surgery_window || '未确定')
function toggleFullDay(day) {
  openFullDays.value = openFullDays.value.includes(day)
    ? openFullDays.value.filter((item) => item !== day)
    : [...openFullDays.value, day]
}
onMounted(() => refreshPatientFromApi(patient.value.id, false))
onActivated(() => refreshPatientFromApi(patient.value.id, false))
</script>

<template>
  <section class="patient-page plan-page">
    <div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">距手术：{{ surgeryWindow }}</p><h1>专属方案</h1></div></div>
    <StatePanel v-if="!isPublished" icon="◇" title="当前暂无已发布方案" text="AI草稿必须经过医护审核后才会显示给你。" />
    <template v-else>
      <section class="mobile-card plan-meta"><div><p class="eyebrow">当前管理周期</p><h2>第1周 · 距手术：{{ surgeryWindow }}</h2></div><span class="published-mark">已发布</span></section>
      <section class="mobile-card plan-goal"><p class="eyebrow">本周管理目标</p><h2 v-if="shown(structured.stage_goals?.overall_goal) || shown(plan.goal)">{{ shown(structured.stage_goals?.overall_goal) || shown(plan.goal) }}</h2><div class="goal-list"><span v-if="hasValue(structured.stage_goals?.muscle_goal)">保护肌肉</span><span v-if="hasValue(structured.stage_goals?.body_fat_goal)">降低体脂</span><span v-if="hasValue(structured.stage_goals?.waist_goal)">改善腰围</span><span v-if="hasValue(structured.stage_goals?.functional_goal)">提升运动能力</span><span v-if="hasValue(structured.stage_goals?.surgery_preparation_goal)">完成术前准备</span></div></section>
       <section class="mobile-card today-center"><div class="card-title-row"><div><p class="eyebrow">今日执行中心 · 第{{ today?.day || 1 }}天</p><h2>今天按计划完成并记录</h2></div></div><section class="today-module"><div class="today-module-head"><h3>今日饮食</h3><RouterLink to="/patient/records/diet">记录今日饮食</RouterLink></div><div v-if="today?.diet?.length" class="today-meal-list"><article v-for="meal in today.diet" :key="meal.meal_type" class="today-meal"><div class="meal-title"><strong>{{ mealLabels[meal.meal_type] || '餐次' }}</strong><span>{{ mealTitle(meal) }}</span></div><div v-for="component in mealComponents(meal)" :key="component.knowledge_item_id || component.dish_name" class="patient-ingredient"><b>{{ component.dish_name || component.meal_name }}</b><small v-for="(ingredient, index) in ingredientRows(component)" :key="index">{{ ingredient.name }}<template v-if="ingredient.amount !== undefined && ingredient.amount !== null"> {{ formatNumber(ingredient.amount) }}{{ ingredient.unit }}</template><template v-if="ingredient.basis">（{{ ingredient.basis }}）</template><template v-if="ingredient.method"> · {{ ingredient.method }}</template></small></div><p class="patient-macros">{{ hasValue(meal.estimated_energy) ? '能量 ' + formatNumber(meal.estimated_energy) + ' kcal' : '' }} {{ hasValue(meal.estimated_protein) ? '· 蛋白 ' + formatNumber(meal.estimated_protein) + 'g' : '' }}</p></article></div><p v-else class="patient-empty">今日暂无饮食安排</p></section><section class="today-module"><div class="today-module-head"><h3>今日运动</h3><RouterLink to="/patient/records/exercise">记录运动完成情况</RouterLink></div><div v-for="group in [{ key: 'aerobic', label: '有氧' }, { key: 'resistance', label: '抗阻' }, { key: 'flexibility', label: '柔韧/功能' }]" :key="group.key" class="patient-exercise-group"><h4 v-if="today?.[group.key]?.length">{{ group.label }}</h4><article v-for="item in (today?.[group.key] || [])" :key="item.exercise_id || item.name" class="patient-task-card"><div><b>{{ item.name || item.exercise_name }}</b><small v-if="item.exercise_id">动作编号：{{ item.exercise_id }}</small></div><span v-if="dose(item)">{{ dose(item) }}</span><p v-if="item.stop_conditions">停止条件：{{ cleanText(item.stop_conditions) }}</p></article></div><p v-if="today && !today.aerobic?.length && !today.resistance?.length && !today.flexibility?.length" class="patient-empty">今日为恢复/日常活动</p></section><section class="today-module"><div class="today-module-head"><h3>今日肺预康复</h3><RouterLink to="/patient/records/pulmonary">记录完成情况</RouterLink></div><article v-for="item in (today?.pulmonary_prehab || structured.pulmonary_prehab_plan || []).filter((item) => hasValue(dose(item)))" :key="item.pulmonary_id || item.name" class="patient-task-card"><div><b>{{ item.name || item.action_name }}</b><small v-if="item.pulmonary_id">项目编号：{{ item.pulmonary_id }}</small></div><span v-if="dose(item)">{{ dose(item) }}</span><p v-if="item.steps">操作要点：{{ cleanText(item.steps) }}</p><p v-if="item.stop_conditions">停止条件：{{ cleanText(item.stop_conditions) }}</p></article></section><section class="today-module monitoring-module"><div class="today-module-head"><h3>今日监测/记录</h3><RouterLink to="/patient/records">去记录</RouterLink></div><p>体重、体脂率、腰围、饮食、运动、肺预康复及疲劳/气促/疼痛均在记录后更新。</p></section></section>
      <section class="mobile-card safety-patient"><p class="eyebrow">安全提醒</p><p>如出现胸痛、明显气促、头晕、咯血等情况，请立即停止训练并联系医护。</p></section>
      <section class="mobile-card plan-section"><p class="eyebrow">今日监测</p><h3>{{ shown(structured.monitoring_plan?.instructions, '按计划完成每日记录') }}</h3><p v-if="structured.monitoring_plan?.items">监测项目：{{ shown(structured.monitoring_plan.items) }}</p></section>
      <section class="mobile-card full-week-section"><button class="full-week-toggle" @click="showFullWeek = !showFullWeek">{{ showFullWeek ? '收起本周完整方案' : '查看本周完整方案' }} <span>{{ showFullWeek ? '⌃' : '⌄' }}</span></button><div v-if="showFullWeek" class="full-week-list"><article v-for="day in weekDays" :key="day.day" class="full-day-card"><button class="day-toggle" @click="toggleFullDay(day.day)"><span>第{{ day.day }}天{{ day.day === (today?.day || 1) ? ' · 今日' : '' }}</span><span>{{ openFullDays.includes(day.day) ? '收起' : '展开' }}</span></button><div v-if="openFullDays.includes(day.day)" class="full-day-content"><div v-for="meal in (day.diet || [])" :key="meal.meal_type" class="compact-line"><b>{{ mealLabels[meal.meal_type] || '餐次' }}</b><span>{{ mealTitle(meal) }}</span></div><div v-for="group in [{ key: 'aerobic', label: '有氧' }, { key: 'resistance', label: '抗阻' }, { key: 'flexibility', label: '柔韧/功能' }]" :key="group.key"><p v-if="day[group.key]?.length" class="compact-group-title">{{ group.label }}</p><div v-for="item in (day[group.key] || [])" :key="item.exercise_id || item.name" class="compact-line"><span>{{ item.name || item.exercise_name }}</span><small>{{ dose(item) }}</small></div></div><div v-for="item in (day.pulmonary_prehab || []).filter((item) => hasValue(dose(item)))" :key="item.pulmonary_id || item.name" class="compact-line"><span>肺预康复：{{ item.name || item.action_name }}</span><small>{{ dose(item) }}</small></div></div></article></div></section>
    </template>
    <p class="patient-footnote">患者端只显示已由医护审核并发布的方案。</p>
  </section>
</template>
