<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <label v-for="(value, key) in draft.details"
      ><span class="label">{{ key }}</span
      ><input v-model="draft.details[key]" class="field" placeholder="待确认"
    /></label>
  </div>
  <div class="flex justify-between gap-3">
    <p class="text-xs text-slate-500">
      请核对交易信息。可手动填写，无需先调用模型。
    </p>
    <button
      @click="generateDraft('outline')"
      :disabled="busy"
      class="button primary"
    >
      {{ busy ? "正在生成…" : "确认信息并生成大纲" }}
    </button>
  </div>
</template>
