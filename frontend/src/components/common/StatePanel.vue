<script setup>
defineProps({ icon: { type: String, default: '✦' }, title: { type: String, required: true }, text: { type: String, required: true } })
</script>
<template><div class="state-panel"><div class="state-icon">{{ icon }}</div><h3>{{ title }}</h3><p>{{ text }}</p></div></template>
