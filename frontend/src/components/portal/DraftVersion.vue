<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="previewDraftVersion" class="modal">
    <div class="modal-panel max-w-3xl p-6 space-y-4">
      <div class="flex justify-between">
        <h2 class="font-bold">
          历史草稿 · {{ dateTime(previewDraftVersion.created_at) }}
        </h2>
        <button @click="previewDraftVersion = null">✕</button>
      </div>
      <pre class="whitespace-pre-wrap text-sm leading-relaxed">{{
        previewDraftVersion.text ||
        previewDraftVersion.outline ||
        previewDraftVersion.background
      }}</pre>
    </div>
  </div>
</template>
