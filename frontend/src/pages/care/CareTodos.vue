<script setup>
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getCareTodos } from '../../mock/careTodos'
import { patientStore, refreshCareTodos } from '../../stores/patientStore'

const route = useRoute()
const tabMap = { assessment: 'pending-assessment', 'assessment-review': 'assessment-review', 'plan-review': 'plan-review', publish: 'publish', returned: 'returned' }
const tabs = [
  { key: 'pending-assessment', label: '待评估' },
  { key: 'assessment-review', label: '待审核评估' },
  { key: 'plan-review', label: '待审核方案' },
  { key: 'publish', label: '待发布' },
  { key: 'returned', label: '已退回' },
]
const activeTab = ref(tabMap[route.query.tab] || 'pending-assessment')
const source = computed(() => patientStore.apiTodos.length ? patientStore.apiTodos : getCareTodos())
const filtered = computed(() => source.value.filter((item) => item.tab === activeTab.value))
async function refresh() { await refreshCareTodos(activeTab.value) }
onMounted(refresh)
onActivated(refresh)
watch(activeTab, refresh)
</script>

<template>
  <section class="care-page">
    <div class="care-tabs"><button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button></div>
    <section class="care-panel"><div class="care-panel-head"><div><p class="eyebrow">统一待办队列</p><h2>{{ tabs.find((tab) => tab.key === activeTab)?.label }}</h2></div><span class="care-env">评估与方案统一处理</span></div><p class="care-note">评估审核、方案审核和发布共用一个工作队列，点击患者可进入患者360继续处理。</p></section>
    <section class="care-table-wrap"><table class="care-table"><thead><tr><th>患者</th><th>patient_id</th><th>事项类型</th><th>内容摘要</th><th>更新时间</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="item in filtered" :key="item.key"><td><strong>{{ item.patient }}</strong></td><td><code>{{ item.id }}</code></td><td>{{ item.type }}</td><td>{{ item.summary }}</td><td>{{ item.updated }}</td><td><span class="care-status yellow">{{ item.status }}</span></td><td><RouterLink class="table-action" :to="`/care/patients/${item.id}`">进入患者360</RouterLink></td></tr></tbody></table><div v-if="!filtered.length" class="care-empty">当前暂无待办事项</div></section>
  </section>
</template>
