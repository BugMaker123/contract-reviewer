<script setup>
import { computed } from 'vue';
import PriorityReview from './PriorityReview.vue';
const props = defineProps({ context: { type: Object, required: true } });
const workspace = props.context.workspace;
const result = computed(() => workspace.run?.result);
const admissionLabel = computed(() => ({pass:'已通过',rejected:'未通过',needs_review:'待确认'})[result.value?.admission?.status]);
</script>
<template>
  <details class="wb-functional-overview">
    <summary>审查结论与执行记录</summary>
    <div class="overview-body">
      <div class="overview-version">
        <label for="overview-version-select">审查版本</label>
        <select id="overview-version-select" aria-label="审查历史版本" :value="workspace.run?.id || ''" @change="workspace.selectVersion($event.target.value)"><option value="">当前任务</option><option v-for="version in workspace.versions" :key="version.id" :value="version.id">第 {{ version.number }} 次 · {{ ({queued:'排队中',running:'审查中',completed:'审查完成',failed:'失败',interrupted:'中断'})[version.status] || version.status }}</option></select>
        <div v-if="result" class="overview-baseline"><span>本轮审查稿件</span><strong>{{workspace.run?.baseline_kind === 'accepted' ? '上一版已采纳修订稿' : '当时保存的正文快照'}}</strong></div>
      </div>
      <div v-if="workspace.task?.running_run" class="overview-notice"><p>审查已在后台执行或排队，刷新不会取消任务。</p><div class="overview-notice-actions"><button @click="context.startReview(workspace.task.running_run)">重新连接审查进度</button><button @click="context.cancelReview()">取消后台审查</button></div></div>
      <div v-if="['failed','interrupted'].includes(workspace.task?.status)" class="overview-notice"><p>上次审查失败或中断，已有结果保留。</p><div class="overview-notice-actions"><button @click="context.retryReview()" :disabled="context.retryingReview.value">{{ context.retryingReview.value ? '正在重试…' : '继续重试' }}</button></div></div>
      <template v-if="result">
        <div v-if="result.warning" class="overview-notice"><strong>审查提示</strong><p>{{result.warning}}</p></div>
        <section class="overview-section overview-admission"><header><h3>准入结论</h3><span v-if="admissionLabel" class="overview-status" :class="result.admission.status">{{admissionLabel}}</span></header><p>{{result.admission?.reason || '历史版本未记录'}}</p></section>
        <PriorityReview :context="context" :result="result"/>
        <section class="overview-section overview-verdict"><header><h3>审查总评</h3></header><p>{{result.summary?.verdict || '未记录'}}</p></section>
        <section class="overview-section overview-scope"><header><h3>审查范围</h3></header><p>{{result.coverage || '未记录覆盖范围'}}</p></section>
        <details class="overview-trace"><summary><span>执行计划与轨迹</span><small>{{result.audit_trace?.length||0}} 条记录</small></summary><ol><li v-for="(step,index) in (result.audit_trace || [])" :key="index">{{step.detail}}</li></ol><p v-if="!result.audit_trace?.length">本版本未记录执行轨迹。</p></details>
        <p v-if="context.resultStale.value" class="overview-notice">正文或条件已改变，请重新审查；以上结论属于旧版本。</p>
      </template>
    </div>
  </details>
</template>
