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
  <div v-if="workspace.showConditions" class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6">
    <div class="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between"><h3 class="font-semibold">审查条件 · {{ workspace.modeName }}</h3><button aria-label="关闭审查条件" @click="workspace.showConditions = false">关闭</button></div>
      <p class="text-xs text-slate-500 my-3">修改资料或要求后需重新确认制度要求，并重新审查；旧版本保留。</p>
      <p v-if="error" role="alert" class="text-red-600 text-xs">{{ error }}</p>
      <fieldset :disabled="workspace.historical || workspace.task?.status === 'running' || workspace.verifying || importing || busy">
        <label class="block text-xs">谈判尺度<select v-model="workspace.conditions.scale" class="field"><option>中立</option><option>强势</option><option>弱势</option></select></label>
        <ReviewBackground :context="editor" expanded />
        <div v-if="workspace.conditions.mode === 'compare'" class="space-y-2">
          <label class="text-xs">替换参考合同<input type="file" accept=".docx,.txt,.pdf" @change="importDocument($event,'reference')" /></label>
          <label class="block text-xs">参考合同正文<textarea v-model="workspace.conditions.reference_text" class="field h-40" /></label>
        </div>
        <p v-if="workspace.conditions.checklist" class="text-xs text-slate-500">清单：{{ workspace.conditions.checklist.name }} · v{{ workspace.conditions.checklist.version }}（固定本次版本）</p>
        <button @click="save" :disabled="workspace.saving" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-xs">保存审查条件</button>
      </fieldset>
    </div>
  </div>
</template>
