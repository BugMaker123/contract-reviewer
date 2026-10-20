<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="form.mode === 'compare'" class="px-6 pb-5 space-y-3">
    <div class="flex justify-between items-center">
      <span class="label mb-0">参考合同</span
      ><button
        @click="$refs.referenceInput.click()"
        :disabled="importing"
        class="button"
      >
        上传参考合同</button
      ><input
        ref="referenceInput"
        type="file"
        class="hidden"
        accept=".docx,.pdf,.txt"
        @change="importDocument($event, 'reference')"
      />
    </div>
    <textarea
      v-model="form.reference_text"
      class="field h-40"
      placeholder="上传或粘贴用于对照的参考合同…"
      aria-label="参考合同正文"
    ></textarea>
    <p class="text-[11px] text-slate-500">
      先识别文本变更，再核验影响；参考合同本身不代表企业标准。
    </p>
  </div>
</template>
