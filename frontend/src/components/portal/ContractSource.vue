<script>
import { ref, watch } from "vue";
import RichContractEditor from "./RichContractEditor.vue";
export default {
  components: { RichContractEditor },
  props: { context: { type: Object, required: true } },
  setup(props) {
    const previewOpen = ref(false), contractInput = ref(null);
    const openFile = () => { if (!props.context.importing.value) contractInput.value?.click(); };
    watch(() => props.context.contractUploadRequest.value, openFile);
    return { ...props.context, previewOpen, contractInput, openFile };
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
      <div class="contract-drop-icon" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
          <path d="M14 3v6h6M8 13h8M8 17h5" />
        </svg>
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
    <RichContractEditor v-else-if="inputMethod === 'paste'" v-model:html="form.paste_html" :text="form.text" :disabled="importing || busy" @text-change="form.text = $event; form.source_id = null" />
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
