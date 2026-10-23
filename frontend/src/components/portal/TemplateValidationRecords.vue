<script setup>
import {computed,ref,watch,onActivated} from 'vue';
import {useRoute,useRouter} from 'vue-router';
import {usePortalShell} from '../../stores/portal.js';
import TemplateCheckReport from './TemplateCheckReport.vue';
const route=useRoute(),router=useRouter(),shell=usePortalShell();
const rows=ref([]),total=ref(0),page=ref(1),pageSize=ref(10),q=ref(''),passed=ref('all'),loading=ref(false),error=ref(''),detail=ref(null);
const pages=computed(()=>Math.max(1,Math.ceil(total.value/pageSize.value)));
const checkLabels={pass:'符合规则',needs_changes:'需修改',needs_review:'需人工确认',incomplete:'检查不完整'};
const date=value=>new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
let sequence=0,detailSequence=0;
async function load(){const request=++sequence;loading.value=true;error.value='';try{const data=await shell.api('/api/template-validations?'+new URLSearchParams({page:page.value,page_size:pageSize.value,q:q.value,passed:passed.value}));if(request!==sequence)return;rows.value=data.items;total.value=data.total;if(page.value>pages.value)page.value=pages.value;}catch(e){if(request===sequence)error.value=e.message;}finally{if(request===sequence)loading.value=false;}}
async function loadDetail(){
  const request=++detailSequence;
  sequence++;
  detail.value=null;
  const validationId = route.params.id || route.query.validation;
  if(!validationId){await load();return;}
  loading.value=true;error.value='';
  try{const saved=await shell.api('/api/template-validations/'+encodeURIComponent(validationId));if(request===detailSequence)detail.value=saved;}
  catch(e){if(request===detailSequence)error.value=e.message;}
  finally{if(request===detailSequence)loading.value=false;}
}
function search(){if(page.value!==1)page.value=1;else load();}
watch(page,load);
watch([pageSize,passed],()=>{if(page.value!==1)page.value=1;else load();});
watch(()=>[route.params.id,route.query.validation],loadDetail,{immediate:true});
onActivated(loadDetail);
</script>
<template>
<div class="template-records">
  <p v-if="error" role="alert" class="records-error">{{error}} <button class="button" @click="loadDetail">重新加载</button></p>
  <TemplateCheckReport v-if="detail" :record="detail" @close="router.replace('/validation-records')"/>
  <template v-else>
    <div class="template-records-heading"><div><h1>模板核验记录</h1><p>每次校验自动保存计算结果，可查看统计和差异报告。</p></div><RouterLink to="/template-checks/new" class="button primary">＋ 新建模板核验</RouterLink></div>
    <div class="template-records-card"><form class="template-records-filters" @submit.prevent="search"><input v-model="q" class="field" aria-label="搜索模板核验记录" placeholder="搜索合同或模板名称"/><select v-model="passed" class="field" aria-label="核验结论"><option value="all">全部核验结论</option><option value="true">符合规则</option><option value="false">需进一步处理</option></select><button class="button" type="submit" :disabled="loading">搜索</button></form>
    <div class="template-records-table"><table><thead><tr><th>合同名称</th><th>基准模板</th><th>核验时间</th><th>核验结论</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{row.filename}}</td><td>{{row.template_name}}<small>发布版本 V{{row.version}}</small></td><td>{{date(row.created_at)}}</td><td><span :class="row.check_status === 'pass' ? 'passed-result' : row.check_status === 'needs_changes' ? 'failed-result' : 'review-result'">{{checkLabels[row.check_status] || '需进一步处理'}}</span></td><td><RouterLink :to="'/validation-records/'+row.id">查看报告</RouterLink></td></tr></tbody></table></div>
    <p v-if="!rows.length" class="template-records-empty">{{loading?'正在加载核验记录…':'暂无匹配的核验记录'}}</p>
    <nav class="template-records-pagination" aria-label="核验记录分页"><span role="status">共 {{total}} 条 · 第 {{page}} / {{pages}} 页</span><div><select v-model.number="pageSize" class="field" aria-label="核验记录每页条数" :disabled="loading"><option :value="10">10 条 / 页</option><option :value="20">20 条 / 页</option><option :value="50">50 条 / 页</option></select><button class="button" :disabled="loading||page===1" @click="page--">上一页</button><button class="button" :disabled="loading||page>=pages" @click="page++">下一页</button></div></nav></div>
  </template>
</div>
</template>
<style scoped>
.template-records-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:24px}.template-records-heading h1{font-size:22px;font-weight:700;color:#0f172a;margin:0 0 8px}.template-records-heading p{color:#64748b;font-size:12px}.template-records-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden}.template-records-filters{display:flex;gap:12px;padding:16px}.template-records-filters input{flex:1}.template-records-filters select{width:180px}.template-records-table{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px}th{background:#f8fafc;color:#64748b;font-weight:500;padding:14px}td{padding:16px 14px;border-top:1px solid #edf1f7;line-height:1.8;color:#475569;overflow-wrap:anywhere}td:first-child{max-width:300px}td small{display:block;color:#94a3b8;font-size:11px}td a{color:#2563eb;white-space:nowrap}.passed-result{color:#059669}.failed-result{color:#dc2626}.review-result{color:#a16207}.template-records-empty{padding:35px;text-align:center;font-size:13px;color:#94a3b8}.template-records-pagination{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 16px;border-top:1px solid #e2e8f0;font-size:12px;color:#64748b}.template-records-pagination>div{display:flex;align-items:center;gap:8px}.template-records-pagination select{width:125px}.records-error{padding:14px;background:#fef2f2;color:#dc2626;border-radius:8px;margin-bottom:18px;font-size:12px}@media(max-width:700px){.template-records-filters,.template-records-pagination{flex-wrap:wrap}.template-records-filters select{width:100%}table{min-width:700px}.template-records-heading{align-items:flex-start;flex-wrap:wrap}}
</style>
