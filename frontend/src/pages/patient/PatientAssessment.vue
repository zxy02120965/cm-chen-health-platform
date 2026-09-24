<script setup>
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { assessmentSections, getSection } from '../../config/assessmentQuestions'
import { assessmentData, currentPatient, refreshPatientFromApi, saveAssessment } from '../../stores/patientStore'

const route = useRoute()
const router = useRouter()
const patient = currentPatient
const section = computed(() => getSection(route.params.sectionId) || assessmentSections[0])
const sectionIndex = computed(() => Math.max(0, assessmentSections.findIndex((item) => item.id === section.value?.id)))
const form = reactive({})
const fieldErrors = reactive({})
const actionError = ref('')
const actionMessage = ref('')
const saving = ref(false)

function cloneValue(value) {
  if (value === undefined || value === null) return value
  if (Array.isArray(value)) return value.map((item) => (item && typeof item === 'object' ? { ...item } : item))
  if (typeof value === 'object') return { ...value }
  return value
}

function blankValue(field) {
  if (field.type === 'checkbox') return []
  if (field.type === 'composite' || field.type === 'labs') return {}
  if (field.type === 'repeaters') return []
  if (field.type === 'liver_elasticity') return {}
  if (field.type === 'q56_goal') return { has_clinician_goal: false, primary_goal: '', weight_target_type: 'NO_SPECIFIC_WEIGHT_TARGET', secondary_goals: [], other_text: '' }
  return ''
}

function load() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  const saved = assessmentData()
  const currentSection = section.value
  if (!currentSection) return
  currentSection.fields.filter((field) => field.patientVisible !== false).forEach((field) => {
    const value = saved[field.key]
    form[field.key] = value === undefined ? blankValue(field) : cloneValue(value)
    if (field.noteKey || field.otherKey) form[field.noteKey || field.otherKey] = saved[field.noteKey || field.otherKey] || ''
    if (field.type === 'composite' && !form[field.key]) form[field.key] = {}
    if (field.type === 'liver_elasticity' && !form[field.key]) form[field.key] = {}
    if (field.type === 'repeaters' && !Array.isArray(form[field.key])) form[field.key] = []
  })
}

watch(() => route.params.sectionId, load, { immediate: true })
watch(() => JSON.stringify(assessmentData()), load)
async function refresh() { await refreshPatientFromApi(); load() }
onMounted(refresh)
onActivated(refresh)

function nullifyMissing(value) {
  if (Array.isArray(value)) return value.map(nullifyMissing)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, nullifyMissing(item)]))
  return value === '' ? null : value
}
function submissionPayload() { return nullifyMissing({ ...form }) }
function isEmptyValue(value) {
  if (value === undefined || value === null || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.values(value).every((item) => isEmptyValue(item))
  return false
}
function validateCurrentSection() {
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key])
  const currentSection = section.value
  if (!currentSection) return false
  currentSection.fields.filter((field) => field.patientVisible !== false).forEach((field) => {
    // Required flags are configuration-driven.  No new required questions are
    // introduced here; optional Q27/Q45/Q50/Q56 therefore never block.
    const conditionallyOptional = field.optionalWhen && typeof field.optionalWhen === 'object'
      ? (Array.isArray(form[field.optionalWhen.key])
          ? form[field.optionalWhen.key].includes(field.optionalWhen.includes)
          : form[field.optionalWhen.key] === field.optionalWhen.includes)
      : Boolean(field.optionalWhen)
    if (field.required === true && !field.optional && !conditionallyOptional && isEmptyValue(form[field.key])) {
      fieldErrors[field.key] = `请填写第${field.questionId}题：${field.label}`
    }
  })
  return Object.keys(fieldErrors).length === 0
}
async function saveCurrent(status = 'DRAFT') {
  actionError.value = ''
  actionMessage.value = ''
  saving.value = true
  try {
    const result = await saveAssessment(submissionPayload(), patient.value.id, status)
    if (!result) throw new Error('评估保存未返回有效结果')
    actionMessage.value = status === 'SUBMITTED' ? '评估已提交，正在生成医护审核草稿' : '已暂存'
    return result
  } catch (error) {
    actionError.value = error?.message || '保存失败，请检查网络后重试'
    return null
  } finally {
    saving.value = false
  }
}
async function saveDraft() {
  const result = await saveCurrent('DRAFT')
  if (result) router.push('/patient/archive')
}
async function continueNext() {
  actionError.value = ''
  actionMessage.value = ''
  if (!validateCurrentSection()) {
    actionError.value = Object.values(fieldErrors)[0] || '请先完成当前步骤必填项'
    return
  }
  const isFinal = sectionIndex.value === assessmentSections.length - 1
  const result = await saveCurrent(isFinal ? 'SUBMITTED' : 'DRAFT')
  if (!result) return
  const next = assessmentSections[sectionIndex.value + 1]
  if (next) router.push(`/patient/archive/${next.id}`)
  else {
    await refreshPatientFromApi(patient.value.id, true)
    router.push('/patient/assessment/result')
  }
}
function updateCheckbox(field, option) {
  const values = form[field.key] || []
  if (option === '无' && values.includes('无')) form[field.key] = ['无']
  else if (option !== '无' && values.includes(option)) form[field.key] = values.filter((item) => item !== '无')
}
function shouldShowNote(field) {
  if (!field.noteKey || !field.noteWhen) return false
  const selected = form[field.key]
  return Array.isArray(selected) ? field.noteWhen.some((item) => selected.includes(item)) : field.noteWhen.includes(selected)
}
function liverValue(key) { return form.q50_liverElastography?.[key] || '' }
function showLiverDetails() { return liverValue('performed') === '是' }
function updateLiverPerformed(value) { if (value === '否') form.q50_liverElastography = { performed: '否' } }
function addRepeater(field) {
  const item = {}
  field.fields.forEach(([key]) => { item[key] = '' })
  form[field.key].push(item)
}
function removeRepeater(field, index) { form[field.key].splice(index, 1) }
const q56PrimaryGoals = [
  ['STANDARD_FAT_LOSS', '标准减脂'], ['ENHANCED_FAT_LOSS', '强化减脂'], ['WEIGHT_MAINTENANCE_MUSCLE_PRESERVATION', '体重维持/保肌'],
  ['NUTRITION_RECOVERY_WEIGHT_GAIN', '营养恢复/增重'], ['STOP_WEIGHT_LOSS', '停止继续下降'], ['MUSCLE_GAIN', '增肌'], ['METABOLIC_CONTROL', '代谢控制'],
  ['FUNCTION_IMPROVEMENT', '提高运动能力'], ['PULMONARY_IMPROVEMENT', '改善肺功能'], ['COMPREHENSIVE_PREOP', '术前综合准备'],
]
const q56SecondaryGoals = [['MUSCLE_PRESERVATION', '肌肉不下降'], ['BODY_FAT_REDUCTION', '体脂下降'], ['WAIST_REDUCTION', '腰围下降'], ['GLUCOSE_CONTROL', '控糖'], ['LIPID_CONTROL', '降脂'], ['URIC_ACID_CONTROL', '降尿酸'], ['FUNCTION_IMPROVEMENT', '提高运动能力'], ['PULMONARY_IMPROVEMENT', '改善肺功能'], ['OTHER', '其他']]
function q56Value(key) { return form.q56_goal?.[key] }
function ensureQ56() { if (!form.q56_goal || typeof form.q56_goal !== 'object') form.q56_goal = blankValue({ type: 'q56_goal' }) }
function toggleQ56Goal(value) { ensureQ56(); form.q56_goal.has_clinician_goal = true; form.q56_goal.primary_goal = value }
function toggleQ56Secondary(value) { ensureQ56(); form.q56_goal.has_clinician_goal = true; const values = form.q56_goal.secondary_goals || []; form.q56_goal.secondary_goals = values.includes(value) ? values.filter((item) => item !== value) : [...values, value] }
function clearQ56() { form.q56_goal = { has_clinician_goal: false, primary_goal: '', weight_target_type: 'NO_SPECIFIC_WEIGHT_TARGET', secondary_goals: [], other_text: '' } }
const bmi = computed(() => {
  const height = Number(form.q14_height)
  const weight = Number(form.q15_weight)
  return height > 0 && weight > 0 ? (weight / ((height / 100) ** 2)).toFixed(1) : '—'
})
</script>

<template>
  <section class="patient-page assessment-page">
    <div class="page-title-mobile">
      <RouterLink to="/patient/archive" class="back-link">‹</RouterLink>
      <div><p class="eyebrow">{{ patient.id }} · 第 {{ sectionIndex + 1 }} / {{ assessmentSections.length }} 步</p><h1>{{ section.title }}</h1></div>
    </div>
    <div class="assessment-stepper"><span v-for="(item, index) in assessmentSections" :key="item.id" :class="{ active: index <= sectionIndex }"></span></div>
    <section class="mobile-card section-intro"><p>{{ section.subtitle }}</p><small>请按实际情况填写，不确定的内容可以留空，之后由医护补录。</small></section>
    <p v-if="actionMessage" class="action-message success">{{ actionMessage }}</p>
    <p v-if="actionError" class="action-message error" role="alert">{{ actionError }}</p>

    <form class="mobile-form" @submit.prevent="continueNext">
      <template v-for="field in section.fields" :key="field.key">
      <div v-if="field.patientVisible !== false" class="form-field" :class="{ wide: ['textarea', 'checkbox', 'composite', 'labs', 'repeaters', 'liver_elasticity'].includes(field.type) }">
        <label>{{ field.questionId }}. {{ field.label }} <small v-if="field.unit">（{{ field.unit }}）</small><small v-if="field.optional || field.optionalWhen">（选填）</small></label>
        <div v-if="field.type === 'q56_goal'" class="q56-form" @vue:mounted="ensureQ56">
          <p class="field-hint">选填，由医护指导填写；不填写时系统按A–F默认模式生成方案。</p>
          <div class="choice-grid"><label v-for="item in q56PrimaryGoals" :key="item[0]" class="choice-label"><input type="radio" name="q56-primary" :checked="q56Value('primary_goal') === item[0]" @change="toggleQ56Goal(item[0])" />{{ item[1] }}</label></div>
          <label>目标周期（自动读取Q6）<input :value="form.q6_surgeryWindow || '未确定'" readonly /></label>
          <label>体重目标</label><div class="choice-grid"><label class="choice-label"><input type="radio" value="NO_SPECIFIC_WEIGHT_TARGET" v-model="form[field.key].weight_target_type" />不设具体目标</label><label class="choice-label"><input type="radio" value="TARGET_WEIGHT_KG" v-model="form[field.key].weight_target_type" />目标体重</label><label class="choice-label"><input type="radio" value="TARGET_CHANGE" v-model="form[field.key].weight_target_type" />目标变化</label></div>
          <input v-if="q56Value('weight_target_type') === 'TARGET_WEIGHT_KG'" v-model.number="form[field.key].target_weight_kg" type="number" min="20" max="300" placeholder="目标体重（kg）" />
          <div v-if="q56Value('weight_target_type') === 'TARGET_CHANGE'" class="form-row-two"><input v-model.number="form[field.key].target_change_weeks" type="number" min="1" placeholder="周数" /><input v-model.number="form[field.key].target_change_kg" type="number" placeholder="变化kg" /></div>
          <div class="checkbox-grid"><label v-for="item in q56SecondaryGoals" :key="item[0]" class="checkbox-label"><input type="checkbox" :checked="(q56Value('secondary_goals') || []).includes(item[0])" @change="toggleQ56Secondary(item[0])" />{{ item[1] }}</label></div>
          <input v-if="(q56Value('secondary_goals') || []).includes('OTHER')" v-model="form[field.key].other_text" class="other-input" placeholder="请补充其他重点" />
          <button type="button" class="link-button" @click="clearQ56">清除医护目标（按系统默认）</button>
        </div>
        <input v-else-if="['text', 'number', 'date', 'tel'].includes(field.type)" v-model="form[field.key]" :type="field.type" :placeholder="field.placeholder" />
        <div v-else-if="field.type === 'radio'" class="choice-grid">
          <label v-for="option in field.options" :key="option" class="choice-label"><input v-model="form[field.key]" type="radio" :name="field.key" :value="option" />{{ option }}</label>
        </div>
        <div v-else-if="field.type === 'checkbox'" class="checkbox-grid">
          <label v-for="option in field.options" :key="option" class="checkbox-label"><input v-model="form[field.key]" type="checkbox" :value="option" @change="updateCheckbox(field, option)" />{{ option }}</label>
        </div>
        <div v-else-if="field.type === 'liver_elasticity'" class="liver-form">
          <div class="choice-grid"><label v-for="option in field.fields[0].options" :key="option" class="choice-label"><input v-model="form[field.key].performed" type="radio" :name="`${field.key}-performed`" :value="option" @change="updateLiverPerformed(option)" />{{ option }}</label></div>
          <template v-if="showLiverDetails()"><label>检查日期<input v-model="form[field.key].checkDate" type="date" /></label><label>检查方式</label><div class="choice-grid"><label v-for="option in field.fields[2].options" :key="option" class="choice-label"><input v-model="form[field.key].method" type="radio" :name="`${field.key}-method`" :value="option" />{{ option }}</label></div><label>肝脏硬度值 LSM（kPa）<input v-model="form[field.key].lsm" type="number" inputmode="decimal" /></label><label>报告结论</label><div class="choice-grid"><label v-for="option in field.fields[4].options" :key="option" class="choice-label"><input v-model="form[field.key].conclusion" type="radio" :name="`${field.key}-conclusion`" :value="option" />{{ option }}</label></div><label>脂肪定量</label><div class="choice-grid"><label v-for="option in field.fields[5].options" :key="option" class="choice-label"><input v-model="form[field.key].fatQuantType" type="radio" :name="`${field.key}-fat`" :value="option" />{{ option }}</label></div><label v-if="liverValue('fatQuantType') === 'CAP'">CAP（dB/m）<input v-model="form[field.key].cap" type="number" inputmode="decimal" /></label><label v-if="liverValue('fatQuantType') === '其他指标'">其他脂肪定量指标<input v-model="form[field.key].otherFatIndex" type="text" /></label></template>
          <small class="field-hint">选填；未做过或未填写的项目保留为空，不按“正常”处理。</small>
        </div>
        <div v-else-if="field.type === 'composite'" class="subfield-grid">
          <label v-for="sub in field.subfields" :key="sub.key"><span class="subfield-label">{{ sub.label }}<em v-if="sub.unit">（{{ sub.unit }}）</em></span><input v-model="form[field.key][sub.key]" :type="sub.type" :placeholder="sub.placeholder" /></label>
        </div>
        <div v-else-if="field.type === 'labs'" class="labs-grid">
          <label class="lab-date">统一检查日期<input v-model="form[field.dateKey]" type="date" /></label>
          <label v-for="lab in field.labs" :key="lab[0]">{{ lab[1] }}<span> · {{ lab[2] }}</span><input v-model="form[field.key][lab[0]]" type="number" inputmode="decimal" /></label>
        </div>
        <div v-else-if="field.type === 'repeaters'" class="repeaters">
          <div v-for="(item, index) in form[field.key]" :key="index" class="repeater-card">
            <div class="repeater-head"><strong>{{ field.itemLabel }} {{ index + 1 }}</strong><button type="button" class="link-button danger" @click="removeRepeater(field, index)">删除</button></div>
            <label v-for="entry in field.fields" :key="entry[0]">{{ entry[1] }}<input v-if="entry[2] !== 'radio'" v-model="item[entry[0]]" :type="entry[2]" /><span v-else class="inline-options"><label v-for="option in entry[3]" :key="option"><input v-model="item[entry[0]]" type="radio" :name="`${field.key}-${index}-${entry[0]}`" :value="option" />{{ option }}</label></span></label>
          </div>
          <button type="button" class="add-row-button" @click="addRepeater(field)">＋ 添加{{ field.itemLabel }}</button>
        </div>
        <input v-if="shouldShowNote(field)" v-model="form[field.noteKey]" class="other-input" :placeholder="field.notePlaceholder || '请补充说明'" />
        <input v-else-if="field.otherKey && (form[field.key] === '其他' || (Array.isArray(form[field.key]) && form[field.key].includes('其他')))" v-model="form[field.otherKey]" class="other-input" placeholder="请补充说明" />
        <small v-if="fieldErrors[field.key]" class="field-error" role="alert">{{ fieldErrors[field.key] }}</small>
      </div>
      </template>
      <div v-if="section.id === 'body-function'" class="derived-note"><span>BMI（由身高＋体重自动计算）</span><strong>{{ bmi }}</strong></div>
      <div class="assessment-actions"><button type="button" class="secondary-mobile" :disabled="saving" @click="saveDraft">{{ saving ? '保存中…' : '暂存，稍后填写' }}</button><button class="primary-mobile" type="submit" :disabled="saving" @click.stop="continueNext">{{ saving ? '保存中…' : (sectionIndex === assessmentSections.length - 1 ? '保存并查看结果' : '保存并继续') }}</button></div>
    </form>
  </section>
</template>
