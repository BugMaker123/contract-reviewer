<script setup>
import {ref, computed, watch} from 'vue';
import {useRoute, onBeforeRouteLeave} from 'vue-router';
import AiReview from './AiReview.vue';
import {usePortalShell} from '../stores/portal.js';
import {readDocument} from '../portal/services/documents.js';
const route = useRoute();
const shell = usePortalShell();
const stage = ref(route.query.checklist ? 'ai' : 'choose');
const aiBusy = ref(false), templates = ref([]), selected = ref('');
const loading = ref(false), busy = ref(false), error = ref('');
const contract = ref(null), result = ref(null), importedContract = ref(null);
const template = computed(() => templates.value.find(t => t.id === selected.value));
const report = computed(() => result.value?.report);
const titles = {
  pass: '已检查内容符合模板规则',
  needs_changes: '发现差异，需要人工确认',
  needs_review: '填写内容需要人工审核',
  incomplete: '检查未完成，部分内容需人工核对',
};
const labels = {pass: '符合规则', manual: '转人工', issue: '需修改', not_checked: '未能检查'};
watch(() => route.query.checklist, value => { if (value) stage.value = 'ai'; });
onBeforeRouteLeave(() => {
  if (busy.value) {
    shell.notify('正在处理，请稍后再切换页面');
    return false;
  }
});

async function openTemplate() {
  stage.value = 'template';
  loading.value = true;
  error.value = '';
  try {
    const rows = [];
    let page = 1, total = 0;
    do {
      const data = await shell.api('/api/contract-templates?status=published&page_size=100&page=' + page++);
      rows.push(...data.items);
      total = data.total;
    } while (rows.length < total);
    templates.value = rows;
    if (!rows.some(t => t.id === selected.value)) selected.value = rows[0]?.id || '';
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function upload(file) {
  if (!file || busy.value) return;
  error.value = '';
  contract.value = null;
  result.value = null;
  if (!/\.docx$/i.test(file.name)) {
    error.value = '模板核验仅支持 DOCX 格式';
    return;
  }
  busy.value = true;
  try {
    const data = await readDocument(file);
    contract.value = {...data, filename: file.name};
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function verify() {
  if (!template.value || !contract.value || busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    result.value = await shell.api('/api/contract-templates/' + template.value.id + '/validate', 'POST', {
      source_id: contract.value.source_id,
      release_id: template.value.release_id,
    });
    stage.value = 'result';
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

function continueAi() {
  importedContract.value = contract.value;
  stage.value = 'ai';
}
</script>
<template><div class="review-entry"><div v-if="stage==='ai'||stage==='template'" class="review-page-heading">
  <div><h1>{{stage==='ai'?'新建合同审查':'已有标准模板核验'}}</h1>
  <p>{{stage==='ai'?'配置审查视角与关注事项，识别合同中的法律与商务风险。':'选择已发布的基准模板，验证合同文字与填写规则'}}</p></div>
  <button class="review-mode-switch" :disabled="busy||aiBusy" @click="stage='choose'">
    <svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/></svg>
    重新选择审查方式
  </button>
</div><KeepAlive><AiReview v-if="stage==='ai'" :imported-contract="importedContract" @processing="aiBusy=$event"/></KeepAlive><template v-if="stage!=='ai'"><div v-if="error" role="alert" class="entry-error">{{error}} <button v-if="stage==='template'" class="btn btn-secondary" :disabled="loading||busy" @click="openTemplate">刷新模板列表</button></div><section v-if="stage==='choose'">


        <div class="page-header">
          <div class="page-title">
            <h1>选择本次审查方式</h1>
            <p>根据合同类型与拟定来源，选择适合的审查方式</p>
          </div>
        </div>

        <div class="cards-grid">
          <!-- AI Review Option -->
          <div class="choice-card" @click="stage='ai'" role="button" tabindex="0" @keydown.enter="stage='ai'" @keydown.space.prevent="stage='ai'">
            <div class="choice-header">
              <div class="card-icon ai">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>
              </div>
              <span class="card-tag">合同风险分析</span>
            </div>
            <h2>AI 智能全面审查</h2>
            <p class="desc">适合外部拟定、非标合同或复杂谈判文本。结合自选法律立场与关注事项，识别合同风险并提供修改建议。</p>
            <div class="features-list">
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                全文风险识别
              </span>
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                甲乙双向立场定制
              </span>
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                修改红线建议
              </span>
            </div>
            <div class="action-link">
              <span>进入 AI 智能审查</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </div>
          </div>

          <!-- Template Review Option -->
          <div class="choice-card" @click="openTemplate" role="button" tabindex="0" @keydown.enter="openTemplate" @keydown.space.prevent="openTemplate">
            <div class="choice-header">
              <div class="card-icon template">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/></svg>
              </div>
              <span class="card-tag" style="background:#ecfdf5;color:#059669;">已发布模板规则</span>
            </div>
            <h2>已有标准模板核验</h2>
            <p class="desc">适合基于企业标准模板所填写的合同。比对固定条款是否发生变更，自动核查必填字段、金额范围、账期及特定合规规则。</p>
            <div class="features-list">
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                固定条款变更核查
              </span>
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                填写项逻辑与格式校验
              </span>
              <span class="feature-chip">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                已配置字段规则校验
              </span>
            </div>
            <div class="action-link" style="color: #059669;">
              <span>选择模板并校验</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </div>
          </div>
        </div>

        <div class="notice-bar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--slate-400); flex-shrink:0;"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
          <span>提示：标准模板审核依据发布模板的既定风控规则；若核验完成后需进一步推敲非标争议，可在报告中一键无缝发起 AI 深度审查。</span>
        </div>
      </section>
<section v-if="stage==='template'">
<div class="stepper"><div class="step-item active"><span class="step-num">1</span>选择基准模板与文档</div><div class="step-divider"></div><div class="step-item" :class="{active:busy}"><span class="step-num">2</span>自动化比对</div><div class="step-divider"></div><div class="step-item"><span class="step-num">3</span>生成核验报告</div></div>
<div class="panel"><p v-if="loading" role="status">正在读取已发布模板…</p><div v-else-if="!templates.length" class="notice-bar">暂无已发布模板。请先在 <RouterLink to="/templates">合同模板</RouterLink> 中配置字段规则并发布。<button class="btn btn-secondary" @click="openTemplate">重新加载</button></div>
<template v-else><div class="form-group"><label class="form-label" for="baseline">选择基准合同模板 <span class="sub">仅展示已发布模板</span></label><select id="baseline" v-model="selected" :disabled="busy" class="form-control" @change="result=null"><option v-for="t in templates" :key="t.id" :value="t.id">{{t.name}}</option></select><div v-if="template" class="template-detail-box"><div class="template-detail-header"><span class="status-tag">正式发布</span>{{template.name}}</div><p class="template-detail-desc">{{template.description||'核验固定文字，以及已配置字段的必填、长度、类型和取值规则。'}}</p></div></div>
<div class="form-group"><label class="form-label" for="validation-file">上传待核验合同文件</label><div class="dropzone" @dragover.prevent @drop.prevent="upload($event.dataTransfer.files[0])"><input id="validation-file" type="file" accept=".docx" :disabled="busy" @change="upload($event.target.files[0]); $event.target.value=''"/><div class="dropzone-icon">↥</div><strong>{{contract?.filename||'拖拽合同文件至此处，或点击浏览上传'}}</strong><p>{{busy?'正在处理，请稍候…':'支持 Microsoft Word (.docx) 格式，文件不超过 10 MB'}}</p></div></div><div class="notice-bar">固定文字发生变更、字段不符合规则或无法完整核验的内容，将提示人工处理。验证结果不作为自动免审依据。</div><div class="panel-footer"><RouterLink to="/templates" class="btn btn-secondary">管理合同模板</RouterLink><button class="btn btn-primary" :disabled="busy||!contract||!template" @click="verify">{{busy?'正在处理…':'开始模板合规核验'}} →</button></div></template></div></section>
<section v-if="stage==='result' && report"><button class="back-btn" @click="stage='template'"><svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m14 7-5 5 5 5"/></svg><span>返回修改核验信息</span></button><div class="page-header"><div class="page-title"><h1>模板核验报告</h1><p>{{contract.filename}} · {{result.template_name}} V{{result.version}}</p></div></div><div class="panel"><div class="result-banner" :class="{'result-pass':report.status==='pass'}"><div class="result-banner-icon">{{report.status==='pass'?'✓':'!'}}</div><div class="result-banner-text"><h2>{{titles[report.status]}}</h2><p>{{report.status==='pass'?'已检查的文字和填写规则符合所选模板发布版本。':'核实填写问题、固定条款变化和未能完整检查的内容。'}}</p></div></div><div class="stats-row"><div class="stat-card"><div class="stat-icon green">✓</div><div class="stat-data"><h3>{{report.counts.pass}}</h3><p>字段符合规则</p></div></div><div class="stat-card"><div class="stat-icon orange">!</div><div class="stat-data"><h3>{{report.counts.issue+report.counts.manual+report.counts.not_checked}}</h3><p>字段需处理</p></div></div><div class="stat-card"><div class="stat-icon purple">≠</div><div class="stat-data"><h3>{{report.counts.differences}}</h3><p>固定内容差异</p></div></div></div><div class="table-container"><table><thead><tr><th>验证字段</th><th>合同中的内容</th><th>结果</th><th>处理说明</th></tr></thead><tbody><tr v-for="f in report.fields" :key="f.id"><td>{{f.name}}</td><td>{{f.value===null?'未能定位':f.value||'（空白）'}}</td><td><span class="tag-status" :class="f.status==='pass'?'pass':f.status==='issue'?'danger':'warning'">{{labels[f.status]}}</span></td><td>{{f.reason||'符合已发布版本字段规则'}}</td></tr></tbody></table></div><article v-for="(d,i) in report.differences" :key="i" class="difference"><h3>变化 {{i+1}} · {{d.reason}}</h3><div><p><b>模板原文</b>{{d.original}}</p><p><b>上传合同</b>{{d.current}}</p></div></article><div class="notice-bar scope"><strong>检查范围与限制</strong><p v-for="(w,i) in report.limitations" :key="i">{{w}}</p><p>仅检查文字、段落结构和配置的字段规则。格式、合并单元格、图片及复杂对象需另行人工核对。本结果不代表合同整体法律风险结论。</p></div><div class="panel-footer"><button class="btn btn-secondary" @click="stage='template'">重新验证</button><button class="btn btn-primary" @click="continueAi">继续 AI 审查 →</button></div></div></section>
</template></div></template><style scoped>
    .review-entry {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --primary-light: #eff6ff;
      --primary-glow: rgba(37, 99, 235, 0.18);

      --accent: #4f46e5;
      --accent-gradient: linear-gradient(135deg, #2563eb 0%, #4f46e5 50%, #7c3aed 100%);
      --emerald-gradient: linear-gradient(135deg, #059669 0%, #10b981 100%);

      --slate-950: #090d16;
      --slate-900: #0f172a;
      --slate-800: #1e293b;
      --slate-700: #334155;
      --slate-600: #475569;
      --slate-500: #64748b;
      --slate-400: #94a3b8;
      --slate-300: #cbd5e1;
      --slate-200: #e2e8f0;
      --slate-100: #f1f5f9;
      --slate-50:  #f8fafc;

      --success: #10b981;
      --success-bg: #ecfdf5;
      --success-border: #a7f3d0;
      --warning: #f59e0b;
      --warning-bg: #fffbeb;
      --warning-border: #fde68a;
      --danger: #ef4444;
      --danger-bg: #fef2f2;
      --danger-border: #fecaca;

      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 18px;
      --radius-xl: 24px;

      --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
      --shadow-md: 0 4px 16px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -2px rgba(15, 23, 42, 0.04);
      --shadow-lg: 0 12px 32px -4px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.03);
      --shadow-hover: 0 20px 38px -6px rgba(37, 99, 235, 0.12), 0 8px 16px -4px rgba(15, 23, 42, 0.06);

      --transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }

    .review-entry {
      background: transparent;
      color: var(--slate-800);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 14px;
      line-height: 1.5;

    }

    button, input, select, textarea {
      font-family: inherit;

    }

    /* ================= SECTION / ANIMATIONS ================= */
    section {
      animation: fadeIn 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .hidden {
      display: none !important;
    }

    /* Page Intro */
    .page-header {
      margin-bottom: 28px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }

    .page-title h1 {
      font-size: 26px;
      font-weight: 700;
      color: var(--slate-900);
      letter-spacing: -0.6px;
      margin-bottom: 6px;
    }

    .page-title p {
      font-size: 14px;
      color: var(--slate-500);
    }

    /* Back Button */
    .back-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      min-height: 32px;
      margin: 0 0 18px -5px;
      padding: 4px 0;
      border: 0;
      border-radius: 4px;
      background: transparent;
      box-shadow: none;
      color: #7b879a;
      font-size: 13px;
      font-weight: 400;
      cursor: pointer;
      transition: color .15s ease;
    }
    .back-btn svg { flex-shrink: 0; }
    .back-btn:hover:not(:disabled) { color: #2563eb; }
    .back-btn:disabled { opacity: .45; cursor: not-allowed; }
    .ai-return { margin-left: 19px; }


    /* Panels & Cards */
    .panel {
      background: #ffffff;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-lg);
      padding: 28px;
      box-shadow: var(--shadow-sm);
      position: relative;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 11px 24px;
      border-radius: var(--radius-sm);
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      transition: var(--transition);
      border: none;
      text-decoration: none;
      white-space: nowrap;
    }

    .btn-primary {
      background: var(--accent-gradient);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
    }

    .btn-primary:hover:not(:disabled) {
      box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
      transform: translateY(-1px);
    }

    .btn-primary:disabled {
      background: var(--slate-300);
      cursor: not-allowed;
      box-shadow: none;
      transform: none;
      color: var(--slate-500);
    }

    .btn-secondary {
      background: #ffffff;
      border: 1px solid var(--slate-300);
      color: var(--slate-700);
      box-shadow: var(--shadow-sm);
    }

    .btn-secondary:hover {
      background: var(--slate-50);
      border-color: var(--slate-400);
      color: var(--slate-900);
    }

    /* ================= CARDS / CHOICE SECTION ================= */
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 24px;
      margin: 10px 0 24px;
    }

    .choice-card {
      background: #ffffff;
      border: 2px solid var(--slate-200);
      border-radius: var(--radius-xl);
      padding: 36px 32px;
      text-align: left;
      cursor: pointer;
      transition: var(--transition);
      position: relative;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }

    .choice-card:hover {
      border-color: var(--primary);
      transform: translateY(-4px);
      box-shadow: var(--shadow-hover);
    }

    .choice-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 22px;
    }

    .card-icon {
      width: 58px;
      height: 58px;
      border-radius: var(--radius-md);
      display: grid;
      place-items: center;
      font-size: 24px;
      transition: var(--transition);
    }

    .card-icon.ai {
      background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
      color: var(--accent);
      border: 1px solid #c7d2fe;
    }

    .card-icon.template {
      background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
      color: #059669;
      border: 1px solid #a7f3d0;
    }

    .choice-card:hover .card-icon {
      transform: scale(1.08);
    }

    .card-tag {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      background: var(--slate-100);
      color: var(--slate-500);
    }

    .choice-card h2 {
      font-size: 20px;
      font-weight: 700;
      color: var(--slate-900);
      margin-bottom: 10px;
    }

    .choice-card p.desc {
      font-size: 13.5px;
      color: var(--slate-500);
      line-height: 1.65;
      margin-bottom: 20px;
      flex: 1;
    }

    .features-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 26px;
    }

    .feature-chip {
      font-size: 12px;
      padding: 4px 10px;
      background: var(--slate-50);
      border: 1px solid var(--slate-200);
      border-radius: 6px;
      color: var(--slate-600);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .action-link {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 14px;
      font-weight: 600;
      color: var(--primary);
      margin-top: auto;
    }

    .choice-card:hover .action-link {
      gap: 10px;
    }

    /* Notice Bar */
    .notice-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #f8fafc;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-sm);
      padding: 12px 18px;
      font-size: 12.5px;
      color: var(--slate-500);
    }

    /* ================= STEPPER ================= */
    .stepper {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 28px;
      padding: 6px 0;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      font-weight: 500;
      color: var(--slate-400);
    }

    .step-num {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 12px;
      font-weight: 700;
      background: var(--slate-100);
      color: var(--slate-500);
      border: 1px solid var(--slate-200);
    }

    .step-item.active {
      color: var(--primary);
      font-weight: 600;
    }

    .step-item.active .step-num {
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }

    .step-divider {
      width: 32px;
      height: 1px;
      background: var(--slate-200);
    }

    /* ================= FORMS ================= */
    .form-group {
      margin-bottom: 24px;
    }

    .form-label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13.5px;
      font-weight: 600;
      color: var(--slate-800);
      margin-bottom: 8px;
    }

    .form-label span.sub {
      font-size: 12px;
      font-weight: 400;
      color: var(--slate-400);
    }

    .form-control {
      width: 100%;
      background: #ffffff;
      border: 1px solid var(--slate-300);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      font-size: 13.5px;
      color: var(--slate-800);
      transition: var(--transition);
    }

    .form-control:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }

    /* Template Info Card */
    .template-detail-box {
      background: #f8fafc;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-sm);
      padding: 14px 18px;
      margin-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .template-detail-header {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 13px;
      color: var(--slate-800);
    }

    .template-detail-desc {
      font-size: 12.5px;
      color: var(--slate-500);
      line-height: 1.6;
    }

    /* Modern Dropzone */
    .dropzone {
      border: 2px dashed var(--slate-300);
      background: #fafbfc;
      border-radius: var(--radius-md);
      padding: 38px 24px;
      text-align: center;
      cursor: pointer;
      transition: var(--transition);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      position: relative;
    }

    .dropzone:hover {
      border-color: var(--primary);
      background: #f4f8ff;
    }

    .dropzone-icon {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: #eff6ff;
      color: var(--primary);
      display: grid;
      place-items: center;
      font-size: 22px;
      margin-bottom: 4px;
      transition: var(--transition);
    }

    .dropzone:hover .dropzone-icon {
      transform: translateY(-2px);
    }

    .dropzone strong {
      font-size: 14px;
      color: var(--slate-800);
      font-weight: 600;
    }

    .dropzone p {
      font-size: 12px;
      color: var(--slate-400);
    }

    .dropzone input[type="file"] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }

    /* Card Footer / Actions */
    .panel-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 22px;
      margin-top: 26px;
      border-top: 1px solid var(--slate-100);
    }

    /* ================= RESULT SCREEN ================= */
    .result-banner {
      background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
      border: 1px solid #fde68a;
      border-radius: var(--radius-lg);
      padding: 24px 28px;
      display: flex;
      align-items: center;
      gap: 20px;
      margin-bottom: 24px;
    }

    .result-banner-icon {
      width: 46px;
      height: 46px;
      background: #f59e0b;
      color: #ffffff;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 22px;
      font-weight: 800;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }

    .result-banner-text h2 {
      font-size: 18px;
      font-weight: 700;
      color: #92400e;
      margin-bottom: 4px;
    }

    .result-banner-text p {
      font-size: 13px;
      color: #b45309;
    }

    /* Stats Grid */
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 26px;
    }

    .stat-card {
      background: var(--slate-50);
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-md);
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      transition: var(--transition);
    }

    .stat-card:hover {
      background: #ffffff;
      box-shadow: var(--shadow-sm);
    }

    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: var(--radius-sm);
      display: grid;
      place-items: center;
      font-size: 20px;
    }

    .stat-icon.green {
      background: #ecfdf5;
      color: #10b981;
    }

    .stat-icon.orange {
      background: #fffbeb;
      color: #f59e0b;
    }

    .stat-icon.purple {
      background: #f5f3ff;
      color: #8b5cf6;
    }

    .stat-data h3 {
      font-size: 26px;
      font-weight: 800;
      color: var(--slate-900);
      line-height: 1.1;
      letter-spacing: -0.5px;
    }

    .stat-data p {
      font-size: 12px;
      color: var(--slate-500);
      font-weight: 500;
      margin-top: 4px;
    }

    /* Data Table */
    .table-container {
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-md);
      overflow: hidden;
      margin-bottom: 20px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }

    thead {
      background: #f8fafc;
      border-bottom: 1px solid var(--slate-200);
    }

    th {
      padding: 14px 18px;
      color: var(--slate-500);
      font-weight: 600;
      font-size: 12.5px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    td {
      padding: 16px 18px;
      border-bottom: 1px solid var(--slate-100);
      color: var(--slate-700);
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover td {
      background: #fafbfc;
    }

    .tag-status {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }

    .tag-status.pass {
      background: #ecfdf5;
      color: #059669;
      border: 1px solid #a7f3d0;
    }

    .tag-status.warning {
      background: #fffbeb;
      color: #d97706;
      border: 1px solid #fde68a;
    }

    .tag-status.danger {
      background: #fef2f2;
      color: #dc2626;
      border: 1px solid #fecaca;
    }

    /* Responsive */
    @media (max-width: 900px) {
      .cards-grid {
        grid-template-columns: 1fr;
      }
      .stats-row {
        grid-template-columns: 1fr;
      }
    }

button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid #93c5fd;outline-offset:3px}.review-entry{width:100%;max-width:none;margin:0;color:var(--slate-800)}.choice-card:focus-visible{outline:3px solid #93c5fd;outline-offset:4px}.entry-error{background:#fef2f2;color:#b91c1c;padding:14px;border-radius:8px;margin-bottom:20px}.btn:disabled{opacity:.5;cursor:not-allowed}.difference{border:1px solid #e2e8f0;border-radius:12px;padding:18px;margin:16px 0}.difference h3{font-size:14px;margin-bottom:12px}.difference>div{display:grid;grid-template-columns:1fr 1fr;gap:12px}.difference p{background:#f8fafc;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere}.difference b{display:block;margin-bottom:8px}.scope{display:block}.scope p{margin-top:8px}.table-container{overflow:auto}td{overflow-wrap:anywhere;max-width:350px}.result-pass{background:#ecfdf5;border-color:#a7f3d0}.result-pass .result-banner-icon{background:#059669}.result-pass h2,.result-pass p{color:#047857}@media(max-width:700px){.stepper{flex-wrap:wrap}.step-divider{display:none}.difference>div{grid-template-columns:1fr}.panel-footer{gap:12px;flex-wrap:wrap}.form-label{flex-wrap:wrap;gap:6px}.panel{padding:20px}table{min-width:650px}}

.review-page-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin:0 0 24px}
.review-page-heading h1{margin:0;font-size:22px;line-height:1.4;font-weight:750;letter-spacing:-.4px;color:#0f172a}
.review-page-heading p{margin:8px 0 0;font-size:12px;line-height:1.7;color:#64748b}
.review-mode-switch{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:36px;padding:8px 13px;border:1px solid #dce3ed;border-radius:8px;background:#fff;color:#475569;font-size:12px;line-height:1.5;font-weight:500;white-space:nowrap;cursor:pointer;transition:border-color .15s,color .15s,background .15s}
.review-mode-switch:hover:not(:disabled){color:#2563eb;border-color:#b8cdf6;background:#f8faff}
.review-mode-switch:disabled{opacity:.45;cursor:not-allowed}
@media(max-width:650px){.review-page-heading{gap:16px;flex-wrap:wrap;margin-bottom:20px}.review-page-heading h1{font-size:20px}.review-mode-switch{min-height:34px}.review-page-heading p{font-size:12px}}
</style>
