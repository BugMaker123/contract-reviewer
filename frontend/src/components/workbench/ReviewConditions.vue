<script setup>
import { computed, ref } from 'vue';
import ReviewBackground from '../portal/ReviewBackground.vue';
import { readDocument, appendMaterial } from '../../portal/services/documents.js';
const props = defineProps({ context: {type:Object,required:true} });
const workspace = props.context.workspace;
const importing = ref(false), busy = ref(false), error = ref('');
const changed = source => workspace.conditions.references.filter(r => r.name === source).forEach(r => r.confirmed = false);
const addRequirement = (source = '用户要求') => {
  if (workspace.conditions.requirements.length >= 100) { error.value = '审核要求最多100条'; return; }
  changed(source);
  workspace.conditions.requirements.push({id:'custom-' + crypto.randomUUID(),text:'',source,priority:'required',evidence:''});
};
const removeMaterial = index => {
  const material = workspace.conditions.references[index];
  workspace.conditions.requirements = workspace.conditions.requirements.filter(r => r.source !== material.name);
  workspace.conditions.references.splice(index,1);
};
const importDocument = async (event, target) => {
  const file = event.target.files?.[0]; if (!file) return;
  importing.value = true; error.value = '';
  try { const data = await readDocument(file);
    if (target === 'reference') workspace.conditions.reference_text = data.text;
    else appendMaterial(workspace.conditions.references,file,data);
  } catch (err) { error.value = err.message; }
  finally { importing.value = false; event.target.value = ''; }
};
const extractRequirements = async material => {
  busy.value = true; error.value = '';
  try {
    const response = await fetch('/api/requirements/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({material,model_config_data:workspace.getModel()})});
    const data = await response.json(); if (!response.ok) throw new Error(data.detail || '要求提取失败');
    const retained = workspace.conditions.requirements.filter(r => r.source !== material.name);
    if (retained.length + data.requirements.length > 100) throw new Error('审核要求最多100条');
    workspace.conditions.requirements = [...retained,...data.requirements]; material.confirmed = false;
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
};
const editor = computed(() => ({form:workspace.conditions,importing:importing.value,busy:busy.value,addRequirement,removeMaterial,importDocument,extractRequirements}));
const save = async () => {
  try { await workspace.flush(); workspace.showConditions = false; }
  catch (err) { error.value = err.message; }
};
</script>
<template>
  <div v-if="workspace.showConditions" class="conditions-overlay">
    <section class="conditions-dialog" role="dialog" aria-modal="true" aria-labelledby="conditions-title">
      <div class="conditions-header">
        <div><span class="conditions-eyebrow">REVIEW SETTINGS</span><h2 id="conditions-title">修改审查条件 <span>{{ workspace.modeName }}</span></h2><p>补充交易信息，让审查建议更贴合本次业务。</p></div>
        <button class="conditions-close" aria-label="关闭审查条件" @click="workspace.showConditions = false">×</button>
      </div>
      <div class="conditions-body">
      <div class="conditions-notice"><span aria-hidden="true">i</span><p>修改后需重新审查，旧版本将保留。涉及公司制度的要求，请重新核对并确认。</p></div>
      <p v-if="error" role="alert" class="conditions-error">{{ error }}</p>
      <fieldset class="conditions-fields" :disabled="workspace.historical || ['running','queued'].includes(workspace.task?.status) || workspace.verifying || importing || busy">
        <div class="conditions-basics">
          <div><h3>审查策略</h3><p>确定本次谈判中建议的取舍尺度</p></div>
          <label>谈判尺度<select v-model="workspace.conditions.scale" aria-label="谈判尺度" class="field"><option>中立</option><option>强势</option><option>弱势</option></select></label>
        </div>
        <div v-if="workspace.conditions.checklist" class="conditions-checklist"><span class="conditions-checklist-icon" aria-hidden="true">✓</span><div><small>本次审查清单</small><strong>{{ workspace.conditions.checklist.name }}</strong></div><span class="conditions-version">v{{ workspace.conditions.checklist.version }} · 版本已固定</span></div>
        <ReviewBackground :context="editor" expanded />
        <div v-if="workspace.conditions.mode === 'compare'" class="conditions-reference">
          <label class="text-xs">替换参考合同<input type="file" accept=".docx,.txt,.pdf" @change="importDocument($event,'reference')" /></label>
          <label class="block text-xs">参考合同正文<textarea v-model="workspace.conditions.reference_text" class="field h-40" /></label>
        </div>
      </fieldset>
      </div>
      <div class="conditions-footer"><span>{{ importing ? '正在读取资料…' : busy ? '正在提取审核要求…' : '条件保存后，点击「重新审查」应用更改' }}</span><button @click="save" :disabled="workspace.saving || workspace.historical || ['running','queued'].includes(workspace.task?.status) || workspace.verifying || importing || busy" class="conditions-save">{{ workspace.saving ? '保存中…' : '保存审查条件' }}</button></div>
    </section>
  </div>
</template>

<style scoped>
.conditions-overlay { position:fixed; inset:0; z-index:60; display:flex; align-items:center; justify-content:center; padding:28px; background:rgb(15 23 42 / 38%); backdrop-filter:blur(3px); }
.conditions-dialog { width:860px; max-width:100%; max-height:calc(100dvh - 56px); display:flex; flex-direction:column; overflow:hidden; background:#fff; border:1px solid #e2e8f0; border-radius:18px; box-shadow:0 24px 80px #0f172a30; color:#334155; }
.conditions-header { display:flex; justify-content:space-between; align-items:flex-start; padding:25px 30px 22px; border-bottom:1px solid #e8edf4; flex-shrink:0; }
.conditions-eyebrow { color:#64748b; font-size:10px; font-weight:600; letter-spacing:1.8px; }
.conditions-header h2 { display:flex; align-items:center; gap:12px; margin:7px 0 8px; color:#0f172a; font-size:21px; font-weight:650; }
.conditions-header h2 span { padding:4px 9px; border-radius:6px; background:#eff6ff; color:#2563eb; font-size:11px; font-weight:500; }
.conditions-header p { margin:0; color:#64748b; font-size:12px; }
.conditions-close { display:grid; place-items:center; width:32px; height:32px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; font-size:23px; color:#64748b; cursor:pointer; }
.conditions-close:hover { background:#f1f5f9; color:#0f172a; }
.conditions-body { min-height:0; overflow-y:auto; padding:22px 30px 26px; background:#f8fafc; scrollbar-gutter:stable; }
.conditions-notice { display:flex; gap:9px; align-items:center; padding:11px 13px; border:1px solid #dbeafe; border-radius:8px; background:#eff6ff; color:#42638d; font-size:12px; line-height:1.7; margin-bottom:20px; }
.conditions-notice > span { display:grid; place-items:center; width:16px; height:16px; flex-shrink:0; border:1px solid #93b4df; border-radius:50%; font-size:11px; }.conditions-notice p { margin:0; }
.conditions-fields { border:0; padding:0; margin:0; min-width:0; }
.conditions-basics { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:18px 20px; border:1px solid #e2e8f0; border-radius:10px; background:#fff; margin-bottom:14px; }
.conditions-basics h3 { font-size:14px; font-weight:600; color:#1e293b; margin:0 0 5px; }.conditions-basics p { color:#94a3b8; font-size:11px; margin:0; }.conditions-basics label { width:230px; max-width:50%; font-size:11px; color:#64748b; }
.conditions-checklist { display:flex; align-items:center; gap:12px; padding:14px 18px; border:1px solid #dbe6f4; background:#f0f5fc; border-radius:10px; margin-bottom:16px; }.conditions-checklist-icon { display:grid; place-items:center; background:#fff; width:32px; height:36px; border:1px solid #dbe6f4; border-radius:6px; color:#2563eb; }.conditions-checklist small { display:block; font-size:10px; color:#64748b; margin-bottom:3px; }.conditions-checklist strong { font-size:12px; font-weight:600; }.conditions-version { margin-left:auto; font-size:10px; color:#64748b; white-space:nowrap; }
.conditions-footer { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:17px 30px; border-top:1px solid #e2e8f0; background:#fff; flex-shrink:0; }.conditions-footer > span { color:#94a3b8; font-size:11px; }.conditions-save { border:1px solid #2563eb; background:#2563eb; color:#fff; border-radius:8px; padding:10px 20px; font-size:12px; font-weight:600; cursor:pointer; }.conditions-save:hover { background:#1d4ed8; }.conditions-save:disabled { opacity:.5; cursor:not-allowed; }
.conditions-error { color:#b91c1c; background:#fef2f2; border-radius:8px; padding:10px 13px; font-size:12px; margin-bottom:14px; }
.conditions-reference { padding:20px; background:#fff; border:1px solid #e2e8f0; border-radius:10px; margin-top:16px; }
.conditions-dialog :deep(.field) { display:block; box-sizing:border-box; width:100%; margin-top:7px; padding:10px 12px; border:1px solid #dce3ed; border-radius:7px; background:#fff; color:#334155; font:inherit; font-size:12px; line-height:1.7; outline:none; box-shadow:none; }
.conditions-dialog :deep(.field:focus) { border-color:#7aa7f8; box-shadow:0 0 0 3px #2563eb0c; }.conditions-dialog :deep(textarea.field) { min-height:95px; resize:vertical; }.conditions-dialog :deep(.field::placeholder) { color:#a1adbd; }.conditions-dialog :deep(.label) { display:block; margin-bottom:0; color:#475569; font-size:12px; font-weight:500; }
.conditions-fields > :deep(details) { padding:0; border:0; }.conditions-fields > :deep(details > summary) { padding:4px 0 14px; color:#334155; font-size:13px; font-weight:600; list-style:none; cursor:pointer; }.conditions-fields > :deep(details > summary::-webkit-details-marker) { display:none; }.conditions-fields > :deep(details > div) { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin:0; }.conditions-fields > :deep(details > div > label) { padding:18px; border:1px solid #e2e8f0; border-radius:10px; background:#fff; }.conditions-fields > :deep(details > div > div) { grid-column:1 / -1; padding:18px; border:1px solid #e2e8f0; border-radius:10px; background:#fff; }
.conditions-fields > :deep(details > div > *) { margin-top:0 !important; }
.conditions-dialog :deep(.button) { padding:7px 12px; border:1px solid #dbe3ef; border-radius:6px; background:#fff; color:#2563eb; font-size:11px; line-height:1.6; cursor:pointer; }.conditions-dialog :deep(.button:hover) { background:#eff6ff; }.conditions-dialog :deep(button:focus-visible) { outline:2px solid #2563eb; outline-offset:3px; }.conditions-dialog :deep(button:disabled) { cursor:not-allowed; opacity:.5; }
@media(max-width:640px) { .conditions-overlay { padding:12px; }.conditions-dialog { max-height:calc(100dvh - 24px); border-radius:12px; }.conditions-header,.conditions-body { padding:20px; }.conditions-footer { padding:15px 20px; }.conditions-footer > span { max-width:50%; line-height:1.7; }.conditions-fields > :deep(details > div) { grid-template-columns:1fr; }.conditions-basics { align-items:flex-start; flex-direction:column; gap:12px; }.conditions-basics label { width:100%; max-width:none; }.conditions-checklist { flex-wrap:wrap; }.conditions-version { margin-left:44px; }.conditions-header h2 { font-size:18px; } }
</style>
