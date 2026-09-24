<script setup>
import { computed, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { currentPatient, dailyRecordData, planData, saveDailyRecord } from '../../stores/patientStore'
import { mockPublishedPlanTasks } from '../../mock/dailyRecords'

const options = ['步行训练', '肩关节活动', '拉伸训练', '肌力训练', '燃脂操', '其他']
const existing = computed(() => dailyRecordData().exercise || {})
const planTasks = computed(() => {
  const published = planData(currentPatient.value?.id)?.draft?.exercise_plan
  if (Array.isArray(published) && published.length) return published.map((item) => ({ type: item.exercise_name, name: item.exercise_name, duration: item.duration, reps: item.repetitions, sets: item.sets }))
  return mockPublishedPlanTasks[currentPatient.value?.id]?.exercise || mockPublishedPlanTasks.default.exercise
})
const planFor = (type) => planTasks.value.find((task) => task.type === type) || { duration: '', reps: '', sets: '' }

function normalizeItems(value) {
  if (Array.isArray(value?.items) && value.items.length) {
    return value.items.map((item) => {
      const plan = planFor(item.type || item.name || '其他')
      return {
        type: item.type || item.name || '其他',
        planDuration: item.planDuration ?? item.plannedDuration ?? item.plan?.duration ?? plan.duration,
        planReps: item.planReps ?? item.plannedReps ?? item.plan?.reps ?? plan.reps,
        planSets: item.planSets ?? item.plannedSets ?? item.plan?.sets ?? plan.sets,
        actualDuration: item.actualDuration ?? item.duration ?? '',
        actualReps: item.actualReps ?? item.reps ?? '',
        actualSets: item.actualSets ?? item.sets ?? '',
        intensity: item.intensity || '轻度',
      }
    })
  }
  if (value?.type) {
    const plan = planFor(value.type === '步行' ? '步行训练' : value.type)
    return [{ type: value.type === '步行' ? '步行训练' : value.type, planDuration: plan.duration, planReps: plan.reps, planSets: plan.sets, actualDuration: value.duration || '', actualReps: value.reps || '', actualSets: value.sets || '', intensity: value.intensity || '轻度' }]
  }
  return []
}

const form = reactive({ date: existing.value.date || new Date().toISOString().slice(0, 10), items: normalizeItems(existing.value), otherDetail: existing.value.otherDetail || '', discomfort: existing.value.discomfort || '无', note: existing.value.note || '' })
const selectedTypes = computed(() => form.items.map((item) => item.type))
const displayItemName = (item) => item.type === '其他' && form.otherDetail.trim() ? form.otherDetail.trim() : item.type
function makeItem(type) {
  const plan = planFor(type)
  return { type, planDuration: plan.duration, planReps: plan.reps, planSets: plan.sets, actualDuration: '', actualReps: '', actualSets: '', intensity: '轻度' }
}
function toggleItem(type, checked) {
  if (checked && !selectedTypes.value.includes(type)) form.items.push(makeItem(type))
  if (!checked) form.items = form.items.filter((item) => item.type !== type)
}
  async function save() {
  const hasDose = form.items.some((item) => item.actualDuration || item.actualReps || item.actualSets)
  const result = await saveDailyRecord('exercise', { date: form.date, items: form.items.map((item) => ({ ...item })), otherDetail: form.otherDetail, discomfort: form.discomfort, note: form.note, status: hasDose ? 'completed' : 'pending', label: hasDose ? '今日已记录' : '待记录', detail: form.items.map((item) => displayItemName(item)).join('、') || '尚未选择运动项目' })
    window.alert(result?.ok ? '运动记录已保存' : '网络异常，运动记录待同步，请稍后重试')
}
</script>

<template>
  <section class="patient-page record-detail-page">
    <div class="page-title-mobile"><RouterLink to="/patient/records" class="back-link">‹</RouterLink><div><p class="eyebrow">P-04-03 · 每日打卡</p><h1>运动记录</h1></div></div>
    <section class="mobile-card record-form-card">
      <div class="form-field"><label>日期</label><input v-model="form.date" type="date" /></div>
      <div class="record-plan-notice"><strong>今日任务来自已发布方案</strong><span>计划值由医护审核后发布，患者不可修改。</span></div>
      <div class="form-field"><label>运动项目（可多选）</label><div class="checkbox-grid exercise-options"><label v-for="item in options" :key="item" class="checkbox-label"><input type="checkbox" :checked="selectedTypes.includes(item)" @change="toggleItem(item, $event.target.checked)" />{{ item }}</label></div></div>
      <div v-if="selectedTypes.includes('其他')" class="form-field"><label>其他运动项目</label><input v-model="form.otherDetail" type="text" placeholder="请填写具体是什么运动" /></div>
      <div v-if="form.items.length" class="exercise-dose-list">
        <div v-for="item in form.items" :key="item.type" class="exercise-dose-card">
          <div class="exercise-dose-head"><strong>{{ displayItemName(item) }}</strong><span>医生方案任务</span></div>
          <div class="plan-dose-grid"><span>计划时长<strong>{{ item.planDuration || '—' }}<small v-if="item.planDuration">分钟</small></strong></span><span>计划次数<strong>{{ item.planReps || '—' }}<small v-if="item.planReps">次</small></strong></span><span>计划组数<strong>{{ item.planSets || '—' }}<small v-if="item.planSets">组</small></strong></span></div>
          <p class="actual-dose-label">填写实际完成情况</p>
          <div class="form-row-two"><div class="form-field"><label>实际完成时长（分钟）</label><input v-model="item.actualDuration" type="number" min="0" placeholder="可选" /></div><div class="form-field"><label>实际完成次数</label><input v-model="item.actualReps" type="number" min="0" placeholder="可选" /></div></div>
          <div class="form-row-two"><div class="form-field"><label>实际完成组数</label><input v-model="item.actualSets" type="number" min="0" placeholder="可选" /></div><div class="form-field"><label>实际强度</label><select v-model="item.intensity"><option>轻度</option><option>中等</option><option>较高</option></select></div></div>
        </div>
      </div>
      <div class="form-field"><label>是否出现不适</label><div class="choice-grid"><label v-for="item in ['无','有']" :key="item" class="choice-label"><input v-model="form.discomfort" type="radio" name="exerciseDiscomfort" :value="item" />{{ item }}</label></div></div>
      <div class="form-field"><label>备注</label><textarea v-model="form.note" placeholder="记录运动后的感受或不适"></textarea></div>
      <button class="primary-mobile full-button" type="button" @click="save">保存今日运动</button>
    </section>
    <section class="mobile-card"><p class="eyebrow">历史记录</p><div class="history-row"><strong>2026-09-03</strong><span>步行训练 25分钟 · 轻度</span></div><div class="history-row"><strong>2026-09-02</strong><span>拉伸训练 3组 · 中等</span></div></section>
  </section>
</template>
