<script setup>
defineProps({
  planStatus: { type: String, default: '' },
  reviewEligible: { type: Boolean, default: false },
  publishEligible: { type: Boolean, default: false },
  reviewText: { type: String, default: '' },
  publishConfirm: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:reviewText',
  'return',
  'approve',
  'request-publish',
  'confirm-publish',
  'cancel-publish',
])
</script>

<template>
  <div class="clinician-plan-actions">
    <label>审核备注（可选）<textarea :value="reviewText" @input="emit('update:reviewText', $event.target.value)"></textarea></label>

    <div class="care-actions">
      <template v-if="planStatus !== 'PUBLISHED'">
        <button type="button" @click="emit('return')">退回修改</button>
        <button type="button" class="primary-care" :disabled="!reviewEligible" @click="emit('approve')">审核通过</button>
        <button type="button" class="primary-care" :disabled="!publishEligible" @click="emit('request-publish')">发布给患者</button>
      </template>
      <button v-else class="published-action" disabled>已发布</button>
    </div>

    <div v-if="publishConfirm" class="confirm-panel">
      <strong>确认发布给患者？</strong>
      <button type="button" class="primary-care" @click="emit('confirm-publish')">确认发布</button>
      <button type="button" @click="emit('cancel-publish')">取消</button>
    </div>

  </div>
</template>
