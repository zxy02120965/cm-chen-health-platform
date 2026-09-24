<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
const range = ref('7天')
const metrics = ['体重', '体脂率', '肌肉/骨骼肌', '水分', '腰围', '饮食完成率', '运动完成率', '肺预康复完成率', '疲劳', '气促', '疼痛']
</script>
<template><section class="patient-page record-detail-page"><div class="page-title-mobile"><RouterLink to="/patient/records" class="back-link">‹</RouterLink><div><p class="eyebrow">P-04-05 · 数据趋势</p><h1>健康趋势</h1></div></div><div class="range-tabs"><button v-for="item in ['7天','14天','30天','3个月']" :key="item" :class="{ active: range === item }" @click="range = item">{{ item }}</button></div><section v-for="(metric,index) in metrics" :key="metric" class="mobile-card trend-card"><div class="card-title-row"><div><p class="eyebrow">{{ metric }}</p><h2>{{ index < 5 ? '趋势记录' : '完成趋势' }}</h2></div><span class="trend-filter">{{ range }}</span></div><div class="fake-chart"><i :style="{height:`${42+index*3}%`}"></i><i :style="{height:`${55+index*2}%`}"></i><i :style="{height:`${48+index*4}%`}"></i><i :style="{height:`${66-index}%`}"></i><i :style="{height:`${58+index*2}%`}"></i></div><p class="record-hint">Mock趋势数据，仅用于页面演示；周复评会结合数据完整度和安全状态。</p></section></section></template>
