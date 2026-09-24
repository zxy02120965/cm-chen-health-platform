<script setup>
import { computed, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { currentPatient, dailyRecordData, planData, saveDailyRecord } from '../../stores/patientStore'
import { mockPublishedPlanTasks } from '../../mock/dailyRecords'

const options = ['缩唇呼吸', '腹式呼吸', '呼吸操', '步行配合呼吸', '其他']
const existing = computed(() => dailyRecordData().pulmonary || {})
const planTasks = computed(() => {
  const published = planData(currentPatient.value?.id)?.draft?.pulmonary_prehab_plan
  if (Array.isArray(published) && published.length) return published.map((item) => ({ name: item.action_name, times: item.daily_frequency, duration: item.duration, sets: item.sets }))
  return mockPublishedPlanTasks[currentPatient.value?.id]?.pulmonary || mockPublishedPlanTasks.default.pulmonary
})
const planFor = (name) => planTasks.value.find((task) => task.name === name) || { times: '', duration: '', sets: '' }

function normalizeItems(value) {
  if (Array.isArray(value?.items) && value.items.length) {
    return value.items.map((item) => {
      const name = item.name || item.training || '缩唇呼吸'
      const plan = planFor(name)
      return {
        name,
        planTimes: item.planTimes ?? item.planned ?? item.plan?.times ?? plan.times,
        planDuration: item.planDuration ?? item.plan?.duration ?? plan.duration,
        planSets: item.planSets ?? item.plan?.sets ?? plan.sets,
        actualTimes: item.actualTimes ?? item.completed ?? '',
        actualDuration: item.actualDuration ?? '',
        actualSets: item.actualSets ?? '',
        intensity: item.intensity || '轻度',
      }
    })
  }
  if (Array.isArray(value?.trainings) && value.trainings.length) return value.trainings.map((name) => makeItem(name, value))
  return [makeItem(value.training || '缩唇呼吸', value)]
}
function makeItem(name, source = {}) {
  const plan = planFor(name)
  return { name, planTimes: source.planTimes ?? source.planned ?? plan.times, planDuration: source.planDuration ?? plan.duration, planSets: source.planSets ?? plan.sets, actualTimes: source.actualTimes ?? source.completed ?? '', actualDuration: source.actualDuration ?? '', actualSets: source.actualSets ?? '', intensity: source.intensity || '轻度' }
}

const form = reactive({ date: existing.value.date || new Date().toISOString().slice(0, 10), items: normalizeItems(existing.value), otherDetail: existing.value.otherDetail || '', breathing: existing.value.breathing || '', discomfort: existing.value.discomfort || '无', note: existing.value.note || '' })
const selectedNames = computed(() => form.items.map((item) => item.name))
const displayItemName = (item) => item.name === '其他' && form.otherDetail.trim() ? form.otherDetail.trim() : item.name
function toggleItem(name, checked) {
  if (checked && !selectedNames.value.includes(name)) form.items.push(makeItem(name))
  if (!checked) form.items = form.items.filter((item) => item.name !== name)
}
function itemStatus(item) {
  const byTimes = Number(item.planTimes) > 0 && Number(item.actualTimes) >= Number(item.planTimes)
  const byDuration = Number(item.planDuration) > 0 && Number(item.actualDuration) >= Number(item.planDuration)
  return byTimes || byDuration ? '已完成' : '待完成'
}
  async function save() {
  const hasDose = form.items.some((item) => item.actualTimes || item.actualDuration || item.actualSets)
  const complete = form.items.length > 0 && form.items.every((item) => itemStatus(item) === '已完成')
  const result = await saveDailyRecord('pulmonary', { date: form.date, items: form.items.map((item) => ({ ...item })), otherDetail: form.otherDetail, breathing: form.breathing, discomfort: form.discomfort, note: form.note, status: complete ? 'completed' : hasDose ? 'attention' : 'pending', label: complete ? '今日已完成' : hasDose ? '部分完成' : '待记录', detail: form.items.map((item) => `${displayItemName(item)} ${item.actualTimes || 0}/${item.planTimes || '—'}`).join('、') })
  window.alert(result?.ok ? '肺预康复记录已保存' : '网络异常，肺预康复记录待同步，请稍后重试')
  window.alert('肺预康复记录已保存')
}
</script>

<template>
  <section class="patient-page record-detail-page">
    <div class="page-title-mobile"><RouterLink to="/patient/records" class="back-link">‹</RouterLink><div><p class="eyebrow">P-04-04 · 每日打卡</p><h1>肺预康复记录</h1></div></div>
    <section class="mobile-card record-form-card">
      <div class="form-field"><label>日期</label><input v-model="form.date" type="date" /></div>
      <div class="record-plan-notice"><strong>今日任务来自已发布方案</strong><span>计划值由医护审核后发布，患者不可修改。</span></div>
      <div class="form-field"><label>今日训练项目（可多选）</label><div class="checkbox-grid exercise-options"><label v-for="item in options" :key="item" class="checkbox-label"><input type="checkbox" :checked="selectedNames.includes(item)" @change="toggleItem(item, $event.target.checked)" />{{ item }}</label></div></div>
      <div v-if="selectedNames.includes('其他')" class="form-field"><label>其他训练项目</label><input v-model="form.otherDetail" type="text" placeholder="请填写具体是什么训练" /></div>
      <div v-if="form.items.length" class="pulmonary-dose-list">
        <div v-for="item in form.items" :key="item.name" class="pulmonary-dose-row">
          <div class="pulmonary-dose-copy"><strong>{{ displayItemName(item) }}</strong><small>完成状态：<span :class="{ done: itemStatus(item) === '已完成' }">{{ itemStatus(item) }}</span></small></div>
          <div class="pulmonary-dose-fields">
            <div class="plan-dose-grid"><span>计划次数<strong>{{ item.planTimes || '—' }}<small v-if="item.planTimes">次</small></strong></span><span>计划时长<strong>{{ item.planDuration || '—' }}<small v-if="item.planDuration">分钟</small></strong></span><span>计划组数<strong>{{ item.planSets || '—' }}<small v-if="item.planSets">组</small></strong></span></div>
            <p class="actual-dose-label">填写实际完成情况</p>
            <div class="form-row-two"><div class="form-field"><label>实际完成次数</label><input v-model="item.actualTimes" type="number" min="0" placeholder="可选" /></div><div class="form-field"><label>实际完成时长（分钟）</label><input v-model="item.actualDuration" type="number" min="0" placeholder="可选" /></div></div>
            <div class="form-row-two"><div class="form-field"><label>实际完成组数</label><input v-model="item.actualSets" type="number" min="0" placeholder="可选" /></div><div class="form-field"><label>实际强度</label><select v-model="item.intensity"><option>轻度</option><option>中等</option><option>较高</option></select></div></div>
          </div>
        </div>
      </div>
      <div class="form-field"><label>是否出现不适</label><div class="choice-grid"><label v-for="item in ['无','有']" :key="item" class="choice-label"><input v-model="form.discomfort" type="radio" name="pulmonaryDiscomfort" :value="item" />{{ item }}</label></div></div>
      <div class="form-field"><label>呼吸训练记录</label><textarea v-model="form.breathing" placeholder="记录训练时长、呼吸感受"></textarea></div>
      <div class="form-field"><label>备注</label><textarea v-model="form.note" placeholder="记录训练后的感受或不适"></textarea></div>
      <button class="primary-mobile full-button" type="button" @click="save">保存今日训练</button>
    </section>
    <section class="mobile-card"><p class="eyebrow">历史完成情况</p><div class="history-row"><strong>2026-09-03</strong><span>缩唇呼吸、腹式呼吸 · 计划3次 · 完成3次</span></div><div class="history-row"><strong>2026-09-02</strong><span>呼吸操 · 计划2次 · 完成1次</span></div></section>
  </section>
</template>
