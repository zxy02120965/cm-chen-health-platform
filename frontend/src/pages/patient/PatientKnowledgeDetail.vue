<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import StatePanel from '../../components/common/StatePanel.vue'
import { getKnowledgeItem } from '../../mock/knowledge'
const route = useRoute(); const item = computed(() => getKnowledgeItem(route.params.id))
</script>
<template><section class="patient-page knowledge-detail"><div v-if="item" class="page-title-mobile"><RouterLink to="/patient/knowledge" class="back-link">‹</RouterLink><div><p class="eyebrow">{{ item.category }} · {{ item.type }} · {{ item.duration }}</p><h1>{{ item.title }}</h1></div></div><template v-if="item"><section class="mobile-card"><p class="eyebrow">内容简介</p><p class="knowledge-intro">{{ item.intro }}</p></section><section class="video-placeholder"><div class="video-screen"><span class="play-mark">▶</span><strong>医院视频号</strong><small>扫码观看医院官方宣教视频</small></div><p>二维码占位图：后续替换为医院官方二维码即可。</p></section><section v-if="item.type === '图文'" class="mobile-card article-lite"><p class="eyebrow">图文辅助说明</p><h2>请结合医护团队的个性化建议阅读</h2><p>这是一段简短的图文内容占位，后续可替换为经审核的医院宣教文字。</p></section></template><StatePanel v-else icon="?" title="暂未找到这条宣教内容" text="请返回知识科普首页，选择其他医院宣教内容。" /><RouterLink to="/patient/knowledge" class="secondary-mobile back-knowledge">返回知识科普</RouterLink></section></template>
