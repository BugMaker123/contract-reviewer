<script setup>
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue';
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router';
import ReviewIcon from '../components/portal/ReviewIcon.vue';
import { usePortalShell } from '../stores/portal.js';

const shell = usePortalShell();
const router = useRouter();
const route = useRoute();

/** 初始化起草需求表单数据 */
const empty = () => ({
  title: '',
  contract_type: '采购合同',
  party_a: '',
  party_b: '',
  perspective: '中立审慎',
  transaction: '',
  payment: '',
  requirements: '',
});

const brief = reactive(empty());
if (!route.params.id) {
  try {
    const cached = sessionStorage.getItem('contract_drafting_new_brief');
    if (cached) Object.assign(brief, JSON.parse(cached));
  } catch {}
}
import { watch } from 'vue';
watch(brief, (val) => {
  if (!route.params.id) {
    try {
      sessionStorage.setItem('contract_drafting_new_brief', JSON.stringify(val));
    } catch {}
  }
}, { deep: true });
const draft = ref(null);
const title = ref('');
const text = ref('');
const busy = ref(false);
const error = ref('');
const operation = ref('');
const mode = ref('edit');

const contractTypes = [
  '采购合同',
  '销售合同',
  '服务合同',
  '技术开发合同',
  '租赁合同',
  '保密协议',
  '合作协议',
  '其他合同',
];

const focusOptions = [
  '明确验收标准与异议期限',
  '约定逾期付款与违约责任',
  '明确知识产权归属',
  '约定保密义务与期限',
];

const readiness = computed(() => {
  if (!brief.title.trim()) return '请填写合同名称';
  if (brief.transaction.trim().length < 10) return '请补充至少 10 字的交易安排';
  return '需求已就绪，可以生成合同草稿';
});

const canGenerate = computed(() => Boolean(brief.title.trim()) && brief.transaction.trim().length >= 10);

const briefChanged = computed(() => (
  draft.value && JSON.stringify(brief) !== JSON.stringify({ ...empty(), ...draft.value.brief })
));

const missing = computed(() => draft.value?.missing_information || []);

const dirty = computed(() => (
  draft.value && (title.value !== draft.value.title || text.value !== draft.value.text)
));

const isEmpty = computed(() => (
  !brief.title &&
  !brief.party_a &&
  !brief.party_b &&
  !brief.transaction &&
  !brief.payment &&
  !brief.requirements
));

function show(saved) {
  draft.value = saved;
  title.value = saved.title;
  text.value = saved.text;
  Object.assign(brief, empty(), saved.brief);
  mode.value = 'edit';
}

async function persist() {
  if (!dirty.value) return draft.value;
  if (!title.value.trim() || !text.value.trim()) {
    throw new Error('合同名称和正文不能为空，请补充后保存');
  }
  const saved = await shell.api('/api/contract-drafts/' + draft.value.id, 'PUT', {
    title: title.value,
    text: text.value,
    revision: draft.value.revision,
  });
  draft.value = saved;
  return saved;
}

async function action(fn, name = 'load') {
  if (busy.value) return;
  busy.value = true;
  operation.value = name;
  error.value = '';
  try {
    await fn();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
    operation.value = '';
  }
}

function generate() {
  if (!canGenerate.value || busy.value) return;
  action(async () => {
    await persist();
    const saved = await shell.api('/api/contract-drafts/generate', 'POST', {
      brief: { ...brief },
      model_config_data: shell.model,
    });
    shell.notify('合同草稿已生成并保存');
    sessionStorage.removeItem('contract_drafting_new_brief');
    busy.value = false;
    await router.replace('/drafting/' + saved.id + '/edit');
    Object.assign(brief, empty());
  }, 'generate');
}

function save() {
  action(async () => {
    await persist();
    shell.notify('草稿已保存');
  }, 'save');
}

function download() {
  action(async () => {
    const saved = await persist();
    const response = await fetch('/api/contract-drafts/' + saved.id + '/word');
    if (!response.ok) throw new Error('Word 导出失败，请重试');
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = saved.title + '.docx';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, 'download');
}

function review() {
  action(async () => {
    const saved = await persist();
    const roles = {
      '甲方立场': '甲方(买方/采购方/委托方)',
      '乙方立场': '乙方(卖方/开发方/服务方)',
      '中立审慎': '中立审慎',
    };
    const task = await shell.api('/api/tasks', 'POST', {
      title: saved.title,
      text: saved.text,
      type: saved.brief.contract_type,
      role: roles[saved.brief.perspective] || '中立审慎',
      mode: 'deep',
      background: saved.brief.transaction,
      focus: saved.brief.requirements,
    });
    busy.value = false;
    try { sessionStorage.setItem('workbench_return_to', '/drafting/' + saved.id + '/edit'); } catch {}
    await router.push('/workbench?task=' + task.id);
  }, 'review');
}

function addFocus(value) {
  const items = brief.requirements.split('；').filter(Boolean);
  const next = (items.includes(value) ? items.filter(item => item !== value) : [...items, value]).join('；');
  if (next.length > 10000) {
    shell.notify('起草要求最多 10,000 字，请精简后添加');
    return;
  }
  brief.requirements = next;
}

function example() {
  if (!isEmpty.value) return;
  Object.assign(brief, {
    title: '办公设备采购合同',
    contract_type: '采购合同',
    perspective: '甲方立场',
    transaction: '甲方向乙方采购 20 台办公电脑，合同签订后 15 个工作日内送至甲方指定地点。到货后 5 个工作日内完成数量、配置及运行情况验收，质量保修期为验收合格后 12 个月。',
    payment: '合同总价人民币 100,000 元（含税）。签约后支付 30%，验收合格并收到合规发票后支付 70%。',
    requirements: '明确验收标准与异议期限；约定逾期交付与质量不合格的违约责任',
  });
}

function beforeUnload(event) {
  if (dirty.value || busy.value) {
    event.preventDefault();
    event.returnValue = '';
  }
}

onBeforeRouteLeave(async () => {
  if (busy.value) {
    shell.notify('正在处理，请稍后再切换页面');
    return false;
  }
  if (dirty.value) {
    try {
      await persist();
    } catch (e) {
      error.value = e.message;
      shell.notify('修改未能保存，请保存后再离开');
      return false;
    }
  }
});

async function loadDraft() {
  if (!route.params.id) return;
  await action(async () => {
    show(await shell.api('/api/contract-drafts/' + route.params.id));
  });
}

onActivated(() => {
  loadDraft();
  window.addEventListener('beforeunload', beforeUnload);
});

onDeactivated(() => {
  window.removeEventListener('beforeunload', beforeUnload);
});
</script>
<template>
  <div class="drafting-page">
    <RouterLink to="/drafting" class="back-link"><ReviewIcon name="arrow"/>返回起草列表</RouterLink>
    <header class="drafting-heading">
      <div><h1>{{route.params.id?'编辑合同草稿':'新建合同起草'}}</h1><p>{{route.params.id?'完善合同内容，保存后导出或发起审查。':'填写交易需求，生成可编辑的合同草稿。'}}</p></div>
      <div class="heading-actions"><RouterLink to="/drafting" class="button">返回列表</RouterLink><button v-if="draft" class="button primary" :disabled="busy||!dirty" @click="save"><ReviewIcon name="save"/>{{operation==='save'?'保存中…':'保存草稿'}}</button></div>
    </header>
    <ol v-if="!route.params.id||draft" class="drafting-workflow" aria-label="合同起草流程">
      <li class="active"><span>1</span><div><strong>描述起草需求</strong><small>明确交易内容与我方立场</small></div></li>
      <li :class="{active:draft}"><span>2</span><div><strong>生成与完善草稿</strong><small>在线编辑，补充关键约定</small></div></li>
      <li><span>3</span><div><strong>导出或发起审查</strong><small>导出 Word，或继续识别风险</small></div></li>
    </ol>
    <p v-if="error" class="drafting-error" role="alert"><ReviewIcon name="info"/>{{error}}</p>
    <div v-if="route.params.id&&!draft" class="drafting-card editor-load-state"><p>{{busy?'正在加载合同草稿…':'草稿暂时无法加载，请重试或返回列表。'}}</p><button v-if="!busy" class="button" @click="loadDraft">重新加载</button></div>
    <div v-else class="drafting-layout">
      <form class="drafting-brief drafting-card" @submit.prevent="generate">
        <div class="card-heading"><div class="section-title"><span class="section-icon"><ReviewIcon name="settings"/></span><div><h2>起草需求</h2><p>信息越完整，草稿越贴合实际交易</p></div></div><button type="button" class="text-button" :disabled="busy||!isEmpty" title="仅在需求为空时填入示例" @click="example">填入示例</button></div>
        <fieldset :disabled="busy">
          <div class="form-section"><h3>基本信息 <small>确定合同类型与起草视角</small></h3>
            <label>合同名称 <span class="required">*</span><input v-model="brief.title" required maxlength="200" placeholder="例如：年度设备采购合同"/></label>
            <div class="drafting-pair"><label>合同类型<select v-model="brief.contract_type"><option v-for="v in contractTypes" :key="v">{{v}}</option></select></label><label>起草立场<select v-model="brief.perspective"><option>中立审慎</option><option>甲方立场</option><option>乙方立场</option></select></label></div>
            <div class="drafting-pair"><label>甲方名称<input v-model="brief.party_a" maxlength="500" placeholder="输入甲方全称（选填）"/></label><label>乙方名称<input v-model="brief.party_b" maxlength="500" placeholder="输入乙方全称（选填）"/></label></div>
          </div>
          <div class="form-section"><h3>交易安排 <small>描述合同需要约定的核心事项</small></h3>
            <label>交易内容与履行安排 <span class="required">*</span><textarea v-model="brief.transaction" required minlength="10" maxlength="15000" rows="5" placeholder="说明交易标的、数量、交付方式、履行期限及验收安排…"/><span class="field-hint"><span>至少 10 字，建议写明交付与验收条件</span><span>{{brief.transaction.length.toLocaleString()}} / 15,000</span></span></label>
            <label>价款与付款安排 <span class="optional">选填</span><textarea v-model="brief.payment" maxlength="5000" rows="3" placeholder="例如：含税总价、预付款比例、尾款支付条件、开票要求…"/></label>
          </div>
          <div class="form-section"><h3>补充要求 <small>按需添加您关注的条款</small></h3>
            <div class="focus-options" aria-label="常用起草要求"><button v-for="item in focusOptions" :key="item" type="button" :aria-pressed="brief.requirements.split('；').includes(item)" :class="{selected:brief.requirements.split('；').includes(item)}" @click="addFocus(item)">＋ {{item}}</button></div>
            <label>其他起草要求 <span class="optional">选填</span><textarea v-model="brief.requirements" maxlength="10000" rows="3" placeholder="补充违约责任、解除条件、争议解决等要求…"/></label>
          </div>
          <div class="generate-footer"><p class="drafting-note"><ReviewIcon name="info"/>未提供的必要信息将留空，并列入待补充清单。</p><button class="button primary drafting-generate" :disabled="busy||!canGenerate" type="submit"><span v-if="operation==='generate'" class="spinner"/><ReviewIcon v-else name="sparkles"/>{{operation==='generate'?'正在生成合同草稿…':draft?'按当前需求生成新草稿':'生成合同草稿'}}</button><p class="readiness" aria-live="polite">{{draft?'重新生成将另存一份，保留当前草稿':readiness}}</p></div>
        </fieldset>
      </form>
      <section class="drafting-output drafting-card" :aria-busy="busy">
        <div class="card-heading"><div class="section-title"><span class="section-icon"><ReviewIcon name="document"/></span><div><h2>合同草稿</h2><p>{{draft?'完善正文后，可导出或继续审查':'生成后自动保存，支持在线修改'}}</p></div></div><span v-if="draft" class="save-state" :class="{unsaved:dirty}" role="status"><i/>{{dirty?'有未保存修改':'已保存'}}</span><span v-else class="pill">待生成</span></div>
        <template v-if="draft">
          <div class="drafting-tools"><div class="view-switch" role="group" aria-label="正文显示方式"><button :aria-pressed="mode==='edit'" :class="{active:mode==='edit'}" @click="mode='edit'">编辑</button><button :aria-pressed="mode==='preview'" :class="{active:mode==='preview'}" @click="mode='preview'">预览</button></div><button class="button" :disabled="busy" @click="download">{{operation==='download'?'导出中…':'导出 Word'}}</button></div>
          <div class="drafting-document">
            <label v-if="mode==='edit'" class="drafting-output-title">合同名称<input v-model="title" :disabled="busy" maxlength="200" aria-label="草稿合同名称" required/></label>
            <details v-if="missing.length" class="drafting-missing"><summary><ReviewIcon name="info"/>待补充信息 <span>{{missing.length}} 项</span><small>展开查看</small></summary><p>以下为生成时识别的缺失信息，请在正文中核对并补充。</p><ul><li v-for="(item,i) in missing" :key="i">{{item}}</li></ul></details>
            <p v-if="briefChanged" class="brief-changed">起草需求已调整，当前正文保持原内容。点击左侧生成按钮可另存新草稿。</p>
            <textarea v-if="mode==='edit'" v-model="text" :disabled="busy" class="drafting-editor" aria-label="合同草稿正文" maxlength="200000" spellcheck="false"/>
            <article v-else class="document-preview" aria-label="合同草稿预览"><h3>{{title}}</h3><div>{{text.startsWith(title+'\n')?text.slice(title.length).trimStart():text}}</div></article>
          </div>
          <footer class="output-footer"><div><span>{{text.length.toLocaleString()}} 字</span><p>导出或送审前会保存当前修改</p></div><button class="button primary" :disabled="busy||!title.trim()||!text.trim()" @click="review"><ReviewIcon name="shield"/>{{operation==='review'?'正在创建审查…':'进入合同审查'}}<ReviewIcon name="arrow"/></button></footer>
        </template>
        <div v-else class="drafting-empty" role="status">
          <template v-if="operation==='generate'"><span class="empty-icon"><span class="spinner"/></span><h3>正在将交易需求整理成合同</h3><p>正在生成条款与待补充清单，请稍候。<br/>完成后草稿将自动保存到起草记录。</p><div class="generation-skeleton"><i/><i/><i/><i/></div></template>
          <template v-else><div class="empty-paper" aria-hidden="true"><ReviewIcon name="document"/><i/><i/><i/><span><ReviewIcon name="sparkles"/></span></div><h3>让清晰的需求，成为完整的约定</h3><p>在左侧填写交易信息，生成您的第一份合同草稿。<br/>您可以随时修改正文，再导出或进入审查。</p><div class="empty-features"><span><ReviewIcon name="check"/>完整合同条款</span><span><ReviewIcon name="check"/>在线编辑保存</span><span><ReviewIcon name="check"/>Word 导出</span></div><button type="button" class="text-button example-link" :disabled="busy||!isEmpty" @click="example">试试填写示例 <ReviewIcon name="arrow"/></button></template>
        </div>
      </section>
    </div>
  </div>
</template>
<style scoped src="../styles/contract-drafting.css"></style>
