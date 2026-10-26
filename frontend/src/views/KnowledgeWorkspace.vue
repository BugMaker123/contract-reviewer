<script setup>
import { computed, onActivated, ref } from 'vue';
import { useRoute } from 'vue-router';
import { usePortalShell } from '../stores/portal.js';
const route = useRoute(), shell = usePortalShell(), {api} = shell;
const isChat = computed(() => route.meta.page === 'chat');
const documents = ref([]), selected = ref([]), sessions = ref([]), session = ref(null);
const question = ref(''), query = ref(''), hits = ref([]), detail = ref(null), error = ref(''), notice = ref(''), busy = ref(false);
const current = ref('');
async function refresh() { [documents.value, sessions.value] = await Promise.all([api('/api/knowledge/documents'), api('/api/knowledge/sessions')]); }
async function run(action) { if (busy.value) return; busy.value = true; error.value = ''; notice.value = ''; try { await action(); } catch(e) {error.value=e.message;} finally {busy.value=false;} }
onActivated(() => run(refresh));
async function upload(file) {
  if (!file) return;
  await run(async () => {
    const body = new FormData(); body.append('file',file);
    const response = await fetch('/api/contracts/import',{method:'POST',body}); const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '上传失败');
    const document = await api('/api/knowledge/documents','POST',{source_id:data.source_id,name:file.name.slice(0,160)});
    await refresh(); if (selected.value.length<30) selected.value.push(document.id);
    notice.value='资料已解析并建立本地关键词图谱，可立即检索；语义关系需点击“构建语义图谱”。';
  });
}
async function inspect(item) { await run(async () => {detail.value = await api('/api/knowledge/documents/' + item.id);}); }
async function index(item) { await run(async () => {
  notice.value='正在提取实体与关系，按每8个片段调用模型；请保留页面…';
  await api('/api/knowledge/documents/' + item.id + '/index','POST',{revision:item.revision,model_config_data:shell.model});
  await refresh(); detail.value=await api('/api/knowledge/documents/' + item.id); notice.value='语义图谱构建完成，所有实体关系均通过原文引用校验。';
}); }
async function remove(item) { await run(async () => {
  await api('/api/knowledge/documents/' + item.id + '?revision=' + item.revision,'DELETE');
  selected.value=selected.value.filter(id=>id!==item.id); if(detail.value?.id===item.id) detail.value=null;
  await refresh(); notice.value='已移出知识库；原件和历史审查、对话快照保留。';
}); }
async function search() { await run(async () => { const params=new URLSearchParams({q:query.value}); selected.value.forEach(id=>params.append('document_ids',id)); hits.value=(await api('/api/knowledge/search?'+params)).citations; if(!hits.value.length) notice.value='未检索到相关片段，请调整关键词或资料范围。'; }); }
async function openSession(id) { await run(async () => {session.value=await api('/api/knowledge/sessions/'+id); current.value=id;}); }
async function newSession() { await run(async () => {session.value=await api('/api/knowledge/sessions','POST',{}); current.value=session.value.id; await refresh();}); }
async function send() { if(!question.value.trim()) return; await run(async () => {
  if (!session.value) session.value=await api('/api/knowledge/sessions','POST',{});
  current.value=session.value.id;
  session.value=await api('/api/knowledge/sessions/'+session.value.id+'/messages','POST',{
    revision:session.value.revision,question:question.value,document_ids:selected.value,model_config_data:shell.model});
  question.value=''; await refresh();
}); }
</script>
<template>
  <div class="knowledge-workspace">
    <header class="knowledge-heading"><div><p>LexisGraph · 本地知识空间</p><h1>{{isChat?'知识库对话':'知识库与图谱'}}</h1><p>{{isChat?'结合资料与历史对话讨论合同问题，再选择需要带入审核的内容。':'上传制度、业务资料与合同范本，构建可追溯的知识图谱。'}}</p></div><RouterLink class="button" :to="isChat?'/knowledge':'/chat'">{{isChat?'管理知识库':'开始对话'}} →</RouterLink></header>
    <p v-if="error" class="knowledge-error" role="alert">{{error}}</p><p v-if="notice" class="knowledge-notice" role="status">{{notice}}</p>
    <div class="knowledge-grid">
      <aside class="knowledge-card"><h2>本次使用的资料 <small>{{selected.length}} / 30</small></h2><p>未勾选资料时，可进行普通对话。</p>
        <label class="knowledge-upload">{{busy?'正在处理…':'＋ 上传资料'}}<input type="file" accept=".txt,.pdf,.docx" :disabled="busy" @change="upload($event.target.files[0]);$event.target.value=''"/></label>
        <p>DOCX、文字型 PDF、TXT，最多10 MB。扫描件需先做 OCR。</p>
        <div v-for="item in documents" :key="item.id" class="knowledge-document"><label><input type="checkbox" v-model="selected" :value="item.id" :disabled="busy||(!selected.includes(item.id)&&selected.length>=30)"/><strong>{{item.name}}</strong></label><small>{{item.chunk_count}} 片段 · {{item.method==='model-entities-relations'?'语义实体关系':'关键词同现'}}</small><div class="knowledge-actions"><button :disabled="busy" @click="inspect(item)">查看图谱</button><button :disabled="busy" @click="index(item)">构建语义图谱</button><button :disabled="busy" @click="remove(item)">移出知识库</button></div></div>
        <p v-if="!documents.length">尚无资料，上传后即可本地检索。</p>
        <template v-if="isChat"><div class="knowledge-session-heading"><h2>历史对话</h2><button class="button" :disabled="busy" @click="newSession">新建</button></div><button v-for="item in sessions" :key="item.id" class="knowledge-session" :class="{active:current===item.id}" :disabled="busy" @click="openSession(item.id)">{{item.title}}</button></template>
      </aside>
      <main class="knowledge-card">
        <template v-if="isChat"><div class="knowledge-session-heading"><h2>{{session?.title||'新对话'}}</h2><RouterLink v-if="session?.messages.length" class="button" :to="'/reviews/new?knowledge_session='+session.id">选择对话用于审查 →</RouterLink></div>
          <p>回答会显示引用原文。未配置模型时仅返回检索摘录；配置模型后支持多轮语义对话。</p>
          <div class="knowledge-chat" aria-live="polite"><p v-if="!session?.messages.length" class="knowledge-empty">可以询问：“采购制度中付款需要哪些条件？”或“结合这些资料，验收条款应关注什么？”</p><article v-for="message in session?.messages||[]" :key="message.id" class="knowledge-message" :class="message.role"><b>{{message.role==='user'?'你':'LexisGraph'}}</b><div class="knowledge-answer">{{message.text}}</div><small v-if="message.mode==='extractive'">本地原文摘录 · 未进行模型分析</small><details v-for="citation in message.citations||[]" :key="citation.id" class="knowledge-citation"><summary>{{citation.name}} · 提取文本第 {{citation.line}} 行</summary><p>{{citation.quote||citation.text}}</p><a :href="'/api/sources/'+citation.source_id+'/file'" target="_blank" rel="noopener">查看原件</a><small>证据 {{citation.id}} · {{citation.method==='model-entities-relations'?'语义图谱':'关键词图谱'}}</small></details></article></div>
          <form @submit.prevent="send"><label for="knowledge-question">输入问题</label><textarea id="knowledge-question" v-model="question" class="field" rows="3" maxlength="5000" :disabled="busy" placeholder="输入问题，可结合上文继续追问…"/><div class="knowledge-compose"><small>使用 {{selected.length}} 份资料；最多50轮。所选对话经确认后可带入合同审核。</small><button class="button primary" :disabled="busy||!question.trim()">{{busy?'正在处理…':'发送'}}</button></div></form>
        </template>
        <template v-else><h2>检索验证</h2><p>文本相关性检索结合两跳实体关系扩展。未命中不代表资料不存在，检索结果不替代知识库全文核验。</p><form class="knowledge-search" @submit.prevent="search"><input v-model="query" class="field" maxlength="5000" placeholder="输入条款、业务问题或关键词"/><button class="button primary" :disabled="busy||!query.trim()||!selected.length">检索</button></form>
          <details v-for="citation in hits" :key="citation.id" class="knowledge-citation" open><summary>{{citation.name}} · 第 {{citation.line}} 行 · {{citation.match==='graph'?'关系扩展':'文本命中'}}</summary><p>{{citation.text}}</p><small v-for="(path,i) in citation.paths" :key="i">{{path.source}} → {{path.relation}} → {{path.target}}</small><a :href="'/api/sources/'+citation.source_id+'/file'" target="_blank" rel="noopener">查看原件</a></details>
        </template>
        <section v-if="detail" class="knowledge-graph"><div class="knowledge-session-heading"><h2>{{detail.name}} · 图谱详情</h2><button class="button" @click="detail=null">关闭</button></div><p>{{detail.method==='model-entities-relations'?'模型提取实体关系，附原文依据。':'当前为本地关键词同现图，关系仅表示同片段出现，不代表语义或法律事实。'}}</p><div class="knowledge-entities"><span v-for="name in [...new Set(detail.entities.map(e=>e.name))]" :key="name">{{name}}</span></div><details v-for="(edge,i) in detail.relations" :key="i" class="knowledge-citation"><summary>{{edge.source}} → {{edge.relation}} → {{edge.target}} · {{edge.chunk_id}}</summary><p>{{edge.evidence}}</p></details><p v-if="!detail.relations.length">本次没有提取到有原文依据的关系。</p></section>
      </main>
    </div>
  </div>
</template>
<style scoped>
.knowledge-workspace{max-width:1420px;margin:auto;color:#1e293b;font-size:14px}.knowledge-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:24px}.knowledge-heading h1{font-size:28px;font-weight:700;margin:8px 0}.knowledge-workspace p{color:#64748b;line-height:1.8;margin:10px 0}.knowledge-grid{display:grid;grid-template-columns:310px minmax(0,1fr);gap:22px}.knowledge-card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:24px;min-width:0;align-self:start}.knowledge-card h2{font-size:16px;font-weight:650}.knowledge-card small{color:#64748b;font-size:12px}.knowledge-document{padding:18px 0;border-bottom:1px solid #eef2f6}.knowledge-document label{display:flex;gap:8px;overflow-wrap:anywhere}.knowledge-document>small{display:block;margin:8px 0}.knowledge-actions{display:flex;gap:10px;flex-wrap:wrap}.knowledge-actions button{font-size:12px;color:#2563eb}.knowledge-upload{position:relative;display:block;border:1px dashed #93b4e8;padding:18px;text-align:center;border-radius:10px;margin-top:18px;color:#2563eb;cursor:pointer}.knowledge-upload input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%}.knowledge-session-heading{display:flex;gap:12px;align-items:center;justify-content:space-between;margin:12px 0}.knowledge-session{display:block;width:100%;text-align:left;overflow-wrap:anywhere;padding:12px;border-radius:8px;margin-top:6px;background:#f8fafc}.knowledge-session.active{background:#eff6ff;color:#2563eb}.knowledge-chat{max-height:60vh;min-height:200px;overflow:auto;margin:24px 0}.knowledge-message{border:1px solid #e2e8f0;background:#f8fafc;border-radius:12px;padding:18px;margin-bottom:18px}.knowledge-message.user{background:#eff6ff;border-color:#dbeafe}.knowledge-answer{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9;margin:8px 0}.knowledge-citation{border:1px solid #dbe4ef;border-radius:8px;padding:12px;margin:12px 0;font-size:12px;overflow-wrap:anywhere}.knowledge-citation summary{cursor:pointer;color:#334155}.knowledge-citation p{white-space:pre-wrap}.knowledge-citation small{display:block;margin-top:8px}.knowledge-citation a{color:#2563eb;display:block;margin-top:10px}.knowledge-search,.knowledge-compose{display:flex;gap:12px;align-items:center;margin:14px 0}.knowledge-compose{justify-content:space-between}.knowledge-graph{margin-top:24px;border-top:1px solid #e2e8f0;padding-top:16px;max-height:600px;overflow:auto}.knowledge-entities{display:flex;gap:8px;flex-wrap:wrap}.knowledge-entities span{background:#eff6ff;border:1px solid #dbeafe;border-radius:20px;padding:5px 10px;font-size:12px}.knowledge-error,.knowledge-notice{padding:14px;border-radius:8px;background:#eff6ff}.knowledge-workspace .knowledge-error{background:#fef2f2;color:#b91c1c}.knowledge-empty{padding:24px}button:disabled{opacity:.5;cursor:wait}input[type=checkbox]{accent-color:#2563eb}textarea{margin-top:10px}@media(max-width:900px){.knowledge-grid{grid-template-columns:1fr}.knowledge-heading{align-items:flex-start}.knowledge-card{padding:18px}}
</style>
