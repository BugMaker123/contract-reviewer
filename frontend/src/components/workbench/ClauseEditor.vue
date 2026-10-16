<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="clauseEdit"
    class="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-6"
  >
    <div
      class="bg-white border border-slate-200 rounded-xl p-6 max-w-2xl w-full space-y-4 shadow-xl"
    >
      <h3 class="font-semibold">编辑条款 · {{ clauseEdit.title }}</h3>
      <p class="text-xs text-slate-500">
        保存将更新待审正文，旧审查结果及处理记录保留，请重新审查新版本。
      </p>
      <textarea
        :disabled="documentSaving"
        v-model="clauseEdit.text"
        class="w-full h-56 text-sm leading-relaxed p-4 border border-slate-200 rounded-lg"
      ></textarea>
      <div class="flex justify-end gap-3">
        <button
          @click="clauseEdit = null"
          class="px-3 py-2 text-xs text-slate-500"
        >
          取消</button
        ><button
          @click="saveClauseEditor"
          :disabled="documentSaving"
          class="px-4 py-2 text-xs text-white bg-blue-600 rounded-lg"
        >
          保存条款
        </button>
      </div>
    </div>
  </div>
</template>
