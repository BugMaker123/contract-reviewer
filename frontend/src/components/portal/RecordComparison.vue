<script setup>
import {computed,nextTick,onMounted,onBeforeUnmount,ref,watch} from 'vue';
import ReviewIcon from './ReviewIcon.vue';
const props=defineProps({task:{type:Object,required:true}}),emit=defineEmits(['close']);
const versions=ref([]),before=ref('initial'),after=ref(props.task.active_run),scope=ref('current');
const result=ref(null),error=ref(''),loading=ref(true),onlyChanges=ref(false),selectedChange=ref(0);
const originalFrame=ref(null),revisedFrame=ref(null),ready=ref({original:false,revised:false}),previewError=ref('');
let generation=0;
const snapshots=computed(()=>!['initial',''].includes(before.value));
const query=computed(()=>new URLSearchParams({before_run:before.value,after_run:after.value,scope:scope.value}).toString());
const beforeLabel=computed(()=>before.value==='initial'?'首次审查原稿':before.value?'第 '+result.value?.before_number+' 轮输入快照':'第 '+result.value?.after_number+' 轮审查原稿');
const afterLabel=computed(()=>snapshots.value?'目标轮次输入快照':scope.value==='all'?'全部有效建议稿（含未采纳）':'已采纳修改稿');
const frameUrl=side=>'/static/document-preview.html?'+new URLSearchParams({comparison:props.task.id,before_run:before.value,run:after.value,scope:scope.value,side,pane:side,readonly:'1'});
const frames=()=>({original:originalFrame.value,revised:revisedFrame.value});
function mark(focus=false){
  if(!result.value)return;
  for(const [side,frame] of Object.entries(frames())){
    if(!ready.value[side])continue;
    frame?.contentWindow?.postMessage(JSON.parse(JSON.stringify({type:'lexis-mark-differences',side,text:result.value[side],changes:result.value.changes,charRanges:result.value[side+'_chars'],onlyChanges:onlyChanges.value,selectedChange:selectedChange.value,focus})),location.origin);
  }
}
async function move(direction){const count=result.value?.changes.length||0;if(!count)return;selectedChange.value=(selectedChange.value+direction+count)%count;mark(true);}
function receive(event){
  if(event.origin!==location.origin)return;
  const side=Object.entries(frames()).find(([,frame])=>frame?.contentWindow===event.source)?.[0];
  if(!side)return;
  if(event.data?.type==='lexis-document-ready'){ready.value={...ready.value,[side]:true};mark(true);}
  if(event.data?.type==='lexis-document-error')previewError.value='文档预览失败：'+event.data.message;
  if(event.data?.type==='lexis-document-scroll'&&result.value){
    const other=side==='original'?'revised':'original';
    const map=result.value[side+'_map'];
    frames()[other]?.contentWindow?.postMessage({...event.data,type:'lexis-sync-scroll',index:map?.[event.data.index]},location.origin);
  }
}
async function load(){
  const ticket=++generation;loading.value=true;error.value='';result.value=null;previewError.value='';ready.value={original:false,revised:false};
  try{
    const response=await fetch('/api/tasks/'+props.task.id+'/comparison?'+query.value),data=await response.json();
    if(!response.ok)throw Error(data.detail||'对比失败');
    if(ticket===generation){result.value=data;selectedChange.value=0;if(!data.changes.length)onlyChanges.value=false;}
  }catch(e){if(ticket===generation)error.value=e.message;}
  finally{if(ticket===generation)loading.value=false;}
}
async function initialize(){
  loading.value=true;
  try{
    const response=await fetch('/api/tasks/'+props.task.id);
    if(!response.ok)throw Error('版本列表读取失败');
    const data=await response.json();versions.value=data.runs.filter(run=>run.status==='completed');
    await load();
  }catch(e){error.value=e.message;loading.value=false;}
}
watch([before,after,scope],load);
watch(onlyChanges,async()=>{await nextTick();mark(true);});
watch(()=>props.task.id,initialize,{immediate:true});
onMounted(()=>window.addEventListener('message',receive));
onBeforeUnmount(()=>{generation++;window.removeEventListener('message',receive);});
</script>
<template>
<Teleport to="body"><div class="comparison-overlay" @click.self="emit('close')"><section class="comparison-dialog" role="dialog" aria-modal="true" aria-label="审核前后对比">
  <div class="comparison-header"><div class="comparison-title"><span class="comparison-title-icon"><ReviewIcon name="document"/></span><div><h2>审核前后对比</h2><p :title="task.title">{{task.title}}</p></div></div><button class="comparison-close" aria-label="关闭对比" @click="emit('close')">×</button></div>
  <div class="comparison-controls">
    <label>比较基准<select v-model="before" :disabled="!versions.length"><option value="initial">首次审查原稿（查看累计修改）</option><option value="">所选轮次审查原稿（仅本轮）</option><option v-for="v in versions" :key="v.id" :value="v.id">第 {{v.number}} 次审查输入快照</option></select></label>
    <span class="comparison-arrow" aria-hidden="true">→</span>
    <label>目标版本<select v-model="after" :disabled="!versions.length"><option v-for="v in versions" :key="v.id" :value="v.id">第 {{v.number}} 次审查{{snapshots?'输入快照':''}}</option></select></label>
    <label v-if="!snapshots">修改范围<select v-model="scope"><option value="current">仅已采纳修改</option><option value="all">全部有效建议（含未采纳）</option></select></label>
    <div class="comparison-links"><a v-if="['pending_review','completed'].includes(task.status)&&after===task.active_run" :href="`/api/runs/${after}/export?scope=report`" class="comparison-action">导出意见书</a><RouterLink class="comparison-action primary" :to="`/workbench?task=${task.id}&run=${after}`">打开此版本<ReviewIcon name="arrow"/></RouterLink></div>
  </div>
  <div class="comparison-toolbar"><div class="comparison-metrics"><span class="comparison-total"><strong>{{loading?'—':result?.changes.length??'—'}}</strong>处文本变化</span><span class="comparison-legend removed">删除文字</span><span class="comparison-legend added">新增文字</span><span v-if="!snapshots&&scope==='all'" class="comparison-proposal-badge">建议预览 · 未自动采纳</span></div><div class="comparison-tools"><label class="comparison-toggle"><input v-model="onlyChanges" type="checkbox" :disabled="loading||!result?.changes.length"/>仅看差异</label><button aria-label="上一处差异" :disabled="loading||!result?.changes.length" @click="move(-1)">↑</button><span>{{result?.changes.length?selectedChange+1:0}} / {{result?.changes.length||0}}</span><button aria-label="下一处差异" :disabled="loading||!result?.changes.length" @click="move(1)">↓</button></div></div>
  <p v-if="result&&!result.changes.length" class="comparison-identical" role="status">{{!snapshots&&scope==='current'&&result.pending_count?'所选范围内暂无已采纳的文本变化，另有 '+result.pending_count+' 项未采纳建议。':'所选两个稿件的文字一致。'}}<button v-if="!snapshots&&scope==='current'&&result.pending_count" class="comparison-action" @click="scope='all'">查看全部建议差异</button><span v-else-if="before===''">可将比较基准切换为「首次审查原稿」查看累计修改。</span></p>
  <p v-if="result?.warnings?.length" class="comparison-warning" role="status">{{result.warnings.length}} 项建议存在定位冲突，未计入建议稿，请在工作台核对。</p>
  <div class="comparison-column-headings"><div><span class="comparison-dot before-dot"/>修改前 <small>{{beforeLabel}}</small></div><div><span class="comparison-dot after-dot"/>修改后 <small>{{afterLabel}}</small></div></div>
  <p v-if="loading" role="status" class="comparison-state">正在读取版本并生成对比…</p><div v-else-if="error" role="alert" class="comparison-state comparison-error">{{error}}<button @click="initialize">重新加载</button></div>
  <div v-if="previewError" class="comparison-warning" role="alert">{{previewError}}<button class="comparison-action" @click="load">重新加载文档</button></div>
  <div v-if="result&&!loading" class="comparison-documents" :key="query">
    <iframe ref="originalFrame" :src="frameUrl('original')" title="修改前合同原格式文档" sandbox="allow-scripts allow-same-origin"/>
    <iframe ref="revisedFrame" :src="frameUrl('revised')" title="修改后合同原格式文档" sandbox="allow-scripts allow-same-origin"/>
  </div>
  <div class="comparison-footer"><span>{{snapshots?'对比两个轮次的固定输入快照。':scope==='all'?'显示有效修订建议，包含尚未采纳的建议，不代表已确认修改。':'对比原稿与已采纳修改稿，未采纳建议不计入正文变化。'}}</span><span>保留文档排版 · 字级差异高亮 · 同步阅读</span></div>
</section></div></Teleport>
</template>
<style scoped>
.comparison-overlay{position:fixed;inset:0;z-index:70;display:flex;align-items:center;justify-content:center;padding:28px;background:#0f172a66;backdrop-filter:blur(4px);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.5}
.comparison-overlay *{box-sizing:border-box}
.comparison-dialog{width:1440px;max-width:100%;height:calc(100dvh - 56px);max-height:1100px;display:flex;flex-direction:column;overflow:hidden;background:white;border:1px solid #e2e8f0;border-radius:18px;box-shadow:0 24px 80px #0f172a33;color:#334155}
.comparison-header{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:24px 28px;border-bottom:1px solid #e2e8f0}
.comparison-title{display:flex;align-items:center;gap:14px;min-width:0}.comparison-title>div{min-width:0}.comparison-title-icon{display:grid;place-items:center;flex-shrink:0;width:46px;height:46px;border:1px solid #dbeafe;border-radius:12px;color:#2563eb;background:#eff6ff}.comparison-title-icon svg{width:24px;height:24px}.comparison-header h2{margin:0 0 5px;font-size:21px;font-weight:650;color:#0f172a}.comparison-header p{margin:0;font-size:13px;color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.comparison-close{width:34px;height:34px;border:1px solid #e2e8f0;border-radius:8px;background:white;font-size:24px;color:#64748b;flex-shrink:0;cursor:pointer}.comparison-close:hover{color:#0f172a;background:#f1f5f9}
.comparison-controls{display:flex;align-items:center;gap:16px;padding:20px 28px;background:#f8fafc;border-bottom:1px solid #e2e8f0}.comparison-controls label{flex:1;max-width:330px;font-size:12px;font-weight:500;color:#475569}.comparison-controls select{display:block;width:100%;height:40px;margin-top:8px;padding:9px 12px;border:1px solid #dbe3ef;border-radius:8px;color:#334155;background-color:white;font-family:inherit;font-size:13px;cursor:pointer}.comparison-arrow{padding-top:24px;color:#94a3b8}.comparison-links{margin-left:auto;display:flex;gap:10px;align-self:flex-end;white-space:nowrap}.comparison-action{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:40px;padding:9px 14px;border:1px solid #dbe3ef;border-radius:8px;background:white;color:#475569;text-decoration:none;font-size:12px;font-weight:600}.comparison-action:hover{background:#f1f5f9}.comparison-action.primary{background:#2563eb;border-color:#2563eb;color:white}.comparison-action.primary:hover{background:#1d4ed8}.comparison-action[aria-disabled=true]{opacity:.5;cursor:wait}
.comparison-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 28px;border-bottom:1px solid #e2e8f0;font-size:12px}.comparison-metrics{display:flex;align-items:center;gap:10px;color:#64748b}.comparison-total{display:flex;align-items:center;gap:7px;margin-right:8px}.comparison-metrics strong{color:#2563eb;font-size:22px;font-weight:700;line-height:1.2}.comparison-legend{padding:4px 10px;border:1px solid transparent;border-radius:6px;font-size:12px}.removed{background:#fff1f2;color:#be123c;border-color:#ffe4e6}.added{background:#ecfdf5;color:#047857;border-color:#d1fae5}.comparison-tools{display:flex;align-items:center;gap:10px;color:#64748b;font-variant-numeric:tabular-nums}.comparison-toggle{display:flex;align-items:center;gap:7px;margin-right:8px;padding:7px 10px;border-radius:7px;background:#f1f5f9;color:#475569;cursor:pointer}.comparison-tools input{accent-color:#2563eb;width:14px;height:14px;margin:0}.comparison-tools button{width:32px;height:32px;border:1px solid #dbe3ef;border-radius:7px;background:white;color:#475569;font-size:16px;cursor:pointer}.comparison-tools button:hover:not(:disabled){color:#2563eb;border-color:#93c5fd;background:#eff6ff}.comparison-tools button:disabled{opacity:.4;cursor:not-allowed}
.comparison-column-headings{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);background:#f8fafc;border-bottom:1px solid #e2e8f0}.comparison-column-headings>div{padding:14px 26px;display:flex;align-items:center;gap:9px;font-size:13px;font-weight:600;color:#334155}.comparison-column-headings>div+div{border-left:1px solid #e2e8f0}.comparison-column-headings small{margin-left:auto;color:#64748b;font-size:12px;font-weight:400}.comparison-dot{width:7px;height:7px;border-radius:50%}.before-dot{background:#e11d48}.after-dot{background:#059669}
.comparison-content{flex:1;min-height:0;overflow:auto;scrollbar-gutter:stable;background:white}.comparison-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);border-bottom:1px solid #e2e8f0}.comparison-row>div{padding:22px 26px;min-width:0;border-left:3px solid transparent}.comparison-row>div+div{border-left:1px solid #e2e8f0}.comparison-row p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.95;font-size:14px;color:#334155}.comparison-row .text-removed{background:#fff7f8}.comparison-row .text-added{background:#f3fcf8}.comparison-row .text-removed p{color:#9f2940}.comparison-row .text-added p{color:#16634d}.comparison-change-label{display:inline-flex;align-items:center;margin-bottom:12px;padding:3px 8px;border:1px solid #e2e8f0;border-radius:5px;background:white;font-size:11px;font-weight:500;color:#64748b}.text-removed .comparison-change-label{border-color:#fecdd3;color:#be123c;background:#fff1f2}.text-added .comparison-change-label{border-color:#a7f3d0;color:#047857;background:#ecfdf5}.comparison-row.is-focused>div:first-child{border-left-color:#2563eb}.comparison-row.is-focused .comparison-change-label{box-shadow:0 0 0 2px #2563eb12}.comparison-state{padding:70px 20px;text-align:center;color:#64748b;font-size:14px}.comparison-error{color:#b91c1c}.comparison-error button{display:block;margin:15px auto;padding:8px 14px;border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff;color:#2563eb;cursor:pointer}.comparison-identical{margin:0;padding:20px 26px;color:#047857;background:#ecfdf5;font-size:13px}
.comparison-footer{display:flex;justify-content:space-between;gap:16px;padding:15px 28px;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;background:#f8fafc}.comparison-header,.comparison-controls,.comparison-toolbar,.comparison-column-headings,.comparison-footer{flex-shrink:0}.comparison-overlay button:focus-visible,.comparison-overlay select:focus-visible,.comparison-overlay a:focus-visible{outline:2px solid #2563eb;outline-offset:3px}
@media(max-width:1100px){.comparison-controls{flex-wrap:wrap}.comparison-controls label{max-width:none}.comparison-links{width:100%;justify-content:flex-end}.comparison-action{min-height:36px;padding:7px 12px}}
@media(max-width:800px){.comparison-overlay{padding:10px}.comparison-dialog{height:calc(100dvh - 20px);border-radius:12px}.comparison-header,.comparison-controls{padding:16px}.comparison-title-icon{width:38px;height:38px}.comparison-header h2{font-size:18px}.comparison-controls{gap:10px}.comparison-controls label{min-width:120px}.comparison-links{justify-content:flex-start}.comparison-toolbar{padding:12px 16px;flex-wrap:wrap;gap:12px}.comparison-row>div{padding:16px 12px}.comparison-row p{font-size:13px}.comparison-footer{padding:12px 16px}.comparison-footer>span:last-child{display:none}.comparison-column-headings>div{padding:12px}.comparison-column-headings small{display:none}.comparison-tools{gap:7px}}
.comparison-documents{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);background:#f1f5f9}.comparison-documents iframe{height:100%;width:100%;min-height:0;border:0}.comparison-documents iframe+iframe{border-left:1px solid #dbe3ef}.comparison-identical{display:flex;align-items:center;gap:12px;flex-wrap:wrap;flex-shrink:0}.comparison-identical .comparison-action{padding:5px 10px;min-height:30px;color:#2563eb;border-color:#bfdbfe}.comparison-warning{flex-shrink:0;padding:10px 28px;margin:0;background:#fffbeb;color:#92400e;font-size:12px}.comparison-proposal-badge{font-size:11px;background:#fffbeb;color:#92400e;padding:4px 8px;border-radius:5px}.comparison-state{flex:1}.comparison-controls label{max-width:280px}.comparison-toolbar{flex-wrap:wrap}.comparison-controls{flex-wrap:wrap}.comparison-links{align-self:flex-end}
</style>
