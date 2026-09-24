<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getKnowledgeItems } from '../../mock/knowledge'
const selected = ref('全部')
const categories = ['全部', '术前准备', '营养管理', '运动康复', '肺预康复', '术后恢复', '常见问题']
const publishedItems = computed(() => getKnowledgeItems().filter((item) => item.status === 'PUBLISHED'))
const items = computed(() => selected.value === '全部' ? publishedItems.value : publishedItems.value.filter((item) => item.category === selected.value))
</script>
<template><section class="patient-page knowledge-page"><div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">医院健康宣教视频入口</p><h1>知识科普</h1></div></div><div class="knowledge-tabs"><button v-for="category in categories" :key="category" :class="{ active: selected === category }" @click="selected = category">{{ category }}</button></div><div class="knowledge-list"><RouterLink v-for="item in items" :key="item.id" :to="`/patient/knowledge/${item.id}`" class="knowledge-item"><span class="knowledge-icon">{{ item.type === '视频' ? '▶' : '文' }}</span><div><strong>{{ item.title }}</strong><small>{{ item.category }} · {{ item.type }} · {{ item.duration }}</small><p>{{ item.intro }}</p></div><b>›</b></RouterLink></div><p v-if="!items.length" class="empty-copy">暂无该分类内容。</p><p class="patient-footnote">视频为医院官方宣教入口，图文内容作为辅助说明。</p></section></template>
