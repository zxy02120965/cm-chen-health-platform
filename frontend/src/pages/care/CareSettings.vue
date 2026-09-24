<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getKnowledgeItems, publishKnowledgeItem } from '../../mock/knowledge'

const route = useRoute()
const tab = ref(route.query.tab === 'education' ? 'education' : 'system')
const refreshKey = ref(0)
const education = computed(() => { refreshKey.value; return getKnowledgeItems().map((item, index) => ({ ...item, statusLabel: item.status === 'PUBLISHED' ? '已发布' : '草稿', updated: item.publishedAt ? String(item.publishedAt).slice(0, 10) : `2026-09-${String(3 - Math.min(index, 2)).padStart(2, '0')}` })) })
function publish(item) { publishKnowledgeItem(item.id); refreshKey.value += 1 }
</script>

<template>
  <section class="care-page">
    <div class="care-tabs"><button :class="{ active: tab === 'system' }" @click="tab = 'system'">系统设置</button><button :class="{ active: tab === 'education' }" @click="tab = 'education'">宣教管理</button></div>
    <section v-if="tab === 'system'" class="care-panel"><p class="eyebrow">系统管理</p><h2>账号与原型配置</h2><div class="care-detail-grid"><div><span>医护账号</span><strong>统一审核医护账号</strong></div><div><span>数据环境</span><strong>Mock · 不连接生产</strong></div><div><span>权限模式</span><strong>一名审核医护</strong></div></div><p class="care-note">正式登录、权限策略和消息设置将在后续接入真实服务。</p></section>
    <section v-else class="care-table-wrap"><table class="care-table"><thead><tr><th>标题</th><th>分类</th><th>内容类型</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead><tbody><tr v-for="item in education" :key="item.title"><td><strong>{{ item.title }}</strong></td><td>{{ item.category }}</td><td>{{ item.type }}</td><td><span class="care-status" :class="item.statusLabel === '草稿' ? 'yellow' : ''">{{ item.statusLabel }}</span></td><td>{{ item.updated }}</td><td><button v-if="item.status !== 'PUBLISHED'" class="table-action" @click="publish(item)">发布</button><span v-else class="care-note">患者端已同步</span></td></tr></tbody></table></section>
  </section>
</template>
