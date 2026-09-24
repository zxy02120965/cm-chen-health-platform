<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { allConsultations, consultationData, sendConsultationReply, updateConsultation } from '../../stores/patientStore'
import { getMockPatient } from '../../mock/patients'

const route = useRoute()
const tabs = ['待处理', '未回复', '已回复', '已完成']
const tab = ref(tabs.includes(route.query.tab) ? route.query.tab : '待处理')
const search = ref('')
const selected = ref(null)
const replyText = ref('')
const consultations = computed(() => allConsultations().filter((item) => { const patient = getMockPatient(item.patientId); const hit = !search.value || `${patient.name}${patient.id}${item.summary}`.includes(search.value); const tabHit = tab.value === '待处理' ? item.handling !== '已完成' : tab.value === '未回复' ? item.status === '待回复' : tab.value === '已回复' ? item.status === '已回复' : item.status === '已完成'; return hit && tabHit }))
function openReply(item) { selected.value = item; replyText.value = '' }
function sendReply() { if (!selected.value || !replyText.value.trim()) return; sendConsultationReply(selected.value.id, replyText.value); selected.value = consultationData(selected.value.patientId).find((item) => item.id === selected.value.id); replyText.value = '' }
function complete(item) { updateConsultation(item.id, { status: '已完成', handling: '已完成' }); if (selected.value?.id === item.id) selected.value = null }
</script>

<template><section class="care-page"><div class="care-tabs"><button v-for="item in tabs" :key="item" :class="{ active: tab === item }" @click="tab = item">{{ item }}</button></div><div class="care-toolbar"><input v-model="search" placeholder="搜索患者姓名、patient_id或咨询内容" /><span>共 {{ consultations.length }} 条咨询</span></div><section class="care-table-wrap"><table class="care-table"><thead><tr><th>咨询编号</th><th>咨询时间</th><th>患者</th><th>性别</th><th>咨询类型</th><th>内容摘要</th><th>消息状态</th><th>处理状态</th><th>责任医护</th><th>操作</th></tr></thead><tbody><tr v-for="item in consultations" :key="item.id"><td><code>{{ item.id }}</code></td><td>{{ item.createdAt }}</td><td><RouterLink class="table-action" :to="`/care/patients/${item.patientId}`">{{ getMockPatient(item.patientId).name }}</RouterLink></td><td>{{ getMockPatient(item.patientId).sex }}</td><td>{{ item.type }}</td><td>{{ item.summary }}</td><td><span class="care-status" :class="item.status === '待回复' ? 'yellow' : item.status === '已完成' ? '' : 'blue'">{{ item.status }}</span></td><td>{{ item.handling }}</td><td>{{ item.repliedBy || '—' }}</td><td><button class="table-action-button" @click="openReply(item)">{{ item.status === '待回复' ? '回复' : '查看/回复' }}</button><button v-if="item.status !== '已完成'" class="table-action-button" @click="complete(item)">完成</button><RouterLink class="table-action" :to="`/care/patients/${item.patientId}`">患者360</RouterLink></td></tr></tbody></table><div v-if="!consultations.length" class="care-empty">当前没有匹配的咨询</div></section><section v-if="selected" class="care-panel consult-detail-panel"><div class="care-panel-head"><div><p class="eyebrow">咨询详情 · {{ selected.id }}</p><h2>{{ getMockPatient(selected.patientId).name }} · {{ selected.type }}</h2><small>{{ selected.createdAt }}</small></div><button class="table-action-button" @click="selected = null">关闭</button></div><div class="message-thread"><div v-for="(message,index) in (selected.messages || [{ from: 'patient', text: selected.summary, at: selected.createdAt }])" :key="index" class="message-bubble" :class="message.from"><span>{{ message.from === 'patient' ? '患者' : '医护' }} · {{ message.at }}</span><p>{{ message.text }}</p></div></div><div class="reply-composer"><textarea v-model="replyText" placeholder="请输入医护回复内容"></textarea><button class="primary-care" @click="sendReply">发送回复</button></div></section></section></template>
