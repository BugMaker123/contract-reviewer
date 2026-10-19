<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue';
const props = defineProps({context:{type:Object,required:true}});
const paragraphs = ref([]), error = ref(''), loading = ref(false), scope = ref('report');
let generation = 0;
watch(() => [props.context.showReportModal.value, props.context.workspace.run?.revision, scope.value], async ([open]) => {
  const ticket = ++generation;
  if (!open || !props.context.workspace.run) return;
  loading.value = true; error.value = ''; paragraphs.value = [];
  try {
    await props.context.workspace.flush();
    const response = await fetch(`/api/runs/${props.context.workspace.run.id}/report-content?scope=${scope.value}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '意见书读取失败');
    if (ticket === generation) paragraphs.value = data.paragraphs;
  } catch (err) { if (ticket === generation) error.value = err.message; }
  finally { if (ticket === generation) loading.value = false; }
});
const metadata = computed(() => paragraphs.value.slice(1, 8));
const content = computed(() => paragraphs.value.slice(8));
const directory = computed(() => content.value.map((paragraph,index) => ({ ...paragraph, id: 'report-section-' + index })).filter(paragraph => paragraph.heading));
const jumpTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
const splitField = (text) => { const index = text.indexOf('：'); return { label: text.slice(0,index), value: text.slice(index + 1) }; };
const riskClass = (text) => text.startsWith('【未满足】') || text.startsWith('【重大风险】') || text.startsWith('重大风险 ·') ? 'report-risk-high' : text.startsWith('【待确认】') || text.startsWith('【一般风险】') || text.startsWith('一般风险 ·') ? 'report-risk-medium' : text.startsWith('【优化建议】') || text.startsWith('优化建议 ·') ? 'report-risk-low' : text.startsWith('【符合】') || text.startsWith('【有利条款】') || text.startsWith('有利条款 ·') ? 'report-risk-favorable' : '';
let previousTitle = null, printingTitle = '';
const preparePrintTitle = () => {
  if (!props.context.showReportModal.value) return;
  if (previousTitle === null) previousTitle = document.title;
  const contractName = metadata.value[0]?.text?.replace(/^合同名称[：:]\s*/, '') || props.context.workspace.run?.input?.title || props.context.workspace.task?.title || '未命名合同';
  const safeName = contractName.replace(/[<>:"/\\|?*\x00-\x1f]/g, '-').replace(/[.\s]+$/, '').trim() || '未命名合同';
  printingTitle = `${safeName}-审查意见书-第${props.context.workspace.run?.number || 1}次审查${scope.value === 'applied_report' ? '-仅已采纳意见' : ''}`;
  document.title = printingTitle;
};
const restorePrintTitle = () => {
  if (previousTitle !== null && document.title === printingTitle) document.title = previousTitle;
  previousTitle = null;
};
onMounted(() => { window.addEventListener('beforeprint', preparePrintTitle); window.addEventListener('afterprint', restorePrintTitle); });
onUnmounted(() => { restorePrintTitle(); window.removeEventListener('beforeprint', preparePrintTitle); window.removeEventListener('afterprint', restorePrintTitle); });
watch(() => props.context.showReportModal.value, (open) => { if (!open) restorePrintTitle(); });
const print = () => {
  preparePrintTitle();
  try { window.print(); } catch (error) { restorePrintTitle(); throw error; }
};
const download = () => { props.context.workspace.exportScope = scope.value; props.context.workspace.exportWord(); };
</script>
<template>
  <div v-if="context.showReportModal.value" class="wb-report-overlay fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4">
    <section class="wb-report-dialog" role="dialog" aria-modal="true" aria-labelledby="report-preview-title">
      <header class="wb-report-toolbar no-print">
        <div class="wb-report-toolbar-title"><strong id="report-preview-title">审查意见书</strong><span>第 {{ context.workspace.run?.number }} 次审查</span></div><div class="wb-report-actions">
        <select class="wb-report-scope" v-model="scope" aria-label="意见书范围"><option value="report">全部审查意见</option><option value="applied_report">仅已采纳意见</option></select>
        <button class="wb-report-download" :disabled="loading || !!error || !context.workspace.canExportReport" :title="context.workspace.canExportReport ? '' : '请先完成审查'" @click="download">下载 Word</button>
        <button :disabled="loading || !!error || !context.workspace.canExportReport" :title="context.workspace.canExportReport ? '' : '请先完成审查'" @click="print">打印 / 存为 PDF</button>
        <button aria-label="关闭意见书" @click="context.showReportModal.value = false">关闭</button>
      </div></header>
      <p v-if="loading" class="p-4">正在生成意见书…</p><p v-if="error" role="alert" class="p-4 text-red-600">{{ error }}</p>
      <div class="wb-report-body">
        <nav v-if="directory.length" class="wb-report-directory" aria-label="审查意见书目录">
          <h2>目录</h2>
          <a href="#report-document-top" @click.prevent="jumpTo('report-document-top')">合同信息与审查结论</a>
          <a v-for="entry in directory" :key="entry.id" :href="'#' + entry.id" :class="riskClass(entry.text)" @click.prevent="jumpTo(entry.id)">{{ entry.text }}</a>
        </nav>
      <div class="wb-report-scroll">
        <article v-if="!loading && !error && paragraphs.length" id="printable-report" class="wb-report-paper">
          <p class="wb-report-eyebrow">LEXISGRAPH · 合同审查</p>
          <h1 id="report-document-top">{{ paragraphs[0].text }}</h1>
          <p class="wb-report-subtitle">{{ context.workspace.task?.title || '合同审查结果' }}</p>
          <dl class="wb-report-metadata">
            <div v-for="(paragraph,index) in metadata" :key="index"><dt>{{ splitField(paragraph.text).label }}</dt><dd>{{ splitField(paragraph.text).value }}</dd></div>
          </dl>
          <p v-if="context.resultStale.value" class="wb-report-notice">正文或审查条件已改变，本意见书属于历史审查输入。</p>
          <div class="wb-report-content">
            <template v-for="(paragraph,index) in content" :key="index">
              <h2 v-if="paragraph.heading" :id="'report-section-' + index" :class="riskClass(paragraph.text)">{{ paragraph.text }}</h2>
              <p v-else :class="riskClass(paragraph.text)">{{ paragraph.text }}</p>
            </template>
          </div>
        </article>
      </div>
      </div>
    </section>
  </div>
</template>
