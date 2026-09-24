<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { mockPatients } from '../../mock/patients'
import { getCareAlerts, markCareAlertHandled } from '../../mock/careAlerts'

const route = useRoute()
const handled = ref([])
const tabs = ['全部', '黄色关注', '红色重点', '已处理']
const tab = ref(tabs.includes(route.query.tab) ? route.query.tab : '全部')
const alertItems = ref(getCareAlerts())
const alerts = computed(() => alertItems.value.map((item) => ({ ...item, patient: mockPatients.find((patient) => patient.id === item.patientId), handled: item.handled || handled.value.includes(item.patientId) })))
const filtered = computed(() => alerts.value.filter((item) => tab.value === '全部' || (tab.value === '黄色关注' && item.level === 'yellow') || (tab.value === '红色重点' && item.level === 'red') || (tab.value === '已处理' && item.handled)))
function levelText(level) { return level === 'red' ? '红色重点' : '黄色关注' }
function markHandled(id) { if (!handled.value.includes(id)) handled.value.push(id); alertItems.value = markCareAlertHandled(id) }
</script>

<template><section class="care-page"><div class="care-tabs"><button v-for="item in tabs" :key="item" :class="{ active: tab === item }" @click="tab = item">{{ item }}</button></div><div class="care-toolbar"><span>跨患者异常与重点患者队列 · 共 {{ filtered.length }} 条</span></div><section class="care-table-wrap"><table class="care-table"><thead><tr><th>患者</th><th>异常类型</th><th>最新数据/摘要</th><th>安全等级</th><th>触发时间</th><th>处理状态</th><th>责任医护</th><th>操作</th></tr></thead><tbody><tr v-for="item in filtered" :key="item.patient.id"><td><RouterLink class="table-action" :to="`/care/patients/${item.patient.id}`">{{ item.patient.name }}</RouterLink><small>{{ item.patient.id }}</small></td><td>{{ item.type }}</td><td>{{ item.value }}</td><td><span class="care-status" :class="item.level">{{ levelText(item.level) }}</span></td><td>{{ item.triggeredAt }}</td><td>{{ item.handled ? '已处理' : '待处理' }}</td><td>审核医护</td><td><button v-if="!item.handled" class="table-action-button" @click="markHandled(item.patient.id)">标记处理</button><RouterLink class="table-action" :to="`/care/patients/${item.patient.id}`">患者360</RouterLink></td></tr></tbody></table><div v-if="!filtered.length" class="care-empty">当前没有匹配的异常记录</div></section></section></template>
