<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { computed } from 'vue'
const route = useRoute()
const nav = [{ label: '工作台', to: '/care/dashboard', key: 'dashboard' }, { label: '患者管理', to: '/care/patients', key: 'patients' }, { label: '待办管理', to: '/care/todos', key: 'todos' }, { label: '监测与预警', to: '/care/alerts', key: 'alerts' }, { label: '咨询管理', to: '/care/consults', key: 'consults' }, { label: '系统管理', to: '/care/settings', key: 'settings' }]
const active = computed(() => route.meta.careNav || 'dashboard')
</script>
<template>
  <div class="care-shell"><aside class="care-sidebar"><div class="care-brand"><span class="brand-mark">CM</span><div><strong>CM Chen</strong><small>统一医护工作台</small></div></div><div class="care-user"><span>医护</span><div><strong>审核医护账号</strong><small>一名审核 · 演示环境</small></div></div><nav><RouterLink v-for="item in nav" :key="item.key" :to="item.to" :class="{ active: active === item.key }">{{ item.label }}</RouterLink></nav><RouterLink class="back-patient" to="/patient/home">← 返回患者端</RouterLink></aside><main class="care-content"><header class="care-header"><div><p class="eyebrow">医护端 Web · V1.0</p><h1>{{ nav.find((item) => item.key === active)?.label || '患者360' }}</h1></div><span class="care-env">Mock数据 · 不连接生产</span></header><RouterView /></main></div>
</template>
