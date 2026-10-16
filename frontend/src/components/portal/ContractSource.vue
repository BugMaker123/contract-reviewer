<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div class="p-6">
    <input
      type="file"
      ref="contractInput"
      class="hidden"
      accept=".docx,.pdf,.txt"
      @change="importDocument($event, 'contract')"
    />
    <div
      v-if="inputMethod === 'file' && !form.text"
      class="drop-area"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="
        dragging = false;
        importDocument($event, 'contract', true);
      "
      @click="!importing && $refs.contractInput.click()"
    >
      <div
        class="mx-auto w-12 h-12 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-center text-2xl text-blue-600 mb-4"
      >
        ↥
      </div>
      <div class="text-sm font-semibold">
        {{
          importing ? "正在提取合同正文…" : "拖拽合同文件至此处，或点击浏览文件"
        }}
      </div>
      <div class="text-xs text-slate-400 mt-2">
        DOCX · 文字型 PDF · TXT，最大 10 MB
      </div>
    </div>
    <div v-else-if="inputMethod === 'file'" class="space-y-3">
      <div
        class="flex justify-between items-center p-3 rounded-lg bg-blue-50 border border-blue-200"
      >
        <div class="text-xs text-blue-800">
          <strong>{{ form.title }}</strong>
          <div class="mt-1 text-slate-500">已提取正文，请核对内容</div>
        </div>
        <button
          @click="$refs.contractInput.click()"
          :disabled="importing"
          class="button"
        >
          重新选择
        </button>
      </div>
      <details>
        <summary class="text-xs text-blue-600 cursor-pointer">
          核对或修正提取正文
        </summary>
        <textarea
          v-model="form.text"
          class="field mt-3 h-48 leading-relaxed"
          aria-label="提取合同正文"
        ></textarea>
      </details>
    </div>
    <textarea
      v-else-if="inputMethod === 'paste'"
      v-model="form.text"
      class="field h-52 leading-relaxed"
      placeholder="在此粘贴合同正文…"
      aria-label="合同正文"
    ></textarea>
    <div v-else class="space-y-2">
      <p class="text-xs text-slate-500 mb-3">
        示例用于熟悉流程，请勿作为实际业务合同。
      </p>
      <button
        v-for="(sample, key) in samples"
        @click="selectSample(key)"
        class="w-full p-4 border rounded-xl text-left"
        :class="
          sampleKey === key
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-200 bg-slate-50'
        "
      >
        <span class="text-xs font-semibold">{{ sample.title }}</span
        ><span class="pill ml-2">示例</span
        ><span class="text-[11px] text-slate-500 mt-2 block"
          >{{ sample.type }} · {{ sample.text.length }} 字</span
        >
      </button>
    </div>
  </div>
</template>
