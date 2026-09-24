<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { assessmentSections } from '../../config/assessmentQuestions'
import { assessmentProgress, currentPatient } from '../../stores/patientStore'
const progress = computed(() => assessmentProgress())
const patient = currentPatient
</script>

<template>
  <section class="patient-page">
    <div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">{{ patient.id }} · 健康评估</p><h1>健康档案</h1></div></div>
    <section class="mobile-card profile-linked-note"><strong>身份资料已单独维护</strong><p>姓名、性别、出生年月和联系方式来自个人资料，评估页面只填写健康相关信息。</p><RouterLink to="/patient/profile">查看个人资料 ›</RouterLink></section>
    <section class="mobile-card archive-summary"><div><p class="eyebrow">评估完成度</p><strong>{{ progress }}%</strong><p>资料将用于形成你的评估结果和管理建议</p></div><div class="progress-ring"><span>{{ progress }}%</span></div></section>
    <div class="section-list"><RouterLink v-for="section in assessmentSections" :key="section.id" :to="`/patient/archive/${section.id}`" class="archive-section"><span class="section-index">{{ section.icon }}</span><div class="archive-section-copy"><strong>{{ section.title }}</strong><small>{{ section.subtitle }}</small></div><span class="section-arrow">›</span></RouterLink></div>
    <RouterLink class="result-entry" to="/patient/assessment/result"><span>✦</span><div><strong>查看综合评估结果</strong><small>用容易理解的方式查看当前重点和下一步</small></div><b>›</b></RouterLink>
    <RouterLink class="result-entry" to="/patient/medical-files"><span>▤</span><div><strong>医疗资料</strong><small>上传、查看CT/病理/检验资料（不自动识别）</small></div><b>›</b></RouterLink>
    <p class="patient-footnote">报告图片只上传、保存和查看，不自动识别。</p>
  </section>
</template>
