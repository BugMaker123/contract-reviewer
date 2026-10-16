<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="showEditor"
    class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6"
  >
    <div class="bg-white rounded-xl p-6 w-full max-w-3xl space-y-4 shadow-xl">
      <h3 class="font-semibold text-slate-900">编辑审查原文</h3>
      <p class="text-xs text-slate-500">
        保存正文后需要重新审查。已采纳的修改请通过“导出修订稿”保留。
      </p>
      <div class="grid grid-cols-2 gap-3 text-xs">
        <label
          >合同名称<input
            v-model="editTitle"
            class="mt-1 w-full border rounded-lg p-2" /></label
        ><label
          >合同类型<input
            v-model="editType"
            class="mt-1 w-full border rounded-lg p-2"
        /></label>
      </div>
      <textarea
        :disabled="documentSaving"
        v-model="editText"
        aria-label="编辑合同正文"
        class="w-full h-80 border border-slate-200 rounded-lg p-4 text-sm leading-relaxed outline-none focus:border-blue-500"
      ></textarea>
      <div class="flex justify-end gap-3">
        <button
          @click="showEditor = false"
          class="text-xs text-slate-600 px-3 py-2"
        >
          取消</button
        ><button
          @click="saveEditor"
          :disabled="documentSaving || !editText.trim()"
          class="text-xs bg-blue-600 text-white rounded-lg px-4 py-2"
        >
          保存正文
        </button>
      </div>
    </div>
  </div>
</template>
