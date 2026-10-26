<script setup>
import {ref,computed,onActivated} from 'vue';
import ReviewIcon from '../components/portal/ReviewIcon.vue';
import {usePortalShell} from '../stores/portal.js';
const shell=usePortalShell();
const rows=ref([]),total=ref(0),page=ref(1),q=ref(''),busy=ref(false),error=ref('');
const pages=computed(()=>Math.max(1,Math.ceil(total.value/10)));
const date=v=>new Date(v).toLocaleString('zh-CN',{hour12:false,timeZone:'Asia/Shanghai'});
async function load(next=page.value){
  if(busy.value)return;
  busy.value=true;error.value='';
  try{
    const data=await shell.api('/api/contract-drafts?'+new URLSearchParams({page:next,q:q.value}));
    rows.value=data.items;total.value=data.total;page.value=next;
    if(next>pages.value){busy.value=false;await load(pages.value);}
  }catch(e){error.value=e.message;}finally{busy.value=false;}
}
const changePage=next=>load(next);
onActivated(()=>load());
</script>
<template>
  <div class="drafting-page drafting-list">
    <header class="drafting-heading"><div><h1>合同起草</h1><p>管理已生成的合同草稿，继续编辑、导出或发起审查。</p></div><RouterLink v-can="'drafting.create'" to="/drafting/new" class="button primary"><ReviewIcon name="plus"/>新建起草</RouterLink></header>
    <p v-if="error" class="drafting-error" role="alert">{{error}} <button class="button" :disabled="busy" @click="load()">重新加载</button></p>
    <section class="drafting-card drafting-history">
      <div class="drafting-history-heading"><div class="section-title"><span class="section-icon"><ReviewIcon name="records"/></span><div><h2>起草记录 <span class="history-count">{{total}}</span></h2><p>每次生成独立保存，随时打开继续编辑</p></div></div><form @submit.prevent="changePage(1)"><div class="search-field"><ReviewIcon name="search"/><input v-model="q" aria-label="搜索起草记录" placeholder="搜索合同名称" maxlength="200"/></div><button class="button" :disabled="busy">搜索</button></form></div>
      <div class="history-table-wrap"><table><thead><tr><th>合同名称</th><th>合同类型 / 起草立场</th><th>更新时间</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td><div class="history-name"><ReviewIcon name="document"/><strong>{{row.title}}</strong></div></td><td><span class="pill">{{row.brief.contract_type}}</span><span class="history-perspective">{{row.brief.perspective}}</span></td><td class="history-date">{{date(row.updated_at)}}</td><td><RouterLink class="text-button" :to="'/drafting/'+row.id+'/edit'">编辑草稿<ReviewIcon name="arrow"/></RouterLink></td></tr><tr v-if="!rows.length"><td colspan="4" class="drafting-history-empty"><ReviewIcon :name="q?'search':'records'"/><strong>{{busy?'正在读取记录…':q?'没有找到匹配的草稿':'暂无起草记录'}}</strong><p>{{q?'请调整合同名称关键词后重新搜索':'新建起草并生成合同后，您可以在这里继续编辑、导出或送审'}}</p><RouterLink v-if="!q&&!busy" v-can="'drafting.create'" to="/drafting/new" class="button primary list-empty-action">新建起草</RouterLink></td></tr></tbody></table></div>
      <nav class="drafting-pagination" aria-label="起草记录分页"><span>共 {{total}} 条 · 第 {{page}} / {{pages}} 页</span><div><button class="button" :disabled="busy||page<=1" @click="changePage(page-1)">上一页</button><button class="button" :disabled="busy||page>=pages" @click="changePage(page+1)">下一页</button></div></nav>
    </section>
  </div>
</template>
<style scoped src="../styles/contract-drafting.css"></style>
