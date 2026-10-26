<script setup>
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { usePortalShell } from '../../stores/portal.js';
const props = defineProps({ form: {type:Object, required:true} });
const {api} = usePortalShell(), route = useRoute();
const documents = ref([]), sessions = ref([]), messages = ref([]), error = ref(''), loading = ref(false);
let selection = 0;
async function loadMessages(id) {
  const request = ++selection;
  messages.value = [];
  if (!id) return;
  loading.value = true;
  try { const data = await api('/api/knowledge/sessions/' + id); if (request === selection) messages.value = data.messages; }
  catch (e) { error.value = e.message; }
  finally { if (request === selection) loading.value = false; }
}
watch(() => props.form.knowledge_session_id, (id) => {
  props.form.knowledge_message_ids = [];
  props.form.knowledge_context_confirmed = false;
  loadMessages(id);
});
watch(() => props.form.knowledge_message_ids, () => { props.form.knowledge_context_confirmed = false; }, {deep:true});
onMounted(async () => {
  try {
    [documents.value, sessions.value] = await Promise.all([api('/api/knowledge/documents'), api('/api/knowledge/sessions')]);
    const id = route.query.knowledge_session;
    if (id && sessions.value.some(item => item.id === id)) props.form.knowledge_session_id = id;
    else await loadMessages(props.form.knowledge_session_id);
  } catch (e) { error.value = e.message; }
});
</script>
<template>
  <details class="knowledge-selection">
    <summary>知识库与对话辅助审查 <small>{{form.knowledge_document_ids?.length || 0}} 份资料 · {{form.knowledge_message_ids?.length || 0}} 条对话</small></summary>
    <p>选择本次审查使用的资料。系统按合同正文检索原文并扩展图关系，命中证据将随审查版本保存。</p>
    <p v-if="error" role="alert">{{error}}</p>
    <div class="knowledge-docs"><label v-for="item in documents" :key="item.id"><input type="checkbox" v-model="form.knowledge_document_ids" :value="item.id"/> {{item.name}} <small>{{item.method==='model-entities-relations'?'语义实体关系':'关键词同现'}} · {{item.chunk_count}} 片段</small></label></div>
    <p v-if="!documents.length">尚无资料，可先前往 <RouterLink to="/knowledge">知识库</RouterLink> 上传。</p>
    <label>对话来源<select class="field" v-model="form.knowledge_session_id"><option :value="null">不使用对话内容</option><option v-for="item in sessions" :key="item.id" :value="item.id">{{item.title}}</option></select></label>
    <p v-if="loading" role="status">正在读取对话…</p>
    <div class="knowledge-messages"><label v-for="item in messages" :key="item.id"><input type="checkbox" v-model="form.knowledge_message_ids" :value="item.id"/><span><b>{{item.role==='user'?'用户':'助手'}}</b> {{item.text}}</span></label></div>
    <label v-if="form.knowledge_message_ids?.length" class="knowledge-confirm"><input type="checkbox" v-model="form.knowledge_context_confirmed"/> 我已核对所选对话，同意将其作为本次审核背景；助手回答中的推断仍需原文核验。</label>
  </details>
</template>
<style scoped>
.knowledge-selection{border-top:1px solid #e2e8f0;padding:20px 24px;font-size:13px}.knowledge-selection summary{cursor:pointer;font-weight:600}.knowledge-selection small,.knowledge-selection p{color:#64748b}.knowledge-selection p{margin:12px 0}.knowledge-selection select{margin-top:8px}.knowledge-docs,.knowledge-messages{display:grid;gap:10px;margin:14px 0}.knowledge-messages{max-height:280px;overflow:auto}.knowledge-messages label{display:flex;gap:8px;border:1px solid #e2e8f0;padding:12px;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere}.knowledge-confirm{display:block;background:#eff6ff;padding:14px;border-radius:8px}input{accent-color:#2563eb}
</style>
