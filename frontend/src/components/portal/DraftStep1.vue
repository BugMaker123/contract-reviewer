<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <label class="block"
    ><span class="label">起草背景与要求</span
    ><textarea
      v-model="draft.background"
      class="field h-36"
      placeholder="描述合同类型、交易目的、合作安排和我方要求…"
    ></textarea>
  </label>
  <div class="flex justify-between items-center">
    <span class="label mb-0">参考模板（可选）</span
    ><button
      @click="$refs.templateInput.click()"
      class="button"
      :disabled="importing"
    >
      导入模板</button
    ><input
      type="file"
      ref="templateInput"
      class="hidden"
      accept=".docx,.pdf,.txt"
      @change="importDocument($event, 'template')"
    />
  </div>
  <details v-if="draft.template_text">
    <summary class="text-xs text-blue-600 cursor-pointer">
      查看参考模板（{{ draft.template_text.length }} 字）
    </summary>
    <textarea v-model="draft.template_text" class="field h-36 mt-3"></textarea>
  </details>
  <div class="flex justify-between items-center">
    <span class="label mb-0">起草参考资料</span
    ><button
      @click="$refs.draftMaterialInput.click()"
      class="button"
      :disabled="importing || draft.references.length >= 5"
    >
      添加参考资料</button
    ><input
      type="file"
      ref="draftMaterialInput"
      class="hidden"
      accept=".docx,.pdf,.txt"
      @change="importDocument($event, 'draft_material')"
    />
  </div>
  <div
    v-for="(material, index) in draft.references"
    class="text-xs border border-slate-200 rounded-lg p-3"
  >
    <div class="flex justify-between">
      <span>{{ material.name }} · {{ material.text.length }} 字</span
      ><button
        @click="draft.references.splice(index, 1)"
        class="text-slate-400"
      >
        移除
      </button>
    </div>
    <details class="mt-2">
      <summary class="text-blue-600 cursor-pointer">核对内容</summary>
      <textarea v-model="material.text" class="field h-24 mt-2"></textarea>
    </details>
  </div>
  <button
    @click="generateDraft('details')"
    :disabled="busy || !draft.background.trim() || !draft.title.trim()"
    class="button primary"
  >
    {{ busy ? "正在分析…" : "分析待确认交易信息" }}
  </button>
  <p class="text-[11px] text-slate-500">
    需配置可用模型。未知的交易信息会保留为待确认，不自动编造。
  </p>
</template>
