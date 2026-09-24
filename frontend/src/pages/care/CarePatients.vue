<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { mockPatients } from '../../mock/patients'
import { getCareAlerts } from '../../mock/careAlerts'
import { allConsultations, assessmentData, assessmentProgress, patientStore, refreshCarePatients } from '../../stores/patientStore'
import { labelFor } from '../../config/enumLabels'

const search = ref('')
const status = ref('全部')
const tabs = ['全部', '管理中', '待评估', '待审核', '重点关注', '已完成']
const patients = computed(() => patientStore.apiCarePatients.length ? patientStore.apiCarePatients : mockPatients)
const consultCounts = computed(() => Object.fromEntries(patients.value.map((p) => [p.id, allConsultations().filter((item) => item.patientId === p.id && item.handling !== '已完成').length])))

function currentAssessment(id) { return assessmentData(id) || {} }
// Q6 is the single surgery-window source. Legacy surgeryDays is only a fallback
// while a patient's latest assessment has not loaded.
function surgeryWindow(p) { const q6 = currentAssessment(p.id).q6_surgeryWindow; return q6 || p.surgeryWindow || (p.surgeryDays ? `${p.surgeryDays}天` : '未确定') }
function pendingItems(p) {
  const items = []
  const assessmentStatus = p.assessmentStatus || currentAssessment(p.id)._status
  if (['pending', 'DRAFT', 'IN_PROGRESS', 'SUBMITTED'].includes(assessmentStatus)) items.push('评估')
  if (['PENDING_REVIEW', 'IN_REVIEW', 'RULE_GENERATED_PENDING_REVIEW', 'AI_GENERATED_PENDING_REVIEW', 'RETURNED'].includes(p.planStatus)) items.push('方案')
  if (consultCounts.value[p.id]) items.push(`${consultCounts.value[p.id]}条咨询`)
  const alerts = getCareAlerts().filter((item) => item.patientId === p.id && !item.handled)
  if (alerts.length) items.push(`${alerts.length}条预警`)
  return items
}
function safetyText(value) { return value === 'red' ? '红色重点' : value === 'yellow' ? '黄色关注' : '绿色安全' }
function phenotypeText(value) { return String(value || '').split('｜')[0] || '—' }
function assessmentText(p) { return `${p.assessmentCompletion ?? assessmentProgress(p.id)}%` }
function isTabMatch(p) {
  if (status.value === '全部') return true
  if (status.value === '待评估') return ['pending', 'DRAFT', 'IN_PROGRESS'].includes(p.assessmentStatus)
  if (status.value === '待审核') return ['SUBMITTED', 'UNDER_REVIEW'].includes(p.assessmentStatus) || ['PENDING_REVIEW', 'IN_REVIEW', 'AI_GENERATED_PENDING_REVIEW', 'RULE_GENERATED_PENDING_REVIEW', 'RETURNED'].includes(p.planStatus)
  if (status.value === '重点关注') return ['yellow', 'red'].includes(p.safety)
  if (status.value === '已完成') return p.planStatus === 'COMPLETED'
  return ['completed', 'COMPLETED', 'PUBLISHED'].includes(p.assessmentStatus) || ['PUBLISHED', 'IN_REVIEW', 'APPROVED_PENDING_MDT_ACTIVATION'].includes(p.planStatus)
}
const filtered = computed(() => patients.value.filter((p) => { const q = search.value.trim().toLowerCase(); return (!q || `${p.name}${p.id}${p.patient_id || ''}`.toLowerCase().includes(q)) && isTabMatch(p) }))
onMounted(refreshCarePatients)
onActivated(refreshCarePatients)
</script>

<template>
  <section class="care-page">
    <div class="care-tabs"><button v-for="tab in tabs" :key="tab" :class="{ active: status === tab }" @click="status = tab">{{ tab }}</button></div>
    <div class="care-toolbar"><input v-model="search" placeholder="搜索患者姓名或 patient_id" /><span>共 {{ filtered.length }} 位患者</span></div>
    <section class="care-table-wrap patient-list-table">
      <table class="care-table">
        <thead><tr><th>患者信息</th><th>距手术</th><th>A-F分型</th><th>安全等级</th><th>评估完成度</th><th>方案状态</th><th>待处理事项</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="p in filtered" :key="p.id">
            <td><strong>{{ p.name }}</strong><small>{{ p.sex }} · {{ p.age }} · <code>{{ p.id }}</code></small></td>
            <td>{{ surgeryWindow(p) }}</td>
            <td><span class="phenotype-chip">{{ phenotypeText(p.phenotype) }}型</span></td>
            <td><span class="care-status" :class="p.safety">{{ safetyText(p.safety) }}</span></td>
            <td><strong class="progress-cell">{{ assessmentText(p) }}</strong></td>
            <td><span class="plan-status">{{ labelFor(p.planStatus, 'plan_status') }}</span></td>
            <td><span v-if="pendingItems(p).length" class="pending-summary">{{ pendingItems(p).join(' · ') }}</span><span v-else class="quiet-summary">无</span></td>
            <td><RouterLink class="table-action" :to="`/care/patients/${p.id}`">查看</RouterLink></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="care-empty">没有匹配的患者</div>
    </section>
  </section>
</template>
