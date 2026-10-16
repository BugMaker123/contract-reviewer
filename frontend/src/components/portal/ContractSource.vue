<script>
import { ref } from "vue";
export default {
  props: { context: { type: Object, required: true } },
  setup(props) {
    const previewOpen = ref(false);
    return { ...props.context, previewOpen };
  },
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
        <div class="contract-file-actions">
          <button type="button" class="button soft" @click="previewOpen = true">预览合同</button>
          <button type="button" @click="$refs.contractInput.click()" :disabled="importing" class="button">重新选择</button>
        </div>
      </div>
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
    <div v-if="previewOpen" class="modal" @click.self="previewOpen = false">
      <section class="modal-panel contract-preview" role="dialog" aria-modal="true" aria-labelledby="contract-preview-title" @keydown.esc="previewOpen = false">
        <header class="contract-preview-header">
          <div><h2 id="contract-preview-title">合同预览</h2><p>{{ form.title || '未命名合同' }}</p></div>
          <button type="button" class="button" aria-label="关闭预览" @click="previewOpen = false">关闭</button>
        </header>
        <iframe v-if="form.source_id" class="contract-preview-document" :src="'/static/document-preview.html?source=' + encodeURIComponent(form.source_id) + '&readonly=1'" title="合同原件预览" sandbox="allow-scripts allow-same-origin allow-downloads"></iframe>
        <div v-else class="contract-preview-content">{{ form.text }}</div>
      </section>
    </div>
  </div>
</template>
