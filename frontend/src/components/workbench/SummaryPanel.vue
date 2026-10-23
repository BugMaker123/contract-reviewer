<script setup>
import { computed } from 'vue';
const props = defineProps({context:{type:Object,required:true}});
const issues = computed(() => props.context.reviewIssues.value);
const handled = computed(() => issues.value.filter(issue => props.context.appliedIssueIds.value.includes(issue.id) || ['applied','rejected'].includes(props.context.workspace.decisions[issue.id])).length);
const levels = computed(() => [
  {id:'all',name:'全部意见'}, {id:'critical',name:'重大风险'},
  {id:'warning',name:'一般风险'}, {id:'info',name:'优化建议'},
  ...(issues.value.some(issue => issue.severity === 'favorable') ? [{id:'favorable',name:'有利条款'}] : [])
]);
const count = id => id === 'all' ? issues.value.length : issues.value.filter(issue => issue.severity === id).length;
const select = id => { props.context.severityFilter.value = props.context.severityFilter.value === id ? 'all' : id; };
</script>
<template>
  <section class="wb-integrated-overview" aria-label="风险概览">
    <div class="wb-nav-status-heading"><strong>风险概览</strong><span>{{ handled }} / {{ issues.length }} 项已处理</span></div>
    <div class="wb-risk-filter-tabs" role="group" aria-label="按风险等级筛选">
      <button v-for="level in levels" :key="level.id" type="button" :class="['risk-' + level.id, {active:context.severityFilter.value === level.id}]" :aria-pressed="context.severityFilter.value === level.id" @click="select(level.id)">
        <strong>{{ count(level.id) }}</strong><span>{{ level.name }}</span>
      </button>
    </div>
  </section>
</template>
