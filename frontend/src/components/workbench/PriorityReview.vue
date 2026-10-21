<script setup>
import { computed, unref } from 'vue';
const props = defineProps({ context: { type:Object, required:true }, result: Object });
const result = computed(() => props.result || unref(props.context.reviewResult) || {});
const snapshot = computed(() => props.context.workspace?.run?.input || {});
const hasRequirements = computed(() => !!(snapshot.value.focus?.trim() || snapshot.value.requirements?.length || snapshot.value.checklist?.items?.length || props.context.workspace?.run?.current_verification?.findings?.length));
const findings = computed(() => {
  const values = result.value.requirement_findings?.length ? result.value.requirement_findings : (result.value.checklist_findings || []).map(item => ({...item,text:item.requirement,source:'审查清单 · ' + (snapshot.value.checklist?.name || ''),origin:'checklist'}));
  const rank = {fail:0,needs_review:1,pass:2,not_applicable:3};
  return [...values].sort((a,b) => (rank[a.status] ?? 1) - (rank[b.status] ?? 1));
});
const counts = computed(() => ({pass:findings.value.filter(item => item.status==='pass').length,fail:findings.value.filter(item => item.status==='fail').length,pending:findings.value.filter(item => item.status==='needs_review').length}));
const references = computed(() => result.value.priority_review?.references || snapshot.value.references || []);
const background = computed(() => result.value.priority_review?.background || snapshot.value.background || '');
const label = (status) => ({pass:'符合',fail:'未满足',needs_review:'待确认',not_applicable:'不适用'})[status] || '待确认';
</script>
<template>
  <section v-if="hasRequirements || findings.length || background || references.length" class="wb-priority-review" aria-label="重点要求核验">
    <header><h3>重点要求核验 <span>{{ findings.length }} 项</span></h3><small>本轮原文</small></header>
    <p class="wb-priority-scope">本轮审查重点的逐项核对结果。</p>
    <p v-if="context.resultStale.value" class="wb-priority-stale">正文或条件已修改，以下为旧版本结论。</p>
    <div v-if="findings.length" class="wb-priority-counts"><span class="is-fail">未满足 {{ counts.fail }}</span><span class="is-pending">待确认 {{ counts.pending }}</span><span class="is-pass">符合 {{ counts.pass }}</span></div>
    <template v-for="(item,index) in findings.slice(0,3)" :key="item.id">
      <details class="wb-priority-item" :class="'priority-' + item.status">
        <summary><span class="wb-priority-status">{{ label(item.status) }}</span><span>{{ item.text }}</span></summary>
        <p class="wb-priority-source">{{ item.source }}</p><p>{{ item.explanation }}</p>
        <blockquote v-if="item.evidence">{{ item.evidence }}</blockquote>
        <p v-if="item.conflict_with?.length" class="wb-priority-stale">与其他要求冲突，须先明确条件再重新审查。</p>
      </details>
    </template>
    <details v-if="findings.length > 3" class="wb-priority-rest"><summary>查看其余 {{ findings.length - 3 }} 项重点要求</summary>
      <details v-for="item in findings.slice(3)" :key="item.id" class="wb-priority-item" :class="'priority-' + item.status"><summary><span class="wb-priority-status">{{ label(item.status) }}</span><span>{{ item.text }}</span></summary><p class="wb-priority-source">{{ item.source }}</p><p>{{ item.explanation }}</p><blockquote v-if="item.evidence">{{ item.evidence }}</blockquote><p v-if="item.conflict_with?.length" class="wb-priority-stale">要求存在冲突，请明确条件。</p></details>
    </details>
    <details v-if="background || references.length" class="wb-priority-context"><summary>审查依据 <span v-if="background">交易背景</span><span v-if="references.length">{{ references.length }} 份资料</span></summary><p v-if="background">{{ background }}</p><p v-for="ref in references" :key="ref.name">{{ ref.kind==='policy' ? '公司制度' : '参考资料' }}：{{ ref.name }}</p><small>背景与资料作为条件及证据参与审查，不代表已写入合同。</small></details>
  </section>
</template>
