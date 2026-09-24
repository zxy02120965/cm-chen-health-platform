<script setup>
import { onActivated, onMounted, reactive } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { currentPatient, patientProfileData, refreshPatientFromApi, savePatientProfile } from '../../stores/patientStore'

const router = useRouter()
const patient = currentPatient
const profile = patientProfileData()
const form = reactive({ name: profile.name || '', sex: profile.sex || '', birthDate: profile.birthDate || '', phone: profile.phone || '', avatar: profile.avatar || '' })
async function refresh() { await refreshPatientFromApi(patient.value.id); Object.assign(form, patientProfileData(patient.value.id)) }
onMounted(refresh)
onActivated(refresh)
async function save() {
  await savePatientProfile({ ...form })
  window.alert('个人资料已保存')
  router.push('/patient/home')
}
</script>

<template>
  <section class="patient-page profile-page">
    <div class="page-title-mobile"><RouterLink to="/patient/home" class="back-link">‹</RouterLink><div><p class="eyebrow">{{ patient.id }} · 账号资料</p><h1>个人资料</h1></div></div>
    <section class="mobile-card profile-note"><p>以下信息用于账号身份展示，不属于健康评估内容。</p></section>
    <form class="mobile-card record-form-card" @submit.prevent="save">
      <div class="form-field"><label for="profile-name">姓名</label><input id="profile-name" v-model="form.name" type="text" autocomplete="name" /></div>
      <div class="form-field"><label>性别</label><div class="choice-grid"><label v-for="item in ['男', '女']" :key="item" class="choice-label"><input v-model="form.sex" type="radio" name="profile-sex" :value="item" />{{ item }}</label></div></div>
      <div class="form-field"><label for="profile-birth">出生年月</label><input id="profile-birth" v-model="form.birthDate" type="date" autocomplete="bday" /></div>
      <div class="form-field"><label for="profile-phone">联系方式</label><input id="profile-phone" v-model="form.phone" type="tel" autocomplete="tel" placeholder="请输入联系方式" /></div>
      <div class="form-field"><label for="profile-avatar">头像标识</label><input id="profile-avatar" v-model="form.avatar" type="text" maxlength="2" placeholder="可填写姓名首字" /></div>
      <div class="assessment-actions"><RouterLink to="/patient/home" class="secondary-mobile">取消</RouterLink><button class="primary-mobile" type="submit">保存资料</button></div>
    </form>
  </section>
</template>
