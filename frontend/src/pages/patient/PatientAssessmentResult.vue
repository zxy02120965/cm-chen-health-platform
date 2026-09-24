<script setup>
import { computed, onActivated, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { assessmentResultData, currentPatient, refreshPatientFromApi } from '../../stores/patientStore'
const patient = currentPatient
onMounted(() => refreshPatientFromApi())
onActivated(() => refreshPatientFromApi())
const summary = computed(() => assessmentResultData())
const progress = computed(() => summary.value.completion)
const result = computed(() => progress.value < 35 ? { title: '还需要补充一些资料', tone: 'yellow', issue: '目前最重要的是完善身体测量、饮食摄入和手术时间等信息。', focus: '先完成资料补充，暂不急着设定具体的减重或运动目标。', risk: '资料不足时，系统不会把未填写内容当作正常。', next: '继续补充评估，完成后由医护团队确认。' } : summary.value.safety === 'red' ? { title: '当前需要医护重点关注', tone: 'red', issue: '你填写了需要及时核实的症状或异常信息。', focus: '先联系医护团队确认，暂缓相关运动进阶。', risk: '红色状态下不会自动调整饮食、运动或治疗。', next: '进入在线咨询或等待医护处理。' } : { title: '你的管理重点已形成', tone: 'blue', issue: summary.value.phenotype.split('｜')[1], focus: summary.value.focus?.join?.('；') || '围绕营养充分、肌肉保护和术前功能逐步执行。', risk: '后续每周根据体重、体脂率和腰围复评。', next: '等待医护审核后查看已发布方案。' })
</script>

<template><section class="patient-page result-page"><div class="page-title-mobile"><RouterLink to="/patient/archive" class="back-link">‹</RouterLink><div><p class="eyebrow">{{ patient.id }} · 综合结果</p><h1>我的评估结果</h1></div></div><section class="result-hero" :class="result.tone"><div class="result-symbol">{{ result.tone === 'red' ? '!' : result.tone === 'yellow' ? '○' : '✓' }}</div><p class="eyebrow">评估完成度 {{ progress }}%</p><h2>{{ result.title }}</h2><p>{{ result.issue }}</p></section><div class="result-cards"><section class="mobile-card"><p class="eyebrow">当前管理重点</p><h3>{{ result.focus }}</h3></section><section class="mobile-card"><p class="eyebrow">风险提示</p><h3>{{ result.risk }}</h3></section><section class="mobile-card"><p class="eyebrow">下一步</p><h3>{{ result.next }}</h3></section></div><div class="result-actions"><RouterLink to="/patient/archive" class="secondary-mobile">返回档案</RouterLink><RouterLink to="/patient/plan" class="primary-mobile">查看方案状态</RouterLink></div><p class="patient-footnote">这是健康管理提示，不替代医生诊断。</p></section></template>
