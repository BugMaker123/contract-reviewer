<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <label class="block"
    ><span class="label">合同正文</span
    ><textarea
      v-model="draft.text"
      @mouseup="captureSelection"
      @keyup="captureSelection"
      class="field h-[500px] leading-loose"
      placeholder="生成后在此核对并编辑合同正文…"
    ></textarea>
  </label>
  <p class="text-xs text-slate-500">
    保存后可导出 Word，或送入审查工作台。仍含【待填写】的内容请先补充。
  </p>
  <details class="border-t border-slate-200 pt-4">
    <summary class="cursor-pointer text-xs font-semibold text-blue-600">
      定向改写选中条款
    </summary>
    <div class="mt-4 space-y-3">
      <p class="text-xs text-slate-500">
        在正文中选中条款，或在下方粘贴需要改写的完整原文。生成后先核对，再确认替换。
      </p>
      <label class="block"
        ><span class="label">需要改写的原文</span
        ><textarea
          v-model="rewriteSelection.original"
          class="field h-24"
        ></textarea></label
      ><label class="block"
        ><span class="label">改写要求</span
        ><input
          v-model="rewriteSelection.instruction"
          class="field"
          placeholder="如：保持金额与期限不变，改为更温和的表达" /></label
      ><button
        @click="requestRewrite"
        :disabled="
          busy ||
          !rewriteSelection.original.trim() ||
          !rewriteSelection.instruction.trim()
        "
        class="button primary"
      >
        生成改写建议
      </button>
      <div
        v-if="rewriteSelection.proposal"
        class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 space-y-3"
      >
        <p class="text-sm whitespace-pre-wrap leading-relaxed text-emerald-900">
          {{ rewriteSelection.proposal }}
        </p>
        <button @click="applyRewrite" :disabled="busy" class="button primary">
          确认替换并保存</button
        ><button @click="rewriteSelection.proposal = ''" class="button">
          放弃建议
        </button>
      </div>
    </div>
  </details>
</template>
