<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="patient-page"><div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">每日打卡与反馈</p><h1>数据记录</h1></div></div>
    <section class="record-intro mobile-card"><p class="eyebrow">今天的健康记录</p><h2>把完成情况告诉医护团队</h2><p>体重、饮食、运动和肺康复记录会用于每周复评与方案调整。</p></section>
    <div class="record-grid"><RouterLink to="/patient/records/body" class="record-entry"><span>⚖</span><div><strong>体重/体脂</strong><small>记录体重、体脂率和腰围</small></div><b>›</b></RouterLink><RouterLink to="/patient/records/diet" class="record-entry"><span>▤</span><div><strong>饮食</strong><small>早餐、午餐、晚餐＋图片和文字</small></div><b>›</b></RouterLink><RouterLink to="/patient/records/exercise" class="record-entry"><span>↗</span><div><strong>运动</strong><small>类型、时间、强度和完成情况</small></div><b>›</b></RouterLink><RouterLink to="/patient/records/pulmonary" class="record-entry"><span>◎</span><div><strong>肺预康复</strong><small>训练项目、计划次数和完成次数</small></div><b>›</b></RouterLink></div>
    <RouterLink to="/patient/records/trend" class="trend-entry"><div><p class="eyebrow">我的趋势</p><strong>查看体重、体脂、腰围、运动和肺康复变化</strong></div><span>›</span></RouterLink>
    <p class="patient-footnote">图片只上传、保存和查看，暂不自动识别。</p>
  </section>
</template>
