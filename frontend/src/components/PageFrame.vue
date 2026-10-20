<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>
<template>
  <div
    v-if="error"
    role="alert"
    class="max-w-6xl mx-auto mb-5 p-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-700 flex justify-between gap-3"
  >
    <span>{{ error }}</span
    ><button @click="error = ''" aria-label="关闭错误提示">✕</button>
  </div>
  <div v-if="loading" class="empty" role="status">正在加载工作记录…</div>
  <slot v-else />
</template>
