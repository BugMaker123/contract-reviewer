<script setup>
import { nextTick, onActivated, ref, watch } from 'vue';
import { usePortalShell } from '../stores/portal.js';
const shell = usePortalShell(), {api} = shell;
const documents = ref([]), selected = ref([]), sessions = ref([]), session = ref(null);
const question = ref(''), pending = ref(''), error = ref(''), busy = ref(false), loading = ref(false), showSources = ref(false);
const conversation = ref(null), composer = ref(null);
const suggestions = [
  {title:'梳理审查重点',text:'采购合同中，付款与验收条款应该重点关注什么？',icon:'01'},
  {title:'查找制度依据',text:'根据我选择的资料，付款前需要满足哪些条件？请引用原文。',icon:'02'},
  {title:'推敲条款风险',text:'合同约定“乙方承担一切损失”，应如何分析和修改？',icon:'03'},
];
async function refresh() {
  loading.value = true;
  try {
    [documents.value,sessions.value]=await Promise.all([api('/api/knowledge/documents'),api('/api/knowledge/sessions')]);
    selected.value=selected.value.filter(id=>documents.value.some(item=>item.id===id));
  } catch(e) { error.value=e.message==='Not Found'?'知识库服务未就绪，请重启后端后重试。':e.message; }
  finally {loading.value=false;}
}
onActivated(refresh);
async function scroll() {await nextTick();if(conversation.value)conversation.value.scrollTop=conversation.value.scrollHeight;}
watch([() => session.value?.messages.length, pending], scroll);
function newChat() {if(busy.value)return;session.value=null;question.value='';error.value='';composer.value?.focus();}
async function openSession(item) {
  if(busy.value)return;
  error.value='';loading.value=true;
  try {
    session.value=await api('/api/knowledge/sessions/'+item.id);
    const last = [...session.value.messages].reverse().find(message=>message.role==='assistant');
    selected.value=(last?.document_ids||[]).filter(id=>documents.value.some(document=>document.id===id));
    await scroll();
  } catch(e) {error.value=e.message;} finally {loading.value=false;}
}
async function upload(file) {
  if(!file||busy.value)return;
  busy.value=true;error.value='';
  try {
    const body=new FormData();body.append('file',file);
    const response=await fetch('/api/contracts/import',{method:'POST',body});const source=await response.json();
    if(!response.ok)throw new Error(typeof source.detail==='string'?source.detail:'资料上传失败');
    const document=await api('/api/knowledge/documents','POST',{name:file.name.slice(0,160),source_id:source.source_id});
    await refresh();if(selected.value.length<30)selected.value.push(document.id);
  }catch(e){error.value=e.message;}finally{busy.value=false;}
}
async function send() {
  if(!question.value.trim()||busy.value||loading.value)return;
  busy.value=true;error.value='';pending.value=question.value;
  try {
    if(!session.value)session.value=await api('/api/knowledge/sessions','POST',{});
    session.value=await api('/api/knowledge/sessions/'+session.value.id+'/messages','POST',{
      revision:session.value.revision,question:question.value,document_ids:selected.value,model_config_data:shell.model,
    });
    question.value='';await refresh();
  }catch(e){error.value=e.message;}finally{pending.value='';busy.value=false;await scroll();composer.value?.focus();}
}
function keydown(event){if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();send();}}
function suggest(text){question.value=text;composer.value?.focus();}
</script>
<template>
  <section class="chat-workspace">
    <aside class="chat-history">
      <button class="chat-new" :disabled="busy" @click="newChat"><span>＋</span> 新建对话 <kbd>↗</kbd></button>
      <div class="chat-history-title">最近对话 <span>{{sessions.length}}</span></div>
      <p v-if="loading&&!sessions.length" class="chat-muted">正在读取…</p>
      <p v-else-if="!sessions.length" class="chat-muted">你的对话会保存在这里</p>
      <nav aria-label="历史对话"><button v-for="item in sessions" :key="item.id" :class="{active:session?.id===item.id}" :disabled="busy" @click="openSession(item)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l-3 3V11.5a9 9 0 0 1 18 0Z"/></svg><span>{{item.title}}</span></button></nav>
      <RouterLink class="chat-library" to="/knowledge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4h6l2 2h8v14H4Z"/><path d="M8 11h8m-8 4h5"/></svg> 管理知识库 <span>↗</span></RouterLink>
    </aside>
    <main class="chat-main">
      <header class="chat-top"><div><span class="chat-status"></span><strong>{{session?.messages.length?session.title:'合同助手'}}</strong></div><RouterLink v-if="session?.messages.length" class="chat-review" :to="'/reviews/new?knowledge_session='+session.id">用于合同审查 <span>↗</span></RouterLink><span v-else class="chat-top-label">LexisGraph</span></header>
      <div v-if="error" class="chat-error" role="alert"><span>{{error}}</span><button :disabled="loading" @click="error='';refresh()">重试</button></div>
      <div ref="conversation" class="chat-conversation" aria-live="polite">
        <div v-if="!session?.messages.length&&!pending" class="chat-welcome">
          <div class="chat-emblem"><svg viewBox="0 0 40 40" fill="none"><path d="m20 6 14 14-14 14L6 20 20 6Z" stroke="currentColor" stroke-width="1.6"/><path d="m20 14 6 6-6 6-6-6 6-6Z" fill="currentColor"/></svg></div>
          <p class="chat-eyebrow">你的合同工作伙伴</p><h1>把合同问题，聊清楚。</h1><p class="chat-subtitle">分析条款、查找依据，或从一个具体问题开始。</p>
          <div class="chat-suggestions"><button v-for="item in suggestions" :key="item.title" @click="suggest(item.text)"><small>{{item.icon}}</small><strong>{{item.title}}</strong><span>{{item.text}}</span><i>↗</i></button></div>
        </div>
        <div v-else class="chat-thread"><article v-for="message in session?.messages||[]" :key="message.id" class="chat-message" :class="message.role"><div v-if="message.role==='assistant'" class="chat-avatar">◇</div><div class="chat-message-content"><span v-if="message.role==='assistant'" class="chat-author">LexisGraph <small v-if="message.mode==='extractive'">原文检索</small></span><div class="chat-answer">{{message.text}}</div><details v-if="message.citations?.length" class="chat-references"><summary>{{message.citations.length}} 条参考依据 <span>⌄</span></summary><div v-for="citation in message.citations" :key="citation.id" class="chat-reference"><strong>{{citation.name}} <small>提取文本 · 第 {{citation.line}} 行</small></strong><p>{{citation.quote||citation.text}}</p><a :href="'/api/sources/'+citation.source_id+'/file'" target="_blank" rel="noopener">查看原件 ↗</a></div></details></div></article><template v-if="pending"><article class="chat-message user"><div class="chat-message-content"><div class="chat-answer">{{pending}}</div></div></article><article class="chat-message assistant"><div class="chat-avatar">◇</div><div class="chat-thinking"><span></span><span></span><span></span> 正在整理回答</div></article></template></div>
      </div>
      <footer class="chat-bottom">
        <form class="chat-composer" @submit.prevent="send">
          <textarea ref="composer" id="knowledge-question" v-model="question" aria-label="输入问题" rows="2" maxlength="5000" :disabled="busy" placeholder="询问合同问题，或结合知识库深入讨论…" @keydown="keydown"/>
          <div class="chat-composer-tools"><div class="chat-scope-wrap"><button type="button" class="chat-scope" :class="{selected:selected.length}" :aria-expanded="showSources" @click="showSources=!showSources"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 4h5l2 2h7v11H3Z"/></svg>{{selected.length?'已选 '+selected.length+' 份资料':'添加参考资料'}} <span>⌃</span></button><div v-if="showSources" class="chat-sources"><div class="chat-sources-title"><strong>参考资料</strong><button type="button" aria-label="关闭资料选择" @click="showSources=false">×</button></div><p>选择本轮对话使用的资料</p><label v-for="item in documents" :key="item.id" class="chat-source-row"><input type="checkbox" v-model="selected" :value="item.id" :disabled="busy||(!selected.includes(item.id)&&selected.length>=30)"/><span>{{item.name}}</span></label><p v-if="!documents.length" class="chat-muted">还没有资料，上传一份开始吧。</p><label class="chat-source-upload">＋ 上传资料<input type="file" accept=".docx,.pdf,.txt" :disabled="busy" @change="upload($event.target.files[0]);$event.target.value=''"/></label><small>DOCX / PDF / TXT · 最大 10 MB</small></div></div><button type="submit" class="chat-send" :disabled="busy||loading||!question.trim()" aria-label="发送问题"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 19V5m-6 6 6-6 6 6"/></svg></button></div>
        </form>
        <p class="chat-footnote">回答供审核参考，请结合原文核实。<span>Enter 发送 · Shift + Enter 换行</span></p>
      </footer>
    </main>
  </section>
</template>
<style scoped>
.chat-workspace{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;display:grid;grid-template-columns:224px minmax(0,1fr);height:calc(100dvh - 128px);min-height:560px;max-width:1600px;margin:0 auto;background:#fff;border:1px solid #e5eaf1;border-radius:16px;overflow:hidden;color:#1e293b;font-size:14px}.chat-workspace button{font-family:inherit;cursor:pointer}.chat-history{display:flex;flex-direction:column;background:#f8fafc;border-right:1px solid #edf0f5;padding:20px 14px;min-height:0}.chat-new{display:flex;align-items:center;gap:10px;width:100%;padding:11px 12px;border:1px solid #dce4ef;border-radius:9px;background:white;text-align:left;font-size:13px;font-weight:600;box-shadow:0 2px 3px #0f172a03}.chat-new>span{font-size:20px;color:#2563eb}.chat-new kbd{margin-left:auto;color:#94a3b8;font-size:13px;font-weight:400}.chat-history-title{display:flex;justify-content:space-between;padding:28px 10px 12px;color:#8b98ab;font-size:11px;letter-spacing:.04em}.chat-history nav{overflow:auto;flex:1;min-height:0}.chat-history nav button{display:flex;align-items:center;gap:9px;width:100%;padding:12px 10px;text-align:left;border-radius:8px;color:#64748b;font-size:12px;margin:3px 0}.chat-history nav button svg{width:15px;height:15px;flex-shrink:0}.chat-history nav button span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chat-history nav button.active{background:#eaf0fc;color:#2455a5}.chat-history nav button:hover{background:#edf1f7}.chat-library{margin-top:auto;border-top:1px solid #e4eaf2;padding:18px 9px 0;display:flex;align-items:center;gap:8px;font-size:12px;color:#64748b}.chat-library svg{width:17px;height:17px}.chat-library span{margin-left:auto}.chat-muted{font-size:12px;color:#94a3b8;padding:10px;line-height:1.8}.chat-main{display:flex;flex-direction:column;min-width:0;min-height:0;position:relative}.chat-top{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px 28px;border-bottom:1px solid #f0f3f7;flex-shrink:0;height:65px}.chat-top>div{display:flex;align-items:center;gap:9px;min-width:0}.chat-top strong{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.chat-status{width:6px;height:6px;background:#6596db;border-radius:50%;flex-shrink:0}.chat-top-label{font-size:11px;color:#9aa7ba;letter-spacing:.06em}.chat-review{font-size:12px;color:#2563eb;white-space:nowrap}.chat-review span{margin-left:8px}.chat-conversation{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column}.chat-welcome{margin:auto;width:100%;max-width:820px;padding:38px 40px 50px;text-align:center}.chat-emblem{display:flex;align-items:center;justify-content:center;width:64px;height:64px;margin:0 auto 22px;border:1px solid #d8e5fa;border-radius:19px;background:linear-gradient(145deg,#f3f7ff,#fff);color:#3b72d2;box-shadow:0 8px 24px #2563eb08}.chat-emblem svg{width:38px;height:38px}.chat-eyebrow{font-size:11px;letter-spacing:.15em;color:#94a3b8;margin-bottom:12px}.chat-welcome h1{font-size:30px;line-height:1.5;letter-spacing:-.035em;font-weight:650;color:#1c2c45;margin:0}.chat-subtitle{font-size:13px;color:#8a98ab;margin:13px 0 34px}.chat-suggestions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;text-align:left}.chat-suggestions button{padding:18px 16px 22px;border:1px solid #e8edf5;border-radius:12px;text-align:left;position:relative;background:#fff;transition:background .15s,border .15s}.chat-suggestions button:hover{border-color:#b8cdf2;background:#f8faff}.chat-suggestions small{font-size:10px;letter-spacing:.08em;color:#9daec5;display:block;margin-bottom:16px}.chat-suggestions strong{font-size:13px;font-weight:600;display:block;margin-bottom:10px}.chat-suggestions span{font-size:11px;line-height:1.8;color:#94a3b8;display:block;padding-bottom:4px}.chat-suggestions i{font-style:normal;position:absolute;right:12px;top:16px;color:#b8c6db}.chat-bottom{padding:8px 32px 18px;background:#fff;flex-shrink:0}.chat-composer{border:1px solid #dce4ef;border-radius:16px;max-width:820px;margin:auto;padding:16px 18px 12px;box-shadow:0 4px 20px #253c6306;transition:border .2s}.chat-composer:focus-within{border-color:#9bb9ec;box-shadow:0 0 0 3px #2563eb05}.chat-composer textarea{display:block;width:100%;border:0;outline:0;box-shadow:none!important;resize:none;background:transparent;font-family:inherit;font-size:13px;line-height:1.9;color:#334155;min-height:58px}.chat-composer textarea::placeholder{color:#a4afc0}.chat-composer-tools{display:flex;justify-content:space-between;align-items:center;margin-top:8px}.chat-scope{display:flex;gap:6px;align-items:center;font-size:11px;padding:6px 8px;border-radius:6px;background:#f5f7fa;color:#7c8ba0}.chat-scope svg{width:15px;height:15px}.chat-scope.selected{color:#2563eb;background:#eff6ff}.chat-scope>span{margin-left:4px;color:#94a3b8}.chat-send{width:33px;height:33px;background:#2563eb;color:white;border-radius:10px;display:flex;align-items:center;justify-content:center}.chat-send svg{width:19px;height:19px}.chat-send:disabled{background:#e8edf5;color:#a9b7cc;opacity:1}.chat-footnote{max-width:800px;margin:11px auto 0;font-size:10px;color:#a4afbe;display:flex;justify-content:space-between}.chat-scope-wrap{position:relative}.chat-sources{position:absolute;bottom:42px;left:0;background:white;border:1px solid #dfe7f2;border-radius:12px;padding:16px;width:320px;max-height:360px;overflow:auto;box-shadow:0 12px 40px #2436531a;z-index:20}.chat-sources-title{display:flex;justify-content:space-between;font-size:13px}.chat-sources-title button{font-size:20px;color:#94a3b8}.chat-sources>p{font-size:11px;color:#94a3b8;margin:8px 0 14px}.chat-source-row{display:flex;gap:8px;font-size:12px;padding:10px 0;align-items:center}.chat-source-row span{overflow-wrap:anywhere}.chat-source-upload{position:relative;display:block;padding:10px;background:#f5f8fe;text-align:center;color:#2563eb;border-radius:7px;font-size:12px;margin:12px 0 8px;cursor:pointer}.chat-source-upload input{position:absolute;inset:0;opacity:0;width:100%;cursor:pointer}.chat-sources>small{font-size:10px;color:#9aa7ba}.chat-error{background:#fff7f5;border-bottom:1px solid #ffe8e2;color:#b4533c;padding:11px 28px;font-size:12px;display:flex;justify-content:space-between;gap:20px}.chat-error button{color:#2563eb;white-space:nowrap}.chat-thread{width:100%;max-width:850px;margin:0 auto;padding:30px 28px}.chat-message{display:flex;gap:13px;margin:0 0 30px;align-items:flex-start}.chat-avatar{background:#f1f5fc;border:1px solid #e3eaf7;color:#4a7ac7;width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:18px}.chat-message-content{min-width:0;max-width:100%}.chat-author{font-size:11px;font-weight:600;color:#64748b;display:block;margin:5px 0 12px}.chat-author small{font-size:10px;font-weight:400;color:#94a3b8;margin-left:8px}.chat-answer{font-size:13px;line-height:1.95;white-space:pre-wrap;overflow-wrap:anywhere;color:#334155}.chat-message.user{justify-content:flex-end}.chat-message.user .chat-message-content{background:#eef3fb;border:1px solid #e6edf8;border-radius:14px 14px 3px 14px;padding:12px 17px;max-width:85%}.chat-references{border:1px solid #e6ecf5;border-radius:9px;padding:10px 13px;margin-top:15px;font-size:11px;color:#64748b;max-width:600px}.chat-references summary{cursor:pointer;display:flex;justify-content:space-between}.chat-reference{padding:14px 0 4px;border-top:1px solid #edf1f6;margin-top:10px}.chat-reference strong{font-size:11px;display:block;color:#475569}.chat-reference small{font-weight:400;margin-left:8px;color:#94a3b8}.chat-reference p{white-space:pre-wrap;line-height:1.9;margin:10px 0;color:#7e8ca0}.chat-reference a{color:#2563eb;font-size:10px}.chat-thinking{display:flex;align-items:center;gap:5px;color:#94a3b8;font-size:12px;padding-top:8px}.chat-thinking span{width:4px;height:4px;background:#93b4e6;border-radius:50%;animation:pulse 1.2s ease-in-out infinite}.chat-thinking span:nth-child(2){animation-delay:.15s}.chat-thinking span:nth-child(3){animation-delay:.3s;margin-right:5px}@keyframes pulse{50%{opacity:.25}}button:disabled{cursor:default;opacity:.55}input[type=checkbox]{accent-color:#2563eb}@media(min-width:1600px){.chat-welcome{max-width:900px;padding-left:55px;padding-right:55px}.chat-welcome h1{font-size:34px}}@media(max-width:1100px){.chat-workspace{grid-template-columns:180px minmax(0,1fr)}.chat-welcome{padding:28px 24px}.chat-suggestions{grid-template-columns:1fr}.chat-suggestions button{padding:12px 15px}.chat-suggestions small,.chat-suggestions span{display:none}.chat-suggestions strong{margin:0}.chat-welcome h1{font-size:25px}.chat-footnote span{display:none}}@media(max-width:700px){.chat-workspace{grid-template-columns:1fr;height:calc(100dvh - 110px)}.chat-history{display:none}.chat-top{padding:15px 18px}.chat-bottom{padding:8px 15px 15px}.chat-thread{padding:24px 18px}.chat-sources{width:270px}.chat-welcome{padding:24px}}
</style>
