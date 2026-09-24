<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import StatePanel from '../../components/common/StatePanel.vue'
import { mockMedicalFiles } from '../../mock/assessments'
import { currentPatient } from '../../stores/patientStore'

const patient = currentPatient
const files = ref(mockMedicalFiles.filter((file) => file.patientId === patient.value.id))
function onUpload(event) {
  const selected = Array.from(event.target.files || [])
  selected.forEach((file, index) => files.value.unshift({ id: `LOCAL-${Date.now()}-${index}`, patientId: patient.value.id, type: '其他医疗资料', date: new Date().toISOString().slice(0, 10), name: file.name, status: '已保存', note: '演示上传' }))
  event.target.value = ''
}
const hasFiles = computed(() => files.value.length > 0)
</script>

<template>
  <section class="patient-page">
    <div class="page-title-mobile"><RouterLink to="/patient/archive" class="back-link">‹</RouterLink><div><p class="eyebrow">独立资料管理 · 不属于Q1–Q55</p><h1>医疗资料</h1></div></div>
    <section class="mobile-card upload-card"><div><p class="eyebrow">上传资料</p><h2>只保存、查看，不自动识别</h2><small>支持胸部CT、病理资料、检验报告和其他医疗资料。</small></div><label class="primary-mobile upload-trigger">＋ 选择文件<input type="file" multiple accept="image/*,.pdf" @change="onUpload" /></label></section>
    <div v-if="hasFiles" class="file-list"><div v-for="file in files" :key="file.id" class="file-row"><span class="file-icon">▤</span><div><strong>{{ file.name }}</strong><small>{{ file.type }} · {{ file.date }} · {{ file.status }}</small></div><button type="button" class="link-button">查看</button></div></div>
    <StatePanel v-else icon="▤" title="暂无医疗资料" text="上传后可以在这里查看文件，不会自动生成诊断结论。" />
    <p class="patient-footnote">医疗资料仅供患者与授权医护查看。</p>
  </section>
</template>
