<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import StatePanel from '../../components/common/StatePanel.vue'
import { currentPatient, consultationData, saveConsultation } from '../../stores/patientStore'

const sent = ref(false)
const type = ref('饮食')
const description = ref('')
const consultations = computed(() => consultationData(currentPatient.value.id))
function submit() {
  if (!description.value.trim()) return
  saveConsultation({ type: type.value, summary: description.value.trim() })
  description.value = ''
  sent.value = true
}
function statusClass(status) { return status === '已完成' ? 'green' : status === '已回复' ? 'blue' : 'yellow' }
</script>

<template>
  <section class="patient-page"><div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">一对一沟通 · {{ currentPatient.id }}</p><h1>在线咨询</h1></div></div><div class="consult-status"><span class="status-dot"></span>医护团队通常会在工作时间回复</div>
    <section class="mobile-card" v-if="!sent"><p class="eyebrow">新建咨询</p><label class="form-field wide">咨询分类<select v-model="type"><option>饮食</option><option>运动</option><option>肺预康复</option><option>指标变化</option><option>方案问题</option><option>其他</option></select></label><label class="form-field wide">咨询描述<textarea v-model="description" placeholder="请描述你想咨询的问题"></textarea></label><div class="upload-box compact"><span>＋</span><strong>上传相关图片（可选）</strong><small>图片只保存，不自动识别</small></div><button class="primary-mobile full-button" @click="submit">提交咨询</button></section>
    <section v-else class="mobile-card"><StatePanel icon="✓" title="咨询已提交" text="医护团队回复后，会在这里显示。" /><button class="secondary-mobile full-button" type="button" @click="sent = false">继续新建咨询</button></section>
    <section class="mobile-card"><div class="card-title-row"><div><p class="eyebrow">历史咨询</p><h2>与医护团队的沟通记录</h2></div><span class="status-text">{{ consultations.length }}条</span></div><div v-if="consultations.length" class="consult-history-list"><div v-for="item in consultations" :key="item.id" class="consult-row"><div><strong>{{ item.type }}</strong><small>{{ item.summary }}</small><div v-if="item.messages?.length" class="patient-message-list"><small v-for="(message,index) in item.messages" :key="index" :class="message.from === 'clinician' ? 'consult-reply' : ''">{{ message.from === 'clinician' ? '医护' : '我' }}：{{ message.text }}</small></div><small v-else-if="item.reply" class="consult-reply">医护回复：{{ item.reply }}</small></div><span class="care-status" :class="statusClass(item.status)">{{ item.status }}</span></div></div><p v-else class="empty-copy">您目前没有咨询记录。</p></section>
  </section>
</template>
