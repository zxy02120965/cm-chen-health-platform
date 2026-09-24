<script setup>
import { computed, onActivated, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { mockPatients } from '../../mock/patients'
import { mockActivities } from '../../mock/activities'
import { getCareTodos } from '../../mock/careTodos'
import { getCareAlerts } from '../../mock/careAlerts'
import { allConsultations, patientStore, refreshCareTodos, refreshDashboardSummary } from '../../stores/patientStore'

const sourceTodos = computed(() => patientStore.apiTodos.length ? patientStore.apiTodos : getCareTodos())
const tasks = computed(() => sourceTodos.value.slice(0, 3).map((item) => ({ patient: item.patient, type: item.type, summary: item.summary, status: item.status, id: item.id })))

const todoCounts = computed(() => ({
  pendingAssessment: sourceTodos.value.filter((item) => item.tab === 'pending-assessment').length,
  assessmentReview: sourceTodos.value.filter((item) => item.tab === 'assessment-review').length,
  planReview: sourceTodos.value.filter((item) => item.tab === 'plan-review').length,
  publish: sourceTodos.value.filter((item) => item.tab === 'publish').length,
  total: sourceTodos.value.length,
}))
const alertCounts = computed(() => {
  const alerts = getCareAlerts()
  return {
  yellow: alerts.filter((item) => item.level === 'yellow').length,
  red: alerts.filter((item) => item.level === 'red').length,
  pending: alerts.filter((item) => !item.handled).length,
  }
})
const consultCounts = computed(() => {
  const list = allConsultations()
  return {
    unreplied: list.filter((item) => item.status === '待回复').length,
    pending: list.filter((item) => item.handling !== '已完成').length,
  }
})
const patientCount = computed(() => patientStore.apiDashboard?.patients ?? (patientStore.apiCarePatients.length || mockPatients.length))
const refresh = async () => { await Promise.all([refreshDashboardSummary(), refreshCareTodos(),]) }
onMounted(refresh)
onActivated(refresh)
</script>

<template>
  <section class="care-page">
    <div class="care-metrics">
      <RouterLink to="/care/patients" class="care-metric-link"><span>管理患者总数</span><strong>{{ patientCount }}</strong><small>统一医护账号</small></RouterLink>
      <RouterLink to="/care/todos" class="care-metric-link"><span>待办总数</span><strong class="yellow">{{ todoCounts.total }}</strong><small>评估、审核与发布</small></RouterLink>
      <RouterLink to="/care/alerts?tab=红色重点" class="care-metric-link"><span>红色重点</span><strong class="red">{{ alertCounts.red }}</strong><small>需尽快处理</small></RouterLink>
      <RouterLink to="/care/consults?tab=未回复" class="care-metric-link"><span>未回复咨询</span><strong class="yellow">{{ consultCounts.unreplied }}</strong><small>等待医护回复</small></RouterLink>
    </div>

    <section class="care-dashboard-sections">
      <article class="care-dashboard-section"><div class="care-panel-head"><div><p class="eyebrow">待办管理</p><h2>评估与方案流程</h2></div><RouterLink to="/care/todos">查看全部 →</RouterLink></div><div class="care-stat-grid"><RouterLink class="care-stat-link" to="/care/todos?tab=pending-assessment"><span>待评估</span><strong>{{ todoCounts.pendingAssessment }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/todos?tab=assessment-review"><span>待审核评估</span><strong>{{ todoCounts.assessmentReview }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/todos?tab=plan-review"><span>待审核方案</span><strong>{{ todoCounts.planReview }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/todos?tab=publish"><span>待发布</span><strong>{{ todoCounts.publish }}</strong></RouterLink></div></article>
      <article class="care-dashboard-section"><div class="care-panel-head"><div><p class="eyebrow">监测与预警</p><h2>异常重点患者</h2></div><RouterLink to="/care/alerts">查看全部 →</RouterLink></div><div class="care-stat-grid"><RouterLink class="care-stat-link" to="/care/alerts?tab=黄色关注"><span>黄色关注</span><strong class="yellow">{{ alertCounts.yellow }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/alerts?tab=红色重点"><span>红色重点</span><strong class="red">{{ alertCounts.red }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/alerts?tab=全部"><span>待处理异常</span><strong>{{ alertCounts.pending }}</strong></RouterLink></div></article>
      <article class="care-dashboard-section"><div class="care-panel-head"><div><p class="eyebrow">咨询管理</p><h2>患者沟通队列</h2></div><RouterLink to="/care/consults">查看全部 →</RouterLink></div><div class="care-stat-grid"><RouterLink class="care-stat-link" to="/care/consults?tab=未回复"><span>未回复</span><strong class="yellow">{{ consultCounts.unreplied }}</strong></RouterLink><RouterLink class="care-stat-link" to="/care/consults?tab=待处理"><span>待处理</span><strong>{{ consultCounts.pending }}</strong></RouterLink></div></article>
    </section>

    <div class="care-grid-two">
      <section class="care-panel"><div class="care-panel-head"><div><p class="eyebrow">今日待处理</p><h2>需要你关注的事项</h2></div><RouterLink to="/care/patients">查看患者列表 →</RouterLink></div><div class="care-task" v-for="task in tasks" :key="task.patient"><span class="task-status">{{ task.status }}</span><div><strong>{{ task.patient }} · {{ task.type }}</strong><small>{{ task.summary }}</small></div><RouterLink :to="`/care/patients/${task.id}`">查看</RouterLink></div></section>
      <section class="care-panel"><div class="care-panel-head"><div><p class="eyebrow">最近动态</p><h2>患者管理进展</h2></div></div><ul class="care-activity"><li v-for="item in mockActivities" :key="item.id">{{ item.text }} <small>{{ item.time }}</small></li></ul></section>
    </div>
  </section>
</template>
