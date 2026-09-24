<script setup>
import { RouterLink } from 'vue-router'
</script>
<template><section class="patient-page"><div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">服务入口</p><h1>更多服务</h1></div></div><div class="service-list"><div v-for="item in [['术前提醒','按手术时间查看准备事项','◷'],['检查报告归档','查看已上传的医疗资料','▤'],['复诊预约','现有医院服务入口','◫'],['帮助与隐私','数据使用说明','?']]" :key="item[0]" class="service-item"><span>{{ item[2] }}</span><div><strong>{{ item[0] }}</strong><small>{{ item[1] }}</small></div><em>建设中</em></div></div><p class="patient-footnote">未开放的服务会在后续版本逐步接入。</p></section></template>
