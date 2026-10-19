<script setup>
defineProps({ context: { type: Object, required: true } });
</script>

<template>
  <section class="stale-review-notice" role="status">
    <span class="stale-review-icon" aria-hidden="true">↻</span>
    <h3>审查条件已改变</h3>
    <p>请按当前条件重新审查，生成对应的导航与建议。</p>
    <button @click="context.requestReview()" :disabled="context.isReviewing.value || context.workspace.loading || context.workspace.historical || context.revisionBusy.value || ['running', 'queued'].includes(context.workspace.task?.status)">重新审查</button>
    <small>切回原审查条件，将恢复原有意见和处理进度。</small>
  </section>
</template>

<style scoped>
.stale-review-notice { margin:20px 16px; padding:30px 20px; border:1px dashed #cbd9ee; border-radius:12px; background:#f8faff; text-align:center; }
.stale-review-icon { display:grid; place-items:center; width:38px; height:38px; margin:0 auto 16px; border-radius:10px; background:#eaf1ff; color:#2563eb; font-size:25px; }
.stale-review-notice h3 { margin:0 0 10px; color:#334155; font-size:14px; font-weight:600; }
.stale-review-notice p { margin:0; color:#64748b; font-size:12px; line-height:1.9; }
.stale-review-notice button { margin:20px 0 16px; padding:9px 20px; border:1px solid #2563eb; border-radius:7px; background:#2563eb; color:#fff; font-size:12px; font-weight:600; cursor:pointer; }
.stale-review-notice button:disabled { opacity:.5; cursor:not-allowed; }
.stale-review-notice small { display:block; color:#94a3b8; font-size:11px; line-height:1.8; }
</style>
