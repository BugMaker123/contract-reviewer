<script setup>
import {ref,reactive,computed,onMounted} from 'vue';
import {useRouter} from 'vue-router';
import {usePortalShell} from '../stores/portal.js';
const shell=usePortalShell(),router=useRouter();
const empty=()=>({title:'',contract_type:'采购合同',party_a:'',party_b:'',perspective:'中立审慎',transaction:'',payment:'',requirements:''});
const brief=reactive(empty()),draft=ref(null),title=ref(''),text=ref(''),busy=ref(false),error=ref(''),rows=ref([]),total=ref(0),page=ref(1),q=ref('');
const dirty=computed(()=>draft.value&&(title.value!==draft.value.title||text.value!==draft.value.text));
const pages=computed(()=>Math.max(1,Math.ceil(total.value/10)));
const date=v=>new Date(v).toLocaleString('zh-CN',{hour12:false,timeZone:'Asia/Shanghai'});
async function load(){const data=await shell.api('/api/contract-drafts?'+new URLSearchParams({page:page.value,q:q.value}));rows.value=data.items;total.value=data.total;}
function show(saved){draft.value=saved;title.value=saved.title;text.value=saved.text;Object.assign(brief,saved.brief);}
async function persist(){if(!dirty.value)return draft.value;const saved=await shell.api('/api/contract-drafts/'+draft.value.id,'PUT',{title:title.value,text:text.value,revision:draft.value.revision});draft.value=saved;return saved;}
async function action(fn){if(busy.value)return;busy.value=true;error.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;}}
function generate(){action(async()=>{await persist();const saved=await shell.api('/api/contract-drafts/generate','POST',{brief:{...brief},model_config_data:shell.model});show(saved);page.value=1;await load();shell.notify('合同草稿已生成并保存');});}
function save(){action(async()=>{await persist();await load();shell.notify('草稿已保存');});}
function open(row){action(async()=>{await persist();show(await shell.api('/api/contract-drafts/'+row.id));});}
function reset(){action(async()=>{await persist();draft.value=null;title.value='';text.value='';Object.assign(brief,empty());});}
function download(){action(async()=>{const saved=await persist();const response=await fetch('/api/contract-drafts/'+saved.id+'/word');if(!response.ok)throw Error('Word 导出失败，请重试');const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=saved.title+'.docx';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});}
function review(){action(async()=>{const saved=await persist();const roles={'甲方立场':'甲方(买方/采购方/委托方)','乙方立场':'乙方(卖方/开发方/服务方)','中立审慎':'中立审慎'};const task=await shell.api('/api/tasks','POST',{title:saved.title,text:saved.text,type:saved.brief.contract_type,role:roles[saved.brief.perspective]||'中立审慎',mode:'deep',background:saved.brief.transaction,focus:saved.brief.requirements});await router.push('/workbench?task='+task.id);});}
function changePage(next){action(async()=>{page.value=next;await load();});}
onMounted(()=>action(load));
</script>
<template>
<div class="drafting-page">
  <header class="drafting-heading"><div><h1>合同起草</h1><p>描述交易安排，生成可编辑的合同草稿，再导出或进入审查。</p></div><button class="button" :disabled="busy" @click="reset">＋ 新建起草</button></header>
  <p v-if="error" class="drafting-error" role="alert">{{error}}</p>
  <div class="drafting-layout">
    <form class="drafting-brief drafting-card" @submit.prevent="generate">
      <div class="drafting-section-title"><span class="drafting-step">1</span><h2>填写起草需求</h2></div>
      <fieldset :disabled="busy">
        <label>合同名称 <span>*</span><input v-model="brief.title" required maxlength="200" placeholder="例如：年度设备采购合同"/></label>
        <div class="drafting-pair"><label>合同类型<select v-model="brief.contract_type"><option v-for="v in ['采购合同','销售合同','服务合同','技术开发合同','租赁合同','保密协议','合作协议','其他合同']" :key="v">{{v}}</option></select></label><label>起草立场<select v-model="brief.perspective"><option>中立审慎</option><option>甲方立场</option><option>乙方立场</option></select></label></div>
        <div class="drafting-pair"><label>甲方名称<input v-model="brief.party_a" maxlength="500" placeholder="可稍后补充"/></label><label>乙方名称<input v-model="brief.party_b" maxlength="500" placeholder="可稍后补充"/></label></div>
        <label>交易内容与履行安排 <span>*</span><textarea v-model="brief.transaction" required minlength="10" maxlength="15000" rows="5" placeholder="说明采购或服务内容、数量、交付方式、履行期限及验收安排（至少10字）"/></label>
        <label>价款与付款安排<textarea v-model="brief.payment" maxlength="5000" rows="3" placeholder="金额、税费、付款节点、开票要求等"/></label>
        <label>其他起草要求<textarea v-model="brief.requirements" maxlength="10000" rows="3" placeholder="违约责任、解除条件、保密约定等"/></label>
        <p class="drafting-note">未提供的信息将留空，并列入待补充清单。</p>
        <button class="button primary drafting-generate" type="submit">{{busy?'正在处理，请稍候…':draft?'按当前需求生成新草稿':'生成合同草稿'}}</button>
      </fieldset>
    </form>
    <section class="drafting-output drafting-card" :aria-busy="busy">
      <div class="drafting-section-title"><span class="drafting-step">2</span><h2>合同草稿</h2><span v-if="draft" class="drafting-save-state">{{dirty?'有未保存修改':'已保存'}}</span></div>
      <template v-if="draft">
        <div class="drafting-tools"><button class="button" :disabled="busy||!dirty" @click="save">保存草稿</button><button class="button" :disabled="busy" @click="download">导出 Word</button><button class="button primary" :disabled="busy" @click="review">进入合同审查 →</button></div>
        <label class="drafting-output-title">合同名称<input v-model="title" :disabled="busy" maxlength="200" aria-label="草稿合同名称"/></label>
        <details v-if="draft.missing_information.length" class="drafting-missing" open><summary>生成时需补充的信息 · {{draft.missing_information.length}} 项</summary><ul><li v-for="(item,i) in draft.missing_information" :key="i">{{item}}</li></ul></details>
        <textarea v-model="text" :disabled="busy" class="drafting-editor" aria-label="合同草稿正文" maxlength="200000" spellcheck="false"/>
        <p class="drafting-note">{{text.length.toLocaleString()}} 字 · 导出或送审前会先保存当前修改</p>
      </template>
      <div v-else class="drafting-empty"><span aria-hidden="true">✎</span><h3>{{busy?'正在处理起草请求':'从一份清晰的交易需求开始'}}</h3><p>{{busy?'生成完成后会自动保存，请稍候。':'在左侧填写交易信息，合同草稿将显示在这里。'}}</p><div><span>完整条款</span><span>在线编辑</span><span>Word 导出</span></div></div>
    </section>
  </div>
  <section class="drafting-card drafting-history"><div class="drafting-history-heading"><div><h2>起草记录</h2><p>每次生成单独保存，编辑原草稿不会覆盖其他记录。</p></div><form @submit.prevent="changePage(1)"><input v-model="q" aria-label="搜索起草记录" placeholder="搜索合同名称" maxlength="200"/><button class="button" :disabled="busy">搜索</button></form></div>
    <table><thead><tr><th>合同名称</th><th>合同类型</th><th>更新时间</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{row.title}}</td><td>{{row.brief.contract_type}}</td><td>{{date(row.updated_at)}}</td><td><button :disabled="busy" @click="open(row)">打开草稿</button></td></tr><tr v-if="!rows.length"><td colspan="4" class="drafting-history-empty">暂无起草记录</td></tr></tbody></table>
    <nav class="drafting-pagination" aria-label="起草记录分页"><span>共 {{total}} 条 · 第 {{page}} / {{pages}} 页</span><div><button class="button" :disabled="busy||page<=1" @click="changePage(page-1)">上一页</button><button class="button" :disabled="busy||page>=pages" @click="changePage(page+1)">下一页</button></div></nav>
  </section>
</div>
</template>
<style scoped>
.drafting-page{max-width:1700px;margin:auto;color:#1e293b}.drafting-heading,.drafting-history-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:26px}.drafting-heading h1{font-size:26px;font-weight:700;color:#0f172a;margin:0 0 8px}.drafting-heading p,.drafting-history-heading p{font-size:13px;color:#64748b;margin:0}.drafting-layout{display:grid;grid-template-columns:minmax(340px,.85fr) minmax(450px,1.3fr);gap:24px;align-items:start}.drafting-card{background:white;border:1px solid #dfe6ef;border-radius:16px;padding:26px;box-shadow:0 3px 12px #33415503}.drafting-section-title{display:flex;align-items:center;gap:10px;margin-bottom:24px}.drafting-section-title h2,.drafting-history h2{font-size:16px;font-weight:650;margin:0}.drafting-step{background:#eff5ff;color:#2563eb;border-radius:8px;width:28px;height:28px;display:grid;place-items:center;font-size:13px;font-weight:650}.drafting-save-state{margin-left:auto;color:#64748b;font-size:12px}.drafting-page fieldset{padding:0;border:0;min-width:0}.drafting-page label{display:block;font-size:13px;color:#475569;margin-bottom:18px}.drafting-page label>span{color:#ef4444}.drafting-page input,.drafting-page select,.drafting-page textarea{display:block;width:100%;border:1px solid #dbe3ef;border-radius:8px;padding:11px 12px;margin-top:8px;background:#fff;color:#1e293b;font:inherit;box-sizing:border-box}.drafting-page textarea{resize:vertical;line-height:1.7}.drafting-page input:focus,.drafting-page select:focus,.drafting-page textarea:focus{outline:2px solid #bfdbfe;outline-offset:1px;border-color:#3b82f6}.drafting-page input::placeholder,.drafting-page textarea::placeholder{color:#94a3b8}.drafting-pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.drafting-note{font-size:12px;color:#94a3b8;margin:12px 0}.drafting-generate{width:100%;justify-content:center;margin-top:8px}.drafting-output{min-height:780px}.drafting-tools{display:flex;justify-content:flex-end;gap:8px;margin-bottom:20px;flex-wrap:wrap}.drafting-missing{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;font-size:12px;color:#92400e;margin-bottom:16px}.drafting-missing summary{cursor:pointer;font-weight:600}.drafting-missing ul{padding-left:20px;margin:10px 0 0;line-height:1.8}.drafting-page .drafting-editor{min-height:540px;font:15px/1.9 'SimSun',serif;padding:24px;background:#fcfcfd}.drafting-empty{min-height:620px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}.drafting-empty>span{width:64px;height:64px;border-radius:18px;background:#eff5ff;color:#2563eb;font-size:32px;display:grid;place-items:center;margin-bottom:20px}.drafting-empty h3{font-size:18px;font-weight:600;margin:0 0 10px}.drafting-empty p{color:#94a3b8;font-size:13px}.drafting-empty>div{display:flex;gap:12px;margin-top:22px}.drafting-empty>div span{font-size:12px;color:#64748b;border:1px solid #e2e8f0;border-radius:6px;padding:6px 10px}.drafting-history{margin-top:24px}.drafting-history-heading{margin-bottom:20px}.drafting-history-heading h2{margin-bottom:6px}.drafting-history-heading form{display:flex;gap:8px}.drafting-history-heading input{margin:0}.drafting-history table{width:100%;font-size:13px;border-collapse:collapse;text-align:left}.drafting-history th{background:#f8fafc;color:#64748b;font-weight:500}.drafting-history td,.drafting-history th{padding:14px;border-bottom:1px solid #edf2f7}.drafting-history td button{color:#2563eb}.drafting-history-empty{text-align:center;color:#94a3b8}.drafting-pagination{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#64748b;padding-top:18px}.drafting-pagination>div{display:flex;gap:8px}.drafting-error{background:#fff1f2;color:#be123c;border:1px solid #fecdd3;border-radius:8px;padding:14px;font-size:13px;margin-bottom:20px}.drafting-page button:disabled{opacity:.5;cursor:not-allowed}@media(max-width:1100px){.drafting-layout{grid-template-columns:1fr}.drafting-output{min-height:500px}.drafting-empty{min-height:400px}.drafting-history-heading{align-items:start;flex-direction:column}}
</style>
