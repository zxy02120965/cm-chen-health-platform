<script setup>
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { mockPatients } from '../mock/patients'
import { currentPatient, patientProfileData, patientStore, persist, syncFromStorage, refreshPatientFromApi } from '../stores/patientStore'

const router = useRouter()
const patient = currentPatient
const profile = computed(() => patientProfileData())
const isDev = import.meta.env.DEV
const showMockSwitcher = ref(false)
function changePatient(event) { patientStore.currentId = event.target.value; persist(); router.push('/patient/home') }
async function refresh() { syncFromStorage(); await refreshPatientFromApi(patientStore.currentId) }
onMounted(refresh)
onActivated(refresh)
watch(() => router.currentRoute.value.fullPath, refresh)
</script>

<template>
  <div class="patient-app"><header class="patient-topbar"><div class="patient-brand"><span class="brand-mark">CM</span><div><strong>CM Chen</strong><small>我的健康管理</small></div></div><div class="patient-account"><div class="patient-identity"><strong>{{ profile.name }}</strong><span>{{ profile.sex }} · {{ patient.age }} · {{ patient.id }}</span></div><button v-if="isDev" type="button" class="mock-toggle" @click="showMockSwitcher = !showMockSwitcher">Mock测试</button><select v-if="isDev && showMockSwitcher" :value="patientStore.currentId" aria-label="开发测试患者切换" @change="changePatient"><option v-for="p in mockPatients" :key="p.id" :value="p.id">{{ p.id }} · {{ p.name }}</option></select><RouterLink class="care-link" to="/care/dashboard">医护端预览</RouterLink></div></header><main class="patient-main"><RouterView /></main></div>
</template>
