<script setup>
import { computed, onActivated, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { currentPatient, assessmentProgress, patientProfileData, patientEvents, syncFromStorage } from '../../stores/patientStore'
import { getCareAlerts } from '../../mock/careAlerts'

const patient = currentPatient
const profile = computed(() => patientProfileData())
const progress = computed(() => Math.max(patient.value.weeklyProgress, assessmentProgress()))
const modules = [
  ['▣', '健康档案', '/patient/archive', '查看和补充评估'],
  ['◇', '专属方案', '/patient/plan', '查看已发布方案'],
  ['▦', '数据记录', '/patient/records', '记录和查看趋势'],
  ['◎', '知识科普', '/patient/knowledge', '图文和视频'],
  ['✚', '在线咨询', '/patient/consult', '给医护团队留言'],
  ['♡', '更多服务', '/patient/services', '术前提醒等'],
]
const updates = computed(() => patientEvents(patient.value.id).slice(0, 5).map((item) => `${item.text} · ${item.time}`))
const activeAlert = computed(() => getCareAlerts().find((item) => item.patientId === patient.value.id && !item.handled))
onMounted(syncFromStorage)
onActivated(syncFromStorage)
</script>

<template>
  <section class="patient-page home-page"><div class="patient-profile"><div class="patient-avatar">{{ profile.avatar || profile.name.slice(0, 1) }}</div><div class="profile-copy"><p class="eyebrow">{{ patient.stage }}</p><h1>{{ profile.name }}，您好</h1><p>{{ profile.sex }} · {{ patient.age }} · {{ patient.id }}</p></div><RouterLink to="/patient/profile" class="edit-profile">编辑</RouterLink></div><div class="module-grid-mobile"><RouterLink v-for="item in modules" :key="item[1]" :to="item[2]" class="module-tile"><span class="module-icon">{{ item[0] }}</span><strong>{{ item[1] }}</strong><small>{{ item[3] }}</small></RouterLink></div><section class="mobile-card progress-card"><div class="card-title-row"><div><p class="eyebrow">本周优化进度</p><h2>稳步完成今天的计划</h2></div><span class="progress-number">{{ progress }}%</span></div><div class="progress-track-mobile"><div :style="{ width: `${progress}%` }"></div></div><div class="progress-details"><span>饮食 <b>{{ Math.min(100, progress + 4) }}%</b></span><span>运动 <b>{{ Math.max(0, progress - 6) }}%</b></span><span>肺预康复 <b>{{ Math.max(0, progress - 2) }}%</b></span><span>数据记录 <b>{{ Math.min(100, progress + 8) }}%</b></span></div></section><section class="mobile-card"><div class="card-title-row"><div><p class="eyebrow">最新动态</p><h2>今天也有新进展</h2></div><span class="dot-live"></span></div><div class="update-list"><div v-for="(update, index) in updates" :key="update" class="update-item"><span class="update-dot">{{ index + 1 }}</span><p>{{ update }}</p></div></div></section><p class="patient-footnote">数据加密保护 · 演示原型 V1.0 · 图片只保存不识别</p></section>
</template>
